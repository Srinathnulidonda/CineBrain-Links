# server/app/utils/jwt_utils.py

import jwt
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from flask import current_app

logger = logging.getLogger(__name__)


class JWTManager:
    
    def __init__(self):
        self.secret_key = current_app.config.get("SECRET_KEY")
        if not self.secret_key:
            raise ValueError("SECRET_KEY must be configured")
        
        self.algorithm = "HS256"
        self.access_token_expires = timedelta(hours=1)
        self.refresh_token_expires = timedelta(days=30)

    def generate_access_token(self, user_id: str, email: str) -> str:
        """Generate JWT access token"""
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "email": email,
            "iat": now,
            "exp": now + self.access_token_expires,
            "type": "access",
            "jti": secrets.token_urlsafe(16),  # Unique token ID for blacklisting
            "aud": "savlink-users"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def generate_refresh_token(self, user_id: str) -> str:
        """Generate JWT refresh token"""
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + self.refresh_token_expires,
            "type": "refresh",
            "jti": secrets.token_urlsafe(16),
            "aud": "savlink-users"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_access_token(self, token: str, check_blacklist: bool = True) -> Optional[Dict]:
        """Verify and decode access token"""
        try:
            # Decode token
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                audience="savlink-users",
                options={"require": ["exp", "sub", "type", "jti"]}
            )
            
            # Check token type
            if payload.get("type") != "access":
                logger.debug("Invalid token type")
                return None
            
            # Check if token is blacklisted
            if check_blacklist:
                jti = payload.get("jti")
                if jti:
                    try:
                        from app.services.redis_service import RedisService
                        redis = RedisService()
                        if redis.is_token_blacklisted(jti):
                            logger.debug("Token is blacklisted")
                            return None
                    except Exception as e:
                        logger.warning(f"Blacklist check failed: {e}")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return None
        except jwt.InvalidAudienceError:
            logger.debug("Invalid token audience")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None

    def verify_refresh_token(self, token: str) -> Optional[Dict]:
        """Verify and decode refresh token"""
        try:
            # Decode token
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                audience="savlink-users",
                options={"require": ["exp", "sub", "type"]}
            )
            
            # Check token type
            if payload.get("type") != "refresh":
                logger.debug("Invalid refresh token type")
                return None
            
            # Check if token is blacklisted
            import hashlib
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            try:
                from app.services.redis_service import RedisService
                redis = RedisService()
                if redis.is_token_blacklisted(f"refresh_{token_hash}"):
                    logger.debug("Refresh token is blacklisted")
                    return None
            except Exception as e:
                logger.warning(f"Refresh token blacklist check failed: {e}")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.debug("Refresh token expired")
            return None
        except jwt.InvalidAudienceError:
            logger.debug("Invalid refresh token audience")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid refresh token: {e}")
            return None
        except Exception as e:
            logger.error(f"Refresh token verification error: {e}")
            return None

    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """Get token expiration time without verification"""
        try:
            payload = jwt.decode(
                token, 
                options={"verify_signature": False, "verify_exp": False}
            )
            exp = payload.get("exp")
            if exp:
                return datetime.utcfromtimestamp(exp)
            return None
        except Exception:
            return None