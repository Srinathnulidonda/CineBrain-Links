# server/app/models/user.py

import uuid
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    
    # Password hash for local auth
    password_hash = db.Column(db.String(255), nullable=True)
    
    # Profile fields
    name = db.Column(db.String(100), nullable=True)
    avatar_url = db.Column(db.String(512), nullable=True)
    auth_provider = db.Column(db.String(20), nullable=False, default="email")
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    
    # User preferences and status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    default_click_tracking = db.Column(db.Boolean, default=True, nullable=False)
    default_privacy_level = db.Column(db.String(20), default="private", nullable=False)
    data_retention_days = db.Column(db.Integer, nullable=True)
    
    # Account security
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    last_failed_login = db.Column(db.DateTime, nullable=True)
    password_changed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    links = db.relationship("Link", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    folders = db.relationship("Folder", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    tags = db.relationship("Tag", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    templates = db.relationship("LinkTemplate", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    activity_logs = db.relationship("ActivityLog", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def __init__(self, email: str, password: str = None, name: str = None, avatar_url: str = None, auth_provider: str = "email"):
        # Email is required and must be valid
        if not email:
            raise ValueError("Email is required")
        
        self.email = str(email).lower().strip()
        self.name = name or self.email.split("@")[0].replace(".", " ").title()
        self.avatar_url = avatar_url
        self.auth_provider = auth_provider or "email"
        
        # Set password if provided
        if password:
            self.set_password(password)

    def set_password(self, password: str) -> None:
        """Set user password hash"""
        if not password:
            raise ValueError("Password cannot be empty")
        
        self.password_hash = generate_password_hash(password)
        self.password_changed_at = datetime.utcnow()

    def check_password(self, password: str) -> bool:
        """Check if provided password matches stored hash"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def verify_email(self) -> None:
        """Mark email as verified"""
        self.email_verified = True
        self.updated_at = datetime.utcnow()

    def record_login_attempt(self, successful: bool) -> None:
        """Record login attempt"""
        if successful:
            self.failed_login_attempts = 0
            self.last_failed_login = None
            self.last_login_at = datetime.utcnow()
        else:
            self.failed_login_attempts += 1
            self.last_failed_login = datetime.utcnow()

    def is_account_locked(self) -> bool:
        """Check if account is locked due to failed attempts"""
        if self.failed_login_attempts < 5:
            return False
        
        if not self.last_failed_login:
            return False
        
        # Lock for 15 minutes after 5 failed attempts
        from datetime import timedelta
        lockout_time = timedelta(minutes=15)
        return datetime.utcnow() < self.last_failed_login + lockout_time

    def unlock_account(self) -> None:
        """Unlock account by resetting failed attempts"""
        self.failed_login_attempts = 0
        self.last_failed_login = None

    def deactivate(self) -> None:
        """Deactivate user account"""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate user account"""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def to_dict(self, include_sensitive: bool = False) -> dict:
        try:
            links_count = self.links.filter_by(is_deleted=False).count() if hasattr(self, 'links') else 0
        except:
            links_count = 0
        
        try:
            folders_count = self.folders.count() if hasattr(self, 'folders') else 0
        except:
            folders_count = 0
        
        data = {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "auth_provider": self.auth_provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "links_count": links_count,
            "folders_count": folders_count,
            "preferences": {
                "default_click_tracking": self.default_click_tracking,
                "default_privacy_level": self.default_privacy_level,
                "data_retention_days": self.data_retention_days,
            }
        }
        
        if include_sensitive:
            data.update({
                "failed_login_attempts": self.failed_login_attempts,
                "last_failed_login": self.last_failed_login.isoformat() if self.last_failed_login else None,
                "password_changed_at": self.password_changed_at.isoformat() if self.password_changed_at else None,
                "is_account_locked": self.is_account_locked()
            })
        
        return data

    def __repr__(self) -> str:
        return f"<User {self.email}>"