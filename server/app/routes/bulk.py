# server/app/routes/bulk.py

import logging
from datetime import datetime

from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.link import Link
from app.models.tag import Tag, LinkTag
from app.models.folder import Folder
from app.models.activity_log import ActivityType
from app.services.activity_service import ActivityService
from app.services.redis_service import RedisService
from app.utils.base_url import get_public_base_url

bulk_bp = Blueprint("bulk", __name__)
logger = logging.getLogger(__name__)


def api_response():
    return current_app.api_response


def validate_link_ids(link_ids: list, user_id: str) -> list:
    if not link_ids or not isinstance(link_ids, list):
        return []
    return Link.query.filter(
        Link.id.in_(link_ids),
        Link.user_id == user_id,
        Link.is_deleted == False
    ).all()


@bulk_bp.route("/move", methods=["POST"])
@jwt_required()
def bulk_move():
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    link_ids = data.get("link_ids", [])
    folder_id = data.get("folder_id")

    if not link_ids:
        return api_response().error("No links specified", 400)

    if folder_id:
        folder = Folder.query.filter_by(id=folder_id, user_id=user_id).first()
        if not folder:
            return api_response().error("Folder not found", 404)

    links = validate_link_ids(link_ids, user_id)

    if not links:
        return api_response().error("No valid links found", 404)

    try:
        for link in links:
            link.folder_id = folder_id

        db.session.commit()

        ActivityService.log(
            user_id=user_id,
            activity_type=ActivityType.BULK_OPERATION,
            resource_type="links",
            metadata={"operation": "move", "count": len(links), "folder_id": folder_id}
        )

        return api_response().success(
            data={"affected": len(links)},
            message=f"Moved {len(links)} links"
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Bulk move failed: {e}")
        return api_response().error("Bulk move failed", 500)


@bulk_bp.route("/tag", methods=["POST"])
@jwt_required()
def bulk_add_tags():
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    link_ids = data.get("link_ids", [])
    tag_ids = data.get("tag_ids", [])
    action = data.get("action", "add")

    if not link_ids:
        return api_response().error("No links specified", 400)

    if not tag_ids:
        return api_response().error("No tags specified", 400)

    links = validate_link_ids(link_ids, user_id)
    tags = Tag.query.filter(Tag.id.in_(tag_ids), Tag.user_id == user_id).all()

    if not links or not tags:
        return api_response().error("No valid links or tags found", 404)

    try:
        for link in links:
            for tag in tags:
                if action == "add":
                    existing = LinkTag.query.filter_by(link_id=link.id, tag_id=tag.id).first()
                    if not existing:
                        db.session.add(LinkTag(link_id=link.id, tag_id=tag.id))
                elif action == "remove":
                    LinkTag.query.filter_by(link_id=link.id, tag_id=tag.id).delete()

        db.session.commit()

        ActivityService.log(
            user_id=user_id,
            activity_type=ActivityType.BULK_OPERATION,
            resource_type="links",
            metadata={"operation": f"tag_{action}", "count": len(links), "tags": len(tags)}
        )

        return api_response().success(
            data={"affected": len(links)},
            message=f"Updated tags for {len(links)} links"
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Bulk tag failed: {e}")
        return api_response().error("Bulk tag operation failed", 500)


@bulk_bp.route("/delete", methods=["POST"])
@jwt_required()
def bulk_delete():
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    link_ids = data.get("link_ids", [])
    permanent = data.get("permanent", False)

    if not link_ids:
        return api_response().error("No links specified", 400)

    if permanent:
        links = Link.query.filter(Link.id.in_(link_ids), Link.user_id == user_id).all()
    else:
        links = validate_link_ids(link_ids, user_id)

    if not links:
        return api_response().error("No valid links found", 404)

    try:
        slugs = [l.slug for l in links if l.slug]

        if permanent:
            for link in links:
                db.session.delete(link)
        else:
            for link in links:
                link.soft_delete()

        db.session.commit()

        redis_service = RedisService()
        for slug in slugs:
            try:
                redis_service.invalidate_link_cache(slug)
            except Exception:
                pass

        ActivityService.log(
            user_id=user_id,
            activity_type=ActivityType.BULK_OPERATION,
            resource_type="links",
            metadata={"operation": "delete", "permanent": permanent, "count": len(links)}
        )

        action = "permanently deleted" if permanent else "moved to trash"
        return api_response().success(
            data={"affected": len(links)},
            message=f"Successfully {action} {len(links)} links"
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Bulk delete failed: {e}")
        return api_response().error("Bulk delete failed", 500)


@bulk_bp.route("/restore", methods=["POST"])
@jwt_required()
def bulk_restore():
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    link_ids = data.get("link_ids", [])

    if not link_ids:
        return api_response().error("No links specified", 400)

    links = Link.query.filter(
        Link.id.in_(link_ids),
        Link.user_id == user_id,
        Link.is_deleted == True
    ).all()

    if not links:
        return api_response().error("No deleted links found", 404)

    try:
        for link in links:
            link.restore()

        db.session.commit()

        redis_service = RedisService()
        for link in links:
            if link.slug:
                try:
                    redis_service.cache_link(link.slug, link.to_cache_dict())
                except Exception:
                    pass

        return api_response().success(
            data={"affected": len(links)},
            message=f"Restored {len(links)} links"
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Bulk restore failed: {e}")
        return api_response().error("Bulk restore failed", 500)


@bulk_bp.route("/toggle", methods=["POST"])
@jwt_required()
def bulk_toggle():
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    link_ids = data.get("link_ids", [])
    is_active = data.get("is_active")

    if not link_ids:
        return api_response().error("No links specified", 400)

    if is_active is None:
        return api_response().error("is_active value required", 400)

    links = validate_link_ids(link_ids, user_id)

    if not links:
        return api_response().error("No valid links found", 404)

    try:
        for link in links:
            link.is_active = bool(is_active)

        db.session.commit()

        redis_service = RedisService()
        for link in links:
            if link.slug:
                try:
                    redis_service.cache_link(link.slug, link.to_cache_dict())
                except Exception:
                    pass

        status = "enabled" if is_active else "disabled"
        return api_response().success(
            data={"affected": len(links)},
            message=f"Successfully {status} {len(links)} links"
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Bulk toggle failed: {e}")
        return api_response().error("Bulk toggle failed", 500)


@bulk_bp.route("/export", methods=["POST"])
@jwt_required()
def bulk_export():
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    base_url = get_public_base_url()

    link_ids = data.get("link_ids", [])
    format_type = data.get("format", "json")

    if link_ids:
        links = validate_link_ids(link_ids, user_id)
    else:
        links = Link.query.filter_by(user_id=user_id, is_deleted=False).all()

    if not links:
        return api_response().error("No links to export", 404)

    export_data = []
    for link in links:
        export_data.append({
            "original_url": link.original_url,
            "short_url": f"{base_url}/{link.slug}" if link.slug else None,
            "title": link.title,
            "notes": link.notes,
            "link_type": link.link_type.value,
            "folder": link.folder.name if link.folder else None,
            "tags": [t.name for t in link.tags],
            "clicks": link.clicks,
            "is_active": link.is_active,
            "created_at": link.created_at.isoformat()
        })

    if format_type == "csv":
        import csv
        import io

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "original_url", "short_url", "title", "notes", "link_type",
            "folder", "tags", "clicks", "is_active", "created_at"
        ])
        writer.writeheader()
        for row in export_data:
            row["tags"] = ", ".join(row["tags"])
            writer.writerow(row)

        return current_app.response_class(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=savlink_export.csv"}
        )

    return api_response().success(data={
        "links": export_data,
        "count": len(export_data),
        "exported_at": datetime.utcnow().isoformat()
    })