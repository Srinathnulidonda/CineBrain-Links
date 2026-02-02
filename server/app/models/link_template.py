import uuid
from datetime import datetime
from typing import Optional

from app.extensions import db


class LinkTemplate(db.Model):
    __tablename__ = "link_templates"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    
    url_pattern = db.Column(db.Text, nullable=True)
    default_title = db.Column(db.String(255), nullable=True)
    default_notes = db.Column(db.Text, nullable=True)
    default_folder_id = db.Column(db.String(36), db.ForeignKey("folders.id", ondelete="SET NULL"), nullable=True)
    default_tags = db.Column(db.JSON, nullable=True)
    default_category_id = db.Column(db.String(36), db.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    
    variables = db.Column(db.JSON, nullable=True)
    
    is_shared = db.Column(db.Boolean, default=False, nullable=False)
    usage_count = db.Column(db.Integer, default=0, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_template_user_name"),
    )

    def __init__(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        url_pattern: Optional[str] = None,
        default_title: Optional[str] = None,
        default_notes: Optional[str] = None,
        default_folder_id: Optional[str] = None,
        default_tags: Optional[list] = None,
        variables: Optional[dict] = None,
    ):
        self.user_id = user_id
        self.name = name.strip()
        self.description = description
        self.url_pattern = url_pattern
        self.default_title = default_title
        self.default_notes = default_notes
        self.default_folder_id = default_folder_id
        self.default_tags = default_tags
        self.variables = variables

    def increment_usage(self) -> None:
        self.usage_count += 1

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "url_pattern": self.url_pattern,
            "default_title": self.default_title,
            "default_notes": self.default_notes,
            "default_folder_id": self.default_folder_id,
            "default_tags": self.default_tags,
            "default_category_id": self.default_category_id,
            "variables": self.variables,
            "is_shared": self.is_shared,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<LinkTemplate {self.name}>"
