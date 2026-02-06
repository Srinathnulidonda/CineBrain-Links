# server/app/routes/auth.py

from flask import Blueprint, request, g
from app.utils.auth import require_auth

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/verify", methods=["POST"])
def verify_token():
    """Verify Firebase token and return user info"""
    from app.services.firebase_auth import FirebaseAuthService
    
    data = request.get_json()
    id_token = data.get("idToken")
    
    if not id_token:
        return current_app.api_response.error(
            "ID token is required",
            400,
            "MISSING_ID_TOKEN"
        )
    
    # Verify Firebase token
    claims = FirebaseAuthService.verify_token(id_token)
    if not claims:
        return current_app.api_response.error(
            "Invalid or expired token",
            401,
            "INVALID_TOKEN"
        )
    
    # Get or create user
    user, error = FirebaseAuthService.get_or_create_user(claims)
    if not user:
        return current_app.api_response.error(
            error or "Authentication failed",
            500,
            "AUTH_ERROR"
        )
    
    return current_app.api_response.success({
        "user": user.to_dict()
    })


@auth_bp.route("/me", methods=["GET"])
@require_auth
def get_current_user():
    """Get current user profile"""
    return current_app.api_response.success({
        "user": g.current_user.to_dict()
    })


@auth_bp.route("/me", methods=["PUT"])
@require_auth
def update_profile():
    """Update user profile"""
    from app.extensions import db
    
    data = request.get_json()
    user = g.current_user
    
    # Update allowed fields
    if "name" in data:
        user.name = data["name"].strip() if data["name"] else None
    
    if "default_click_tracking" in data:
        user.default_click_tracking = bool(data["default_click_tracking"])
    
    if "default_privacy_level" in data:
        if data["default_privacy_level"] in ["private", "unlisted", "public"]:
            user.default_privacy_level = data["default_privacy_level"]
    
    if "data_retention_days" in data:
        days = data["data_retention_days"]
        if days is None or (isinstance(days, int) and 1 <= days <= 365):
            user.data_retention_days = days
    
    db.session.commit()
    
    return current_app.api_response.success({
        "user": user.to_dict(),
        "message": "Profile updated successfully"
    })


@auth_bp.route("/logout", methods=["POST"])
@require_auth
def logout():
    """Logout endpoint (client should delete Firebase token)"""
    # Note: Firebase tokens are stateless, so we just confirm logout
    return current_app.api_response.success({
        "message": "Logged out successfully"
    })