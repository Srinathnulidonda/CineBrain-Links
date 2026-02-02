# server/app/routes/health.py

import logging

from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.link import Link
from app.models.link_health import LinkHealthCheck
from app.services.health_service import HealthService
from app.utils.base_url import get_public_base_url

health_bp = Blueprint("health", __name__)
logger = logging.getLogger(__name__)


def api_response():
    return current_app.api_response


@health_bp.route("/links/<link_id>/check", methods=["POST"])
@jwt_required()
def check_link_health(link_id: str):
    user_id = get_jwt_identity()

    link = Link.query.filter_by(id=link_id, user_id=user_id, is_deleted=False).first()

    if not link:
        return api_response().error("Link not found", 404, "NOT_FOUND")

    try:
        result = HealthService.check_url(link.original_url)

        health_check = LinkHealthCheck(
            link_id=link.id,
            is_healthy=result["is_healthy"],
            status_code=result.get("status_code"),
            response_time_ms=result.get("response_time_ms"),
            error_message=result.get("error_message")
        )

        db.session.add(health_check)

        link.last_checked_at = health_check.checked_at
        link.last_check_status = result.get("status_code")
        link.is_broken = not result["is_healthy"]

        db.session.commit()

        logger.info(f"Health check for link {link_id}: {'healthy' if result['is_healthy'] else 'broken'}")

        return api_response().success(data={
            "health_check": health_check.to_dict(),
            "is_broken": link.is_broken
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Health check failed: {e}")
        return api_response().error("Health check failed", 500)


@health_bp.route("/links/<link_id>/history", methods=["GET"])
@jwt_required()
def get_health_history(link_id: str):
    user_id = get_jwt_identity()

    link = Link.query.filter_by(id=link_id, user_id=user_id, is_deleted=False).first()

    if not link:
        return api_response().error("Link not found", 404, "NOT_FOUND")

    limit = request.args.get("limit", 20, type=int)
    limit = min(limit, 100)

    checks = LinkHealthCheck.query.filter_by(link_id=link_id).order_by(
        LinkHealthCheck.checked_at.desc()
    ).limit(limit).all()

    return api_response().success(data={
        "health_checks": [c.to_dict() for c in checks],
        "last_checked_at": link.last_checked_at.isoformat() if link.last_checked_at else None,
        "is_broken": link.is_broken
    })


@health_bp.route("/broken", methods=["GET"])
@jwt_required()
def get_broken_links():
    user_id = get_jwt_identity()
    base_url = get_public_base_url()

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = Link.query.filter_by(
        user_id=user_id,
        is_deleted=False,
        is_broken=True
    ).order_by(Link.last_checked_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return api_response().success(data={
        "links": [l.to_dict(base_url=base_url) for l in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages,
            "total_items": pagination.total
        }
    })


@health_bp.route("/check-all", methods=["POST"])
@jwt_required()
def check_all_links():
    user_id = get_jwt_identity()

    from datetime import datetime, timedelta

    stale_threshold = datetime.utcnow() - timedelta(hours=24)

    links = Link.query.filter(
        Link.user_id == user_id,
        Link.is_deleted == False,
        db.or_(
            Link.last_checked_at.is_(None),
            Link.last_checked_at < stale_threshold
        )
    ).limit(50).all()

    if not links:
        return api_response().success(
            data={"checked": 0, "broken": 0},
            message="All links have been checked recently"
        )

    checked = 0
    broken = 0

    for link in links:
        try:
            result = HealthService.check_url(link.original_url)

            health_check = LinkHealthCheck(
                link_id=link.id,
                is_healthy=result["is_healthy"],
                status_code=result.get("status_code"),
                response_time_ms=result.get("response_time_ms"),
                error_message=result.get("error_message")
            )
            db.session.add(health_check)

            link.last_checked_at = health_check.checked_at
            link.last_check_status = result.get("status_code")
            link.is_broken = not result["is_healthy"]

            checked += 1
            if link.is_broken:
                broken += 1

        except Exception as e:
            logger.warning(f"Health check failed for {link.id}: {e}")

    db.session.commit()

    return api_response().success(data={
        "checked": checked,
        "broken": broken
    })
