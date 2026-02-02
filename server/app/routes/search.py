# server/app/routes/search.py

import logging

from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.link import Link, LinkType
from app.models.tag import LinkTag
from app.utils.base_url import get_public_base_url

search_bp = Blueprint("search", __name__)
logger = logging.getLogger(__name__)


def api_response():
    return current_app.api_response


@search_bp.route("", methods=["GET"])
@jwt_required()
def search_links():
    user_id = get_jwt_identity()
    base_url = get_public_base_url()

    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    link_type = request.args.get("link_type")
    folder_id = request.args.get("folder_id")
    tag_ids = request.args.getlist("tag_id")
    is_active = request.args.get("is_active", type=lambda x: x.lower() == "true")
    is_pinned = request.args.get("is_pinned", type=lambda x: x.lower() == "true")
    is_broken = request.args.get("is_broken", type=lambda x: x.lower() == "true")

    query = Link.query.filter_by(user_id=user_id, is_deleted=False)

    if q:
        search_term = f"%{q}%"
        query = query.filter(
            db.or_(
                Link.title.ilike(search_term),
                Link.original_url.ilike(search_term),
                Link.notes.ilike(search_term),
                Link.slug.ilike(search_term)
            )
        )

    if link_type:
        try:
            query = query.filter(Link.link_type == LinkType(link_type))
        except ValueError:
            pass

    if folder_id:
        if folder_id == "none":
            query = query.filter(Link.folder_id.is_(None))
        else:
            query = query.filter(Link.folder_id == folder_id)

    if tag_ids:
        query = query.join(LinkTag).filter(LinkTag.tag_id.in_(tag_ids))

    if is_active is not None:
        query = query.filter(Link.is_active == is_active)

    if is_pinned is not None:
        query = query.filter(Link.is_pinned == is_pinned)

    if is_broken is not None:
        query = query.filter(Link.is_broken == is_broken)

    query = query.order_by(Link.is_pinned.desc(), Link.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return api_response().success(data={
        "query": q,
        "links": [l.to_dict(base_url=base_url) for l in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages,
            "total_items": pagination.total
        }
    })


@search_bp.route("/suggestions", methods=["GET"])
@jwt_required()
def search_suggestions():
    user_id = get_jwt_identity()

    q = request.args.get("q", "").strip()

    if not q or len(q) < 2:
        return api_response().success(data={"suggestions": []})

    search_term = f"%{q}%"

    titles = db.session.query(Link.title).filter(
        Link.user_id == user_id,
        Link.is_deleted == False,
        Link.title.isnot(None),
        Link.title.ilike(search_term)
    ).distinct().limit(5).all()

    slugs = db.session.query(Link.slug).filter(
        Link.user_id == user_id,
        Link.is_deleted == False,
        Link.slug.isnot(None),
        Link.slug.ilike(search_term)
    ).distinct().limit(3).all()

    suggestions = []
    for (title,) in titles:
        if title:
            suggestions.append({"type": "title", "value": title})

    for (slug,) in slugs:
        if slug:
            suggestions.append({"type": "slug", "value": slug})

    return api_response().success(data={"suggestions": suggestions[:8]})