# server/app/services/supabase_auth.py

import logging
import time
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from functools import lru_cache

import jwt
import requests
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_pem_x509_certificate

from flask import current_app

from app.extensions import db
from app.models.user import User
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)


class SupabaseAuthService:
    _jwks_cache: Dict = {}
    _jwks_fetch_time: float = 0
    JWKS_CACHE_TTL = 3600  # 1 hour

    @classmethod
    def get_supabase_url(cls) -> str:
        """Get Supabase project URL"""
        return current_app.config.get("SUPABASE_URL", "")

    @classmethod
    def get_supabase_project_id(cls) -> str:
        """Extract project ID from Supabase URL or config"""
        supabase_url = cls.get_supabase_url()
        if supabase_url:
            # Extract from URL: https://xxx.supabase.co
            import re
            match = re.match(r'https://([^.]+)\.supabase\.co', supabase_url)
            if match:
                return match.group(1)
        
        # Fallback to explicit config
        return current_app.config.get("SUPABASE_PROJECT_ID", "")

    @classmethod
    def get_supabase_anon_key(cls) -> str:
        """Get Supabase anonymous key"""
        return current_app.config.get("SUPABASE_ANON_KEY", "")

    @classmethod
    def get_supabase_service_key(cls) -> str:
        """Get Supabase service key (for admin operations)"""
        return current_app.config.get("SUPABASE_SERVICE_KEY", "")

    @classmethod
    def register_user(cls, email: str, password: str, name: Optional[str] = None) -> Tuple[Optional[Dict], Optional[str]]:
        """Register a new user with Supabase"""
        try:
            supabase_url = cls.get_supabase_url()
            anon_key = cls.get_supabase_anon_key()
            
            if not supabase_url or not anon_key:
                logger.error("Supabase configuration missing")
                return None, "Authentication service not configured"
            
            # Prepare user metadata
            user_metadata = {}
            if name:
                user_metadata["full_name"] = name
                user_metadata["name"] = name
            
            # Call Supabase signup endpoint
            response = requests.post(
                f"{supabase_url}/auth/v1/signup",
                headers={
                    "apikey": anon_key,
                    "Content-Type": "application/json"
                },
                json={
                    "email": email,
                    "password": password,
                    "data": user_metadata  # User metadata
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract user info
                user_data = data.get("user", {})
                
                # Create user in our database
                user = User(
                    id=user_data.get("id"),
                    email=user_data.get("email"),
                    name=name or email.split("@")[0].replace(".", " ").title(),
                    auth_provider="email"
                )
                
                db.session.add(user)
                db.session.commit()
                
                # Send welcome email
                try:
                    from app.services.email_service import get_email_service
                    email_service = get_email_service()
                    email_service.send_welcome_email(email, user_name=user.name)
                except Exception as e:
                    logger.warning(f"Welcome email failed: {e}")
                
                # Return tokens
                return {
                    "access_token": data.get("access_token"),
                    "refresh_token": data.get("refresh_token"),
                    "user": user.to_dict()
                }, None
                
            elif response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get("msg") or error_data.get("message") or "Registration failed"
                
                # Check for common errors
                if "already registered" in error_msg.lower():
                    return None, "This email is already registered"
                elif "password" in error_msg.lower():
                    return None, "Password must be at least 8 characters"
                else:
                    return None, error_msg
            else:
                logger.error(f"Supabase signup failed: {response.status_code} - {response.text}")
                return None, "Registration failed. Please try again."
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during registration: {e}")
            return None, "Network error. Please try again."
        except Exception as e:
            logger.error(f"Registration error: {e}")
            db.session.rollback()
            return None, "Registration failed. Please try again."

    @classmethod
    def login_user(cls, email: str, password: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Login user with Supabase"""
        try:
            supabase_url = cls.get_supabase_url()
            anon_key = cls.get_supabase_anon_key()
            
            if not supabase_url or not anon_key:
                logger.error("Supabase configuration missing")
                return None, "Authentication service not configured"
            
            # Call Supabase signin endpoint
            response = requests.post(
                f"{supabase_url}/auth/v1/token",
                headers={
                    "apikey": anon_key,
                    "Content-Type": "application/json"
                },
                params={
                    "grant_type": "password"
                },
                json={
                    "email": email,
                    "password": password
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Get or create user in our database
                user_data = data.get("user", {})
                user = User.query.get(user_data.get("id"))
                
                if not user:
                    # Create user if doesn't exist
                    user = User(
                        id=user_data.get("id"),
                        email=user_data.get("email"),
                        name=user_data.get("user_metadata", {}).get("full_name") or email.split("@")[0].replace(".", " ").title(),
                        auth_provider="email"
                    )
                    db.session.add(user)
                
                # Update last login
                user.last_login_at = datetime.utcnow()
                db.session.commit()
                
                return {
                    "access_token": data.get("access_token"),
                    "refresh_token": data.get("refresh_token"),
                    "user": user.to_dict()
                }, None
                
            elif response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get("error_description") or error_data.get("message") or "Login failed"
                
                if "Invalid login credentials" in error_msg:
                    return None, "Invalid email or password"
                elif "Email not confirmed" in error_msg:
                    return None, "Please verify your email before logging in"
                else:
                    return None, error_msg
            else:
                logger.error(f"Supabase login failed: {response.status_code}")
                return None, "Login failed. Please try again."
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during login: {e}")
            return None, "Network error. Please try again."
        except Exception as e:
            logger.error(f"Login error: {e}")
            db.session.rollback()
            return None, "Login failed. Please try again."

    @classmethod
    def request_password_reset(cls, email: str) -> Tuple[bool, Optional[str]]:
        """Request password reset email from Supabase"""
        try:
            supabase_url = cls.get_supabase_url()
            anon_key = cls.get_supabase_anon_key()
            frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:3000")
            
            if not supabase_url or not anon_key:
                logger.error("Supabase configuration missing")
                return False, "Authentication service not configured"
            
            # Call Supabase recovery endpoint
            response = requests.post(
                f"{supabase_url}/auth/v1/recover",
                headers={
                    "apikey": anon_key,
                    "Content-Type": "application/json"
                },
                json={
                    "email": email,
                    "redirect_to": f"{frontend_url}/reset-password"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Password reset requested for {email}")
                return True, None
            else:
                logger.error(f"Supabase recovery failed: {response.status_code}")
                return False, "Failed to send reset email. Please try again."
                
        except Exception as e:
            logger.error(f"Password reset request error: {e}")
            return False, "Failed to send reset email. Please try again."

    @classmethod
    def reset_password_with_token(cls, token: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """Reset password using recovery token from Supabase"""
        try:
            supabase_url = cls.get_supabase_url()
            anon_key = cls.get_supabase_anon_key()
            
            if not supabase_url or not anon_key:
                logger.error("Supabase configuration missing")
                return False, "Authentication service not configured"
            
            # Call Supabase update user endpoint with recovery token
            response = requests.put(
                f"{supabase_url}/auth/v1/user",
                headers={
                    "apikey": anon_key,
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={
                    "password": new_password
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Password reset successful")
                return True, None
            elif response.status_code == 401:
                return False, "Invalid or expired reset token"
            else:
                error_data = response.json()
                error_msg = error_data.get("msg") or error_data.get("message") or "Password reset failed"
                return False, error_msg
                
        except Exception as e:
            logger.error(f"Password reset error: {e}")
            return False, "Password reset failed. Please try again."

    @classmethod
    def change_password(cls, token: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """Change password for authenticated user"""
        try:
            supabase_url = cls.get_supabase_url()
            anon_key = cls.get_supabase_anon_key()
            
            if not supabase_url or not anon_key:
                return False, "Authentication service not configured"
            
            response = requests.put(
                f"{supabase_url}/auth/v1/user",
                headers={
                    "apikey": anon_key,
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={
                    "password": new_password
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return True, None
            else:
                error_data = response.json()
                error_msg = error_data.get("msg") or error_data.get("message") or "Password change failed"
                return False, error_msg
                
        except Exception as e:
            logger.error(f"Password change error: {e}")
            return False, "Failed to change password"

    @classmethod
    def refresh_token(cls, refresh_token: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Refresh access token using refresh token"""
        try:
            supabase_url = cls.get_supabase_url()
            anon_key = cls.get_supabase_anon_key()
            
            if not supabase_url or not anon_key:
                return None, "Authentication service not configured"
            
            response = requests.post(
                f"{supabase_url}/auth/v1/token",
                headers={
                    "apikey": anon_key,
                    "Content-Type": "application/json"
                },
                params={
                    "grant_type": "refresh_token"
                },
                json={
                    "refresh_token": refresh_token
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "access_token": data.get("access_token"),
                    "refresh_token": data.get("refresh_token")
                }, None
            else:
                return None, "Failed to refresh token"
                
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None, "Failed to refresh token"

    @classmethod
    def logout_user(cls, access_token: str) -> bool:
        """Logout user (revoke token)"""
        try:
            supabase_url = cls.get_supabase_url()
            anon_key = cls.get_supabase_anon_key()
            
            if not supabase_url or not anon_key:
                return False
            
            response = requests.post(
                f"{supabase_url}/auth/v1/logout",
                headers={
                    "apikey": anon_key,
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            return response.status_code == 204
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False

    @classmethod
    def delete_user_account(cls, access_token: str) -> bool:
        """Delete user account from Supabase"""
        try:
            supabase_url = cls.get_supabase_url()
            service_key = cls.get_supabase_service_key()
            
            if not supabase_url or not service_key:
                # If no service key, we can't delete from Supabase
                logger.warning("Cannot delete from Supabase: service key not configured")
                return False
            
            # This requires service role key
            response = requests.delete(
                f"{supabase_url}/auth/v1/admin/users",
                headers={
                    "apikey": service_key,
                    "Authorization": f"Bearer {service_key}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            return response.status_code in [200, 204]
            
        except Exception as e:
            logger.error(f"Delete user from Supabase error: {e}")
            return False

    @classmethod
    def get_jwks(cls) -> Dict:
        """Fetch and cache Supabase JWKS"""
        now = time.time()
        
        # Check cache
        if cls._jwks_cache and (now - cls._jwks_fetch_time) < cls.JWKS_CACHE_TTL:
            return cls._jwks_cache
        
        project_id = cls.get_supabase_project_id()
        if not project_id:
            raise ValueError("SUPABASE_PROJECT_ID not configured")
        
        jwks_url = f"https://{project_id}.supabase.co/auth/v1/keys"
        
        try:
            response = requests.get(jwks_url, timeout=10)
            response.raise_for_status()
            
            cls._jwks_cache = response.json()
            cls._jwks_fetch_time = now
            
            return cls._jwks_cache
            
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            # Return cached version if available
            if cls._jwks_cache:
                return cls._jwks_cache
            raise

    @classmethod
    def verify_token(cls, token: str) -> Optional[Dict]:
        """Verify Supabase JWT and return decoded payload"""
        try:
            # Get unverified header to find key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                logger.warning("JWT missing kid header")
                return None
            
            # Get JWKS
            jwks = cls.get_jwks()
            
            # Find matching key
            key_data = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    key_data = key
                    break
            
            if not key_data:
                logger.warning(f"No matching key for kid: {kid}")
                return None
            
            # Convert JWK to public key
            public_key = cls._jwk_to_public_key(key_data)
            
            # Verify and decode
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience="authenticated",
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "require": ["exp", "sub", "aud"]
                }
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.debug("JWT expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"JWT validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected JWT verification error: {e}")
            return None

    @classmethod
    def _jwk_to_public_key(cls, jwk: Dict):
        """Convert JWK to cryptography public key"""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from base64 import urlsafe_b64decode
        
        def decode_value(val):
            # Add padding if needed
            missing_padding = len(val) % 4
            if missing_padding:
                val += '=' * (4 - missing_padding)
            return int.from_bytes(urlsafe_b64decode(val), 'big')
        
        e = decode_value(jwk['e'])
        n = decode_value(jwk['n'])
        
        public_numbers = rsa.RSAPublicNumbers(e, n)
        public_key = public_numbers.public_key(default_backend())
        
        return public_key

    @classmethod
    def get_or_create_user(cls, token_payload: Dict) -> Tuple[Optional[User], Optional[str]]:
        """Get existing user or create new one from token payload"""
        user_id = token_payload.get("sub")
        if not user_id:
            return None, "Invalid token: missing user ID"
        
        email = token_payload.get("email")
        if not email:
            return None, "Invalid token: missing email"
        
        # Extract user metadata
        user_metadata = token_payload.get("user_metadata", {})
        app_metadata = token_payload.get("app_metadata", {})
        
        # Determine auth provider
        auth_provider = "email"
        if app_metadata.get("provider") == "google":
            auth_provider = "google"
        elif user_metadata.get("iss") and "google" in user_metadata.get("iss"):
            auth_provider = "google"
        
        # Extract profile info
        name = (
            user_metadata.get("full_name") or 
            user_metadata.get("name") or 
            email.split("@")[0].replace(".", " ").title()
        )
        
        avatar_url = (
            user_metadata.get("avatar_url") or 
            user_metadata.get("picture")
        )
        
        try:
            # Check if user exists
            user = User.query.get(user_id)
            
            if user:
                # Update last login
                user.last_login_at = datetime.utcnow()
                
                # Update profile if changed
                if user.email != email:
                    user.email = email
                if name and user.name != name:
                    user.name = name
                if avatar_url and user.avatar_url != avatar_url:
                    user.avatar_url = avatar_url
                if user.auth_provider != auth_provider:
                    user.auth_provider = auth_provider
                
                db.session.commit()
                logger.info(f"User logged in: {user_id}")
                
            else:
                # Create new user
                user = User(
                    id=user_id,
                    email=email,
                    name=name,
                    avatar_url=avatar_url,
                    auth_provider=auth_provider
                )
                user.last_login_at = datetime.utcnow()
                
                db.session.add(user)
                db.session.commit()
                
                logger.info(f"New user created: {user_id} ({email})")
                
                # Optional: Send welcome email
                try:
                    from app.services.email_service import get_email_service
                    email_service = get_email_service()
                    email_service.send_welcome_email(email, user_name=name)
                except Exception as e:
                    logger.warning(f"Welcome email failed: {e}")
            
            return user, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"User provisioning failed: {e}")
            return None, "Failed to provision user"