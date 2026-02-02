# server/app/models/tag.py

import uuid
from datetime import datetime
from typing import Optional

from app.extensions import db


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(7), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    links = db.relationship("Link", secondary="link_tags", back_populates="tags", lazy="dynamic")

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_tag_user_name"),
        db.Index("idx_tag_user_name", "user_id", "name"),
    )

    def __init__(self, user_id: str, name: str, color: Optional[str] = None):
        self.user_id = user_id
        self.name = name.strip().lower()
        self.color = color

    @property
    def usage_count(self) -> int:
        return self.links.filter_by(is_deleted=False).count()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Tag {self.name}>"


class LinkTag(db.Model):
    __tablename__ = "link_tags"

    link_id = db.Column(db.String(36), db.ForeignKey("links.id", ondelete="CASCADE"), primary_key=True)
    tag_id = db.Column(db.String(36), db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.Index("idx_linktag_link", "link_id"),
        db.Index("idx_linktag_tag", "tag_id"),
    )
