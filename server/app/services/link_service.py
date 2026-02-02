# server/app/services/link_service.py

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

from flask import current_app

from app.extensions import db
from app.models.link import Link, LinkType, PrivacyLevel
from app.models.link_version import LinkVersion
from app.models.tag import Tag, LinkTag
from app.models.folder import Folder
from app.services.redis_service import RedisService
from app.services.metadata_service import MetadataService
from app.services.activity_service import ActivityService
from app.models.activity_log import ActivityType
from app.utils.slug import SlugGenerator
from app.utils.validators import URLValidator
from app.utils.base_url import get_public_base_url

logger = logging.getLogger(__name__)


class LinkService:

    @staticmethod
    def create_link(
        user_id: str,
        original_url: str,
        link_type: LinkType = LinkType.SAVED,
        custom_slug: Optional[str] = None,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        folder_id: Optional[str] = None,
        tag_ids: Optional[List[str]] = None,
        category_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        is_pinned: bool = False,
        click_tracking: bool = True,
        privacy_level: PrivacyLevel = PrivacyLevel.PRIVATE,
        custom_metadata: Optional[dict] = None,
        fetch_metadata: bool = True
    ) -> Tuple[Optional[Link], Optional[str], Optional[dict]]:

        is_valid, normalized_url, error = URLValidator.validate(original_url)
        if not is_valid:
            return None, error, None

        slug = None
        if link_type == LinkType.SHORTENED:
            if custom_slug:
                from app.utils.validators import InputValidator
                is_valid, normalized_slug, error = InputValidator.validate_slug(custom_slug)
                if not is_valid:
                    return None, error, None

                if not SlugGenerator.is_available(normalized_slug):
                    return None, "This short link is already taken", None

                slug = normalized_slug
            else:
                generator = SlugGenerator()
                slug = generator.generate_unique()
                if not slug:
                    return None, "Could not generate short link", None

        if folder_id:
            folder = Folder.query.filter_by(id=folder_id, user_id=user_id).first()
            if not folder:
                return None, "Folder not found", None

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
                    db.session.add(LinkTag(link_id=link.id, tag_id=tag.id))

            db.session.commit()

            if link.is_shortened:
                try:
                    RedisService().cache_link(slug, link.to_cache_dict())
                except Exception:
                    pass

            ActivityService.log(
                user_id=user_id,
                activity_type=ActivityType.LINK_CREATED,
                resource_type="link",
                resource_id=link.id,
                resource_title=link.title or link.original_url[:50],
                metadata={"link_type": link_type.value}
            )

            if fetch_metadata:
                MetadataService.update_link_metadata(link, async_update=True)

            return link, None, duplicate_warning

        except Exception as e:
            db.session.rollback()
            logger.error(f"Link creation failed: {e}")
            return None, "Failed to create link", None

    @staticmethod
    def update_link(
        link: Link,
        user_id: str,
        updates: dict
    ) -> Tuple[Optional[Link], Optional[str]]:
        changes = []

        try:
            if "original_url" in updates and updates["original_url"] != link.original_url:
                is_valid, normalized_url, error = URLValidator.validate(updates["original_url"])
                if not is_valid:
                    return None, error

                version = LinkVersion(
                    link_id=link.id,
                    previous_url=link.original_url,
                    previous_slug=link.slug,
                    previous_title=link.title,
                    changed_by=user_id,
                    change_reason=updates.get("change_reason")
                )
                db.session.add(version)

                link.original_url = normalized_url
                changes.append("url")

            if "slug" in updates and link.is_shortened:
                new_slug = updates["slug"].strip().lower() if updates["slug"] else None

                if new_slug and new_slug != link.slug:
                    from app.utils.validators import InputValidator
                    is_valid, normalized_slug, error = InputValidator.validate_slug(new_slug)
                    if not is_valid:
                        return None, error

                    if not SlugGenerator.is_available(normalized_slug):
                        return None, "This short link is already taken"

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
                    changes.append("slug")

            simple_fields = ["title", "notes", "folder_id", "category_id", "is_active"]
            for field in simple_fields:
                if field in updates:
                    setattr(link, field, updates[field])
                    changes.append(field)

            if "is_pinned" in updates:
                if updates["is_pinned"] and not link.is_pinned:
                    link.pin()
                elif not updates["is_pinned"] and link.is_pinned:
                    link.unpin()
                changes.append("is_pinned")

            if "tag_ids" in updates:
                LinkTag.query.filter_by(link_id=link.id).delete()
                for tag_id in updates["tag_ids"]:
                    tag = Tag.query.filter_by(id=tag_id, user_id=user_id).first()
                    if tag:
                        db.session.add(LinkTag(link_id=link.id, tag_id=tag.id))
                changes.append("tags")

            if "expires_at" in updates:
                if updates["expires_at"] is None:
                    link.expires_at = None
                else:
                    try:
                        expires_at = datetime.fromisoformat(
                            updates["expires_at"].replace("Z", "+00:00")
                        )
                        if expires_at <= datetime.utcnow():
                            return None, "Expiration must be in the future"
                        link.expires_at = expires_at
                    except (ValueError, TypeError):
                        return None, "Invalid expiration date format"
                changes.append("expires_at")

            if "click_tracking_enabled" in updates:
                link.click_tracking_enabled = bool(updates["click_tracking_enabled"])

            if "privacy_level" in updates:
                try:
                    link.privacy_level = PrivacyLevel(updates["privacy_level"])
                except ValueError:
                    pass

            if "metadata" in updates:
                link.custom_metadata = updates["metadata"]

            db.session.commit()

            if link.is_shortened and link.slug:
                try:
                    RedisService().cache_link(link.slug, link.to_cache_dict())
                except Exception:
                    pass

            if changes:
                ActivityService.log(
                    user_id=user_id,
                    activity_type=ActivityType.LINK_UPDATED,
                    resource_type="link",
                    resource_id=link.id,
                    resource_title=link.title or link.original_url[:50],
                    metadata={"changes": changes}
                )

            return link, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Link update failed: {e}")
            return None, "Failed to update link"

    @staticmethod
    def delete_link(link: Link, user_id: str, permanent: bool = False) -> Tuple[bool, Optional[str]]:
        try:
            slug = link.slug

            if permanent:
                db.session.delete(link)
            else:
                link.soft_delete()

            db.session.commit()

            if slug:
                try:
                    RedisService().invalidate_link_cache(slug)
                except Exception:
                    pass

            activity_type = ActivityType.LINK_DELETED
            ActivityService.log(
                user_id=user_id,
                activity_type=activity_type,
                resource_type="link",
                resource_id=link.id,
                resource_title=link.title or link.original_url[:50],
                metadata={"permanent": permanent}
            )

            return True, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Link deletion failed: {e}")
            return False, "Failed to delete link"

    @staticmethod
    def restore_link(link: Link, user_id: str) -> Tuple[bool, Optional[str]]:
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

            return True, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Link restore failed: {e}")
            return False, "Failed to restore link"

    @staticmethod
    def duplicate_link(link: Link, user_id: str) -> Tuple[Optional[Link], Optional[str]]:
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

            return new_link, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Link duplicate failed: {e}")
            return None, "Failed to duplicate link"

    @staticmethod
    def get_user_stats(user_id: str, use_cache: bool = True) -> dict:
        if use_cache:
            try:
                cached = RedisService().get_cached_user_stats(user_id)
                if cached:
                    return cached
            except Exception:
                pass

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

        expiring = Link.query.filter(
            Link.user_id == user_id,
            Link.is_deleted == False,
            Link.expires_at.isnot(None),
            Link.expires_at <= datetime.utcnow() + timedelta(days=7),
            Link.expires_at > datetime.utcnow()
        ).count()

        deleted = Link.query.filter_by(user_id=user_id, is_deleted=True).count()

        stats = {
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
        }

        try:
            RedisService().cache_user_stats(user_id, stats, ttl=300)
        except Exception:
            pass

        return stats

    @staticmethod
    def check_expiring_links(hours_before: int = 24) -> List[Link]:
        threshold = datetime.utcnow() + timedelta(hours=hours_before)

        return Link.query.filter(
            Link.is_deleted == False,
            Link.is_active == True,
            Link.expires_at.isnot(None),
            Link.expires_at <= threshold,
            Link.expires_at > datetime.utcnow()
        ).all()

    @staticmethod
    def auto_disable_expired() -> int:
        expired = Link.query.filter(
            Link.is_deleted == False,
            Link.is_active == True,
            Link.expires_at.isnot(None),
            Link.expires_at <= datetime.utcnow()
        ).all()

        count = 0
        for link in expired:
            link.is_active = False
            if link.slug:
                try:
                    RedisService().invalidate_link_cache(link.slug)
                except Exception:
                    pass
            count += 1

        if count > 0:
            db.session.commit()
            logger.info(f"Auto-disabled {count} expired links")

        return count

