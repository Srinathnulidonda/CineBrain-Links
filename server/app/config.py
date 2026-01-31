# server/app/config.py

"""
Configuration classes for different environments.
Optimized for Railway deployment with proper database URL handling.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_database_url():
    """
    Get database URL with Railway and Supabase compatibility.
    Handles various connection string formats.
    """
    database_url = os.environ.get("DATABASE_URL")
    
    if not database_url:
        # Try Railway PostgreSQL individual variables
        pg_host = os.environ.get("PGHOST")
        pg_port = os.environ.get("PGPORT", "5432")
        pg_user = os.environ.get("PGUSER") or os.environ.get("POSTGRES_USER")
        pg_password = os.environ.get("PGPASSWORD") or os.environ.get("POSTGRES_PASSWORD")
        pg_database = os.environ.get("PGDATABASE") or os.environ.get("POSTGRES_DB")
        
        if all([pg_host, pg_user, pg_password, pg_database]):
            database_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
    
    if database_url:
        # Fix postgres:// to postgresql:// (Railway/Heroku compatibility)
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    return database_url


def get_redis_url():
    """Get Redis URL with Railway/Upstash compatibility and SSL handling."""
    redis_url = (
        os.environ.get("REDIS_URL") or
        os.environ.get("REDIS_PRIVATE_URL") or
        os.environ.get("UPSTASH_REDIS_URL")
    )
    
    if redis_url:
        # Upstash requires SSL - ensure rediss:// scheme
        if "upstash.io" in redis_url and redis_url.startswith("redis://"):
            redis_url = redis_url.replace("redis://", "rediss://", 1)
            print(f"[Config] Converted Upstash URL to use SSL (rediss://)")
        
        # Log for debugging (mask password)
        if '@' in redis_url:
            masked = redis_url.split('@')[-1]
            scheme = redis_url.split('://')[0] if '://' in redis_url else 'unknown'
            print(f"[Config] Redis URL found: {scheme}://...@{masked}")
        else:
            print(f"[Config] Redis URL found (local)")
    else:
        print("[Config] No Redis URL configured")
    
    return redis_url


class Config:
    """Base configuration class."""
    
    # Flask core settings
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(32).hex())
    DEBUG = False
    TESTING = False
    FLASK_ENV = os.environ.get("FLASK_ENV", "production")
    
    # Railway environment detection
    RAILWAY_ENVIRONMENT = os.environ.get("RAILWAY_ENVIRONMENT")
    RAILWAY_PUBLIC_DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    IS_RAILWAY = bool(RAILWAY_ENVIRONMENT)
    
    # Database - PostgreSQL
    SQLALCHEMY_DATABASE_URI = get_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 5,
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "max_overflow": 10,
        "pool_timeout": 30,
        "connect_args": {
            "connect_timeout": 10,
        }
    }
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", os.urandom(32).hex())
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ["access", "refresh"]
    
    # Redis - Get URL first
    REDIS_URL = get_redis_url()
    
    # Rate limiting - Flask-Limiter uses RATELIMIT_STORAGE_URI (not URL!)
    RATELIMIT_STORAGE_URI = REDIS_URL if REDIS_URL else "memory://"
    RATELIMIT_DEFAULT = "200 per hour"
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_STRATEGY = "fixed-window"
    RATELIMIT_KEY_PREFIX = "cinbrainlinks_rl"
    
    # Cache TTL settings (in seconds)
    CACHE_TTL_LINK = 3600
    CACHE_TTL_BLACKLIST = 86400 * 31
    
    # Brevo Email Configuration
    BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
    BREVO_SMTP_SERVER = os.environ.get("BREVO_SMTP_SERVER", "smtp-relay.brevo.com")
    BREVO_SMTP_PORT = int(os.environ.get("BREVO_SMTP_PORT", 587))
    BREVO_SMTP_USERNAME = os.environ.get("BREVO_SMTP_USERNAME")
    BREVO_SMTP_PASSWORD = os.environ.get("BREVO_SMTP_PASSWORD")
    BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "noreply@cinbrainlinks.com")
    BREVO_SENDER_NAME = os.environ.get("BREVO_SENDER_NAME", "CinBrainLinks")
    REPLY_TO_EMAIL = os.environ.get("REPLY_TO_EMAIL")
    
    # Application settings
    APP_NAME = "CinBrainLinks"
    
    # URLs
    if RAILWAY_PUBLIC_DOMAIN:
        BASE_URL = f"https://{RAILWAY_PUBLIC_DOMAIN}"
    else:
        BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")
    
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    BACKEND_URL = BASE_URL
    
    # CORS
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
    
    # Password reset
    PASSWORD_RESET_TOKEN_EXPIRES = 3600
    PASSWORD_RESET_SALT = os.environ.get(
        "PASSWORD_RESET_SALT",
        "password-reset-salt-cinbrainlinks-2025"
    )
    
    # Reserved slugs
    RESERVED_SLUGS = {
        "admin", "api", "login", "logout", "register", "signup",
        "dashboard", "settings", "profile", "account", "user", "users",
        "link", "links", "health", "status", "static", "assets",
        "auth", "oauth", "callback", "reset", "password", "verify",
        "help", "support", "contact", "about", "terms", "privacy",
        "blog", "docs", "documentation", "app", "www", "mail",
        "unsubscribe", "preferences", "analytics", "stats", "metrics"
    }
    
    # Slug configuration
    SLUG_MIN_LENGTH = 4
    SLUG_MAX_LENGTH = 20
    AUTO_SLUG_LENGTH = 7
    
    # Sentry
    SENTRY_DSN = os.environ.get("SENTRY_DSN")


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    FLASK_ENV = "development"
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    FLASK_ENV = "testing"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATELIMIT_STORAGE_URI = "memory://"


class ProductionConfig(Config):
    """Production configuration for Railway."""
    DEBUG = False
    FLASK_ENV = "production"
    
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "max_overflow": 20,
        "pool_timeout": 30,
        "connect_args": {
            "connect_timeout": 10,
        }
    }
    
    RATELIMIT_DEFAULT = "100 per hour"
    
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": ProductionConfig
}