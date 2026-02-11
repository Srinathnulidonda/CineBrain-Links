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
from app.services.redis_service import RedisService
from app.services.activity_service import ActivityService
from app.services.email_service import get_email_service
from app.utils.validators import InputValidator
from app.utils.auth import require_auth
from app.utils.helpers import mask_email, hash_string
from app.utils.jwt_utils import JWTManager

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
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=clean_email).first()
        if existing_user:
            return current_app.api_response.error(
                "An account with this email already exists", 
                409
            )
        
        # Create user
        user = User(
            email=clean_email,
            password=password,
            name=name or clean_email.split("@")[0].replace(".", " ").title(),
            auth_provider="email"
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Generate JWT tokens
        jwt_manager = JWTManager()
        access_token = jwt_manager.generate_access_token(user.id, user.email)
        refresh_token = jwt_manager.generate_refresh_token(user.id)
        
        # Generate email verification token
        import secrets
        verification_token = secrets.token_urlsafe(32)
        
        # Store verification token in Redis
        try:
            redis = RedisService()
            redis.store_verification_token(verification_token, user.id, ttl=86400)  # 24 hours
        except Exception:
            pass
        
        # Send verification email
        try:
            email_service = get_email_service()
            email_service.send_email_verification(
                to_email=clean_email,
                verification_token=verification_token,
                user_name=user.name
            )
        except Exception as e:
            logger.warning(f"Verification email failed: {e}")
        
        # Log registration activity
        try:
            ActivityService.log_activity(
                user_id=user.id,
                activity_type=ActivityType.USER_REGISTERED,
                resource_type="user",
                resource_id=user.id,
                extra_data={"email": mask_email(clean_email)},
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
        except Exception as e:
            logger.warning(f"Activity logging failed: {e}")
        
        logger.info(f"User registered: {user.id}")
        
        return current_app.api_response.success(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": user.to_dict(),
                "email_verification_required": not user.email_verified
            },
            "Registration successful! Please check your email to verify your account.",
            201
        )
        
    except Exception as e:
        db.session.rollback()
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
        
        # Check rate limiting for failed attempts
        ip_address = request.remote_addr
        try:
            redis = RedisService()
            failed_attempts = redis.get_failed_login_count(f"ip:{ip_address}")
            if failed_attempts >= 5:
                return current_app.api_response.error(
                    "Too many failed login attempts. Please try again later.",
                    429
                )
        except Exception:
            pass
        
        # Find user by email
        user = User.query.filter_by(email=clean_email).first()
        if not user:
            # Track failed attempt by IP
            try:
                redis.track_failed_login(f"ip:{ip_address}")
            except Exception:
                pass
            return current_app.api_response.error("Invalid email or password", 401)
        
        # Check if account is locked
        if user.is_account_locked():
            return current_app.api_response.error(
                "Account is temporarily locked due to too many failed attempts. Please try again later.",
                423
            )
        
        # Check if account is active
        if not user.is_active:
            return current_app.api_response.error("Account has been deactivated", 403)
        
        # Verify password
        if not user.check_password(password):
            # Record failed attempt
            user.record_login_attempt(successful=False)
            db.session.commit()
            
            # Track failed attempt by IP
            try:
                redis.track_failed_login(f"ip:{ip_address}")
            except Exception:
                pass
            
            return current_app.api_response.error("Invalid email or password", 401)
        
        # Successful login
        user.record_login_attempt(successful=True)
        db.session.commit()
        
        # Clear failed login attempts for IP
        try:
            redis.clear_failed_logins(f"ip:{ip_address}")
        except Exception:
            pass
        
        # Generate JWT tokens
        jwt_manager = JWTManager()
        access_token = jwt_manager.generate_access_token(user.id, user.email)
        refresh_token = jwt_manager.generate_refresh_token(user.id)
        
        # Log successful login
        try:
            ActivityService.log_activity(
                user_id=user.id,
                activity_type=ActivityType.USER_LOGIN,
                resource_type="user",
                resource_id=user.id,
                ip_address=ip_address,
                user_agent=request.headers.get('User-Agent')
            )
        except Exception as e:
            logger.warning(f"Activity logging failed: {e}")
        
        logger.info(f"User logged in: {user.id}")
        
        return current_app.api_response.success(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": user.to_dict()
            },
            "Login successful"
        )
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return current_app.api_response.error(
            "Login failed. Please try again.",
            500
        )


