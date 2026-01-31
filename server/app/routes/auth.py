# server/app/routes/auth.py

"""
Authentication routes.
Handles user registration, login, logout, and password reset.
"""

import secrets
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)

from app.extensions import db, limiter
from app.models.user import User
from app.services.redis_service import RedisService
from app.services.email_service import get_email_service
from app.utils.validators import InputValidator

auth_bp = Blueprint("auth", __name__)


def get_request_info() -> dict:
    """Extract request information for logging and emails."""
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address:
        ip_address = ip_address.split(',')[0].strip()
    
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # Detect device type
    device = "Unknown device"
    if 'Mobile' in user_agent or 'Android' in user_agent:
        device = "Mobile device"
    elif 'iPad' in user_agent or 'Tablet' in user_agent:
        device = "Tablet"
    elif 'Windows' in user_agent:
        device = "Windows PC"
    elif 'Macintosh' in user_agent:
        device = "Mac"
    elif 'Linux' in user_agent:
        device = "Linux PC"
    
    # Detect browser
    browser = ""
    if 'Chrome' in user_agent and 'Edg' not in user_agent:
        browser = "Chrome"
    elif 'Firefox' in user_agent:
        browser = "Firefox"
    elif 'Safari' in user_agent and 'Chrome' not in user_agent:
        browser = "Safari"
    elif 'Edg' in user_agent:
        browser = "Edge"
    
    if browser:
        device = f"{browser} on {device}"
    
    return {
        'ip': ip_address,
        'device': device,
        'user_agent': user_agent
    }


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per minute")
def register():
    """
    Register a new user.
    
    Request body:
        - email: User email address
        - password: User password
        - name: User name (optional)
    
    Returns:
        User data and JWT tokens on success
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    
    email = data.get("email", "").strip()
    password = data.get("password", "")
    name = data.get("name", "").strip()
    
    # Validate email
    is_valid, normalized_email, error = InputValidator.validate_email(email)
    if not is_valid:
        return jsonify({"error": error}), 400
    
    # Validate password
    is_valid, error = InputValidator.validate_password(password)
    if not is_valid:
        return jsonify({"error": error}), 400
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=normalized_email).first()
    if existing_user:
        return jsonify({"error": "Email already registered"}), 409
    
    try:
        # Create new user
        user = User(email=normalized_email, password=password)
        db.session.add(user)
        db.session.commit()
        
        # Generate tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        # Send welcome email (async)
        try:
            email_service = get_email_service()
            user_name = name if name else normalized_email.split('@')[0].title()
            email_service.send_welcome_email(user.email, user_name=user_name)
        except Exception as e:
            current_app.logger.error(f"Failed to send welcome email: {e}")
        
        return jsonify({
            "message": "Registration successful",
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration error: {e}")
        return jsonify({"error": "Registration failed"}), 500


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    """
    Authenticate user and return JWT tokens.
    
    Request body:
        - email: User email address
        - password: User password
    
    Returns:
        User data and JWT tokens on success
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    # Find user
    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401
    
    if not user.is_active:
        return jsonify({"error": "Account is deactivated"}), 403
    
    # Generate tokens
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    return jsonify({
        "message": "Login successful",
        "user": user.to_dict(),
        "access_token": access_token,
        "refresh_token": refresh_token
    }), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    Logout user by blacklisting their JWT token.
    
    Returns:
        Success message
    """
    try:
        jwt_data = get_jwt()
        jti = jwt_data["jti"]
        exp = jwt_data["exp"]
        
        # Calculate TTL for blacklist entry
        now = datetime.utcnow().timestamp()
        ttl = int(exp - now)
        
        # Blacklist the token
        redis_service = RedisService()
        redis_service.blacklist_token(jti, ttl)
        
        return jsonify({"message": "Logout successful"}), 200
        
    except Exception as e:
        current_app.logger.error(f"Logout error: {e}")
        return jsonify({"error": "Logout failed"}), 500


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token using refresh token.
    
    Returns:
        New access token
    """
    try:
        user_id = get_jwt_identity()
        
        # Verify user still exists and is active
        user = User.query.get(user_id)
        if not user or not user.is_active:
            return jsonify({"error": "User not found or inactive"}), 401
        
        # Generate new access token
        access_token = create_access_token(identity=user_id)
        
        return jsonify({
            "access_token": access_token
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {e}")
        return jsonify({"error": "Token refresh failed"}), 500


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """
    Get current authenticated user's profile.
    
    Returns:
        User data
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({"user": user.to_dict()}), 200
        
    except Exception as e:
        current_app.logger.error(f"Get user error: {e}")
        return jsonify({"error": "Failed to get user data"}), 500


@auth_bp.route("/password/forgot", methods=["POST"])
@limiter.limit("3 per minute")
def forgot_password():
    """
    Request password reset email.
    
    Request body:
        - email: User email address
    
    Returns:
        Success message (always returns success to prevent email enumeration)
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    
    email = data.get("email", "").strip().lower()
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
    
    # Always return success to prevent email enumeration
    success_response = jsonify({
        "message": "If an account exists with this email, a password reset link will be sent."
    }), 200
    
    # Find user
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return success_response
    
    try:
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        
        # Store token in Redis
        redis_service = RedisService()
        redis_service.store_reset_token(reset_token, user.id)
        
        # Get request info for email
        request_info = get_request_info()
        
        # Send reset email with request info
        email_service = get_email_service()
        user_name = email.split('@')[0].title()
        email_service.send_password_reset_email(
            to_email=user.email,
            reset_token=reset_token,
            user_name=user_name,
            request_info=request_info
        )
        
    except Exception as e:
        current_app.logger.error(f"Password reset request error: {e}")
    
    return success_response


@auth_bp.route("/password/reset", methods=["POST"])
@limiter.limit("5 per minute")
def reset_password():
    """
    Reset password using token.
    
    Request body:
        - token: Password reset token
        - password: New password
    
    Returns:
        Success message
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    
    token = data.get("token", "").strip()
    new_password = data.get("password", "")
    
    if not token:
        return jsonify({"error": "Reset token is required"}), 400
    
    # Validate password
    is_valid, error = InputValidator.validate_password(new_password)
    if not is_valid:
        return jsonify({"error": error}), 400
    
    try:
        # Get user ID from token
        redis_service = RedisService()
        user_id = redis_service.get_reset_token_user(token)
        
        if not user_id:
            return jsonify({"error": "Invalid or expired reset token"}), 400
        
        # Find user
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Update password
        user.set_password(new_password)
        db.session.commit()
        
        # Invalidate the reset token
        redis_service.invalidate_reset_token(token)
        
        return jsonify({"message": "Password reset successful"}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Password reset error: {e}")
        return jsonify({"error": "Password reset failed"}), 500


@auth_bp.route("/password/change", methods=["POST"])
@jwt_required()
def change_password():
    """
    Change password for authenticated user.
    
    Request body:
        - current_password: Current password
        - new_password: New password
    
    Returns:
        Success message
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    
    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")
    
    if not current_password or not new_password:
        return jsonify({"error": "Current and new passwords are required"}), 400
    
    # Validate new password
    is_valid, error = InputValidator.validate_password(new_password)
    if not is_valid:
        return jsonify({"error": error}), 400
    
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Verify current password
        if not user.check_password(current_password):
            return jsonify({"error": "Current password is incorrect"}), 401
        
        # Update password
        user.set_password(new_password)
        db.session.commit()
        
        return jsonify({"message": "Password changed successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Password change error: {e}")
        return jsonify({"error": "Password change failed"}), 500


@auth_bp.route("/email/stats", methods=["GET"])
@jwt_required()
def get_email_stats():
    """
    Get email service statistics (admin only in production).
    
    Returns:
        Email queue statistics
    """
    try:
        email_service = get_email_service()
        stats = email_service.get_queue_stats()
        return jsonify({"stats": stats}), 200
    except Exception as e:
        current_app.logger.error(f"Email stats error: {e}")
        return jsonify({"error": "Failed to get email stats"}), 500