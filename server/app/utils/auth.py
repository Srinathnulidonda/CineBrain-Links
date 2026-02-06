# server/app/routes/auth.py

from flask import Blueprint, request, g, current_app
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
    
    try:
        db.session.commit()
        return current_app.api_response.success({
            "user": user.to_dict(),
            "message": "Profile updated successfully"
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Profile update failed: {e}")
        return current_app.api_response.error(
            "Failed to update profile",
            500,
            "UPDATE_FAILED"
        )


@auth_bp.route("/password-reset/request", methods=["POST"])
def request_password_reset():
    """Request password reset for Firebase users"""
    from app.extensions import db
    from app.models.user import User
    from app.services.email_service import get_email_service
    from app.utils.validators import InputValidator
    import secrets
    import hashlib
    from datetime import datetime, timedelta
    
    data = request.get_json()
    email = data.get("email")
    
    if not email:
        return current_app.api_response.error(
            "Email is required",
            400,
            "MISSING_EMAIL"
        )
    
    # Validate email
    is_valid, normalized_email, error = InputValidator.validate_email(email)
    if not is_valid:
        return current_app.api_response.error(
            error,
            400,
            "INVALID_EMAIL"
        )
    
    # Check if user exists
    user = User.query.filter_by(email=normalized_email).first()
    if not user:
        # Always return success for security (don't reveal if email exists)
        return current_app.api_response.success({
            "message": "If an account with that email exists, a password reset link has been sent."
        })
    
    try:
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
        
        # Store reset token in Redis with expiration
        from app.services.redis_service import RedisService
        redis_service = RedisService()
        reset_key = f"password_reset:{token_hash}"
        reset_data = {
            "user_id": user.id,
            "email": user.email,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Token expires in 1 hour
        redis_service.client.setex(reset_key, 3600, str(reset_data))
        
        # Send reset email
        email_service = get_email_service()
        request_info = {
            "ip": request.remote_addr,
            "device": request.headers.get("User-Agent", "Unknown")
        }
        
        email_service.send_password_reset_email(
            to_email=user.email,
            reset_token=reset_token,
            user_name=user.name,
            request_info=request_info
        )
        
        # Log activity
        from app.services.activity_service import ActivityService
        from app.models.activity_log import ActivityType
        ActivityService.log_activity(
            user_id=user.id,
            activity_type=ActivityType.PASSWORD_RESET_REQUESTED,
            resource_type="user",
            resource_id=user.id,
            extra_data={"email": user.email},
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent")
        )
        
        return current_app.api_response.success({
            "message": "If an account with that email exists, a password reset link has been sent."
        })
        
    except Exception as e:
        current_app.logger.error(f"Password reset request failed: {e}")
        return current_app.api_response.error(
            "Failed to process password reset request",
            500,
            "RESET_REQUEST_FAILED"
        )


@auth_bp.route("/password-reset/verify", methods=["POST"])
def verify_reset_token():
    """Verify password reset token"""
    from app.services.redis_service import RedisService
    import hashlib
    import ast
    
    data = request.get_json()
    token = data.get("token")
    
    if not token:
        return current_app.api_response.error(
            "Reset token is required",
            400,
            "MISSING_TOKEN"
        )
    
    try:
        # Hash token to match stored version
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Check if token exists in Redis
        redis_service = RedisService()
        reset_key = f"password_reset:{token_hash}"
        reset_data_str = redis_service.client.get(reset_key)
        
        if not reset_data_str:
            return current_app.api_response.error(
                "Invalid or expired reset token",
                400,
                "INVALID_TOKEN"
            )
        
        # Parse reset data
        reset_data = ast.literal_eval(reset_data_str)
        
        return current_app.api_response.success({
            "message": "Reset token is valid",
            "email": reset_data.get("email")
        })
        
    except Exception as e:
        current_app.logger.error(f"Token verification failed: {e}")
        return current_app.api_response.error(
            "Invalid reset token",
            400,
            "INVALID_TOKEN"
        )


@auth_bp.route("/password-reset/confirm", methods=["POST"])
def confirm_password_reset():
    """Reset password using Firebase Admin SDK"""
    from app.services.redis_service import RedisService
    from app.services.firebase_auth import FirebaseAuthService
    from firebase_admin import auth
    import hashlib
    import ast
    
    data = request.get_json()
    token = data.get("token")
    new_password = data.get("password")
    
    if not token or not new_password:
        return current_app.api_response.error(
            "Reset token and new password are required",
            400,
            "MISSING_FIELDS"
        )
    
    # Validate password
    from app.utils.validators import InputValidator
    is_valid, error = InputValidator.validate_password(new_password)
    if not is_valid:
        return current_app.api_response.error(
            error,
            400,
            "INVALID_PASSWORD"
        )
    
    try:
        # Verify token
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        redis_service = RedisService()
        reset_key = f"password_reset:{token_hash}"
        reset_data_str = redis_service.client.get(reset_key)
        
        if not reset_data_str:
            return current_app.api_response.error(
                "Invalid or expired reset token",
                400,
                "INVALID_TOKEN"
            )
        
        reset_data = ast.literal_eval(reset_data_str)
        user_email = reset_data.get("email")
        
        # Initialize Firebase Admin if needed
        FirebaseAuthService.initialize()
        
        # Get Firebase user by email
        firebase_user = auth.get_user_by_email(user_email)
        
        # Update password in Firebase
        auth.update_user(firebase_user.uid, password=new_password)
        
        # Delete used token
        redis_service.client.delete(reset_key)
        
        # Log activity
        from app.models.user import User
        user = User.query.filter_by(email=user_email).first()
        if user:
            from app.services.activity_service import ActivityService
            from app.models.activity_log import ActivityType
            ActivityService.log_activity(
                user_id=user.id,
                activity_type=ActivityType.PASSWORD_RESET_COMPLETED,
                resource_type="user",
                resource_id=user.id,
                extra_data={"email": user_email},
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent")
            )
        
        return current_app.api_response.success({
            "message": "Password has been reset successfully"
        })
        
    except Exception as e:
        current_app.logger.error(f"Password reset failed: {e}")
        return current_app.api_response.error(
            "Failed to reset password",
            500,
            "RESET_FAILED"
        )


@auth_bp.route("/logout", methods=["POST"])
@require_auth
def logout():
    """Logout endpoint (client should delete Firebase token)"""
    # Log activity
    try:
        from app.services.activity_service import ActivityService
        from app.models.activity_log import ActivityType
        ActivityService.log_activity(
            user_id=g.current_user.id,
            activity_type=ActivityType.USER_LOGOUT,
            resource_type="user",
            resource_id=g.current_user.id,
            extra_data={"email": g.current_user.email},
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent")
        )
    except Exception as e:
        current_app.logger.warning(f"Failed to log logout activity: {e}")
    
    return current_app.api_response.success({
        "message": "Logged out successfully"
    })


@auth_bp.route("/delete-account", methods=["POST"])
@require_auth
def delete_account():
    """Delete user account - requires Firebase token verification"""
    from app.extensions import db
    from app.services.activity_service import ActivityService
    from app.models.activity_log import ActivityType
    from app.services.firebase_auth import FirebaseAuthService
    from firebase_admin import auth
    
    user = g.current_user
    user_id = user.id
    email = user.email
    firebase_uid = user.firebase_uid
    
    try:
        # Log account deletion before deleting
        ActivityService.log_activity(
            user_id=user_id,
            activity_type=ActivityType.ACCOUNT_DELETED,
            resource_type="user",
            resource_id=user_id,
            extra_data={"email": email},
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent")
        )
        
        # Delete from Firebase (optional - user can also delete from Firebase console)
        if firebase_uid:
            try:
                FirebaseAuthService.initialize()
                auth.delete_user(firebase_uid)
            except Exception as e:
                current_app.logger.warning(f"Failed to delete Firebase user: {e}")
        
        # Soft delete or hard delete user (depending on your requirements)
        user.is_active = False
        user.email = f"deleted_{user_id}@deleted.local"  # Anonymize
        user.name = None
        user.avatar_url = None
        
        # Or hard delete (uncomment if you prefer):
        # db.session.delete(user)
        
        db.session.commit()
        
        # Send account deletion confirmation email
        try:
            from app.services.email_service import get_email_service
            email_service = get_email_service()
            email_service.send_account_deletion_email(
                to_email=email,
                user_name=user.name or email.split("@")[0]
            )
        except Exception as e:
            current_app.logger.warning(f"Failed to send deletion confirmation email: {e}")
        
        return current_app.api_response.success({
            "message": "Account deleted successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Account deletion failed: {e}")
        return current_app.api_response.error(
            "Failed to delete account",
            500,
            "DELETE_FAILED"
        )


@auth_bp.route("/stats", methods=["GET"])
@require_auth
def get_user_stats():
    """Get user statistics"""
    user = g.current_user
    
    try:
        # Get user statistics
        stats = {
            "total_links": user.links.filter_by(is_deleted=False).count(),
            "total_folders": user.folders.count(),
            "total_tags": user.tags.count(),
            "total_clicks": db.session.query(db.func.sum(user.links.filter_by(is_deleted=False).subquery().c.clicks)).scalar() or 0,
            "active_links": user.links.filter_by(is_deleted=False, is_active=True).count(),
            "pinned_links": user.links.filter_by(is_deleted=False, is_pinned=True).count(),
            "broken_links": user.links.filter_by(is_deleted=False, is_broken=True).count(),
        }
        
        # Get recent activity count
        from datetime import datetime, timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        stats["recent_activity"] = user.activity_logs.filter(
            user.activity_logs.c.created_at >= week_ago
        ).count()
        
        return current_app.api_response.success({
            "stats": stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get user stats: {e}")
        return current_app.api_response.error(
            "Failed to retrieve user statistics",
            500,
            "STATS_ERROR"
        )


@auth_bp.route("/sessions", methods=["GET"])
@require_auth
def get_user_sessions():
    """Get user login sessions (Firebase doesn't track sessions, so return current session info)"""
    user = g.current_user
    claims = g.token_claims
    
    try:
        session_info = {
            "current_session": {
                "user_id": user.id,
                "email": user.email,
                "login_time": claims.get("iat"),
                "expires_at": claims.get("exp"),
                "auth_provider": user.auth_provider,
                "firebase_uid": user.firebase_uid
            }
        }
        
        return current_app.api_response.success(session_info)
        
    except Exception as e:
        current_app.logger.error(f"Failed to get session info: {e}")
        return current_app.api_response.error(
            "Failed to retrieve session information",
            500,
            "SESSION_ERROR"
        )