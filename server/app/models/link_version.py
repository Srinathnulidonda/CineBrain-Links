# server/app/models/link_version.py

import uuid
from datetime import datetime

from app.extensions import db


class LinkVersion(db.Model):
    __tablename__ = "link_versions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    link_id = db.Column(db.String(36), db.ForeignKey("links.id", ondelete="CASCADE"), nullable=False, index=True)
    
    previous_url = db.Column(db.Text, nullable=False)
    previous_slug = db.Column(db.String(50), nullable=True)
    previous_title = db.Column(db.String(255), nullable=True)
    
    changed_by = db.Column(db.String(36), nullable=True)
    change_reason = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    link = db.relationship("Link", back_populates="versions")

    def __init__(
        self,
        link_id: str,
        previous_url: str,
        previous_slug: str = None,
        previous_title: str = None,
        changed_by: str = None,
        change_reason: str = None,
    ):
        self.link_id = link_id
        self.previous_url = previous_url
        self.previous_slug = previous_slug
        self.previous_title = previous_title
        self.changed_by = changed_by
        self.change_reason = change_reason

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "previous_url": self.previous_url,
            "previous_slug": self.previous_slug,
            "previous_title": self.previous_title,
            "change_reason": self.change_reason,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<LinkVersion {self.id[:8]}>"