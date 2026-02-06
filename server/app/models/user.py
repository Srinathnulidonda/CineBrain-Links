# server/app/models/user.py

import uuid
from datetime import datetime

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    # Use UUID as primary key for Supabase compatibility
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Firebase UID for authentication
    firebase_uid = db.Column(db.String(255), unique=True, nullable=True, index=True)
    
    # User profile
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=True)
    avatar_url = db.Column(db.String(512), nullable=True)
    auth_provider = db.Column(db.String(20), nullable=False, default="email")  # "email" or "google"
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    
    # User preferences
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=True, nullable=False)  # Firebase handles verification
    default_click_tracking = db.Column(db.Boolean, default=True, nullable=False)
    default_privacy_level = db.Column(db.String(20), default="private", nullable=False)
    data_retention_days = db.Column(db.Integer, nullable=True)

    # Relationships
    links = db.relationship("Link", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    folders = db.relationship("Folder", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    tags = db.relationship("Tag", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    templates = db.relationship("LinkTemplate", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    activity_logs = db.relationship("ActivityLog", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def __init__(self, firebase_uid: str = None, email: str = None, name: str = None, 
                 avatar_url: str = None, auth_provider: str = "email"):
        self.firebase_uid = firebase_uid
        self.email = email.lower().strip() if email else None
        self.name = name
        self.avatar_url = avatar_url
        self.auth_provider = auth_provider

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "firebase_uid": self.firebase_uid,
            "email": self.email,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "auth_provider": self.auth_provider,
            "created_at": self.created_at.isoformat(),
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
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