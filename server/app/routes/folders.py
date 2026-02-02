# server/app/routes/folders.py

import logging
from typing import Optional

from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.folder import Folder
from app.models.link import Link
from app.models.activity_log import ActivityType
from app.services.activity_service import ActivityService
from app.utils.validators import InputValidator

folders_bp = Blueprint("folders", __name__)
logger = logging.getLogger(__name__)


def api_response():
    return current_app.api_response


def get_user_folder(folder_id: str, user_id: str) -> Optional[Folder]:
    return Folder.query.filter_by(id=folder_id, user_id=user_id).first()


@folders_bp.route("", methods=["POST"])
@jwt_required()
def create_folder():
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    description = data.get("description", "").strip() if data.get("description") else None
    color = data.get("color", "").strip() if data.get("color") else None
    icon = data.get("icon", "").strip() if data.get("icon") else None
    parent_id = data.get("parent_id")

    if not name:
        return api_response().error("Folder name is required", 400)

    if len(name) > 100:
        return api_response().error("Folder name is too long (max 100 characters)", 400)

    existing = Folder.query.filter_by(user_id=user_id, name=name).first()
    if existing:
        return api_response().error("A folder with this name already exists", 409, "FOLDER_EXISTS")

    if parent_id:
        parent = get_user_folder(parent_id, user_id)
        if not parent:
            return api_response().error("Parent folder not found", 404)

    try:
        max_order = db.session.query(db.func.max(Folder.sort_order)).filter_by(
            user_id=user_id,
            parent_id=parent_id
        ).scalar() or 0

        folder = Folder(
            user_id=user_id,
            name=name,
            description=description,
            color=color,
            icon=icon,
            parent_id=parent_id,
            sort_order=max_order + 1
        )

        db.session.add(folder)
        db.session.commit()

        ActivityService.log(
            user_id=user_id,
            activity_type=ActivityType.FOLDER_CREATED,
            resource_type="folder",
            resource_id=folder.id,
            resource_title=folder.name
        )

        logger.info(f"Folder created: {folder.id} by user {user_id}")

        return api_response().success(
            data={"folder": folder.to_dict()},
            message="Folder created",
            status=201
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Folder creation failed: {e}")
        return api_response().error("Failed to create folder", 500)


@folders_bp.route("", methods=["GET"])
@jwt_required()
def get_folders():
    user_id = get_jwt_identity()

    include_children = request.args.get("include_children", "true").lower() == "true"
    flat = request.args.get("flat", "false").lower() == "true"

    if flat:
        folders = Folder.query.filter_by(user_id=user_id).order_by(Folder.sort_order).all()
        return api_response().success(data={
            "folders": [f.to_dict() for f in folders]
        })

    root_folders = Folder.query.filter_by(
        user_id=user_id,
        parent_id=None
    ).order_by(Folder.sort_order).all()

    return api_response().success(data={
        "folders": [f.to_dict(include_children=include_children) for f in root_folders]
    })


@folders_bp.route("/<folder_id>", methods=["GET"])
@jwt_required()
def get_folder(folder_id: str):
    user_id = get_jwt_identity()
    folder = get_user_folder(folder_id, user_id)

    if not folder:
        return api_response().error("Folder not found", 404, "NOT_FOUND")

    return api_response().success(data={"folder": folder.to_dict(include_children=True)})


@folders_bp.route("/<folder_id>", methods=["PUT"])
@jwt_required()
def update_folder(folder_id: str):
    user_id = get_jwt_identity()
    folder = get_user_folder(folder_id, user_id)

    if not folder:
        return api_response().error("Folder not found", 404, "NOT_FOUND")

    data = request.get_json() or {}

    try:
        if "name" in data:
            name = data["name"].strip()
            if not name:
                return api_response().error("Folder name is required", 400)

            existing = Folder.query.filter(
                Folder.user_id == user_id,
                Folder.name == name,
                Folder.id != folder_id
            ).first()
            if existing:
                return api_response().error("A folder with this name already exists", 409)

            folder.name = name

        if "description" in data:
            folder.description = data["description"].strip() if data["description"] else None

        if "color" in data:
            folder.color = data["color"]

        if "icon" in data:
            folder.icon = data["icon"]

        if "parent_id" in data:
            new_parent_id = data["parent_id"]
            if new_parent_id:
                if new_parent_id == folder_id:
                    return api_response().error("Folder cannot be its own parent", 400)
                parent = get_user_folder(new_parent_id, user_id)
                if not parent:
                    return api_response().error("Parent folder not found", 404)
            folder.parent_id = new_parent_id

        db.session.commit()

        ActivityService.log(
            user_id=user_id,
            activity_type=ActivityType.FOLDER_UPDATED,
            resource_type="folder",
            resource_id=folder.id,
            resource_title=folder.name
        )

        return api_response().success(
            data={"folder": folder.to_dict()},
            message="Folder updated"
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Folder update failed: {e}")
        return api_response().error("Failed to update folder", 500)


@folders_bp.route("/<folder_id>", methods=["DELETE"])
@jwt_required()
def delete_folder(folder_id: str):
    user_id = get_jwt_identity()
    folder = get_user_folder(folder_id, user_id)

    if not folder:
        return api_response().error("Folder not found", 404, "NOT_FOUND")

    action = request.args.get("link_action", "unassign")
    target_folder_id = request.args.get("target_folder_id")

    try:
        if action == "delete":
            Link.query.filter_by(folder_id=folder_id, user_id=user_id).update({"is_deleted": True})
        elif action == "move" and target_folder_id:
            target = get_user_folder(target_folder_id, user_id)
            if not target:
                return api_response().error("Target folder not found", 404)
            Link.query.filter_by(folder_id=folder_id, user_id=user_id).update({"folder_id": target_folder_id})
        else:
            Link.query.filter_by(folder_id=folder_id, user_id=user_id).update({"folder_id": None})

        Folder.query.filter_by(parent_id=folder_id, user_id=user_id).update({"parent_id": folder.parent_id})

        folder_name = folder.name
        db.session.delete(folder)
        db.session.commit()

        ActivityService.log(
            user_id=user_id,
            activity_type=ActivityType.FOLDER_DELETED,
            resource_type="folder",
            resource_id=folder_id,
            resource_title=folder_name
        )

        logger.info(f"Folder deleted: {folder_id} by user {user_id}")

        return api_response().success(message="Folder deleted")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Folder deletion failed: {e}")
        return api_response().error("Failed to delete folder", 500)


@folders_bp.route("/reorder", methods=["POST"])
@jwt_required()
def reorder_folders():
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    folder_orders = data.get("folders", [])

    if not folder_orders:
        return api_response().error("Folder order data required", 400)

    try:
        for item in folder_orders:
            folder_id = item.get("id")
            new_order = item.get("sort_order")

            if folder_id and new_order is not None:
                folder = get_user_folder(folder_id, user_id)
                if folder:
                    folder.sort_order = new_order

        db.session.commit()

        return api_response().success(message="Folder order updated")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Folder reorder failed: {e}")
        return api_response().error("Failed to reorder folders", 500)


@folders_bp.route("/<folder_id>/links", methods=["GET"])
@jwt_required()
def get_folder_links(folder_id: str):
    user_id = get_jwt_identity()
    folder = get_user_folder(folder_id, user_id)

    if not folder:
        return api_response().error("Folder not found", 404, "NOT_FOUND")

    from app.utils.base_url import get_public_base_url
    base_url = get_public_base_url()

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = Link.query.filter_by(
        user_id=user_id,
        folder_id=folder_id,
        is_deleted=False
    ).order_by(Link.is_pinned.desc(), Link.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return api_response().success(data={
        "folder": folder.to_dict(),
        "links": [link.to_dict(base_url=base_url) for link in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages,
            "total_items": pagination.total
        }
    })