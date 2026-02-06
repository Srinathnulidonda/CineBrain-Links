# server/app/services/firebase_auth.py

import logging
from datetime import datetime
from typing import Optional, Dict, Tuple

import firebase_admin
from firebase_admin import auth, credentials
from flask import current_app

from app.extensions import db
from app.models.user import User

logger = logging.getLogger(__name__)


class FirebaseAuthService:
    _app = None
    _initialized = False

    @classmethod
    def initialize(cls):
        """Initialize Firebase Admin SDK"""
        if cls._initialized:
            return
        
        try:
            # Try to get existing app
            cls._app = firebase_admin.get_app()
        except ValueError:
            # Initialize new app
            firebase_config = current_app.config.get("FIREBASE_CONFIG")
            
            if firebase_config:
                # Use service account file/dict
                if isinstance(firebase_config, str):
                    cred = credentials.Certificate(firebase_config)
                else:
                    cred = credentials.Certificate(firebase_config)
            else:
                # Use default credentials (for Cloud Run, etc.)
                cred = credentials.ApplicationDefault()
            
            cls._app = firebase_admin.initialize_app(cred)
        
        cls._initialized = True
        logger.info("Firebase Admin SDK initialized")

    @classmethod
    def verify_token(cls, id_token: str) -> Optional[Dict]:
        """Verify Firebase ID token and return decoded claims"""
        cls.initialize()
        
        try:
            # Verify the ID token
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
            
        except auth.ExpiredIdTokenError:
            logger.debug("Firebase token expired")
            return None
        except auth.InvalidIdTokenError as e:
            logger.debug(f"Invalid Firebase token: {e}")
            return None
        except Exception as e:
            logger.error(f"Firebase token verification failed: {e}")
            return None

    @classmethod
    def get_or_create_user(cls, token_claims: Dict) -> Tuple[Optional[User], Optional[str]]:
        """Get existing user or create new one from Firebase token claims"""
        firebase_uid = token_claims.get("uid")
        if not firebase_uid:
            return None, "Invalid token: missing user ID"
        
        email = token_claims.get("email")
        if not email:
            return None, "Invalid token: missing email"
        
        # Extract user info from token
        name = token_claims.get("name")
        if not name:
            name = email.split("@")[0].replace(".", " ").title()
        
        avatar_url = token_claims.get("picture")
        
        # Determine auth provider from Firebase provider data
        auth_provider = "email"
        firebase_info = token_claims.get("firebase", {})
        sign_in_provider = firebase_info.get("sign_in_provider", "password")
        
        if sign_in_provider == "google.com":
            auth_provider = "google"
        elif sign_in_provider == "password":
            auth_provider = "email"
        
        try:
            # Check if user exists by Firebase UID
            user = User.query.filter_by(firebase_uid=firebase_uid).first()
            
            if user:
                # Update existing user
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
                logger.info(f"User logged in: {firebase_uid}")
                
            else:
                # Check if user exists by email (for migration cases)
                existing_user = User.query.filter_by(email=email).first()
                
                if existing_user:
                    # Link Firebase UID to existing user
                    existing_user.firebase_uid = firebase_uid
                    existing_user.last_login_at = datetime.utcnow()
                    existing_user.auth_provider = auth_provider
                    if name:
                        existing_user.name = name
                    if avatar_url:
                        existing_user.avatar_url = avatar_url
                    
                    db.session.commit()
                    user = existing_user
                    logger.info(f"Linked Firebase UID to existing user: {email}")
                else:
                    # Create new user in Supabase database
                    user = User(
                        firebase_uid=firebase_uid,
                        email=email,
                        name=name,
                        avatar_url=avatar_url,
                        auth_provider=auth_provider
                    )
                    user.last_login_at = datetime.utcnow()
                    
                    db.session.add(user)
                    db.session.commit()
                    
                    logger.info(f"New user created: {firebase_uid} ({email})")
                    
                    # Send welcome email
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