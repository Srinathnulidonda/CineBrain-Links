# server/app/routes/links.py

"""
Link management routes.
Handles CRUD operations for shortened URLs.
"""

from datetime import datetime
from typing import Optional

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db, limiter
from app.models.link import Link
from app.services.redis_service import RedisService
from app.utils.validators import URLValidator, InputValidator
from app.utils.slug import SlugGenerator

links_bp = Blueprint("links", __name__)


@links_bp.route("", methods=["POST"])
@jwt_required()
@limiter.limit("30 per minute")
def create_link():
    """
    Create a new shortened link.
    
    Request body:
        - url: Original URL to shorten (required)
        - custom_slug: Custom slug (optional)
        - expires_at: Expiration datetime ISO format (optional)
        - title: Link title (optional)
        - description: Link description (optional)
    
    Returns:
        Created link data
    """
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    
    original_url = data.get("url", "").strip()
    custom_slug = data.get("custom_slug", "").strip() if data.get("custom_slug") else None
    expires_at_str = data.get("expires_at")
    title = data.get("title", "").strip() if data.get("title") else None
    description = data.get("description", "").strip() if data.get("description") else None
    
    # Validate URL
    is_valid, normalized_url, error = URLValidator.validate(original_url)
    if not is_valid:
        return jsonify({"error": error}), 400
    
    # Handle custom slug or generate one
    if custom_slug:
        is_valid, normalized_slug, error = InputValidator.validate_slug(custom_slug)
        if not is_valid:
            return jsonify({"error": error}), 400
        
        # Check availability
        if not SlugGenerator.is_available(normalized_slug):
            return jsonify({"error": "This slug is already taken"}), 409
        
        slug = normalized_slug
    else:
        # Auto-generate slug
        generator = SlugGenerator()
        slug = generator.generate_unique()
        
        if not slug:
            return jsonify({"error": "Failed to generate unique slug. Please try again."}), 500
    
    # Parse expiration date if provided
    expires_at: Optional[datetime] = None
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            
            # Ensure expiration is in the future
            if expires_at <= datetime.utcnow():
                return jsonify({"error": "Expiration date must be in the future"}), 400
                
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid expiration date format. Use ISO 8601 format."}), 400
    
    # Sanitize optional fields
    if title:
        title = InputValidator.sanitize_string(title, max_length=255)
    if description:
        description = InputValidator.sanitize_string(description, max_length=1000)
    
    try:
        # Create link
        link = Link(
            user_id=user_id,
            slug=slug,
            original_url=normalized_url,
            expires_at=expires_at,
            title=title,
            description=description
        )
        
        db.session.add(link)
        db.session.commit()
        
        # Cache the new link
        try:
            redis_service = RedisService()
            redis_service.cache_link(slug, link.to_cache_dict())
        except Exception as e:
            current_app.logger.warning(f"Failed to cache new link: {e}")
        
        base_url = current_app.config.get("BASE_URL", "")
        
        return jsonify({
            "message": "Link created successfully",
            "link": link.to_dict(include_short_url=True, base_url=base_url)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Link creation error: {e}")
        return jsonify({"error": "Failed to create link"}), 500


@links_bp.route("", methods=["GET"])
@jwt_required()
def get_links():
    """
    Get all links for the authenticated user.
    
    Query parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - is_active: Filter by active status (optional)
        - sort: Sort field (created_at, clicks, default: created_at)
        - order: Sort order (asc, desc, default: desc)
    
    Returns:
        Paginated list of links
    """
    user_id = get_jwt_identity()
    
    # Pagination parameters
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    
    # Filter parameters
    is_active = request.args.get("is_active", type=lambda x: x.lower() == "true")
    
    # Sort parameters
    sort_field = request.args.get("sort", "created_at")
    sort_order = request.args.get("order", "desc")
    
    # Validate sort field
    allowed_sort_fields = {"created_at", "clicks", "expires_at", "slug"}
    if sort_field not in allowed_sort_fields:
        sort_field = "created_at"
    
    # Build query
    query = Link.query.filter_by(user_id=user_id)
    
    if is_active is not None:
        query = query.filter_by(is_active=is_active)
    
    # Apply sorting
    sort_column = getattr(Link, sort_field)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    base_url = current_app.config.get("BASE_URL", "")
    
    links = [link.to_dict(include_short_url=True, base_url=base_url) 
             for link in pagination.items]
    
    return jsonify({
        "links": links,
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages,
            "total_items": pagination.total,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev
        }
    }), 200


@links_bp.route("/<link_id>", methods=["GET"])
@jwt_required()
def get_link(link_id: str):
    """
    Get a specific link by ID.
    
    Returns:
        Link data
    """
    user_id = get_jwt_identity()
    
    link = Link.query.filter_by(id=link_id, user_id=user_id).first()
    
    if not link:
        return jsonify({"error": "Link not found"}), 404
    
    base_url = current_app.config.get("BASE_URL", "")
    
    return jsonify({
        "link": link.to_dict(include_short_url=True, base_url=base_url)
    }), 200


@links_bp.route("/<link_id>", methods=["PUT"])
@jwt_required()
def update_link(link_id: str):
    """
    Update a link.
    
    Request body:
        - is_active: Enable/disable link (optional)
        - expires_at: New expiration datetime (optional, null to remove)
        - title: New title (optional)
        - description: New description (optional)
    
    Returns:
        Updated link data
    """
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    
    link = Link.query.filter_by(id=link_id, user_id=user_id).first()
    
    if not link:
        return jsonify({"error": "Link not found"}), 404
    
    try:
        # Update is_active
        if "is_active" in data:
            link.is_active = bool(data["is_active"])
        
        # Update expiration
        if "expires_at" in data:
            if data["expires_at"] is None:
                link.expires_at = None
            else:
                try:
                    expires_at = datetime.fromisoformat(
                        data["expires_at"].replace("Z", "+00:00")
                    )
                    if expires_at <= datetime.utcnow():
                        return jsonify({
                            "error": "Expiration date must be in the future"
                        }), 400
                    link.expires_at = expires_at
                except (ValueError, TypeError):
                    return jsonify({
                        "error": "Invalid expiration date format"
                    }), 400
        
        # Update title
        if "title" in data:
            link.title = InputValidator.sanitize_string(
                data["title"] or "", max_length=255
            ) or None
        
        # Update description
        if "description" in data:
            link.description = InputValidator.sanitize_string(
                data["description"] or "", max_length=1000
            ) or None
        
        db.session.commit()
        
        # Update cache
        try:
            redis_service = RedisService()
            redis_service.cache_link(link.slug, link.to_cache_dict())
        except Exception as e:
            current_app.logger.warning(f"Failed to update link cache: {e}")
        
        base_url = current_app.config.get("BASE_URL", "")
        
        return jsonify({
            "message": "Link updated successfully",
            "link": link.to_dict(include_short_url=True, base_url=base_url)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Link update error: {e}")
        return jsonify({"error": "Failed to update link"}), 500


@links_bp.route("/<link_id>", methods=["DELETE"])
@jwt_required()
def delete_link(link_id: str):
    """
    Delete a link.
    
    Returns:
        Success message
    """
    user_id = get_jwt_identity()
    
    link = Link.query.filter_by(id=link_id, user_id=user_id).first()
    
    if not link:
        return jsonify({"error": "Link not found"}), 404
    
    slug = link.slug
    
    try:
        db.session.delete(link)
        db.session.commit()
        
        # Invalidate cache
        try:
            redis_service = RedisService()
            redis_service.invalidate_link_cache(slug)
        except Exception as e:
            current_app.logger.warning(f"Failed to invalidate link cache: {e}")
        
        return jsonify({"message": "Link deleted successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Link deletion error: {e}")
        return jsonify({"error": "Failed to delete link"}), 500


@links_bp.route("/<link_id>/toggle", methods=["POST"])
@jwt_required()
def toggle_link(link_id: str):
    """
    Toggle link active status.
    
    Returns:
        Updated link data
    """
    user_id = get_jwt_identity()
    
    link = Link.query.filter_by(id=link_id, user_id=user_id).first()
    
    if not link:
        return jsonify({"error": "Link not found"}), 404
    
    try:
        link.is_active = not link.is_active
        db.session.commit()
        
        # Update cache
        try:
            redis_service = RedisService()
            redis_service.cache_link(link.slug, link.to_cache_dict())
        except Exception as e:
            current_app.logger.warning(f"Failed to update link cache: {e}")
        
        base_url = current_app.config.get("BASE_URL", "")
        
        return jsonify({
            "message": f"Link {'enabled' if link.is_active else 'disabled'} successfully",
            "link": link.to_dict(include_short_url=True, base_url=base_url)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Link toggle error: {e}")
        return jsonify({"error": "Failed to toggle link"}), 500


@links_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_stats():
    """
    Get link statistics for the authenticated user.
    
    Returns:
        Statistics summary
    """
    user_id = get_jwt_identity()
    
    try:
        # Total links
        total_links = Link.query.filter_by(user_id=user_id).count()
        
        # Active links
        active_links = Link.query.filter_by(user_id=user_id, is_active=True).count()
        
        # Total clicks
        total_clicks = db.session.query(
            db.func.sum(Link.clicks)
        ).filter_by(user_id=user_id).scalar() or 0
        
        # Links expiring soon (next 7 days)
        from datetime import timedelta
        expiring_soon = Link.query.filter(
            Link.user_id == user_id,
            Link.expires_at.isnot(None),
            Link.expires_at <= datetime.utcnow() + timedelta(days=7),
            Link.expires_at > datetime.utcnow()
        ).count()
        
        # Top performing links (by clicks)
        base_url = current_app.config.get("BASE_URL", "")
        top_links = Link.query.filter_by(
            user_id=user_id
        ).order_by(Link.clicks.desc()).limit(5).all()
        
        return jsonify({
            "stats": {
                "total_links": total_links,
                "active_links": active_links,
                "inactive_links": total_links - active_links,
                "total_clicks": int(total_clicks),
                "expiring_soon": expiring_soon
            },
            "top_links": [
                link.to_dict(include_short_url=True, base_url=base_url)
                for link in top_links
            ]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Stats error: {e}")
        return jsonify({"error": "Failed to get statistics"}), 500


@links_bp.route("/check-slug", methods=["GET"])
@jwt_required()
def check_slug_availability():
    """
    Check if a slug is available.
    
    Query parameters:
        - slug: Slug to check
    
    Returns:
        Availability status
    """
    slug = request.args.get("slug", "").strip().lower()
    
    if not slug:
        return jsonify({"error": "Slug is required"}), 400
    
    # Validate slug format
    is_valid, _, error = InputValidator.validate_slug(slug)
    if not is_valid:
        return jsonify({
            "available": False,
            "error": error
        }), 200
    
    is_available = SlugGenerator.is_available(slug)
    
    return jsonify({
        "slug": slug,
        "available": is_available
    }), 200