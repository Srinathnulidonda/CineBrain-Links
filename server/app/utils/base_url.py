# server/app/utils/base_url.py

from flask import current_app


def get_public_base_url() -> str:
    return current_app.config.get("PUBLIC_BASE_URL", "https://savlink.vercel.app")


def get_backend_base_url() -> str:
    return current_app.config.get("BASE_URL", "https://savlink.vercel.app")


def get_frontend_url() -> str:
    return current_app.config.get("FRONTEND_URL", "https://savlink.vercel.app")


def build_short_url(slug: str) -> str:
    base = get_public_base_url().rstrip("/")
    return f"{base}/{slug}"


def build_share_url(share_token: str) -> str:
    base = get_public_base_url().rstrip("/")
    return f"{base}/s/{share_token}"


def build_qr_url(slug: str) -> str:
    base = get_public_base_url().rstrip("/")
    return f"{base}/{slug}"


def build_dashboard_url(path: str = "") -> str:
    frontend = get_frontend_url().rstrip("/")
    if path:
        return f"{frontend}/dashboard/{path.lstrip('/')}"
    return f"{frontend}/dashboard"


def build_reset_url(token: str) -> str:
    frontend = get_frontend_url().rstrip("/")
    return f"{frontend}/reset-password?token={token}"


def is_internal_url(url: str) -> bool:
    public_base = get_public_base_url().lower()
    backend_base = get_backend_base_url().lower()
    url_lower = url.lower()
    
    return url_lower.startswith(public_base) or url_lower.startswith(backend_base)
