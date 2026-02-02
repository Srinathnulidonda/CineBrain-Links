# server/app/routes/categories.py

import logging

from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models.category import Category
from app.models.link import Link
from app.utils.base_url import get_public_base_url

categories_bp = Blueprint("categories", __name__)
logger = logging.getLogger(__name__)


def api_response():
    return current_app.api_response


@categories_bp.route("", methods=["GET"])
@jwt_required()
def get_categories():
    categories = Category.query.order_by(Category.sort_order, Category.name).all()

    return api_response().success(data={
        "categories": [c.to_dict() for c in categories]
    })


@categories_bp.route("/<category_id>", methods=["GET"])
@jwt_required()
def get_category(category_id: str):
    category = Category.query.get(category_id)

    if not category:
        return api_response().error("Category not found", 404, "NOT_FOUND")

    return api_response().success(data={"category": category.to_dict()})


@categories_bp.route("/<category_id>/links", methods=["GET"])
@jwt_required()
def get_category_links(category_id: str):
    user_id = get_jwt_identity()
    base_url = get_public_base_url()

    category = Category.query.get(category_id)

    if not category:
        return api_response().error("Category not found", 404, "NOT_FOUND")

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = Link.query.filter_by(
        user_id=user_id,
        category_id=category_id,
        is_deleted=False
    ).order_by(Link.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return api_response().success(data={
        "category": category.to_dict(),
        "links": [l.to_dict(base_url=base_url) for l in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages,
            "total_items": pagination.total
        }
    })
