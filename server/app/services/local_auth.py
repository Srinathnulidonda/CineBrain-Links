# server/app/services/local_auth.py

import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app

from app.extensions import db
from app.models.user import User
from app.services.redis_service import RedisService
from app.services.email_service import get_email_service
from app.utils.jwt_utils import JWTManager

logger = logging.getLogger(__name__)


class LocalAuthService:
    
    @classmethod
    def register_user(cls, email: str, password: str, name: Optional[str] = None) -> Tuple[Optional[Dict], Optional[str]]:
        """Register a new user with local authentication"""
        try:
            if not email:
                return None, "Email is required"
            
            if not password:
                return None, "Password is required"
            
            # Clean email
            email = str(email).strip().lower()
            
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                return None, "An account with this email already exists"
            
            # Generate user ID
            user_id = str(secrets.token_urlsafe(16))
            
            # Hash password
            password_hash = generate_password_hash(password)
            
            # Create user
            user = User(
                id=user_id,
                email=email,
                name=name or email.split("@")[0].replace(".", " ").title(),
                auth_provider="email"
            )
            
            # Store password hash in custom field or separate table
            user.password_hash = password_hash
            user.email_verified = False  # Require email verification
            user.last_login_at = datetime.utcnow()
            
            db.session.add(user)
            db.session.commit()
            
            # Generate email verification token
            verification_token = cls._generate_verification_token(user_id)
            
            # Send verification email
            try:
                email_service = get_email_service()
                email_service.send_email_verification(
                    to_email=email,
                    verification_token=verification_token,
                    user_name=user.name
                )
            except Exception as e:
                logger.warning(f"Verification email failed: {e}")
            
            # Generate JWT tokens
            jwt_manager = JWTManager()
            access_token = jwt_manager.generate_access_token(user_id, email)
            refresh_token = jwt_manager.generate_refresh_token(user_id)
            
            logger.info(f"User registered: {user_id} ({email})")
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": user.to_dict(),
                "email_verification_required": True
            }, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            return None, "Registration failed. Please try again."

    @classmethod
    def login_user(cls, email: str, password: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Login user with email and password"""
        try:
            if not email or not password:
                return None, "Email and password are required"
            
            email = str(email).strip().lower()
            
            # Find user by email
            user = User.query.filter_by(email=email).first()
            if not user:
                return None, "Invalid email or password"
            
            # Check password
            if not hasattr(user, 'password_hash') or not user.password_hash:
                return None, "Invalid email or password"
            
            if not check_password_hash(user.password_hash, password):
                return None, "Invalid email or password"
            
            # Check if account is active
            if not user.is_active:
                return None, "Account has been deactivated"
            
            # Update last login
            user.last_login_at = datetime.utcnow()
            db.session.commit()
            
            # Generate JWT tokens
            jwt_manager = JWTManager()
            access_token = jwt_manager.generate_access_token(user.id, user.email)
            refresh_token = jwt_manager.generate_refresh_token(user.id)
            
            logger.info(f"User logged in: {user.id}")
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": user.to_dict()
            }, None
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            return None, "Login failed. Please try again."

    @classmethod
    def verify_email(cls, token: str) -> Tuple[bool, Optional[str]]:
        """Verify user email with token"""
        try:
            redis = RedisService()
            user_id = redis.get_verification_token_user(token)
            
            if not user_id:
                return False, "Invalid or expired verification token"
            
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            user.email_verified = True
            db.session.commit()
            
            # Invalidate token
            redis.invalidate_verification_token(token)
            
            logger.info(f"Email verified for user: {user_id}")
            return True, None
            
        except Exception as e:
            logger.error(f"Email verification error: {e}")
            return False, "Email verification failed"

    @classmethod
    def request_password_reset(cls, email: str) -> Tuple[bool, Optional[str]]:
        """Request password reset for user"""
        try:
            if not email:
                return False, "Email is required"
            
            email = str(email).strip().lower()
            
            # Find user
            user = User.query.filter_by(email=email).first()
            if not user:
                # Don't reveal if email exists or not
                return True, None
            
            # Generate reset token
            reset_token = cls._generate_reset_token(user.id)
            
            # Send reset email
            try:
                email_service = get_email_service()
                email_service.send_password_reset_email(
                    to_email=email,
                    reset_token=reset_token,
                    user_name=user.name
                )
            except Exception as e:
                logger.error(f"Password reset email failed: {e}")
                return False, "Failed to send reset email"
            
            logger.info(f"Password reset requested for: {user.id}")
            return True, None
            
        except Exception as e:
            logger.error(f"Password reset request error: {e}")
            return False, "Failed to process password reset request"

    @classmethod
    def reset_password_with_token(cls, token: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """Reset password using reset token"""
        try:
            if not token or not new_password:
                return False, "Token and new password are required"
            
            redis = RedisService()
            user_id = redis.get_reset_token_user(token)
            
            if not user_id:
                return False, "Invalid or expired reset token"
            
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            # Update password
            user.password_hash = generate_password_hash(new_password)
            user.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Invalidate reset token
            redis.invalidate_reset_token(token)
            
            # Invalidate all existing refresh tokens for this user
            cls._invalidate_user_tokens(user_id)
            
            logger.info(f"Password reset successful for user: {user_id}")
            return True, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Password reset error: {e}")
            return False, "Password reset failed"

    @classmethod
    def change_password(cls, user_id: str, current_password: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """Change password for authenticated user"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            # Verify current password
            if not hasattr(user, 'password_hash') or not user.password_hash:
                return False, "No password set for this account"
            
            if not check_password_hash(user.password_hash, current_password):
                return False, "Current password is incorrect"
            
            # Update password
            user.password_hash = generate_password_hash(new_password)
            user.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Invalidate all existing refresh tokens for this user
            cls._invalidate_user_tokens(user_id)
            
            logger.info(f"Password changed for user: {user_id}")
            return True, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Password change error: {e}")
            return False, "Failed to change password"

    @classmethod
    def refresh_token(cls, refresh_token: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Refresh access token using refresh token"""
        try:
            jwt_manager = JWTManager()
            
            # Verify refresh token
            payload = jwt_manager.verify_refresh_token(refresh_token)
            if not payload:
                return None, "Invalid refresh token"
            
            user_id = payload.get("sub")
            if not user_id:
                return None, "Invalid refresh token"
            
            # Check if user still exists and is active
            user = User.query.get(user_id)
            if not user or not user.is_active:
                return None, "User not found or inactive"
            
            # Generate new tokens
            new_access_token = jwt_manager.generate_access_token(user_id, user.email)
            new_refresh_token = jwt_manager.generate_refresh_token(user_id)
            
            # Blacklist old refresh token
            cls._blacklist_refresh_token(refresh_token)
            
            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token
            }, None
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None, "Failed to refresh token"

    @classmethod
    def verify_token(cls, token: str) -> Optional[Dict]:
        """Verify access token and return payload"""
        try:
            jwt_manager = JWTManager()
            return jwt_manager.verify_access_token(token)
        except Exception:
            return None

    @classmethod
    def get_or_create_user(cls, token_payload: Dict) -> Tuple[Optional[User], Optional[str]]:
        """Get user from token payload"""
        try:
            user_id = token_payload.get("sub")
            if not user_id:
                return None, "Invalid token: missing user ID"
            
            user = User.query.get(user_id)
            if not user:
                return None, "User not found"
            
            if not user.is_active:
                return None, "Account has been deactivated"
            
            return user, None
            
        except Exception as e:
            logger.error(f"User retrieval error: {e}")
            return None, "Failed to get user"

    @classmethod
    def logout_user(cls, access_token: str, refresh_token: Optional[str] = None) -> bool:
        """Logout user by blacklisting tokens"""
        try:
            jwt_manager = JWTManager()
            
            # Blacklist access token
            access_payload = jwt_manager.verify_access_token(access_token, check_blacklist=False)
            if access_payload:
                jti = access_payload.get("jti")
                if jti:
                    cls._blacklist_access_token(jti)
            
            # Blacklist refresh token if provided
            if refresh_token:
                cls._blacklist_refresh_token(refresh_token)
            
            return True
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False

    @classmethod
    def delete_user_account(cls, user_id: str, password: str) -> Tuple[bool, Optional[str]]:
        """Delete user account with password confirmation"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            # Verify password
            if not check_password_hash(user.password_hash, password):
                return False, "Incorrect password"
            
            # Invalidate all tokens
            cls._invalidate_user_tokens(user_id)
            
            # Delete user (this will cascade to related data)
            db.session.delete(user)
            db.session.commit()
            
            logger.info(f"User account deleted: {user_id}")
            return True, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Account deletion error: {e}")
            return False, "Failed to delete account"

    # Helper methods
    @classmethod
    def _generate_verification_token(cls, user_id: str) -> str:
        """Generate email verification token"""
        token = secrets.token_urlsafe(32)
        try:
            redis = RedisService()
            redis.store_verification_token(token, user_id, ttl=86400)  # 24 hours
        except Exception:
            pass
        return token

    @classmethod
    def _generate_reset_token(cls, user_id: str) -> str:
        """Generate password reset token"""
        token = secrets.token_urlsafe(32)
        try:
            redis = RedisService()
            redis.store_reset_token(token, user_id, ttl=3600)  # 1 hour
        except Exception:
            pass
        return token

    @classmethod
    def _blacklist_access_token(cls, jti: str) -> None:
        """Blacklist access token JTI"""
        try:
            redis = RedisService()
            redis.blacklist_token(jti, ttl=86400)  # 24 hours
        except Exception:
            pass

    @classmethod
    def _blacklist_refresh_token(cls, refresh_token: str) -> None:
        """Blacklist refresh token"""
        try:
            redis = RedisService()
            # Use token hash as key
            token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
            redis.blacklist_token(f"refresh_{token_hash}", ttl=86400 * 30)  # 30 days
        except Exception:
            pass

    @classmethod
    def _invalidate_user_tokens(cls, user_id: str) -> None:
        """Invalidate all tokens for a user"""
        try:
            redis = RedisService()
            # Add user to invalidated list - all future token verifications will check this
            redis.add_to_set("invalidated_users", user_id)
            # This could also be done with a timestamp-based approach
        except Exception:
            pass