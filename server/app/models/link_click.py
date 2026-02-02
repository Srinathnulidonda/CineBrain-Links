# server/app/models/link_click.py

import uuid
from datetime import datetime
from typing import Optional

from app.extensions import db


class LinkClick(db.Model):
    __tablename__ = "link_clicks"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    link_id = db.Column(db.String(36), db.ForeignKey("links.id", ondelete="CASCADE"), nullable=False, index=True)
    
    clicked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    ip_hash = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)
    referrer = db.Column(db.String(512), nullable=True)
    referrer_domain = db.Column(db.String(255), nullable=True, index=True)
    
    device_type = db.Column(db.String(20), nullable=True)
    browser = db.Column(db.String(50), nullable=True)
    os = db.Column(db.String(50), nullable=True)
    
    country_code = db.Column(db.String(2), nullable=True, index=True)
    
    link = db.relationship("Link", back_populates="clicks_history")

    __table_args__ = (
        db.Index("idx_click_link_date", "link_id", "clicked_at"),
        db.Index("idx_click_date", "clicked_at"),
    )

    def __init__(
        self,
        link_id: str,
        ip_hash: Optional[str] = None,
        user_agent: Optional[str] = None,
        referrer: Optional[str] = None,
        country_code: Optional[str] = None,
        **kwargs
    ):
        self.link_id = link_id
        self.ip_hash = ip_hash
        self.user_agent = user_agent
        self.referrer = referrer
        self.country_code = country_code
        
        if referrer:
            try:
                from urllib.parse import urlparse
                self.referrer_domain = urlparse(referrer).netloc
            except Exception:
                pass
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "clicked_at": self.clicked_at.isoformat(),
            "referrer_domain": self.referrer_domain,
            "device_type": self.device_type,
            "browser": self.browser,
            "os": self.os,
            "country_code": self.country_code,
        }

    def __repr__(self) -> str:
        return f"<LinkClick {self.link_id[:8]}>"
