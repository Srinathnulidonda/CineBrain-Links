# server/app/models/shared_link.py

import uuid
import secrets
from datetime import datetime
from typing import Optional

from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class SharedLink(db.Model):
    __tablename__ = "shared_links"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    link_id = db.Column(db.String(36), db.ForeignKey("links.id", ondelete="CASCADE"), nullable=False, index=True)
    
    share_token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    
    expires_at = db.Column(db.DateTime, nullable=True)
    max_views = db.Column(db.Integer, nullable=True)
    view_count = db.Column(db.Integer, default=0, nullable=False)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_viewed_at = db.Column(db.DateTime, nullable=True)

    link = db.relationship("Link", back_populates="shares")

    def __init__(
        self,
        link_id: str,
        password: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        max_views: Optional[int] = None,
    ):
        self.link_id = link_id
        self.share_token = secrets.token_urlsafe(32)
        self.expires_at = expires_at
        self.max_views = max_views
        
        if password:
            self.set_password(password)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return True
        return check_password_hash(self.password_hash, password)

    @property
    def is_expired(self) -> bool:
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        if self.max_views and self.view_count >= self.max_views:
            return True
        return False

    @property
    def is_accessible(self) -> bool:
        return self.is_active and not self.is_expired

    @property
    def has_password(self) -> bool:
        return self.password_hash is not None

    def record_view(self) -> None:
        self.view_count += 1
        self.last_viewed_at = datetime.utcnow()

    def revoke(self) -> None:
        self.is_active = False

    def get_share_url(self, base_url: str) -> str:
        return f"{base_url}/s/{self.share_token}"

    def to_dict(self, base_url: str = "") -> dict:
        data = {
            "id": self.id,
            "share_token": self.share_token,
            "has_password": self.has_password,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "max_views": self.max_views,
            "view_count": self.view_count,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "created_at": self.created_at.isoformat(),
            "last_viewed_at": self.last_viewed_at.isoformat() if self.last_viewed_at else None,
        }
        
        if base_url:
            data["share_url"] = self.get_share_url(base_url)
        
        return data

    def __repr__(self) -> str:
        return f"<SharedLink {self.share_token[:8]}>"
