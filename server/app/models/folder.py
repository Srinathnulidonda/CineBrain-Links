# server/app/models/folder.py

import uuid
from datetime import datetime
from typing import Optional

from app.extensions import db


class Folder(db.Model):
    __tablename__ = "folders"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    color = db.Column(db.String(7), nullable=True)
    icon = db.Column(db.String(50), nullable=True)
    
    parent_id = db.Column(db.String(36), db.ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    links = db.relationship("Link", back_populates="folder", lazy="dynamic")
    children = db.relationship("Folder", backref=db.backref("parent", remote_side=[id]), lazy="selectin")

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_folder_user_name"),
        db.Index("idx_folder_user_order", "user_id", "sort_order"),
    )

    def __init__(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        parent_id: Optional[str] = None,
        sort_order: int = 0,
    ):
        self.user_id = user_id
        self.name = name.strip()
        self.description = description
        self.color = color
        self.icon = icon
        self.parent_id = parent_id
        self.sort_order = sort_order

    @property
    def link_count(self) -> int:
        return self.links.filter_by(is_deleted=False).count()

    def to_dict(self, include_children: bool = False) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "icon": self.icon,
            "parent_id": self.parent_id,
            "sort_order": self.sort_order,
            "is_default": self.is_default,
            "link_count": self.link_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        
        if include_children:
            data["children"] = [child.to_dict() for child in self.children]
        
        return data

    def __repr__(self) -> str:
        return f"<Folder {self.name}>"
