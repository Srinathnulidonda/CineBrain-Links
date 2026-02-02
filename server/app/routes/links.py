# server/app/routes/links.py

import logging
from datetime import datetime
from typing import Optional

from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db, limiter
from app.models.link import Link, LinkType, PrivacyLevel
from app.models.link_version import LinkVersion
from app.models.activity_log import ActivityLog, ActivityType
from app.models.tag import Tag, LinkTag
from app.services.redis_service import RedisService
from app.services.link_service import LinkService
from app.services.activity_service import ActivityService
from app.utils.validators import URLValidator, InputValidator
from app.utils.slug import SlugGenerator
from app.utils.base_url import get_public_base_url

links_bp = Blueprint("links", __name__)
logger = logging.getLogger(__name__)


def api_response():
    return current_app.api_response


def get_user_link(link_id: str, user_id: str) -> Optional[Link]:
    return Link.query.filter_by(id=link_id, user_id=user_id, is_deleted=False).first()


@links_bp.route("", methods=["POST"])
@jwt_required()
@limiter.limit("30 per minute")
def create_link():
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    base_url = get_public_base_url()

    original_url = data.get("url", "").strip()
    link_type_str = data.get("link_type", "saved").lower()
    custom_slug = data.get("custom_slug", "").strip() if data.get("custom_slug") else None
    title = data.get("title", "").strip() if data.get("title") else None
    notes = data.get("notes", "").strip() if data.get("notes") else None
    folder_id = data.get("folder_id")
    tag_ids = data.get("tag_ids", [])
    category_id = data.get("category_id")
    expires_at_str = data.get("expires_at")
    is_pinned = data.get("is_pinned", False)
    click_tracking = data.get("click_tracking_enabled", True)
    privacy_level_str = data.get("privacy_level", "private")
    custom_metadata = data.get("metadata")

    is_valid, normalized_url, error = URLValidator.validate(original_url)
    if not is_valid:
        return api_response().error(error, 400, "INVALID_URL")

    try:
        link_type = LinkType(link_type_str)
    except ValueError:
        return api_response().error("Invalid link type. Use 'saved' or 'shortened'", 400, "INVALID_LINK_TYPE")

    try:
        privacy_level = PrivacyLevel(privacy_level_str)
    except ValueError:
        privacy_level = PrivacyLevel.PRIVATE

    slug = None
    if link_type == LinkType.SHORTENED:
        if custom_slug:
            is_valid, normalized_slug, error = InputValidator.validate_slug(custom_slug)
            if not is_valid:
                return api_response().error(error, 400, "INVALID_SLUG")

            if not SlugGenerator.is_available(normalized_slug):
                return api_response().error("This short link is already taken", 409, "SLUG_TAKEN")

            slug = normalized_slug
        else:
            generator = SlugGenerator()
            slug = generator.generate_unique()
            if not slug:
                return api_response().error("Could not generate short link. Please try again.", 500)

    if folder_id:
        from app.models.folder import Folder
        folder = Folder.query.filter_by(id=folder_id, user_id=user_id).first()
        if not folder:
            return api_response().error("Folder not found", 404, "FOLDER_NOT_FOUND")

    duplicate = Link.query.filter_by(
        user_id=user_id,
        original_url=normalized_url,
        is_deleted=False
    ).first()

    duplicate_warning = None
    if duplicate:
        duplicate_warning = {
            "message": "You already have this URL saved",
            "existing_link_id": duplicate.id,
            "existing_link_title": duplicate.title
        }

    expires_at: Optional[datetime] = None
    if expires_at_str and link_type == LinkType.SHORTENED:
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            if expires_at <= datetime.utcnow():
                return api_response().error("Expiration must be in the future", 400)
        except (ValueError, TypeError):
            return api_response().error("Invalid expiration date format", 400)

    if title:
        title = InputValidator.sanitize_string(title, max_length=255)
    if notes:
        notes = InputValidator.sanitize_string(notes, max_length=5000)

    try:
        link = Link(
            user_id=user_id,
            original_url=normalized_url,
            link_type=link_type,
            slug=slug,
            title=title,
            notes=notes,
            folder_id=folder_id,
            category_id=category_id,
            expires_at=expires_at,
            is_pinned=is_pinned,
            click_tracking_enabled=click_tracking,
            privacy_level=privacy_level,
            custom_metadata=custom_metadata,
        )

        if is_pinned:
            link.pinned_at = datetime.utcnow()

        db.session.add(link)
        db.session.flush()

        if tag_ids:
            tags = Tag.query.filter(Tag.id.in_(tag_ids), Tag.user_id == user_id).all()
            for tag in tags:
                link_tag = LinkTag(link_id=link.id, tag_id=tag.id)
                db.session.add(link_tag)

        db.session.commit()

        if link.is_shortened:
            try:
                RedisService().cache_link(slug, link.to_cache_dict())
            except Exception as e:
                logger.warning(f"Failed to cache link: {e}")

        ActivityService.log(
            user_id=user_id,
            activity_type=ActivityType.LINK_CREATED,
            resource_type="link",
            resource_id=link.id,
            resource_title=link.title or link.original_url[:50],
            metadata={"link_type": link_type.value}
        )

        logger.info(f"Link created: {link.id} ({link_type.value}) by user {user_id}")

        response_data = {"link": link.to_dict(base_url=base_url)}
        if duplicate_warning:
            response_data["warning"] = duplicate_warning

        return api_response().success(
            data=response_data,
            message="Link created",
            status=201
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Link creation failed: {e}")
        return api_response().error("Failed to create link", 500)


@links_bp.route("", methods=["GET"])
@jwt_required()
def get_links():
    user_id = get_jwt_identity()
    base_url = get_public_base_url()

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    link_type = request.args.get("link_type")
    folder_id = request.args.get("folder_id")
    tag_ids = request.args.getlist("tag_id")
    category_id = request.args.get("category_id")
    is_active = request.args.get("is_active", type=lambda x: x.lower() == "true")
    is_pinned = request.args.get("is_pinned", type=lambda x: x.lower() == "true")
    is_broken = request.args.get("is_broken", type=lambda x: x.lower() == "true")
    include_deleted = request.args.get("include_deleted", "false").lower() == "true"

    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    sort_field = request.args.get("sort", "created_at")
    sort_order = request.args.get("order", "desc")

    query = Link.query.filter_by(user_id=user_id)

    if not include_deleted:
        query = query.filter_by(is_deleted=False)

    if link_type:
        try:
            query = query.filter_by(link_type=LinkType(link_type))
        except ValueError:
            pass

    if folder_id:
        if folder_id == "none":
            query = query.filter(Link.folder_id.is_(None))
        else:
            query = query.filter_by(folder_id=folder_id)

    if tag_ids:
        query = query.join(LinkTag).filter(LinkTag.tag_id.in_(tag_ids))

    if category_id:
        query = query.filter_by(category_id=category_id)

    if is_active is not None:
        query = query.filter_by(is_active=is_active)

    if is_pinned is not None:
        query = query.filter_by(is_pinned=is_pinned)

    if is_broken is not None:
        query = query.filter_by(is_broken=is_broken)

    if date_from:
        try:
            query = query.filter(Link.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass

    if date_to:
        try:
            query = query.filter(Link.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    allowed_sorts = {"created_at", "updated_at", "clicks", "last_clicked_at", "title", "pinned_at"}
    if sort_field not in allowed_sorts:
        sort_field = "created_at"

    if is_pinned is None:
        query = query.order_by(Link.is_pinned.desc(), Link.pinned_at.desc().nullslast())

    sort_col = getattr(Link, sort_field)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc().nullslast())
    else:
        query = query.order_by(sort_col.desc().nullslast())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    links = [link.to_dict(base_url=base_url) for link in pagination.items]

    return api_response().success(data={
        "links": links,
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages,
            "total_items": pagination.total,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev
        }
    })


@links_bp.route("/<link_id>", methods=["GET"])
@jwt_required()
def get_link(link_id: str):
    user_id = get_jwt_identity()
    base_url = get_public_base_url()

    include_deleted = request.args.get("include_deleted", "false").lower() == "true"

    if include_deleted:
        link = Link.query.filter_by(id=link_id, user_id=user_id).first()
    else:
        link = get_user_link(link_id, user_id)

    if not link:
        return api_response().error("Link not found", 404, "NOT_FOUND")

    return api_response().success(data={"link": link.to_dict(base_url=base_url)})


@links_bp.route("/<link_id>", methods=["PUT"])
@jwt_required()
def update_link(link_id: str):
    user_id = get_jwt_identity()
    base_url = get_public_base_url()
    link = get_user_link(link_id, user_id)

    if not link:
        return api_response().error("Link not found", 404, "NOT_FOUND")

    data = request.get_json() or {}
    changes_made = []

    try:
        if "original_url" in data and data["original_url"] != link.original_url:
            is_valid, normalized_url, error = URLValidator.validate(data["original_url"])
            if not is_valid:
                return api_response().error(error, 400, "INVALID_URL")

            version = LinkVersion(
                link_id=link.id,
                previous_url=link.original_url,
                previous_slug=link.slug,
                previous_title=link.title,
                changed_by=user_id,
                change_reason=data.get("change_reason")
            )
            db.session.add(version)

            link.original_url = normalized_url
            changes_made.append("url")

        if "slug" in data and link.is_shortened:
            new_slug = data["slug"].strip().lower() if data["slug"] else None

            if new_slug and new_slug != link.slug:
                is_valid, normalized_slug, error = InputValidator.validate_slug(new_slug)
                if not is_valid:
                    return api_response().error(error, 400, "INVALID_SLUG")

                if not SlugGenerator.is_available(normalized_slug):
                    return api_response().error("This short link is already taken", 409, "SLUG_TAKEN")

                old_slug = link.slug

                version = LinkVersion(
                    link_id=link.id,
                    previous_url=link.original_url,
                    previous_slug=old_slug,
                    previous_title=link.title,
                    changed_by=user_id,
                    change_reason="Slug changed"
                )
                db.session.add(version)

                try:
                    RedisService().invalidate_link_cache(old_slug)
                except Exception:
                    pass

                link.slug = normalized_slug
                changes_made.append("slug")

        if "title" in data:
            link.title = InputValidator.sanitize_string(data["title"] or "", max_length=255) or None
            changes_made.append("title")

        if "notes" in data:
            link.notes = InputValidator.sanitize_string(data["notes"] or "", max_length=5000) or None
            changes_made.append("notes")

        if "folder_id" in data:
            if data["folder_id"]:
                from app.models.folder import Folder
                folder = Folder.query.filter_by(id=data["folder_id"], user_id=user_id).first()
                if not folder:
                    return api_response().error("Folder not found", 404)
                link.folder_id = data["folder_id"]
            else:
                link.folder_id = None
            changes_made.append("folder")

        if "category_id" in data:
            link.category_id = data["category_id"] or None
            changes_made.append("category")

        if "tag_ids" in data:
            LinkTag.query.filter_by(link_id=link.id).delete()
            for tag_id in data["tag_ids"]:
                tag = Tag.query.filter_by(id=tag_id, user_id=user_id).first()
                if tag:
                    db.session.add(LinkTag(link_id=link.id, tag_id=tag.id))
            changes_made.append("tags")

        if "is_active" in data:
            link.is_active = bool(data["is_active"])
            changes_made.append("is_active")

        if "is_pinned" in data:
            if data["is_pinned"] and not link.is_pinned:
                link.pin()
            elif not data["is_pinned"] and link.is_pinned:
                link.unpin()
            changes_made.append("is_pinned")

        if "expires_at" in data:
            if data["expires_at"] is None:
                link.expires_at = None
            else:
                try:
                    expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
                    if expires_at <= datetime.utcnow():
                        return api_response().error("Expiration must be in the future", 400)
                    link.expires_at = expires_at
                except (ValueError, TypeError):
                    return api_response().error("Invalid expiration date format", 400)
            changes_made.append("expires_at")

        if "expired_redirect_url" in data:
            if data["expired_redirect_url"]:
                is_valid, normalized, error = URLValidator.validate(data["expired_redirect_url"])
                if not is_valid:
                    return api_response().error(f"Invalid expired redirect URL: {error}", 400)
                link.expired_redirect_url = normalized
            else:
                link.expired_redirect_url = None

        if "click_tracking_enabled" in data:
            link.click_tracking_enabled = bool(data["click_tracking_enabled"])

        if "privacy_level" in data:
            try:
                link.privacy_level = PrivacyLevel(data["privacy_level"])
            except ValueError:
                pass

        if "metadata" in data:
            link.custom_metadata = data["metadata"]

        db.session.commit()

        if link.is_shortened:
            try:
                RedisService().cache_link(link.slug, link.to_cache_dict())
            except Exception:
                pass

        if changes_made:
            ActivityService.log(
                user_id=user_id,
                activity_type=ActivityType.LINK_UPDATED,
                resource_type="link",
                resource_id=link.id,
                resource_title=link.title or link.original_url[:50],
                metadata={"changes": changes_made}
            )

        logger.info(f"Link updated: {link.id} by user {user_id}")

        return api_response().success(
            data={"link": link.to_dict(base_url=base_url)},
            message="Link updated"
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Link update failed: {e}")
        return api_response().error("Failed to update link", 500)


@links_bp.route("/<link_id>", methods=["DELETE"])
@jwt_required()
def delete_link(link_id: str):
    user_id = get_jwt_identity()
    permanent = request.args.get("permanent", "false").lower() == "true"

    link = Link.query.filter_by(id=link_id, user_id=user_id).first()

    if not link:
        return api_response().error("Link not found", 404, "NOT_FOUND")

    try:
        if permanent:
            slug = link.slug
            db.session.delete(link)
            db.session.commit()

            if slug:
                try:
                    RedisService().invalidate_link_cache(slug)
                except Exception:
                    pass

            logger.info(f"Link permanently deleted: {link_id} by user {user_id}")
            return api_response().success(message="Link permanently deleted")
        else:
            link.soft_delete()
            db.session.commit()

            if link.slug:
                try:
                    RedisService().invalidate_link_cache(link.slug)
                except Exception:
                    pass

            ActivityService.log(
                user_id=user_id,
                activity_type=ActivityType.LINK_DELETED,
                resource_type="link",
                resource_id=link.id,
                resource_title=link.title or link.original_url[:50]
            )

            logger.info(f"Link soft deleted: {link_id} by user {user_id}")
            return api_response().success(message="Link moved to trash")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Link deletion failed: {e}")
        return api_response().error("Failed to delete link", 500)


@links_bp.route("/<link_id>/restore", methods=["POST"])
@jwt_required()
def restore_link(link_id: str):
    user_id = get_jwt_identity()
    base_url = get_public_base_url()

    link = Link.query.filter_by(id=link_id, user_id=user_id, is_deleted=True).first()

    if not link:
        return api_response().error("Deleted link not found", 404, "NOT_FOUND")

    try:
        link.restore()
        db.session.commit()

        if link.slug:
            try:
                RedisService().cache_link(link.slug, link.to_cache_dict())
            except Exception:
                pass

        ActivityService.log(
            user_id=user_id,
            activity_type=ActivityType.LINK_RESTORED,
            resource_type="link",
            resource_id=link.id,
            resource_title=link.title or link.original_url[:50]
        )

        logger.info(f"Link restored: {link_id} by user {user_id}")

        return api_response().success(
            data={"link": link.to_dict(base_url=base_url)},
            message="Link restored"
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Link restore failed: {e}")
        return api_response().error("Failed to restore link", 500)


@links_bp.route("/<link_id>/pin", methods=["POST"])
@jwt_required()
def pin_link(link_id: str):
    user_id = get_jwt_identity()
    base_url = get_public_base_url()
    link = get_user_link(link_id, user_id)

    if not link:
        return api_response().error("Link not found", 404, "NOT_FOUND")

    try:
        link.pin()
        db.session.commit()

        return api_response().success(
            data={"link": link.to_dict(base_url=base_url)},
            message="Link pinned"
        )

    except Exception as e:
        db.session.rollback()
        return api_response().error("Failed to pin link", 500)


@links_bp.route("/<link_id>/unpin", methods=["POST"])
@jwt_required()
def unpin_link(link_id: str):
    user_id = get_jwt_identity()
    base_url = get_public_base_url()
    link = get_user_link(link_id, user_id)

    if not link:
        return api_response().error("Link not found", 404, "NOT_FOUND")

    try:
        link.unpin()
        db.session.commit()

        return api_response().success(
            data={"link": link.to_dict(base_url=base_url)},
            message="Link unpinned"
        )

    except Exception as e:
        db.session.rollback()
        return api_response().error("Failed to unpin link", 500)


@links_bp.route("/<link_id>/toggle", methods=["POST"])
@jwt_required()
def toggle_link(link_id: str):
    user_id = get_jwt_identity()
    base_url = get_public_base_url()
    link = get_user_link(link_id, user_id)

    if not link:
        return api_response().error("Link not found", 404, "NOT_FOUND")

    try:
        link.is_active = not link.is_active
        db.session.commit()

        if link.slug:
            try:
                RedisService().cache_link(link.slug, link.to_cache_dict())
            except Exception:
                pass

        status = "enabled" if link.is_active else "disabled"

        return api_response().success(
            data={"link": link.to_dict(base_url=base_url)},
            message=f"Link {status}"
        )

    except Exception as e:
        db.session.rollback()
        return api_response().error("Failed to toggle link", 500)


@links_bp.route("/<link_id>/duplicate", methods=["POST"])
@jwt_required()
def duplicate_link(link_id: str):
    user_id = get_jwt_identity()
    base_url = get_public_base_url()
    link = get_user_link(link_id, user_id)

    if not link:
        return api_response().error("Link not found", 404, "NOT_FOUND")

    try:
        new_slug = None
        if link.is_shortened:
            generator = SlugGenerator()
            new_slug = generator.generate_unique()

        new_link = Link(
            user_id=user_id,
            original_url=link.original_url,
            link_type=link.link_type,
            slug=new_slug,
            title=f"{link.title} (copy)" if link.title else None,
            notes=link.notes,
            folder_id=link.folder_id,
            category_id=link.category_id,
            click_tracking_enabled=link.click_tracking_enabled,
            privacy_level=link.privacy_level,
        )

        db.session.add(new_link)
        db.session.flush()

        for tag in link.tags:
            db.session.add(LinkTag(link_id=new_link.id, tag_id=tag.id))

        db.session.commit()

        return api_response().success(
            data={"link": new_link.to_dict(base_url=base_url)},
            message="Link duplicated",
            status=201
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Link duplicate failed: {e}")
        return api_response().error("Failed to duplicate link", 500)


@links_bp.route("/<link_id>/versions", methods=["GET"])
@jwt_required()
def get_link_versions(link_id: str):
    user_id = get_jwt_identity()
    link = get_user_link(link_id, user_id)

    if not link:
        return api_response().error("Link not found", 404, "NOT_FOUND")

    versions = link.versions.order_by(LinkVersion.created_at.desc()).limit(50).all()

    return api_response().success(data={
        "versions": [v.to_dict() for v in versions]
    })


@links_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_stats():
    user_id = get_jwt_identity()
    base_url = get_public_base_url()

    try:
        total = Link.query.filter_by(user_id=user_id, is_deleted=False).count()
        saved = Link.query.filter_by(user_id=user_id, is_deleted=False, link_type=LinkType.SAVED).count()
        shortened = Link.query.filter_by(user_id=user_id, is_deleted=False, link_type=LinkType.SHORTENED).count()
        active = Link.query.filter_by(user_id=user_id, is_deleted=False, is_active=True).count()
        pinned = Link.query.filter_by(user_id=user_id, is_deleted=False, is_pinned=True).count()
        broken = Link.query.filter_by(user_id=user_id, is_deleted=False, is_broken=True).count()

        total_clicks = db.session.query(db.func.sum(Link.clicks)).filter(
            Link.user_id == user_id,
            Link.is_deleted == False
        ).scalar() or 0

        from datetime import timedelta
        expiring = Link.query.filter(
            Link.user_id == user_id,
            Link.is_deleted == False,
            Link.expires_at.isnot(None),
            Link.expires_at <= datetime.utcnow() + timedelta(days=7),
            Link.expires_at > datetime.utcnow()
        ).count()

        deleted = Link.query.filter_by(user_id=user_id, is_deleted=True).count()

        top_links = Link.query.filter_by(
            user_id=user_id,
            is_deleted=False,
            link_type=LinkType.SHORTENED
        ).order_by(Link.clicks.desc()).limit(5).all()

        recent_links = Link.query.filter_by(
            user_id=user_id,
            is_deleted=False
        ).order_by(Link.created_at.desc()).limit(5).all()

        return api_response().success(data={
            "stats": {
                "total_links": total,
                "saved_links": saved,
                "shortened_links": shortened,
                "active_links": active,
                "inactive_links": total - active,
                "pinned_links": pinned,
                "broken_links": broken,
                "total_clicks": int(total_clicks),
                "expiring_soon": expiring,
                "in_trash": deleted,
            },
            "top_links": [link.to_dict(base_url=base_url) for link in top_links],
            "recent_links": [link.to_dict(base_url=base_url) for link in recent_links]
        })

    except Exception as e:
        logger.error(f"Stats fetch failed: {e}")
        return api_response().error("Failed to get statistics", 500)


@links_bp.route("/check-slug", methods=["GET"])
@jwt_required()
def check_slug():
    slug = request.args.get("slug", "").strip().lower()

    if not slug:
        return api_response().error("Slug is required", 400)

    is_valid, normalized, error = InputValidator.validate_slug(slug)
    if not is_valid:
        return api_response().success(data={"available": False, "reason": error})

    available = SlugGenerator.is_available(normalized)
    return api_response().success(data={"slug": normalized, "available": available})


@links_bp.route("/check-duplicate", methods=["GET"])
@jwt_required()
def check_duplicate():
    user_id = get_jwt_identity()
    url = request.args.get("url", "").strip()
    base_url = get_public_base_url()

    if not url:
        return api_response().error("URL is required", 400)

    is_valid, normalized_url, error = URLValidator.validate(url)
    if not is_valid:
        return api_response().success(data={"valid": False, "reason": error})

    existing = Link.query.filter_by(
        user_id=user_id,
        original_url=normalized_url,
        is_deleted=False
    ).first()

    if existing:
        return api_response().success(data={
            "valid": True,
            "duplicate": True,
            "existing_link": existing.to_dict(base_url=base_url)
        })

    return api_response().success(data={
        "valid": True,
        "duplicate": False,
        "normalized_url": normalized_url
    })


@links_bp.route("/trash", methods=["GET"])
@jwt_required()
def get_trash():
    user_id = get_jwt_identity()
    base_url = get_public_base_url()

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = Link.query.filter_by(user_id=user_id, is_deleted=True)
    query = query.order_by(Link.deleted_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    links = [link.to_dict(base_url=base_url) for link in pagination.items]

    return api_response().success(data={
        "links": links,
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages,
            "total_items": pagination.total,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev
        }
    })


@links_bp.route("/trash/empty", methods=["DELETE"])
@jwt_required()
def empty_trash():
    user_id = get_jwt_identity()

    try:
        deleted = Link.query.filter_by(user_id=user_id, is_deleted=True).all()
        count = len(deleted)

        for link in deleted:
            if link.slug:
                try:
                    RedisService().invalidate_link_cache(link.slug)
                except Exception:
                    pass
            db.session.delete(link)

        db.session.commit()

        logger.info(f"Trash emptied: {count} links by user {user_id}")

        return api_response().success(message=f"Permanently deleted {count} links")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Empty trash failed: {e}")
        return api_response().error("Failed to empty trash", 500)
