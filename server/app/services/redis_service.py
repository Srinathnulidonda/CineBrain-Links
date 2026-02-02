# server/app/services/redis_service.py

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

import redis
from flask import current_app

logger = logging.getLogger(__name__)

KEY_PREFIX = "savlink"


class RedisService:
    _client: Optional[redis.Redis] = None
    _initialized: bool = False

    def __init__(self):
        if not RedisService._initialized:
            self._connect()
        self.client = RedisService._client

    def _connect(self) -> None:
        RedisService._initialized = True

        redis_url = current_app.config.get("REDIS_URL")

        if not redis_url:
            logger.info("Redis not configured, using memory fallback")
            return

        try:
            if "upstash.io" in redis_url and redis_url.startswith("redis://"):
                redis_url = redis_url.replace("redis://", "rediss://", 1)

            RedisService._client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=10,
                socket_connect_timeout=10,
                retry_on_timeout=True,
                health_check_interval=30
            )

            RedisService._client.ping()
            logger.info("Redis connected")

        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            RedisService._client = None

    def _available(self) -> bool:
        if self.client is None:
            return False
        try:
            self.client.ping()
            return True
        except Exception:
            return False

    def _key(self, *parts) -> str:
        return f"{KEY_PREFIX}:{':'.join(str(p) for p in parts)}"

    def cache_link(self, slug: str, data: dict, ttl: int = None) -> bool:
        if not self._available():
            return False

        try:
            ttl = ttl or current_app.config.get("CACHE_TTL_LINK", 3600)
            self.client.setex(self._key("link", slug), ttl, json.dumps(data))
            return True
        except Exception as e:
            logger.debug(f"Cache write failed: {e}")
            return False

    def get_cached_link(self, slug: str) -> Optional[dict]:
        if not self._available():
            return None

        try:
            data = self.client.get(self._key("link", slug))
            return json.loads(data) if data else None
        except Exception:
            return None

    def invalidate_link_cache(self, slug: str) -> bool:
        if not self._available():
            return False

        try:
            self.client.delete(self._key("link", slug))
            return True
        except Exception:
            return False

    def blacklist_token(self, jti: str, ttl: int = None) -> bool:
        if not self._available():
            return False

        try:
            ttl = ttl or current_app.config.get("CACHE_TTL_BLACKLIST", 86400 * 31)
            self.client.setex(self._key("blacklist", jti), ttl, "1")
            return True
        except Exception:
            return False

    def is_token_blacklisted(self, jti: str) -> bool:
        if not self._available():
            return False

        try:
            return self.client.exists(self._key("blacklist", jti)) > 0
        except Exception:
            return False

    def store_reset_token(self, token: str, user_id: str, ttl: int = None) -> bool:
        if not self._available():
            logger.warning("Redis unavailable for reset token storage")
            return False

        try:
            ttl = ttl or current_app.config.get("PASSWORD_RESET_TOKEN_EXPIRES", 3600)
            self.client.setex(self._key("reset", token), ttl, user_id)
            return True
        except Exception as e:
            logger.error(f"Failed to store reset token: {e}")
            return False

    def get_reset_token_user(self, token: str) -> Optional[str]:
        if not self._available():
            return None

        try:
            return self.client.get(self._key("reset", token))
        except Exception:
            return None

    def invalidate_reset_token(self, token: str) -> bool:
        if not self._available():
            return False

        try:
            self.client.delete(self._key("reset", token))
            return True
        except Exception:
            return False

    def cache_user_stats(self, user_id: str, stats: dict, ttl: int = 300) -> bool:
        if not self._available():
            return False

        try:
            self.client.setex(
                self._key("stats", user_id),
                ttl,
                json.dumps(stats)
            )
            return True
        except Exception:
            return False

    def get_cached_user_stats(self, user_id: str) -> Optional[dict]:
        if not self._available():
            return None

        try:
            data = self.client.get(self._key("stats", user_id))
            return json.loads(data) if data else None
        except Exception:
            return None

    def invalidate_user_stats(self, user_id: str) -> bool:
        if not self._available():
            return False

        try:
            self.client.delete(self._key("stats", user_id))
            return True
        except Exception:
            return False

    def increment_click_counter(self, slug: str) -> int:
        if not self._available():
            return 0

        try:
            key = self._key("clicks", slug, datetime.utcnow().strftime("%Y-%m-%d"))
            count = self.client.incr(key)
            self.client.expire(key, 86400 * 7)
            return count
        except Exception:
            return 0

    def get_click_counts(self, slug: str, days: int = 7) -> Dict[str, int]:
        if not self._available():
            return {}

        try:
            result = {}
            for i in range(days):
                from datetime import timedelta
                date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
                key = self._key("clicks", slug, date)
                count = self.client.get(key)
                result[date] = int(count) if count else 0
            return result
        except Exception:
            return {}

    def cache_metadata(self, url_hash: str, metadata: dict, ttl: int = 86400) -> bool:
        if not self._available():
            return False

        try:
            self.client.setex(
                self._key("metadata", url_hash),
                ttl,
                json.dumps(metadata)
            )
            return True
        except Exception:
            return False

    def get_cached_metadata(self, url_hash: str) -> Optional[dict]:
        if not self._available():
            return None

        try:
            data = self.client.get(self._key("metadata", url_hash))
            return json.loads(data) if data else None
        except Exception:
            return None

    def cache_health_status(self, link_id: str, status: dict, ttl: int = 3600) -> bool:
        if not self._available():
            return False

        try:
            self.client.setex(
                self._key("health", link_id),
                ttl,
                json.dumps(status)
            )
            return True
        except Exception:
            return False

    def get_cached_health_status(self, link_id: str) -> Optional[dict]:
        if not self._available():
            return None

        try:
            data = self.client.get(self._key("health", link_id))
            return json.loads(data) if data else None
        except Exception:
            return None

    def add_to_set(self, set_name: str, value: str) -> bool:
        if not self._available():
            return False

        try:
            self.client.sadd(self._key("set", set_name), value)
            return True
        except Exception:
            return False

    def is_in_set(self, set_name: str, value: str) -> bool:
        if not self._available():
            return False

        try:
            return self.client.sismember(self._key("set", set_name), value)
        except Exception:
            return False

    def remove_from_set(self, set_name: str, value: str) -> bool:
        if not self._available():
            return False

        try:
            self.client.srem(self._key("set", set_name), value)
            return True
        except Exception:
            return False

    def rate_limit_check(self, identifier: str, limit: int, window: int = 60) -> tuple:
        if not self._available():
            return True, limit

        try:
            key = self._key("ratelimit", identifier)
            current = self.client.get(key)

            if current is None:
                self.client.setex(key, window, 1)
                return True, limit - 1

            current = int(current)
            if current >= limit:
                ttl = self.client.ttl(key)
                return False, 0

            self.client.incr(key)
            return True, limit - current - 1

        except Exception:
            return True, limit

    def get_stats(self) -> dict:
        stats = {"available": self._available()}

        if stats["available"]:
            try:
                info = self.client.info("memory")
                stats["memory_used"] = info.get("used_memory_human", "unknown")
                stats["cached_links"] = len(self.client.keys(self._key("link", "*")))
                stats["email_queue"] = self.client.llen(self._key("email_queue"))
            except Exception:
                pass

        return stats

    def flush_user_cache(self, user_id: str) -> bool:
        if not self._available():
            return False

        try:
            pattern = self._key("*", user_id, "*")
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)

            self.invalidate_user_stats(user_id)
            return True
        except Exception:
            return False