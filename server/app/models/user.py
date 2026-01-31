# server/app/models/user.py

"""
User model for authentication and user management.
"""

import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(db.Model):
    """User model for authentication."""
    
    __tablename__ = "users"
    
    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationships
    links = db.relationship(
        "Link",
        backref="owner",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    
    def __init__(self, email: str, password: str):
        """Initialize user with email and password."""
        self.email = email.lower().strip()
        self.set_password(password)
    
    def set_password(self, password: str) -> None:
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(
            password,
            method="pbkdf2:sha256",
            salt_length=16
        )
    
    def check_password(self, password: str) -> bool:
        """Verify the user's password."""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self) -> dict:
        """Serialize user to dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "links_count": self.links.count()
        }
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"