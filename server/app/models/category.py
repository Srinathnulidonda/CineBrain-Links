# server/app/models/category.py

import uuid
from datetime import datetime

from app.extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)
    icon = db.Column(db.String(50), nullable=True)
    color = db.Column(db.String(7), nullable=True)
    
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_system = db.Column(db.Boolean, default=True, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    links = db.relationship("Link", back_populates="category", lazy="dynamic")

    def __init__(
        self,
        name: str,
        slug: str,
        description: str = None,
        icon: str = None,
        color: str = None,
        sort_order: int = 0,
    ):
        self.name = name
        self.slug = slug.lower()
        self.description = description
        self.icon = icon
        self.color = color
        self.sort_order = sort_order

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "sort_order": self.sort_order,
        }

    def __repr__(self) -> str:
        return f"<Category {self.name}>"
