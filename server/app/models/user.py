# server/app/models/user.py

import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    display_name = db.Column(db.String(100), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    default_click_tracking = db.Column(db.Boolean, default=True, nullable=False)
    default_privacy_level = db.Column(db.String(20), default="private", nullable=False)
    data_retention_days = db.Column(db.Integer, nullable=True)

    links = db.relationship("Link", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    folders = db.relationship("Folder", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    tags = db.relationship("Tag", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    templates = db.relationship("LinkTemplate", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    activity_logs = db.relationship("ActivityLog", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def __init__(self, email: str, password: str, display_name: str = None):
        self.email = email.lower().strip()
        self.display_name = display_name
        self.set_password(password)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
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
