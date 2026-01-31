# server/app/routes/redirect.py

"""
URL redirect routes.
Handles high-performance URL redirection with caching.
"""

import logging
from datetime import datetime
from threading import Thread

from flask import Blueprint, redirect, jsonify, current_app, request

from app.extensions import db
from app.models.link import Link
from app.services.redis_service import RedisService

redirect_bp = Blueprint("redirect", __name__)
logger = logging.getLogger(__name__)


def increment_click_async(app, slug: str) -> None:
    """
    Increment click count asynchronously.
    
    Args:
        app: Flask application context
        slug: Link slug to increment
    """
    with app.app_context():
        try:
            link = Link.query.filter_by(slug=slug).first()
            if link:
                link.clicks += 1
                db.session.commit()
                logger.debug(f"Click incremented for {slug}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to increment click for {slug}: {e}")


def increment_click_count(slug: str) -> None:
    """
    Queue click increment for async processing.
    Uses threading to avoid blocking the redirect response.
    
    Args:
        slug: Link slug to increment
    """
    app = current_app._get_current_object()
    thread = Thread(target=increment_click_async, args=(app, slug))
    thread.daemon = True
    thread.start()


@redirect_bp.route("/<slug>", methods=["GET"])
def redirect_short_url(slug: str):
    """
    Redirect short URL to original URL.
    
    High-performance redirect with:
    1. Redis cache lookup first
    2. PostgreSQL fallback on cache miss
    3. Async click counting
    4. Proper handling of expired/disabled links
    
    Returns:
        302 redirect to original URL or error response
    """
    slug = slug.lower().strip()
    
    if not slug:
        return jsonify({"error": "Invalid URL"}), 400
    
    # Check reserved slugs to avoid conflicts
    reserved = current_app.config.get("RESERVED_SLUGS", set())
    if slug in reserved:
        return jsonify({"error": "Not found"}), 404
    
    redis_service = None
    link_data = None
    
    # Step 1: Try Redis cache
    try:
        redis_service = RedisService()
        link_data = redis_service.get_cached_link(slug)
        
        if link_data:
            logger.debug(f"Cache hit for {slug}")
            
            # Validate cached data
            if not link_data.get("is_active", True):
                return jsonify({
                    "error": "This link has been disabled"
                }), 410  # Gone
            
            # Check expiration (double-check since cache might be stale)
            if link_data.get("expires_at"):
                expires_at = datetime.fromisoformat(link_data["expires_at"])
                if datetime.utcnow() > expires_at:
                    # Invalidate stale cache
                    redis_service.invalidate_link_cache(slug)
                    return jsonify({
                        "error": "This link has expired"
                    }), 410  # Gone
            
            # Increment click count asynchronously
            increment_click_count(slug)
            
            # Perform redirect
            return redirect(link_data["original_url"], code=302)
            
    except Exception as e:
        logger.warning(f"Redis error for {slug}: {e}")
        # Continue to database fallback
    
    # Step 2: Cache miss - Query database
    logger.debug(f"Cache miss for {slug}, querying database")
    
    link = Link.query.filter_by(slug=slug).first()
    
    if not link:
        return jsonify({"error": "Link not found"}), 404
    
    # Check if link is active
    if not link.is_active:
        return jsonify({
            "error": "This link has been disabled"
        }), 410  # Gone
    
    # Check if link has expired
    if link.is_expired:
        return jsonify({
            "error": "This link has expired"
        }), 410  # Gone
    
    # Step 3: Cache the link data for future requests
    if redis_service:
        try:
            redis_service.cache_link(slug, link.to_cache_dict())
        except Exception as e:
            logger.warning(f"Failed to cache link {slug}: {e}")
    
    # Step 4: Increment click count asynchronously
    increment_click_count(slug)
    
    # Step 5: Perform redirect
    return redirect(link.original_url, code=302)


@redirect_bp.route("/<slug>/preview", methods=["GET"])
def preview_short_url(slug: str):
    """
    Preview a short URL without redirecting.
    Shows link metadata instead of redirecting.
    
    Returns:
        Link preview data
    """
    slug = slug.lower().strip()
    
    if not slug:
        return jsonify({"error": "Invalid URL"}), 400
    
    link = Link.query.filter_by(slug=slug).first()
    
    if not link:
        return jsonify({"error": "Link not found"}), 404
    
    if not link.is_active:
        return jsonify({
            "error": "This link has been disabled"
        }), 410
    
    if link.is_expired:
        return jsonify({
            "error": "This link has expired"
        }), 410
    
    base_url = current_app.config.get("BASE_URL", "")
    
    return jsonify({
        "preview": {
            "slug": link.slug,
            "short_url": f"{base_url}/{link.slug}",
            "original_url": link.original_url,
            "title": link.title,
            "description": link.description,
            "created_at": link.created_at.isoformat(),
            "expires_at": link.expires_at.isoformat() if link.expires_at else None
        }
    }), 200


@redirect_bp.route("/<slug>/qr", methods=["GET"])
def get_qr_code(slug: str):
    """
    Generate QR code for a short URL.
    Returns QR code data URL.
    
    Note: Requires 'qrcode' package with PIL support.
    """
    try:
        import qrcode
        import io
        import base64
    except ImportError:
        return jsonify({
            "error": "QR code generation not available"
        }), 501
    
    slug = slug.lower().strip()
    
    link = Link.query.filter_by(slug=slug).first()
    
    if not link:
        return jsonify({"error": "Link not found"}), 404
    
    if not link.is_accessible:
        return jsonify({
            "error": "This link is not accessible"
        }), 410
    
    base_url = current_app.config.get("BASE_URL", "")
    short_url = f"{base_url}/{link.slug}"
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(short_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return jsonify({
        "qr_code": f"data:image/png;base64,{img_base64}",
        "short_url": short_url
    }), 200