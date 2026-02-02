# server/app/routes/templates.py

import logging
from typing import Optional

from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.link_template import LinkTemplate
from app.utils.validators import InputValidator

templates_bp = Blueprint("templates", __name__)
logger = logging.getLogger(__name__)


def api_response():
    return current_app.api_response


def get_user_template(template_id: str, user_id: str) -> Optional[LinkTemplate]:
    return LinkTemplate.query.filter_by(id=template_id, user_id=user_id).first()


@templates_bp.route("", methods=["POST"])
@jwt_required()
def create_template():
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    name = data.get("name", "").strip()

    if not name:
        return api_response().error("Template name is required", 400)

    if len(name) > 100:
        return api_response().error("Template name is too long", 400)

    existing = LinkTemplate.query.filter_by(user_id=user_id, name=name).first()
    if existing:
        return api_response().error("A template with this name already exists", 409)

    try:
        template = LinkTemplate(
            user_id=user_id,
            name=name,
            description=data.get("description"),
            url_pattern=data.get("url_pattern"),
            default_title=data.get("default_title"),
            default_notes=data.get("default_notes"),
            default_folder_id=data.get("default_folder_id"),
            default_tags=data.get("default_tags"),
            variables=data.get("variables")
        )

        db.session.add(template)
        db.session.commit()

        logger.info(f"Template created: {template.id} by user {user_id}")

        return api_response().success(
            data={"template": template.to_dict()},
            message="Template created",
            status=201
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Template creation failed: {e}")
        return api_response().error("Failed to create template", 500)


@templates_bp.route("", methods=["GET"])
@jwt_required()
def get_templates():
    user_id = get_jwt_identity()

    templates = LinkTemplate.query.filter_by(user_id=user_id).order_by(
        LinkTemplate.usage_count.desc(),
        LinkTemplate.name
    ).all()

    return api_response().success(data={
        "templates": [t.to_dict() for t in templates]
    })


@templates_bp.route("/<template_id>", methods=["GET"])
@jwt_required()
def get_template(template_id: str):
    user_id = get_jwt_identity()
    template = get_user_template(template_id, user_id)

    if not template:
        return api_response().error("Template not found", 404, "NOT_FOUND")

    return api_response().success(data={"template": template.to_dict()})


@templates_bp.route("/<template_id>", methods=["PUT"])
@jwt_required()
def update_template(template_id: str):
    user_id = get_jwt_identity()
    template = get_user_template(template_id, user_id)

    if not template:
        return api_response().error("Template not found", 404, "NOT_FOUND")

    data = request.get_json() or {}

    try:
        if "name" in data:
            name = data["name"].strip()
            if not name:
                return api_response().error("Template name is required", 400)

            existing = LinkTemplate.query.filter(
                LinkTemplate.user_id == user_id,
                LinkTemplate.name == name,
                LinkTemplate.id != template_id
            ).first()
            if existing:
                return api_response().error("This template name already exists", 409)

            template.name = name

        if "description" in data:
            template.description = data["description"]

        if "url_pattern" in data:
            template.url_pattern = data["url_pattern"]

        if "default_title" in data:
            template.default_title = data["default_title"]

        if "default_notes" in data:
            template.default_notes = data["default_notes"]

        if "default_folder_id" in data:
            template.default_folder_id = data["default_folder_id"]

        if "default_tags" in data:
            template.default_tags = data["default_tags"]

        if "variables" in data:
            template.variables = data["variables"]

        db.session.commit()

        return api_response().success(
            data={"template": template.to_dict()},
            message="Template updated"
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Template update failed: {e}")
        return api_response().error("Failed to update template", 500)


@templates_bp.route("/<template_id>", methods=["DELETE"])
@jwt_required()
def delete_template(template_id: str):
    user_id = get_jwt_identity()
    template = get_user_template(template_id, user_id)

    if not template:
        return api_response().error("Template not found", 404, "NOT_FOUND")

    try:
        db.session.delete(template)
        db.session.commit()

        return api_response().success(message="Template deleted")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Template deletion failed: {e}")
        return api_response().error("Failed to delete template", 500)


@templates_bp.route("/<template_id>/use", methods=["POST"])
@jwt_required()
def use_template(template_id: str):
    user_id = get_jwt_identity()
    template = get_user_template(template_id, user_id)

    if not template:
        return api_response().error("Template not found", 404, "NOT_FOUND")

    data = request.get_json() or {}
    variables = data.get("variables", {})

    url = template.url_pattern or ""
    title = template.default_title or ""
    notes = template.default_notes or ""

    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"
        url = url.replace(placeholder, str(value))
        title = title.replace(placeholder, str(value))
        notes = notes.replace(placeholder, str(value))

    template.increment_usage()
    db.session.commit()

    return api_response().success(data={
        "prefill": {
            "url": url,
            "title": title,
            "notes": notes,
            "folder_id": template.default_folder_id,
            "tag_ids": template.default_tags
        }
    })