# server/app/routes/__init__.py

from app.routes.auth import auth_bp
from app.routes.links import links_bp
from app.routes.redirect import redirect_bp
from app.routes.folders import folders_bp
from app.routes.tags import tags_bp
from app.routes.analytics import analytics_bp
from app.routes.sharing import sharing_bp
from app.routes.health import health_bp
from app.routes.bulk import bulk_bp
from app.routes.activity import activity_bp
from app.routes.templates import templates_bp
from app.routes.categories import categories_bp
from app.routes.search import search_bp

__all__ = [
    "auth_bp",
    "links_bp",
    "redirect_bp",
    "folders_bp",
    "tags_bp",
    "analytics_bp",
    "sharing_bp",
    "health_bp",
    "bulk_bp",
    "activity_bp",
    "templates_bp",
    "categories_bp",
    "search_bp",
]