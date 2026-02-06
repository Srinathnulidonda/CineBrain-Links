# server/app/config.py

import os
import sys
from datetime import timedelta
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(Exception):
    pass


def get_database_url() -> Optional[str]:
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        pg_host = os.environ.get("PGHOST")
        pg_port = os.environ.get("PGPORT", "5432")
        pg_user = os.environ.get("PGUSER") or os.environ.get("POSTGRES_USER")
        pg_password = os.environ.get("PGPASSWORD") or os.environ.get("POSTGRES_PASSWORD")
        pg_database = os.environ.get("PGDATABASE") or os.environ.get("POSTGRES_DB")

        if all([pg_host, pg_user, pg_password, pg_database]):
            database_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"

    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    return database_url


def get_redis_url() -> Optional[str]:
    redis_url = (
        os.environ.get("REDIS_URL") or
        os.environ.get("REDIS_PRIVATE_URL") or
        os.environ.get("UPSTASH_REDIS_URL")
    )

    if redis_url and "upstash.io" in redis_url and redis_url.startswith("redis://"):
        redis_url = redis_url.replace("redis://", "rediss://", 1)

    return redis_url


def validate_config(config: 'Config', environment: str) -> List[str]:
    warnings = []

    if not config.SQLALCHEMY_DATABASE_URI:
        raise ConfigurationError(
            "DATABASE_URL is required. Set DATABASE_URL or individual PG* variables."
        )

    # Firebase Auth validation
    if environment == "production":
        if not config.FIREBASE_PROJECT_ID:
            raise ConfigurationError(
                "FIREBASE_PROJECT_ID is required in production."
            )
        if not config.FIREBASE_CONFIG:
            warnings.append("FIREBASE_CONFIG not set. Using Application Default Credentials.")

    if not config.REDIS_URL:
        warnings.append("Redis not configured. Rate limiting will use memory storage.")

    if not config.BREVO_API_KEY and not config.BREVO_SMTP_PASSWORD:
        warnings.append("Email service not configured. Emails will be logged only.")

    if not os.environ.get("FRONTEND_URL"):
        warnings.append("FRONTEND_URL not set. Using default.")

    return warnings


