# server/app/models/link.py

"""
Link model for URL shortening functionality.
"""

import uuid
from datetime import datetime
from typing import Optional

from app.extensions import db


class Link(db.Model):
    """Link model for shortened URLs."""
    
    __tablename__ = "links"
    
    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    slug = db.Column(db.String(50), unique=True, nullable=False, index=True)
    original_url = db.Column(db.Text, nullable=False)
    clicks = db.Column(db.BigInteger, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Optional metadata
    title = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    
    def __init__(
        self,
        user_id: str,
        slug: str,
        original_url: str,
        expires_at: Optional[datetime] = None,
        title: Optional[str] = None,
        description: Optional[str] = None
    ):
        """Initialize a new link."""
        self.user_id = user_id
        self.slug = slug.lower().strip()
        self.original_url = original_url.strip()
        self.expires_at = expires_at
        self.title = title
        self.description = description
    
    @property
    def is_expired(self) -> bool:
        """Check if the link has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_accessible(self) -> bool:
        """Check if the link is accessible for redirection."""
        return self.is_active and not self.is_expired
    
    def increment_clicks(self) -> None:
        """Increment the click counter."""
        self.clicks += 1
    
    def to_dict(self, include_short_url: bool = True, base_url: str = "") -> dict:
        """Serialize link to dictionary."""
        data = {
            "id": self.id,
            "slug": self.slug,
            "original_url": self.original_url,
            "clicks": self.clicks,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "title": self.title,
            "description": self.description
        }
        
        if include_short_url and base_url:
            data["short_url"] = f"{base_url}/{self.slug}"
        
        return data
    
    def to_cache_dict(self) -> dict:
        """Minimal data for Redis cache."""
        return {
            "original_url": self.original_url,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }
    
    def __repr__(self) -> str:
        return f"<Link {self.slug} -> {self.original_url[:50]}...>"