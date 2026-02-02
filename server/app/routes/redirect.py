# server/app/routes/redirect.py

import logging
from datetime import datetime
from threading import Thread
from urllib.parse import urlparse

from flask import Blueprint, redirect, jsonify, current_app, request

from app.extensions import db
from app.models.link import Link, LinkType
from app.models.link_click import LinkClick
from app.services.redis_service import RedisService
from app.services.click_service import ClickService
from app.utils.base_url import get_public_base_url

redirect_bp = Blueprint("redirect", __name__)
logger = logging.getLogger(__name__)

SAFE_SCHEMES = {"http", "https"}


def is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme.lower() in SAFE_SCHEMES
    except Exception:
        return False


def record_click_async(app, link_id: str, slug: str, request_data: dict) -> None:
    with app.app_context():
        try:
            link = Link.query.get(link_id)
            if link and link.click_tracking_enabled:
                link.increment_clicks()

                click = LinkClick(
                    link_id=link_id,
                    ip_hash=request_data.get("ip_hash"),
                    user_agent=request_data.get("user_agent"),
                    referrer=request_data.get("referrer"),
                    country_code=request_data.get("country_code"),
                    device_type=request_data.get("device_type"),
                    browser=request_data.get("browser"),
                    os=request_data.get("os"),
                )
                db.session.add(click)
                db.session.commit()
            elif link:
                link.clicks += 1
                link.last_clicked_at = datetime.utcnow()
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.debug(f"Click recording failed for {slug}: {e}")


def queue_click(link_id: str, slug: str) -> None:
    app = current_app._get_current_object()

    request_data = ClickService.parse_request(request)

    Thread(
        target=record_click_async,
        args=(app, link_id, slug, request_data),
        daemon=True
    ).start()


@redirect_bp.route("/<slug>", methods=["GET"])
def redirect_to_url(slug: str):
    slug = slug.lower().strip()

    if not slug or len(slug) > 50:
        return jsonify({"success": False, "error": {"message": "Invalid link"}}), 400

    reserved = current_app.config.get("RESERVED_SLUGS", set())
    if slug in reserved:
        return jsonify({"success": False, "error": {"message": "Not found"}}), 404

    redis_service = None

    try:
        redis_service = RedisService()
        cached = redis_service.get_cached_link(slug)

        if cached:
            if cached.get("is_deleted"):
                return jsonify({"success": False, "error": {"message": "Link not found"}}), 404

            if not cached.get("is_active", True):
                return jsonify({"success": False, "error": {"message": "This link has been disabled"}}), 410

            if cached.get("expires_at"):
                try:
                    expires = datetime.fromisoformat(cached["expires_at"])
                    if datetime.utcnow() > expires:
                        redis_service.invalidate_link_cache(slug)

                        expired_redirect = cached.get("expired_redirect_url")
                        if expired_redirect and is_safe_url(expired_redirect):
                            return redirect(expired_redirect, code=302)

                        return jsonify({"success": False, "error": {"message": "This link has expired"}}), 410
                except ValueError:
                    pass

            original_url = cached["original_url"]

            if not is_safe_url(original_url):
                logger.warning(f"Blocked unsafe redirect: {slug}")
                return jsonify({"success": False, "error": {"message": "Invalid destination"}}), 400

            link = Link.query.filter_by(slug=slug).first()
            if link:
                queue_click(link.id, slug)

            return redirect(original_url, code=302)

    except Exception as e:
        logger.debug(f"Redis unavailable: {e}")

    link = Link.query.filter_by(slug=slug, link_type=LinkType.SHORTENED).first()

    if not link:
        return jsonify({"success": False, "error": {"message": "Link not found"}}), 404

    if link.is_deleted:
        return jsonify({"success": False, "error": {"message": "Link not found"}}), 404

    if not link.is_active:
        return jsonify({"success": False, "error": {"message": "This link has been disabled"}}), 410

    if link.is_expired:
        if link.expired_redirect_url and is_safe_url(link.expired_redirect_url):
            return redirect(link.expired_redirect_url, code=302)
        return jsonify({"success": False, "error": {"message": "This link has expired"}}), 410

    if not is_safe_url(link.original_url):
        logger.warning(f"Blocked unsafe redirect: {slug}")
        return jsonify({"success": False, "error": {"message": "Invalid destination"}}), 400

    if redis_service:
        try:
            redis_service.cache_link(slug, link.to_cache_dict())
        except Exception:
            pass

    queue_click(link.id, slug)
    return redirect(link.original_url, code=302)


@redirect_bp.route("/<slug>/preview", methods=["GET"])
def preview_link(slug: str):
    slug = slug.lower().strip()
    base_url = get_public_base_url()

    link = Link.query.filter_by(slug=slug, link_type=LinkType.SHORTENED).first()

    if not link or link.is_deleted:
        return jsonify({"success": False, "error": {"message": "Link not found"}}), 404

    if not link.is_active:
        return jsonify({"success": False, "error": {"message": "This link has been disabled"}}), 410

    if link.is_expired:
        return jsonify({"success": False, "error": {"message": "This link has expired"}}), 410

    return jsonify({
        "success": True,
        "data": {
            "slug": link.slug,
            "short_url": f"{base_url}/{link.slug}",
            "original_url": link.original_url,
            "title": link.title,
            "description": link.notes,
            "og_title": link.og_title,
            "og_description": link.og_description,
            "og_image": link.og_image,
            "favicon_url": link.favicon_url,
            "clicks": link.clicks,
            "created_at": link.created_at.isoformat()
        }
    }), 200


@redirect_bp.route("/<slug>/qr", methods=["GET"])
def get_qr_code(slug: str):
    try:
        import qrcode
        import io
        import base64
    except ImportError:
        return jsonify({"success": False, "error": {"message": "QR generation unavailable"}}), 501

    base_url = get_public_base_url()
    link = Link.query.filter_by(slug=slug.lower(), link_type=LinkType.SHORTENED).first()

    if not link or not link.is_accessible or link.is_deleted:
        return jsonify({"success": False, "error": {"message": "Link not accessible"}}), 404

    short_url = f"{base_url}/{link.slug}"

    size = request.args.get("size", "medium")
    size_map = {"small": 5, "medium": 10, "large": 15}
    box_size = size_map.get(size, 10)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=4
    )
    qr.add_data(short_url)
    qr.make(fit=True)

    fg_color = request.args.get("fg", "black")
    bg_color = request.args.get("bg", "white")

    img = qr.make_image(fill_color=fg_color, back_color=bg_color)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    download = request.args.get("download", "false").lower() == "true"
    if download:
        from flask import send_file
        return send_file(
            buffer,
            mimetype="image/png",
            as_attachment=True,
            download_name=f"{link.slug}-qr.png"
        )

    img_b64 = base64.b64encode(buffer.getvalue()).decode()

    return jsonify({
        "success": True,
        "data": {
            "qr_code": f"data:image/png;base64,{img_b64}",
            "short_url": short_url,
            "size": size
        }
    }), 200
