# server/app/routes/auth.py

import logging
from datetime import datetime, timedelta
from typing import Optional

from flask import Blueprint, request, g, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.extensions import db, limiter
from app.models.user import User
from app.models.activity_log import ActivityLog, ActivityType
from app.services.supabase_auth import SupabaseAuthService
from app.services.email_service import get_email_service
from app.services.redis_service import RedisService
from app.services.activity_service import ActivityService
from app.utils.validators import InputValidator
from app.utils.auth import require_auth
from app.utils.helpers import mask_email, hash_string

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per hour")
def register():
    """Register a new user with email and password"""
    try:
        data = request.get_json()
        
        # Validate input
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        name = data.get("name", "").strip()
        
        # Validate email
        is_valid, clean_email, error = InputValidator.validate_email(email)
        if not is_valid:
            return current_app.api_response.error(error, 400)
        
        # Validate password
        is_valid, error = InputValidator.validate_password(password)
        if not is_valid:
            return current_app.api_response.error(error, 400)
        
        # Check if user already exists in our database
        existing_user = User.query.filter_by(email=clean_email).first()
        if existing_user:
            return current_app.api_response.error(
                "An account with this email already exists", 
                409
            )
        
        # Register with Supabase
        result, error = SupabaseAuthService.register_user(
            email=clean_email,
            password=password,
            name=name
        )
        
        if error:
            return current_app.api_response.error(error, 400)
        
        # Log registration activity
        try:
            ActivityService.log_activity(
                user_id=result["user"]["id"],
                activity_type=ActivityType.USER_REGISTERED,
                resource_type="user",
                resource_id=result["user"]["id"],
                extra_data={"email": mask_email(clean_email)},
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
        except Exception as e:
            logger.warning(f"Activity logging failed: {e}")
        
        return current_app.api_response.success(
            {
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "user": result["user"]
            },
            "Registration successful! Please check your email to verify your account.",
            201
        )
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return current_app.api_response.error(
            "Registration failed. Please try again.",
            500
        )


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per hour")
def login():
    """Login with email and password"""
    try:
        data = request.get_json()
        
        # Validate input
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        
        if not email or not password:
            return current_app.api_response.error(
                "Email and password are required",
                400
            )
        
        # Validate email format
        is_valid, clean_email, error = InputValidator.validate_email(email)
        if not is_valid:
            return current_app.api_response.error(error, 400)
        
        # Attempt login with Supabase
        result, error = SupabaseAuthService.login_user(
            email=clean_email,
            password=password
        )
        
        if error:
            # Log failed attempt
            logger.warning(f"Failed login attempt for {mask_email(clean_email)}")
            
            # Track failed login attempts in Redis
            try:
                redis = RedisService()
                identifier = f"login_attempts:{hash_string(clean_email, 'md5')}"
                allowed, remaining = redis.rate_limit_check(identifier, 5, 3600)
                
                if not allowed:
                    return current_app.api_response.error(
                        "Too many failed login attempts. Please try again later.",
                        429
                    )
            except Exception:
                pass
            
            return current_app.api_response.error(error, 401)
        
        # Log successful login
        logger.info(f"User logged in: {result['user']['id']}")
        
        # Log activity
        try:
            ActivityService.log_activity(
                user_id=result["user"]["id"],
                activity_type=ActivityType.USER_LOGIN,
                resource_type="user",
                resource_id=result["user"]["id"],
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
        except Exception:
            pass
        
        return current_app.api_response.success(
            {
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "user": result["user"]
            },
            "Login successful"
        )
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return current_app.api_response.error(
            "Login failed. Please try again.",
            500
        )


@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("3 per hour")
def forgot_password():
    """Request password reset email"""
    try:
        data = request.get_json()
        email = data.get("email", "").strip().lower()
        
        # Validate email
        is_valid, clean_email, error = InputValidator.validate_email(email)
        if not is_valid:
            return current_app.api_response.error(error, 400)
        
        # Check if user exists
        user = User.query.filter_by(email=clean_email).first()
        
        if user:
            # Request password reset from Supabase
            success, error = SupabaseAuthService.request_password_reset(clean_email)
            
            # Log activity
            try:
                ActivityService.log_activity(
                    user_id=user.id,
                    activity_type=ActivityType.PASSWORD_RESET_REQUESTED,
                    resource_type="user",
                    resource_id=user.id,
                    extra_data={"email": mask_email(clean_email)},
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
            except Exception:
                pass
            
            logger.info(f"Password reset requested for {mask_email(clean_email)}")
        
        # Always return success to prevent email enumeration
        return current_app.api_response.success(
            None,
            "If an account exists with this email, you will receive password reset instructions."
        )
        
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        return current_app.api_response.error(
            "Failed to process request. Please try again.",
            500
        )


@auth_bp.route("/reset-password", methods=["POST"])
@limiter.limit("5 per hour")
def reset_password():
    """Reset password with token"""
    try:
        data = request.get_json()
        token = data.get("token", "").strip()
        new_password = data.get("password", "")
        
        if not token:
            return current_app.api_response.error(
                "Reset token is required",
                400
            )
        
        # Validate new password
        is_valid, error = InputValidator.validate_password(new_password)
        if not is_valid:
            return current_app.api_response.error(error, 400)
        
        # Reset password with Supabase
        success, error = SupabaseAuthService.reset_password_with_token(
            token=token,
            new_password=new_password
        )
        
        if not success:
            return current_app.api_response.error(
                error or "Failed to reset password",
                400
            )
        
        # Log activity (we don't know the user from token, so skip for now)
        logger.info("Password reset successful")
        
        return current_app.api_response.success(
            None,
            "Password has been reset successfully. You can now login with your new password."
        )
        
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        return current_app.api_response.error(
            "Failed to reset password. Please try again.",
            500
        )


@auth_bp.route("/refresh", methods=["POST"])
def refresh_token():
    """Refresh access token"""
    try:
        data = request.get_json()
        refresh_token = data.get("refresh_token", "").strip()
        
        if not refresh_token:
            return current_app.api_response.error(
                "Refresh token is required",
                400
            )
        
        # Refresh token with Supabase
        result, error = SupabaseAuthService.refresh_token(refresh_token)
        
        if error:
            return current_app.api_response.error(error, 401)
        
        return current_app.api_response.success(
            {
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"]
            },
            "Token refreshed successfully"
        )
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return current_app.api_response.error(
            "Failed to refresh token",
            500
        )


@auth_bp.route("/logout", methods=["POST"])
@require_auth
def logout():
    """Logout current user"""
    try:
        # Get token from header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            token = None
        
        if token:
            # Logout from Supabase
            SupabaseAuthService.logout_user(token)
            
            # Add token to blacklist if using Redis
            try:
                redis_service = RedisService()
                # Extract token ID if present
                import jwt as pyjwt
                try:
                    unverified_payload = pyjwt.decode(token, options={"verify_signature": False})
                    jti = unverified_payload.get("jti") or token[:50]
                except:
                    jti = token[:50]
                
                redis_service.blacklist_token(jti, ttl=86400)
            except Exception as e:
                logger.warning(f"Token blacklisting failed: {e}")
        
        # Log activity
        try:
            ActivityService.log_activity(
                user_id=g.current_user_id,
                activity_type=ActivityType.USER_LOGOUT,
                resource_type="user",
                resource_id=g.current_user_id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
        except Exception:
            pass
        
        return current_app.api_response.success(
            None,
            "Logged out successfully"
        )
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return current_app.api_response.error(
            "Logout failed",
            500
        )


@auth_bp.route("/me", methods=["GET"])
@require_auth
def get_current_user():
    """Get current user profile"""
    try:
        user = g.current_user
        
        # Try to get cached stats first
        redis = RedisService()
        stats = redis.get_cached_user_stats(user.id)
        
        if not stats:
            # Calculate stats
            stats = {
                "total_links": user.links.filter_by(is_deleted=False).count(),
                "shortened_links": user.links.filter_by(is_deleted=False, link_type='shortened').count(),
                "saved_links": user.links.filter_by(is_deleted=False, link_type='saved').count(),
                "total_clicks": db.session.query(db.func.sum(user.links.c.clicks)).scalar() or 0,
                "total_folders": user.folders.count(),
                "total_tags": user.tags.count()
            }
            
            # Cache stats for 5 minutes
            redis.cache_user_stats(user.id, stats, ttl=300)
        
        user_data = user.to_dict()
        user_data["stats"] = stats
        
        return current_app.api_response.success(user_data)
        
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return current_app.api_response.error(
            "Failed to get user profile",
            500
        )


@auth_bp.route("/me", methods=["PATCH"])
@require_auth
def update_profile():
    """Update user profile"""
    try:
        user = g.current_user
        data = request.get_json()
        
        updated_fields = []
        
        # Update allowed fields
        if "name" in data:
            name = data["name"].strip()
            if len(name) > 100:
                return current_app.api_response.error(
                    "Name is too long (max 100 characters)",
                    400
                )
            if len(name) < 1:
                return current_app.api_response.error(
                    "Name cannot be empty",
                    400
                )
            user.name = name
            updated_fields.append("name")
        
        if "avatar_url" in data:
            avatar_url = data["avatar_url"]
            if avatar_url and len(avatar_url) > 512:
                return current_app.api_response.error(
                    "Avatar URL is too long",
                    400
                )
            user.avatar_url = avatar_url
            updated_fields.append("avatar_url")
        
        if "default_click_tracking" in data:
            user.default_click_tracking = bool(data["default_click_tracking"])
            updated_fields.append("default_click_tracking")
        
        if "default_privacy_level" in data:
            privacy = data["default_privacy_level"]
            if privacy not in ["private", "unlisted", "public"]:
                return current_app.api_response.error(
                    "Invalid privacy level",
                    400
                )
            user.default_privacy_level = privacy
            updated_fields.append("default_privacy_level")
        
        if "data_retention_days" in data:
            retention = data["data_retention_days"]
            if retention is not None:
                if not isinstance(retention, int) or retention < 0:
                    return current_app.api_response.error(
                        "Invalid data retention days",
                        400
                    )
                if retention > 365:
                    return current_app.api_response.error(
                        "Data retention cannot exceed 365 days",
                        400
                    )
            user.data_retention_days = retention
            updated_fields.append("data_retention_days")
        
        if not updated_fields:
            return current_app.api_response.error(
                "No fields to update",
                400
            )
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Invalidate user stats cache
        try:
            redis = RedisService()
            redis.invalidate_user_stats(user.id)
        except Exception:
            pass
        
        # Log activity
        ActivityService.log_activity(
            user_id=user.id,
            activity_type=ActivityType.USER_UPDATED,
            resource_type="user",
            resource_id=user.id,
            extra_data={"fields": updated_fields}
        )
        
        return current_app.api_response.success(
            user.to_dict(),
            "Profile updated successfully"
        )
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Update profile error: {e}")
        return current_app.api_response.error(
            "Failed to update profile",
            500
        )


@auth_bp.route("/change-password", methods=["POST"])
@require_auth
@limiter.limit("3 per hour")
def change_password():
    """Change password for logged-in user"""
    try:
        user = g.current_user
        data = request.get_json()
        
        current_password = data.get("current_password", "")
        new_password = data.get("new_password", "")
        
        if not current_password or not new_password:
            return current_app.api_response.error(
                "Current and new passwords are required",
                400
            )
        
        # Validate new password
        is_valid, error = InputValidator.validate_password(new_password)
        if not is_valid:
            return current_app.api_response.error(error, 400)
        
        # Verify current password
        result, error = SupabaseAuthService.login_user(
            email=user.email,
            password=current_password
        )
        
        if error:
            return current_app.api_response.error(
                "Current password is incorrect",
                401
            )
        
        # Get current token from header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            return current_app.api_response.error("Invalid authorization", 401)
        
        # Change password
        success, error = SupabaseAuthService.change_password(
            token=token,
            new_password=new_password
        )
        
        if not success:
            return current_app.api_response.error(
                error or "Failed to change password",
                400
            )
        
        # Log activity
        ActivityService.log_activity(
            user_id=user.id,
            activity_type=ActivityType.PASSWORD_CHANGED,
            resource_type="user",
            resource_id=user.id,
            ip_address=request.remote_addr
        )
        
        return current_app.api_response.success(
            None,
            "Password changed successfully"
        )
        
    except Exception as e:
        logger.error(f"Change password error: {e}")
        return current_app.api_response.error(
            "Failed to change password",
            500
        )


@auth_bp.route("/delete-account", methods=["DELETE"])
@require_auth
@limiter.limit("1 per hour")
def delete_account():
    """Delete user account (requires password confirmation)"""
    try:
        user = g.current_user
        data = request.get_json()
        
        password = data.get("password", "")
        confirmation = data.get("confirmation", "")
        
        if not password:
            return current_app.api_response.error(
                "Password confirmation is required",
                400
            )
        
        if confirmation != "DELETE":
            return current_app.api_response.error(
                "Please type DELETE to confirm account deletion",
                400
            )
        
        # Verify password with Supabase
        result, error = SupabaseAuthService.login_user(
            email=user.email,
            password=password
        )
        
        if error:
            return current_app.api_response.error(
                "Invalid password",
                401
            )
        
        # Log deletion
        logger.info(f"Account deletion requested for user {user.id}")
        
        # Store user ID for final logging
        user_id = user.id
        user_email = mask_email(user.email)
        
        # Delete user and all related data (cascades)
        db.session.delete(user)
        db.session.commit()
        
        # Also delete from Supabase
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                SupabaseAuthService.delete_user_account(token)
        except Exception as e:
            logger.error(f"Failed to delete from Supabase: {e}")
        
        logger.info(f"Account deleted successfully: {user_id} ({user_email})")
        
        return current_app.api_response.success(
            None,
            "Account deleted successfully"
        )
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete account error: {e}")
        return current_app.api_response.error(
            "Failed to delete account",
            500
        )