@auth_bp.route("/verify-email", methods=["POST"])
def verify_email():
    """Verify email with verification token"""
    try:
        data = request.get_json()
        token = data.get("token", "").strip()
        
        if not token:
            return current_app.api_response.error(
                "Verification token is required",
                400
            )
        
        # Get user ID from token
        redis = RedisService()
        user_id = redis.get_verification_token_user(token)
        
        if not user_id:
            return current_app.api_response.error(
                "Invalid or expired verification token",
                400
            )
        
        # Find and verify user
        user = User.query.get(user_id)
        if not user:
            return current_app.api_response.error("User not found", 404)
        
        # Verify email
        user.verify_email()
        db.session.commit()
        
        # Invalidate token
        redis.invalidate_verification_token(token)
        
        logger.info(f"Email verified for user: {user.id}")
        
        return current_app.api_response.success(
            {"user": user.to_dict()},
            "Email verified successfully!"
        )
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Email verification error: {e}")
        return current_app.api_response.error(
            "Email verification failed",
            500
        )


@auth_bp.route("/resend-verification", methods=["POST"])
@limiter.limit("3 per hour")
def resend_verification():
    """Resend email verification"""
    try:
        data = request.get_json()
        email = data.get("email", "").strip().lower()
        
        if not email:
            return current_app.api_response.error("Email is required", 400)
        
        # Find user
        user = User.query.filter_by(email=email).first()
        if not user:
            # Don't reveal if email exists
            return current_app.api_response.success(
                None,
                "If an account exists with this email, a verification email will be sent."
            )
        
        if user.email_verified:
            return current_app.api_response.error("Email is already verified", 400)
        
        # Generate new verification token
        import secrets
        verification_token = secrets.token_urlsafe(32)
        
        # Store in Redis
        redis = RedisService()
        redis.store_verification_token(verification_token, user.id, ttl=86400)
        
        # Send verification email
        try:
            email_service = get_email_service()
            email_service.send_email_verification(
                to_email=email,
                verification_token=verification_token,
                user_name=user.name
            )
        except Exception as e:
            logger.error(f"Verification email failed: {e}")
            return current_app.api_response.error("Failed to send verification email", 500)
        
        return current_app.api_response.success(
            None,
            "Verification email sent successfully."
        )
        
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        return current_app.api_response.error(
            "Failed to resend verification email",
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
        
        # Find user
        user = User.query.filter_by(email=clean_email).first()
        
        if user:
            # Generate reset token
            import secrets
            reset_token = secrets.token_urlsafe(32)
            
            # Store in Redis
            redis = RedisService()
            redis.store_reset_token(reset_token, user.id, ttl=3600)  # 1 hour
            
            # Send reset email
            try:
                email_service = get_email_service()
                email_service.send_password_reset_email(
                    to_email=clean_email,
                    reset_token=reset_token,
                    user_name=user.name,
                    request_info={
                        "ip": request.remote_addr,
                        "device": request.headers.get("User-Agent", "Unknown")[:50]
                    }
                )
            except Exception as e:
                logger.error(f"Password reset email failed: {e}")
            
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
            except Exception as e:
                logger.warning(f"Activity logging failed: {e}")
            
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
            return current_app.api_response.error("Reset token is required", 400)
        
        # Validate new password
        is_valid, error = InputValidator.validate_password(new_password)
        if not is_valid:
            return current_app.api_response.error(error, 400)
        
        # Get user from token
        redis = RedisService()
        user_id = redis.get_reset_token_user(token)
        
        if not user_id:
            return current_app.api_response.error(
                "Invalid or expired reset token",
                400
            )
        
        # Find user
        user = User.query.get(user_id)
        if not user:
            return current_app.api_response.error("User not found", 404)
        
        # Update password
        user.set_password(new_password)
        user.unlock_account()  # Clear any failed login attempts
        db.session.commit()
        
        # Invalidate reset token
        redis.invalidate_reset_token(token)
        
        # Invalidate all existing tokens for this user
        try:
            redis.add_to_set("invalidated_users", user_id)
        except Exception:
            pass
        
        # Log activity
        try:
            ActivityService.log_activity(
                user_id=user.id,
                activity_type=ActivityType.PASSWORD_CHANGED,
                resource_type="user",
                resource_id=user.id,
                ip_address=request.remote_addr
            )
        except Exception as e:
            logger.warning(f"Activity logging failed: {e}")
        
        logger.info("Password reset successful")
        
        return current_app.api_response.success(
            None,
            "Password has been reset successfully. You can now login with your new password."
        )
        
    except Exception as e:
        db.session.rollback()
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
            return current_app.api_response.error("Refresh token is required", 400)
        
        # Verify refresh token
        jwt_manager = JWTManager()
        payload = jwt_manager.verify_refresh_token(refresh_token)
        
        if not payload:
            return current_app.api_response.error("Invalid refresh token", 401)
        
        user_id = payload.get("sub")
        if not user_id:
            return current_app.api_response.error("Invalid refresh token", 401)
        
        # Check if user still exists and is active
        user = User.query.get(user_id)
        if not user or not user.is_active:
            return current_app.api_response.error("User not found or inactive", 401)
        
        # Check if user tokens have been invalidated
        try:
            redis = RedisService()
            if redis.is_in_set("invalidated_users", user_id):
                return current_app.api_response.error("Session expired", 401)
        except Exception:
            pass
        
        # Generate new tokens
        new_access_token = jwt_manager.generate_access_token(user_id, user.email)
        new_refresh_token = jwt_manager.generate_refresh_token(user_id)
        
        # Blacklist old refresh token
        try:
            import hashlib
            token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
            redis.blacklist_token(f"refresh_{token_hash}", ttl=86400 * 30)
        except Exception:
            pass
        
        return current_app.api_response.success(
            {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token
            },
            "Token refreshed successfully"
        )
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return current_app.api_response.error("Failed to refresh token", 500)


@auth_bp.route("/logout", methods=["POST"])
@require_auth
def logout():
    """Logout current user"""
    try:
        # Get tokens
        access_token = g.token
        data = request.get_json() or {}
        refresh_token = data.get("refresh_token")
        
        # Blacklist access token
        if access_token:
            jti = g.token_payload.get("jti")
            if jti:
                try:
                    redis = RedisService()
                    redis.blacklist_token(jti, ttl=86400)
                except Exception:
                    pass
        
        # Blacklist refresh token if provided
        if refresh_token:
            try:
                import hashlib
                token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
                redis.blacklist_token(f"refresh_{token_hash}", ttl=86400 * 30)
            except Exception:
                pass
        
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
        except Exception as e:
            logger.warning(f"Activity logging failed: {e}")
        
        return current_app.api_response.success(None, "Logged out successfully")
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return current_app.api_response.error("Logout failed", 500)


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
        return current_app.api_response.error("Failed to get user profile", 500)


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
            return current_app.api_response.error("No fields to update", 400)
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Invalidate user stats cache
        try:
            redis = RedisService()
            redis.invalidate_user_stats(user.id)
        except Exception:
            pass
        
        # Log activity
        try:
            ActivityService.log_activity(
                user_id=user.id,
                activity_type=ActivityType.USER_UPDATED,
                resource_type="user",
                resource_id=user.id,
                extra_data={"fields": updated_fields}
            )
        except Exception as e:
            logger.warning(f"Activity logging failed: {e}")
        
        return current_app.api_response.success(
            user.to_dict(),
            "Profile updated successfully"
        )
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Update profile error: {e}")
        return current_app.api_response.error("Failed to update profile", 500)


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
        if not user.check_password(current_password):
            return current_app.api_response.error(
                "Current password is incorrect",
                401
            )
        
        # Update password
        user.set_password(new_password)
        db.session.commit()
        
        # Invalidate all existing tokens for this user
        try:
            redis = RedisService()
            redis.add_to_set("invalidated_users", user.id)
        except Exception:
            pass
        
        # Log activity
        try:
            ActivityService.log_activity(
                user_id=user.id,
                activity_type=ActivityType.PASSWORD_CHANGED,
                resource_type="user",
                resource_id=user.id,
                ip_address=request.remote_addr
            )
        except Exception as e:
            logger.warning(f"Activity logging failed: {e}")
        
        return current_app.api_response.success(
            None,
            "Password changed successfully. Please log in again."
        )
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Change password error: {e}")
        return current_app.api_response.error("Failed to change password", 500)


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
        
        # Verify password
        if not user.check_password(password):
            return current_app.api_response.error("Invalid password", 401)
        
        # Log deletion
        user_id = user.id
        user_email = mask_email(user.email)
        logger.info(f"Account deletion requested for user {user_id}")
        
        # Invalidate all tokens
        try:
            redis = RedisService()
            redis.add_to_set("invalidated_users", user_id)
            redis.flush_user_cache(user_id)
        except Exception:
            pass
        
        # Delete user (this will cascade to related data)
        db.session.delete(user)
        db.session.commit()
        
        logger.info(f"Account deleted successfully: {user_id} ({user_email})")
        
        return current_app.api_response.success(
            None,
            "Account deleted successfully"
        )
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete account error: {e}")
        return current_app.api_response.error("Failed to delete account", 500)