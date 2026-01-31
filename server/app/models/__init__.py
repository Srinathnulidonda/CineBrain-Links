# server/app/models/__init__.py

"""
Database models package.
Import all models here for easy access.
"""

from app.models.user import User
from app.models.link import Link

__all__ = ["User", "Link"]