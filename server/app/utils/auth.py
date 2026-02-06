# server/app/utils/auth.py

import logging
from functools import wraps
from typing import Optional

from flask import request, g, current_app

logger = logging.getLogger(__name__)


def extract_token_from_header() -> Optional[str]:
    """Extract Bearer token from Authorization header"""
    auth_header = request.headers.get("Authorization", "")
    
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    
    return None


def extract_token_from_body() -> Optional[str]:
    """Extract token from request body as fallback"""
    try:
        data = request.get_json()
        if data and 'idToken' in data:
            return data['idToken']
    except Exception:
        pass
    
    return None


def require_auth(f):
    """Decorator that requires valid Firebase ID token and provisions user"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Import here to avoid circular imports
        from app.services.firebase_auth import FirebaseAuthService
        
        # Extract token from header first, then from body as fallback
        token = extract_token_from_header()
        
        if not token:
            token = extract_token_from_body()
        
        if not token:
            logger.warning("No authentication token found in request")
            return current_app.api_response.error(
                "Authentication required", 
                401, 
                "MISSING_TOKEN"
            )
        
        # Log token for debugging (only first few characters)
        logger.debug(f"Verifying token: {token[:20]}...")
        
        # Verify Firebase ID token
        claims = FirebaseAuthService.verify_token(token)
        
        if not claims:
            logger.warning("Token verification failed")
            return current_app.api_response.error(
                "Invalid or expired token", 
                401, 
                "INVALID_TOKEN"
            )
        
        # Get or create user
        user, error = FirebaseAuthService.get_or_create_user(claims)
        
        if not user:
            logger.error(f"User provisioning failed: {error}")
            return current_app.api_response.error(
                "Authentication failed", 
                500, 
                "AUTH_ERROR"
            )
        
        # Log successful authentication
        logger.info(f"User authenticated: {user.email}")
        
        # Attach to request context
        g.current_user = user
        g.current_user_id = user.id
        g.token_claims = claims
        
        return f(*args, **kwargs)
    
    return decorated_function


def optional_auth(f):
    """Decorator that optionally authenticates user if token is present"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Import here to avoid circular imports
        from app.services.firebase_auth import FirebaseAuthService
        
        # Try to extract token
        token = extract_token_from_header()
        if not token:
            token = extract_token_from_body()
        
        if token:
            # Verify Firebase ID token
            claims = FirebaseAuthService.verify_token(token)
            
            if claims:
                # Get or create user
                user, error = FirebaseAuthService.get_or_create_user(claims)
                
                if user:
                    # Attach to request context
                    g.current_user = user
                    g.current_user_id = user.id
                    g.token_claims = claims
                else:
                    logger.warning(f"User provisioning failed: {error}")
        
        # Set defaults if no user authenticated
        if not hasattr(g, 'current_user'):
            g.current_user = None
            g.current_user_id = None
            g.token_claims = None
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_user():
    """Get current authenticated user from request context"""
    return getattr(g, 'current_user', None)


def get_current_user_id():
    """Get current authenticated user ID from request context"""
    return getattr(g, 'current_user_id', None)


def get_token_claims():
    """Get current token claims from request context"""
    return getattr(g, 'token_claims', None)


def is_authenticated():
    """Check if current request is authenticated"""
    return getattr(g, 'current_user', None) is not None


def require_admin(f):
    """Decorator that requires admin privileges (can be extended later)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return current_app.api_response.error(
                "Authentication required", 
                401, 
                "UNAUTHORIZED"
            )
        
        user = get_current_user()
        
        # For now, check if user email is in admin list
        # You can extend this logic as needed
        admin_emails = current_app.config.get('ADMIN_EMAILS', [])
        if user.email not in admin_emails:
            return current_app.api_response.error(
                "Admin access required", 
                403, 
                "FORBIDDEN"
            )
        
        return f(*args, **kwargs)
    
    return decorated_function


# Compatibility aliases for existing code
jwt_required = require_auth
get_jwt_identity = get_current_user_id