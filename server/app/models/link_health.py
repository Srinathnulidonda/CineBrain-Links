# server/app/models/link_health.py

import uuid
from datetime import datetime
from typing import Optional

from app.extensions import db


class LinkHealthCheck(db.Model):
    __tablename__ = "link_health_checks"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    link_id = db.Column(db.String(36), db.ForeignKey("links.id", ondelete="CASCADE"), nullable=False, index=True)
    
    status_code = db.Column(db.Integer, nullable=True)
    response_time_ms = db.Column(db.Integer, nullable=True)
    is_healthy = db.Column(db.Boolean, nullable=False)
    error_message = db.Column(db.String(255), nullable=True)
    
    checked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    link = db.relationship("Link", back_populates="health_checks")

    __table_args__ = (
        db.Index("idx_health_link_date", "link_id", "checked_at"),
    )

    def __init__(
        self,
        link_id: str,
        is_healthy: bool,
        status_code: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ):
        self.link_id = link_id
        self.is_healthy = is_healthy
        self.status_code = status_code
        self.response_time_ms = response_time_ms
        self.error_message = error_message

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "is_healthy": self.is_healthy,
            "error_message": self.error_message,
            "checked_at": self.checked_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<LinkHealthCheck {self.link_id[:8]} {'OK' if self.is_healthy else 'FAIL'}>"
