# server/app/routes/tags.py

import logging
from typing import Optional

from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.tag import Tag, LinkTag
from app.models.link import Link
from app.models.activity_log import ActivityType
from app.services.activity_service import ActivityService

tags_bp = Blueprint("tags", __name__)
logger = logging.getLogger(__name__)


def api_response():
    return current_app.api_response


def get_user_tag(tag_id: str, user_id: str) -> Optional[Tag]:
    return Tag.query.filter_by(id=tag_id, user_id=user_id).first()


@tags_bp.route("", methods=["POST"])
@jwt_required()
def create_tag():
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    name = data.get("name", "").strip().lower()
    color = data.get("color", "").strip() if data.get("color") else None

    if not name:
        return api_response().error("Tag name is required", 400)

    if len(name) > 50:
        return api_response().error("Tag name is too long (max 50 characters)", 400)

    existing = Tag.query.filter_by(user_id=user_id, name=name).first()
    if existing:
        return api_response().error("This tag already exists", 409, "TAG_EXISTS")

    try:
        tag = Tag(user_id=user_id, name=name, color=color)
        db.session.add(tag)
        db.session.commit()

        ActivityService.log(
            user_id=user_id,
            activity_type=ActivityType.TAG_CREATED,
            resource_type="tag",
            resource_id=tag.id,
            resource_title=tag.name
        )

        logger.info(f"Tag created: {tag.id} by user {user_id}")

        return api_response().success(
            data={"tag": tag.to_dict()},
            message="Tag created",
            status=201
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Tag creation failed: {e}")
        return api_response().error("Failed to create tag", 500)


@tags_bp.route("", methods=["GET"])
@jwt_required()
def get_tags():
    user_id = get_jwt_identity()

    sort = request.args.get("sort", "name")
    include_empty = request.args.get("include_empty", "true").lower() == "true"

    query = Tag.query.filter_by(user_id=user_id)

    if sort == "usage":
        tags = query.all()
        tags.sort(key=lambda t: t.usage_count, reverse=True)
    else:
        tags = query.order_by(Tag.name).all()

    if not include_empty:
        tags = [t for t in tags if t.usage_count > 0]

    return api_response().success(data={
        "tags": [t.to_dict() for t in tags]
    })


@tags_bp.route("/<tag_id>", methods=["GET"])
@jwt_required()
def get_tag(tag_id: str):
    user_id = get_jwt_identity()
    tag = get_user_tag(tag_id, user_id)

    if not tag:
        return api_response().error("Tag not found", 404, "NOT_FOUND")

    return api_response().success(data={"tag": tag.to_dict()})


@tags_bp.route("/<tag_id>", methods=["PUT"])
@jwt_required()
def update_tag(tag_id: str):
    user_id = get_jwt_identity()
    tag = get_user_tag(tag_id, user_id)

    if not tag:
        return api_response().error("Tag not found", 404, "NOT_FOUND")

    data = request.get_json() or {}

    try:
        if "name" in data:
            name = data["name"].strip().lower()
            if not name:
                return api_response().error("Tag name is required", 400)

            existing = Tag.query.filter(
                Tag.user_id == user_id,
                Tag.name == name,
                Tag.id != tag_id
            ).first()
            if existing:
                return api_response().error("This tag name already exists", 409)

            tag.name = name

        if "color" in data:
            tag.color = data["color"]

        db.session.commit()

        return api_response().success(
            data={"tag": tag.to_dict()},
            message="Tag updated"
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Tag update failed: {e}")
        return api_response().error("Failed to update tag", 500)


@tags_bp.route("/<tag_id>", methods=["DELETE"])
@jwt_required()
def delete_tag(tag_id: str):
    user_id = get_jwt_identity()
    tag = get_user_tag(tag_id, user_id)

    if not tag:
        return api_response().error("Tag not found", 404, "NOT_FOUND")

    try:
        tag_name = tag.name
        db.session.delete(tag)
        db.session.commit()

        ActivityService.log(
            user_id=user_id,
            activity_type=ActivityType.TAG_DELETED,
            resource_type="tag",
            resource_id=tag_id,
            resource_title=tag_name
        )

        logger.info(f"Tag deleted: {tag_id} by user {user_id}")

        return api_response().success(message="Tag deleted")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Tag deletion failed: {e}")
        return api_response().error("Failed to delete tag", 500)


@tags_bp.route("/<tag_id>/links", methods=["GET"])
@jwt_required()
def get_tag_links(tag_id: str):
    user_id = get_jwt_identity()
    tag = get_user_tag(tag_id, user_id)

    if not tag:
        return api_response().error("Tag not found", 404, "NOT_FOUND")

    from app.utils.base_url import get_public_base_url
    base_url = get_public_base_url()

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = Link.query.join(LinkTag).filter(
        LinkTag.tag_id == tag_id,
        Link.user_id == user_id,
        Link.is_deleted == False
    ).order_by(Link.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return api_response().success(data={
        "tag": tag.to_dict(),
        "links": [link.to_dict(base_url=base_url) for link in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages,
            "total_items": pagination.total
        }
    })


@tags_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_tag_stats():
    user_id = get_jwt_identity()

    tags = Tag.query.filter_by(user_id=user_id).all()

    stats = []
    for tag in tags:
        stats.append({
            "id": tag.id,
            "name": tag.name,
            "color": tag.color,
            "usage_count": tag.usage_count
        })

    stats.sort(key=lambda x: x["usage_count"], reverse=True)

    return api_response().success(data={"tag_stats": stats})