class Config:
    APP_NAME = "Savlink"
    APP_VERSION = "2.0.0"

    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(32).hex())
    DEBUG = False
    TESTING = False

    FLASK_ENV = os.environ.get("FLASK_ENV", "production")
    RAILWAY_ENVIRONMENT = os.environ.get("RAILWAY_ENVIRONMENT")
    RAILWAY_PUBLIC_DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    IS_RAILWAY = bool(RAILWAY_ENVIRONMENT)

    SQLALCHEMY_DATABASE_URI = get_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 5,
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "max_overflow": 10,
        "pool_timeout": 30,
        "connect_args": {"connect_timeout": 10}
    }

    # Firebase Authentication Configuration
    FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID")
    FIREBASE_CONFIG = os.environ.get("FIREBASE_CONFIG")  # Path to service account JSON or dict
    FIREBASE_WEB_API_KEY = os.environ.get("FIREBASE_WEB_API_KEY")  # For frontend use

    # Supabase Database Configuration (keeping for database connection)
    SUPABASE_URL = os.environ.get("SUPABASE_URL")  # Optional: for direct DB operations
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")  # Optional: for admin operations
    SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")  # Optional: for client-side operations

    # Redis Configuration
    REDIS_URL = get_redis_url()
    RATELIMIT_STORAGE_URI = REDIS_URL if REDIS_URL else "memory://"
    RATELIMIT_DEFAULT = "200 per hour"
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_STRATEGY = "fixed-window"
    RATELIMIT_KEY_PREFIX = "savlink_rl"

    # Cache Configuration
    CACHE_TTL_LINK = 3600
    CACHE_TTL_BLACKLIST = 86400 * 31
    CACHE_TTL_METADATA = 86400
    CACHE_TTL_STATS = 300

    # Email Configuration (for notifications only, not auth)
    BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
    BREVO_SMTP_SERVER = os.environ.get("BREVO_SMTP_SERVER", "smtp-relay.brevo.com")
    BREVO_SMTP_PORT = int(os.environ.get("BREVO_SMTP_PORT", 587))
    BREVO_SMTP_USERNAME = os.environ.get("BREVO_SMTP_USERNAME")
    BREVO_SMTP_PASSWORD = os.environ.get("BREVO_SMTP_PASSWORD")
    BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "noreply@savlink.app")
    BREVO_SENDER_NAME = os.environ.get("BREVO_SENDER_NAME", "Savlink")
    REPLY_TO_EMAIL = os.environ.get("REPLY_TO_EMAIL")

    # URL Configuration
    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "https://savlink.vercel.app")
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://savlink.vercel.app")
    
    if RAILWAY_PUBLIC_DOMAIN:
        BASE_URL = f"https://{RAILWAY_PUBLIC_DOMAIN}"
    else:
        BASE_URL = os.environ.get("BASE_URL", "https://savlink.vercel.app")
    
    BACKEND_URL = BASE_URL

    CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]

    # Slug Configuration
    RESERVED_SLUGS = {
        "admin", "api", "login", "logout", "register", "signup",
        "dashboard", "settings", "profile", "account", "user", "users",
        "link", "links", "health", "status", "static", "assets",
        "auth", "oauth", "callback", "reset", "password", "verify",
        "help", "support", "contact", "about", "terms", "privacy",
        "blog", "docs", "app", "www", "mail", "new", "edit", "delete",
        "unsubscribe", "preferences", "analytics", "stats", "metrics",
        "favicon", "robots", "sitemap", "manifest", ".well-known",
        "s", "share", "shared", "public", "folder", "folders",
        "tag", "tags", "search", "bulk", "export", "import",
        "activity", "template", "templates", "category", "categories",
        "qr", "preview", "embed", "widget", "redirect", "firebase"
    }

    SLUG_MIN_LENGTH = 3
    SLUG_MAX_LENGTH = 32
    AUTO_SLUG_LENGTH = 7

    # Limits Configuration
    MAX_LINKS_PER_USER = int(os.environ.get("MAX_LINKS_PER_USER", 10000))
    MAX_FOLDERS_PER_USER = int(os.environ.get("MAX_FOLDERS_PER_USER", 100))
    MAX_TAGS_PER_USER = int(os.environ.get("MAX_TAGS_PER_USER", 500))
    MAX_TAGS_PER_LINK = int(os.environ.get("MAX_TAGS_PER_LINK", 20))

    # Health and Monitoring
    HEALTH_CHECK_TIMEOUT = 10
    HEALTH_CHECK_INTERVAL_HOURS = 24
    METADATA_FETCH_TIMEOUT = 10

    # Data Retention
    CLICK_RETENTION_DAYS = int(os.environ.get("CLICK_RETENTION_DAYS", 365))
    ACTIVITY_RETENTION_DAYS = int(os.environ.get("ACTIVITY_RETENTION_DAYS", 90))
    HEALTH_CHECK_RETENTION_DAYS = int(os.environ.get("HEALTH_CHECK_RETENTION_DAYS", 30))
    TRASH_RETENTION_DAYS = int(os.environ.get("TRASH_RETENTION_DAYS", 30))

    # Feature Flags
    ENABLE_WEEKLY_DIGEST = os.environ.get("ENABLE_WEEKLY_DIGEST", "false").lower() == "true"
    ENABLE_EXPIRATION_ALERTS = os.environ.get("ENABLE_EXPIRATION_ALERTS", "true").lower() == "true"
    ENABLE_BROKEN_LINK_ALERTS = os.environ.get("ENABLE_BROKEN_LINK_ALERTS", "true").lower() == "true"

    # JWT Configuration (for internal tokens, not auth)
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ALGORITHM = "HS256"
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ["access", "refresh"]

    # Security Configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=31)

    # Monitoring
    SENTRY_DSN = os.environ.get("SENTRY_DSN")

    # Firebase Admin SDK Configuration
    FIREBASE_ADMIN_CREDENTIALS = os.environ.get("FIREBASE_ADMIN_CREDENTIALS")  # JSON string of service account
    GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")  # Path to service account file


class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = "development"
    
    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:5000")
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")
    
    # Disable security features in development
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False
    
    # More lenient rate limiting in development
    RATELIMIT_DEFAULT = "1000 per hour"


class TestingConfig(Config):
    TESTING = True
    FLASK_ENV = "testing"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATELIMIT_STORAGE_URI = "memory://"
    SECRET_KEY = "test-secret-key"
    JWT_SECRET_KEY = "test-jwt-secret"
    
    PUBLIC_BASE_URL = "http://localhost:5000"
    FRONTEND_URL = "http://localhost:3000"
    BASE_URL = "http://localhost:5000"
    
    # Disable external services in testing
    FIREBASE_PROJECT_ID = "test-project"
    FIREBASE_CONFIG = None
    
    # Disable security features in testing
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False
    
    # Disable email in testing
    BREVO_API_KEY = None
    BREVO_SMTP_PASSWORD = None


class ProductionConfig(Config):
    DEBUG = False
    FLASK_ENV = "production"

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "max_overflow": 20,
        "pool_timeout": 30,
        "connect_args": {"connect_timeout": 10}
    }

    RATELIMIT_DEFAULT = "100 per hour"

    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Stricter security in production
    WTF_CSRF_ENABLED = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": ProductionConfig
}