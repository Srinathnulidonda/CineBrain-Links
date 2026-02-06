# server/app/utils/auth.py

import logging
from functools import wraps
from typing import Optional

from flask import request, g, current_app

from app.services.supabase_auth import SupabaseAuthService
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)


def extract_token_from_header() -> Optional[str]:
    """Extract Bearer token from Authorization header"""
    auth_header = request.headers.get("Authorization", "")
    
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    
    # Also check for lowercase 'bearer'
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:]
    
    return None


def require_auth(f):
    """Decorator that requires valid Supabase JWT and provisions user"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract token
        token = extract_token_from_header()
        
        if not token:
            return current_app.api_response.error(
                "Authentication required", 
                401, 
                "MISSING_TOKEN"
            )
        
        # Check if token is blacklisted
        try:
            redis = RedisService()
            # Extract JTI or use token prefix for blacklist check
            import jwt as pyjwt
            try:
                unverified_payload = pyjwt.decode(token, options={"verify_signature": False})
                jti = unverified_payload.get("jti") or token[:50]
            except:
                jti = token[:50]
            
            if redis.is_token_blacklisted(jti):
                return current_app.api_response.error(
                    "This session has been signed out", 
                    401, 
                    "TOKEN_REVOKED"
                )
        except Exception as e:
            logger.debug(f"Blacklist check failed: {e}")
        
        # Verify Supabase JWT
        payload = SupabaseAuthService.verify_token(token)
        
        if not payload:
            return current_app.api_response.error(
                "Invalid or expired token", 
                401, 
                "INVALID_TOKEN"
            )
        
        # Get or create user
        user, error = SupabaseAuthService.get_or_create_user(payload)
        
        if not user:
            logger.error(f"User provisioning failed: {error}")
            return current_app.api_response.error(
                "Authentication failed", 
                500, 
                "AUTH_ERROR"
            )
        
        # Check if user is active
        if not user.is_active:
            return current_app.api_response.error(
                "Account has been deactivated", 
                403, 
                "ACCOUNT_INACTIVE"
            )
        
        # Attach to request context
        g.current_user = user
        g.current_user_id = user.id
        g.token_payload = payload
        g.token = token
        
        return f(*args, **kwargs)
    
    return decorated_function


# Compatibility alias for existing code
jwt_required = require_auth


def optional_auth(f):
    """Decorator that optionally authenticates user if token is present"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Try to extract token
        token = extract_token_from_header()
        
        if token:
            try:
                # Check blacklist
                redis = RedisService()
                import jwt as pyjwt
                try:
                    unverified_payload = pyjwt.decode(token, options={"verify_signature": False})
                    jti = unverified_payload.get("jti") or token[:50]
                except:
                    jti = token[:50]
                
                if not redis.is_token_blacklisted(jti):
                    # Verify token
                    payload = SupabaseAuthService.verify_token(token)
                    
                    if payload:
                        # Get user
                        user, _ = SupabaseAuthService.get_or_create_user(payload)
                        
                        if user and user.is_active:
                            g.current_user = user
                            g.current_user_id = user.id
                            g.token_payload = payload
                            g.token = token
            except Exception as e:
                logger.debug(f"Optional auth failed: {e}")
        
        # Continue even if auth failed/missing
        if not hasattr(g, 'current_user'):
            g.current_user = None
            g.current_user_id = None
            g.token_payload = None
            g.token = None
        
        return f(*args, **kwargs)
    
    return decorated_function


def admin_required(f):
    """Decorator that requires admin privileges"""
    @wraps(f)
    @require_auth
    def decorated_function(*args, **kwargs):
        # Check if user has admin role
        user = g.current_user
        
        # You can implement admin check based on your needs
        # For example, check a field in user model or a specific claim in JWT
        # For now, we'll use email domain as example
        
        if not user.email.endswith("@savlink.app"):  # Adjust this logic
            return current_app.api_response.error(
                "Admin access required", 
                403, 
                "ADMIN_REQUIRED"
            )
        
        return f(*args, **kwargs)
    
    return decorated_function