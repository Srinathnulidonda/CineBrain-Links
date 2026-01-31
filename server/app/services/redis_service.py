# server/app/services/redis_service.py

"""
Redis service for caching and token management.
Compatible with Railway Redis and Upstash.
"""

import json
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import redis
from flask import current_app

logger = logging.getLogger(__name__)


class RedisService:
    """Service for Redis operations - caching and JWT blacklist."""
    
    _instance: Optional[redis.Redis] = None
    _connection_attempted: bool = False
    
    def __init__(self):
        """Initialize Redis connection."""
        if not RedisService._connection_attempted:
            self._connect()
        self.client = RedisService._instance
    
    def _connect(self) -> None:
        """Establish Redis connection with Railway/Upstash compatibility."""
        RedisService._connection_attempted = True
        
        redis_url = current_app.config.get("REDIS_URL")
        
        if not redis_url:
            logger.warning("⚠️ Redis URL not configured - running without cache")
            return
        
        try:
            # Upstash requires SSL - ensure rediss:// scheme
            if "upstash.io" in redis_url and redis_url.startswith("redis://"):
                redis_url = redis_url.replace("redis://", "rediss://", 1)
                logger.info("Converted Upstash URL to use SSL (rediss://)")
            
            connection_kwargs = {
                "decode_responses": True,
                "socket_timeout": 10,
                "socket_connect_timeout": 10,
                "retry_on_timeout": True,
                "health_check_interval": 30,
            }
            
            RedisService._instance = redis.from_url(
                redis_url,
                **connection_kwargs
            )
            
            # Test connection
            RedisService._instance.ping()
            logger.info("✅ Redis connection established successfully")
            
        except redis.ConnectionError as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
            RedisService._instance = None
        except Exception as e:
            logger.warning(f"⚠️ Redis initialization error: {e}")
            RedisService._instance = None
    
    def _is_available(self) -> bool:
        """Check if Redis is available."""
        return self.client is not None
    
    # ==================== LINK CACHING ====================
    
    def cache_link(self, slug: str, link_data: dict, ttl: Optional[int] = None) -> bool:
        """Cache link data for fast redirect lookups."""
        if not self._is_available():
            return False
            
        try:
            if ttl is None:
                ttl = current_app.config.get("CACHE_TTL_LINK", 3600)
            
            key = f"cinbrainlinks:link:{slug}"
            self.client.setex(key, ttl, json.dumps(link_data))
            logger.debug(f"Cached link: {slug}")
            return True
            
        except redis.RedisError as e:
            logger.error(f"Failed to cache link {slug}: {e}")
            return False
    
    def get_cached_link(self, slug: str) -> Optional[dict]:
        """Retrieve cached link data."""
        if not self._is_available():
            return None
            
        try:
            key = f"cinbrainlinks:link:{slug}"
            data = self.client.get(key)
            
            if data:
                link_data = json.loads(data)
                
                # Check if link has expired
                if link_data.get("expires_at"):
                    expires_at = datetime.fromisoformat(link_data["expires_at"])
                    if datetime.utcnow() > expires_at:
                        self.invalidate_link_cache(slug)
                        return None
                
                logger.debug(f"Cache hit for link: {slug}")
                return link_data
            
            logger.debug(f"Cache miss for link: {slug}")
            return None
            
        except redis.RedisError as e:
            logger.error(f"Failed to get cached link {slug}: {e}")
            return None
    
    def invalidate_link_cache(self, slug: str) -> bool:
        """Remove link from cache."""
        if not self._is_available():
            return False
            
        try:
            key = f"cinbrainlinks:link:{slug}"
            self.client.delete(key)
            logger.debug(f"Invalidated cache for link: {slug}")
            return True
            
        except redis.RedisError as e:
            logger.error(f"Failed to invalidate cache for {slug}: {e}")
            return False
    
    # ==================== CLICK COUNTING ====================
    
    def queue_click_increment(self, slug: str) -> bool:
        """Queue click increment for async processing."""
        if not self._is_available():
            return False
            
        try:
            self.client.rpush("cinbrainlinks:click_queue", slug)
            return True
        except redis.RedisError as e:
            logger.error(f"Failed to queue click for {slug}: {e}")
            return False
    
    def get_pending_clicks(self, batch_size: int = 100) -> list:
        """Get pending clicks from the queue."""
        if not self._is_available():
            return []
            
        try:
            clicks = []
            for _ in range(batch_size):
                slug = self.client.lpop("cinbrainlinks:click_queue")
                if slug is None:
                    break
                clicks.append(slug)
            return clicks
        except redis.RedisError as e:
            logger.error(f"Failed to get pending clicks: {e}")
            return []
    
    # ==================== JWT BLACKLIST ====================
    
    def blacklist_token(self, jti: str, ttl: Optional[int] = None) -> bool:
        """Add JWT token to blacklist."""
        if not self._is_available():
            logger.debug(f"Redis unavailable - token blacklist disabled")
            return False
            
        try:
            if ttl is None:
                ttl = current_app.config.get("CACHE_TTL_BLACKLIST", 86400 * 31)
            
            key = f"cinbrainlinks:blacklist:{jti}"
            self.client.setex(key, ttl, "1")
            logger.debug(f"Token blacklisted: {jti[:8]}...")
            return True
            
        except redis.RedisError as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False
    
    def is_token_blacklisted(self, jti: str) -> bool:
        """Check if JWT token is blacklisted."""
        if not self._is_available():
            return False
            
        try:
            key = f"cinbrainlinks:blacklist:{jti}"
            return self.client.exists(key) > 0
        except redis.RedisError as e:
            logger.error(f"Failed to check token blacklist: {e}")
            return False
    
    # ==================== PASSWORD RESET ====================
    
    def store_reset_token(self, token: str, user_id: str, ttl: Optional[int] = None) -> bool:
        """Store password reset token."""
        if not self._is_available():
            logger.debug("Redis unavailable - password reset tokens not cached")
            return False
            
        try:
            if ttl is None:
                ttl = current_app.config.get("PASSWORD_RESET_TOKEN_EXPIRES", 3600)
            
            key = f"cinbrainlinks:reset:{token}"
            self.client.setex(key, ttl, user_id)
            return True
            
        except redis.RedisError as e:
            logger.error(f"Failed to store reset token: {e}")
            return False
    
    def get_reset_token_user(self, token: str) -> Optional[str]:
        """Get user ID associated with reset token."""
        if not self._is_available():
            return None
            
        try:
            key = f"cinbrainlinks:reset:{token}"
            user_id = self.client.get(key)
            return user_id
        except redis.RedisError as e:
            logger.error(f"Failed to get reset token: {e}")
            return None
    
    def invalidate_reset_token(self, token: str) -> bool:
        """Invalidate password reset token."""
        if not self._is_available():
            return False
            
        try:
            key = f"cinbrainlinks:reset:{token}"
            self.client.delete(key)
            return True
        except redis.RedisError as e:
            logger.error(f"Failed to invalidate reset token: {e}")
            return False
    
    # ==================== RATE LIMITING ====================
    
    def check_rate_limit(self, key: str, limit: int, window: int) -> tuple:
        """Check and update rate limit."""
        if not self._is_available():
            return True, limit
            
        try:
            rate_key = f"cinbrainlinks:rate:{key}"
            current = self.client.get(rate_key)
            
            if current is None:
                self.client.setex(rate_key, window, 1)
                return True, limit - 1
            
            current = int(current)
            if current >= limit:
                return False, 0
            
            self.client.incr(rate_key)
            return True, limit - current - 1
            
        except redis.RedisError as e:
            logger.error(f"Rate limit check failed: {e}")
            return True, limit
    
    # ==================== STATS ====================
    
    def get_stats(self) -> dict:
        """Get Redis service statistics."""
        stats = {
            "available": self._is_available(),
            "connected": False
        }
        
        if self._is_available():
            try:
                self.client.ping()
                stats["connected"] = True
                
                stats["click_queue_size"] = self.client.llen("cinbrainlinks:click_queue")
                stats["email_queue_size"] = self.client.llen("cinbrainlinks:email_queue")
                
                link_keys = self.client.keys("cinbrainlinks:link:*")
                stats["cached_links"] = len(link_keys)
                
            except Exception as e:
                stats["error"] = str(e)
        
        return stats