# server/app/models/user.py

import uuid
from datetime import datetime

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True)  # Supabase UUID
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    
    # Profile fields from Supabase
    name = db.Column(db.String(100), nullable=True)
    avatar_url = db.Column(db.String(512), nullable=True)
    auth_provider = db.Column(db.String(20), nullable=False, default="email")  # "email" or "google"
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    
    # User preferences
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=True, nullable=False)  # Supabase handles verification
    default_click_tracking = db.Column(db.Boolean, default=True, nullable=False)
    default_privacy_level = db.Column(db.String(20), default="private", nullable=False)
    data_retention_days = db.Column(db.Integer, nullable=True)

    # Relationships
    links = db.relationship("Link", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    folders = db.relationship("Folder", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    tags = db.relationship("Tag", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    templates = db.relationship("LinkTemplate", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    activity_logs = db.relationship("ActivityLog", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def __init__(self, id: str, email: str, name: str = None, avatar_url: str = None, auth_provider: str = "email"):
        self.id = id  # Use Supabase UUID directly
        self.email = email.lower().strip()
        self.name = name
        self.avatar_url = avatar_url
        self.auth_provider = auth_provider

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "auth_provider": self.auth_provider,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "links_count": self.links.filter_by(is_deleted=False).count(),
            "folders_count": self.folders.count(),
            "preferences": {
                "default_click_tracking": self.default_click_tracking,
                "default_privacy_level": self.default_privacy_level,
                "data_retention_days": self.data_retention_days,
            }
        }

    def __repr__(self) -> str:
        return f"<User {self.email}>"