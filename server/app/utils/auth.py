# server/app/utils/auth.py

import logging
from functools import wraps
from typing import Optional

from flask import request, g, current_app

from app.models.user import User
from app.services.redis_service import RedisService
from app.utils.jwt_utils import JWTManager

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
    """Decorator that requires valid JWT and provisions user"""
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
        
        # Verify JWT token
        jwt_manager = JWTManager()
        payload = jwt_manager.verify_access_token(token)
        
        if not payload:
            return current_app.api_response.error(
                "Invalid or expired token", 
                401, 
                "INVALID_TOKEN"
            )
        
        # Get user ID from payload
        user_id = payload.get("sub")
        if not user_id:
            return current_app.api_response.error(
                "Invalid token: missing user ID", 
                401, 
                "INVALID_TOKEN"
            )
        
        # Check if user tokens have been invalidated
        try:
            redis = RedisService()
            if redis.is_in_set("invalidated_users", user_id):
                return current_app.api_response.error(
                    "Session expired. Please log in again.", 
                    401, 
                    "SESSION_EXPIRED"
                )
        except Exception:
            # If Redis is unavailable, continue without this check
            pass
        
        # Get user from database
        user = User.query.get(user_id)
        if not user:
            return current_app.api_response.error(
                "User not found", 
                401, 
                "USER_NOT_FOUND"
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
                # Verify token
                jwt_manager = JWTManager()
                payload = jwt_manager.verify_access_token(token)
                
                if payload:
                    user_id = payload.get("sub")
                    if user_id:
                        # Check if tokens invalidated
                        try:
                            redis = RedisService()
                            if not redis.is_in_set("invalidated_users", user_id):
                                # Get user
                                user = User.query.get(user_id)
                                if user and user.is_active:
                                    g.current_user = user
                                    g.current_user_id = user.id
                                    g.token_payload = payload
                                    g.token = token
                        except Exception:
                            # Get user without Redis check
                            user = User.query.get(user_id)
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
        # For example, check a field in user model or email domain
        # For now, we'll use email domain as example
        
        if not user.email.endswith("@savlink.app"):  # Adjust this logic
            return current_app.api_response.error(
                "Admin access required", 
                403, 
                "ADMIN_REQUIRED"
            )
        
        return f(*args, **kwargs)
    
    return decorated_function


def rate_limit_by_user(f):
    """Decorator that applies rate limiting per authenticated user"""
    @wraps(f)
    @require_auth
    def decorated_function(*args, **kwargs):
        try:
            redis = RedisService()
            user_id = g.current_user_id
            
            # Check rate limit (10 requests per minute per user)
            allowed, remaining = redis.rate_limit_check(
                f"user_rate_limit:{user_id}", 
                limit=10, 
                window=60
            )
            
            if not allowed:
                return current_app.api_response.error(
                    "Rate limit exceeded. Please slow down.",
                    429,
                    "RATE_LIMITED"
                )
            
            # Add rate limit headers
            from flask import make_response
            response = make_response(f(*args, **kwargs))
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response
            
        except Exception:
            # If Redis is unavailable, continue without rate limiting
            return f(*args, **kwargs)
    
    return decorated_function


def require_email_verification(f):
    """Decorator that requires verified email"""
    @wraps(f)
    @require_auth
    def decorated_function(*args, **kwargs):
        user = g.current_user
        
        if not user.email_verified:
            return current_app.api_response.error(
                "Email verification required", 
                403, 
                "EMAIL_NOT_VERIFIED"
            )
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_user() -> Optional[User]:
    """Get current authenticated user from request context"""
    return getattr(g, 'current_user', None)


def get_current_user_id() -> Optional[str]:
    """Get current authenticated user ID from request context"""
    return getattr(g, 'current_user_id', None)


def is_authenticated() -> bool:
    """Check if current request is authenticated"""
    return get_current_user() is not None