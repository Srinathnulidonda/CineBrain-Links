# server/app/routes/__init__.py

"""
Routes package.
"""

from app.routes.auth import auth_bp
from app.routes.links import links_bp
from app.routes.redirect import redirect_bp

__all__ = ["auth_bp", "links_bp", "redirect_bp"]