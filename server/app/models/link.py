# server/app/models/link.py

import uuid
import enum
from datetime import datetime
from typing import Optional, List

from app.extensions import db


class LinkType(enum.Enum):
    SAVED = "saved"
    SHORTENED = "shortened"


class PrivacyLevel(enum.Enum):
    PRIVATE = "private"
    UNLISTED = "unlisted"
    PUBLIC = "public"


class Link(db.Model):
    __tablename__ = "links"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    link_type = db.Column(db.Enum(LinkType), nullable=False, default=LinkType.SAVED, index=True)
    slug = db.Column(db.String(50), unique=True, nullable=True, index=True)
    original_url = db.Column(db.Text, nullable=False)
    
    title = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    folder_id = db.Column(db.String(36), db.ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True)
    category_id = db.Column(db.String(36), db.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False, index=True)
    pinned_at = db.Column(db.DateTime, nullable=True)
    
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    clicks = db.Column(db.BigInteger, default=0, nullable=False)
    last_clicked_at = db.Column(db.DateTime, nullable=True)
    click_tracking_enabled = db.Column(db.Boolean, default=True, nullable=False)
    
    expires_at = db.Column(db.DateTime, nullable=True, index=True)
    expired_redirect_url = db.Column(db.Text, nullable=True)
    
    favicon_url = db.Column(db.String(512), nullable=True)
    og_title = db.Column(db.String(255), nullable=True)
    og_description = db.Column(db.Text, nullable=True)
    og_image = db.Column(db.String(512), nullable=True)
    
    last_checked_at = db.Column(db.DateTime, nullable=True)
    last_check_status = db.Column(db.Integer, nullable=True)
    is_broken = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    privacy_level = db.Column(db.Enum(PrivacyLevel), default=PrivacyLevel.PRIVATE, nullable=False)
    custom_metadata = db.Column(db.JSON, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tags = db.relationship("Tag", secondary="link_tags", back_populates="links", lazy="selectin")
    folder = db.relationship("Folder", back_populates="links", lazy="joined")
    category = db.relationship("Category", back_populates="links", lazy="joined")
    clicks_history = db.relationship("LinkClick", back_populates="link", lazy="dynamic", cascade="all, delete-orphan")
    versions = db.relationship("LinkVersion", back_populates="link", lazy="dynamic", cascade="all, delete-orphan", order_by="LinkVersion.created_at.desc()")
    shares = db.relationship("SharedLink", back_populates="link", lazy="dynamic", cascade="all, delete-orphan")
    health_checks = db.relationship("LinkHealthCheck", back_populates="link", lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (
        db.Index("idx_links_user_type", "user_id", "link_type"),
        db.Index("idx_links_user_folder", "user_id", "folder_id"),
        db.Index("idx_links_user_pinned", "user_id", "is_pinned"),
        db.Index("idx_links_user_deleted", "user_id", "is_deleted"),
        db.Index("idx_links_user_broken", "user_id", "is_broken"),
        db.Index("idx_links_expires", "expires_at", postgresql_where=db.text("expires_at IS NOT NULL")),
    )

    def __init__(
        self,
        user_id: str,
        original_url: str,
        link_type: LinkType = LinkType.SAVED,
        slug: Optional[str] = None,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        folder_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        **kwargs
    ):
        self.user_id = user_id
        self.original_url = original_url.strip()
        self.link_type = link_type
        self.slug = slug.lower().strip() if slug else None
        self.title = title
        self.notes = notes
        self.folder_id = folder_id
        self.expires_at = expires_at
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @property
    def is_shortened(self) -> bool:
        return self.link_type == LinkType.SHORTENED and self.slug is not None

    @property
    def is_saved(self) -> bool:
        return self.link_type == LinkType.SAVED

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_accessible(self) -> bool:
        return self.is_active and not self.is_expired and not self.is_deleted

    def increment_clicks(self) -> None:
        self.clicks += 1
        self.last_clicked_at = datetime.utcnow()

    def pin(self) -> None:
        self.is_pinned = True
        self.pinned_at = datetime.utcnow()

    def unpin(self) -> None:
        self.is_pinned = False
        self.pinned_at = None

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None

    def get_short_url(self, base_url: str) -> Optional[str]:
        if self.is_shortened and self.slug:
            return f"{base_url}/{self.slug}"
        return None

    def to_dict(self, base_url: str = "") -> dict:
        data = {
            "id": self.id,
            "link_type": self.link_type.value,
            "slug": self.slug,
            "original_url": self.original_url,
            "title": self.title,
            "notes": self.notes,
            "folder_id": self.folder_id,
            "folder": self.folder.to_dict() if self.folder else None,
            "category_id": self.category_id,
            "category": self.category.to_dict() if self.category else None,
            "tags": [tag.to_dict() for tag in self.tags] if self.tags else [],
            "is_active": self.is_active,
            "is_pinned": self.is_pinned,
            "pinned_at": self.pinned_at.isoformat() if self.pinned_at else None,
            "is_deleted": self.is_deleted,
            "clicks": self.clicks,
            "last_clicked_at": self.last_clicked_at.isoformat() if self.last_clicked_at else None,
            "click_tracking_enabled": self.click_tracking_enabled,
            "is_expired": self.is_expired,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "favicon_url": self.favicon_url,
            "og_title": self.og_title,
            "og_description": self.og_description,
            "og_image": self.og_image,
            "is_broken": self.is_broken,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "privacy_level": self.privacy_level.value,
            "custom_metadata": self.custom_metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

        if base_url and self.is_shortened:
            data["short_url"] = f"{base_url}/{self.slug}"

        return data

    def to_cache_dict(self) -> dict:
        return {
            "original_url": self.original_url,
            "is_active": self.is_active,
            "is_deleted": self.is_deleted,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "expired_redirect_url": self.expired_redirect_url,
            "click_tracking_enabled": self.click_tracking_enabled,
        }

    def __repr__(self) -> str:
        return f"<Link {self.slug or self.id[:8]}>"
