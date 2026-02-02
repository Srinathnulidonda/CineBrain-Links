# server/app/routes/auth.py

import secrets
import logging
from datetime import datetime

from flask import Blueprint, request, current_app
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
logger = logging.getLogger(__name__)


def api_response():
    return current_app.api_response


def get_client_info() -> dict:
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip:
        ip = ip.split(',')[0].strip()
    
    ua = request.headers.get('User-Agent', '')
    
    if 'Mobile' in ua or 'Android' in ua:
        device = "Mobile"
    elif 'iPad' in ua or 'Tablet' in ua:
        device = "Tablet"
    else:
        device = "Desktop"
    
    return {'ip': ip or 'unknown', 'device': device}


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per minute")
def register():
    data = request.get_json() or {}
    
    email = data.get("email", "").strip()
    password = data.get("password", "")
    name = data.get("name", "").strip()
    
    is_valid, normalized_email, error = InputValidator.validate_email(email)
    if not is_valid:
        return api_response().error(error, 400, "INVALID_EMAIL")
    
    is_valid, error = InputValidator.validate_password(password)
    if not is_valid:
        return api_response().error(error, 400, "INVALID_PASSWORD")
    
    if User.query.filter_by(email=normalized_email).first():
        return api_response().error("An account with this email already exists", 409, "EMAIL_EXISTS")
    
    try:
        user = User(email=normalized_email, password=password)
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"User registered: {user.id}")
        
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        try:
            email_service = get_email_service()
            user_name = name or normalized_email.split('@')[0].title()
            email_service.send_welcome_email(user.email, user_name=user_name)
        except Exception as e:
            logger.warning(f"Welcome email failed: {e}")
        
        return api_response().success(
            data={
                "user": user.to_dict(),
                "access_token": access_token,
                "refresh_token": refresh_token
            },
            message="Account created successfully",
            status=201
        )
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration failed: {e}")
        return api_response().error("Registration failed. Please try again.", 500)


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    data = request.get_json() or {}
    
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    if not email or not password:
        return api_response().error("Email and password are required", 400)
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        logger.info(f"Failed login attempt for: {email[:3]}***")
        return api_response().error("Invalid email or password", 401, "INVALID_CREDENTIALS")
    
    if not user.is_active:
        return api_response().error("This account has been deactivated", 403, "ACCOUNT_INACTIVE")
    
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    logger.info(f"User logged in: {user.id}")
    
    return api_response().success(
        data={
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token
        },
        message="Signed in successfully"
    )


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    try:
        jwt_data = get_jwt()
        jti = jwt_data["jti"]
        exp = jwt_data["exp"]
        
        ttl = max(int(exp - datetime.utcnow().timestamp()), 0)
        
        redis_service = RedisService()
        redis_service.blacklist_token(jti, ttl)
        
        logger.info(f"User logged out: {get_jwt_identity()}")
        
        return api_response().success(message="Signed out successfully")
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return api_response().error("Sign out failed", 500)


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            return api_response().error("Session invalid", 401, "INVALID_SESSION")
        
        access_token = create_access_token(identity=user_id)
        
        return api_response().success(data={"access_token": access_token})
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return api_response().error("Token refresh failed", 500)


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user = User.query.get(get_jwt_identity())
    
    if not user:
        return api_response().error("User not found", 404)
    
    return api_response().success(data={"user": user.to_dict()})


@auth_bp.route("/password/forgot", methods=["POST"])
@limiter.limit("3 per minute")
def forgot_password():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    
    if not email:
        return api_response().error("Email is required", 400)
    
    success_msg = "If an account exists with this email, you will receive a password reset link."
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return api_response().success(message=success_msg)
    
    try:
        reset_token = secrets.token_urlsafe(32)
        
        redis_service = RedisService()
        redis_service.store_reset_token(reset_token, user.id)
        
        client_info = get_client_info()
        
        email_service = get_email_service()
        email_service.send_password_reset_email(
            to_email=user.email,
            reset_token=reset_token,
            user_name=user.email.split('@')[0].title(),
            request_info=client_info
        )
        
        logger.info(f"Password reset requested for user: {user.id}")
        
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
    
    return api_response().success(message=success_msg)


@auth_bp.route("/password/reset", methods=["POST"])
@limiter.limit("5 per minute")
def reset_password():
    data = request.get_json() or {}
    
    token = data.get("token", "").strip()
    new_password = data.get("password", "")
    
    if not token:
        return api_response().error("Reset token is required", 400)
    
    is_valid, error = InputValidator.validate_password(new_password)
    if not is_valid:
        return api_response().error(error, 400, "INVALID_PASSWORD")
    
    try:
        redis_service = RedisService()
        user_id = redis_service.get_reset_token_user(token)
        
        if not user_id:
            return api_response().error(
                "This reset link is invalid or has expired. Please request a new one.",
                400,
                "INVALID_TOKEN"
            )
        
        user = User.query.get(user_id)
        if not user:
            return api_response().error("Account not found", 404)
        
        user.set_password(new_password)
        db.session.commit()
        
        redis_service.invalidate_reset_token(token)
        
        logger.info(f"Password reset completed for user: {user.id}")
        
        return api_response().success(message="Password updated successfully")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Password reset error: {e}")
        return api_response().error("Password reset failed", 500)


@auth_bp.route("/password/change", methods=["POST"])
@jwt_required()
def change_password():
    data = request.get_json() or {}
    
    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")
    
    if not current_password or not new_password:
        return api_response().error("Current and new passwords are required", 400)
    
    is_valid, error = InputValidator.validate_password(new_password)
    if not is_valid:
        return api_response().error(error, 400, "INVALID_PASSWORD")
    
    try:
        user = User.query.get(get_jwt_identity())
        
        if not user:
            return api_response().error("User not found", 404)
        
        if not user.check_password(current_password):
            return api_response().error("Current password is incorrect", 401)
        
        user.set_password(new_password)
        db.session.commit()
        
        logger.info(f"Password changed for user: {user.id}")
        
        return api_response().success(message="Password changed successfully")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Password change error: {e}")
        return api_response().error("Password change failed", 500)