# server/app/models/activity_log.py

import uuid
import enum
from datetime import datetime
from typing import Optional

from app.extensions import db


class ActivityType(enum.Enum):
    # User activities
    USER_REGISTERED = "user_registered"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_UPDATED = "user_updated"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_CHANGED = "password_changed"
    
    # Link activities
    LINK_CREATED = "link_created"
    LINK_UPDATED = "link_updated"
    LINK_DELETED = "link_deleted"
    LINK_RESTORED = "link_restored"
    LINK_CLICKED = "link_clicked"
    LINK_SHARED = "link_shared"
    
    # Folder activities
    FOLDER_CREATED = "folder_created"
    FOLDER_UPDATED = "folder_updated"
    FOLDER_DELETED = "folder_deleted"
    
    # Tag activities
    TAG_CREATED = "tag_created"
    TAG_DELETED = "tag_deleted"
    
    # Bulk operations
    BULK_OPERATION = "bulk_operation"


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    activity_type = db.Column(db.Enum(ActivityType), nullable=False, index=True)

    resource_type = db.Column(db.String(50), nullable=False)
    resource_id = db.Column(db.String(36), nullable=True, index=True)
    resource_title = db.Column(db.String(255), nullable=True)

    extra_data = db.Column(db.JSON, nullable=True)

    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        db.Index("idx_activity_user_date", "user_id", "created_at"),
        db.Index("idx_activity_user_type", "user_id", "activity_type"),
    )

    def __init__(
        self,
        user_id: str,
        activity_type: ActivityType,
        resource_type: str,
        resource_id: Optional[str] = None,
        resource_title: Optional[str] = None,
        extra_data: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        self.user_id = user_id
        self.activity_type = activity_type
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.resource_title = resource_title
        self.extra_data = extra_data
        self.ip_address = ip_address
        self.user_agent = user_agent

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "activity_type": self.activity_type.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_title": self.resource_title,
            "metadata": self.extra_data,  # Keep 'metadata' in API response for compatibility
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<ActivityLog {self.activity_type.value}>"