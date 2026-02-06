# server/app/__init__.py

import os
import sys
import logging
from flask import Flask, jsonify
from flask_cors import CORS

from app.config import config_by_name, validate_config, ConfigurationError
from app.extensions import db, jwt, migrate, limiter

logger = logging.getLogger(__name__)


class ApiResponse:
    @staticmethod
    def success(data=None, message=None, status=200):
        response = {"success": True}
        if message:
            response["message"] = message
        if data is not None:
            response["data"] = data
        return jsonify(response), status

    @staticmethod
    def error(message, status=400, code=None):
        response = {
            "success": False,
            "error": {
                "message": message
            }
        }
        if code:
            response["error"]["code"] = code
        return jsonify(response), status


def create_app(config_name: str = None) -> Flask:
    if config_name is None:
        if os.environ.get("RAILWAY_ENVIRONMENT"):
            config_name = "production"
        else:
            config_name = os.environ.get("FLASK_ENV", "production")

    app = Flask(__name__)

    config_class = config_by_name.get(config_name, config_by_name["production"])
    app.config.from_object(config_class)

    try:
        warnings = validate_config(config_class, config_name)
        for warning in warnings:
            logger.warning(f"Config: {warning}")
    except ConfigurationError as e:
        logger.critical(f"Configuration error: {e}")
        sys.exit(1)

    app.api_response = ApiResponse

    _log_startup(app, config_name)
    _init_extensions(app)
    _setup_cors(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _setup_logging(app)
    _setup_jwt_callbacks(app)
    _init_sentry(app)

    @app.route("/health")
    def health():
        status = {
            "status": "healthy",
            "service": "Savlink",
            "version": app.config["APP_VERSION"]
        }

        try:
            db.session.execute(db.text("SELECT 1"))
            db.session.commit()
            status["database"] = "connected"
        except Exception as e:
            status["database"] = "unavailable"
            status["status"] = "degraded"
            logger.warning(f"Health check: database unavailable - {e}")

        try:
            from app.services.redis_service import RedisService
            redis_svc = RedisService()
            if redis_svc.client:
                redis_svc.client.ping()
                status["cache"] = "connected"
            else:
                status["cache"] = "not configured"
        except Exception:
            status["cache"] = "unavailable"

        code = 200 if status["status"] == "healthy" else 503
        return jsonify(status), code

    @app.route("/")
    def root():
        return jsonify({
            "service": "Savlink API",
            "version": app.config["APP_VERSION"],
            "status": "running",
            "documentation": "/api",
            "health": "/health"
        }), 200

    with app.app_context():
        _init_database(app)
        _seed_categories(app)

    return app


def _log_startup(app: Flask, config_name: str) -> None:
    redis_status = "configured" if app.config.get("REDIS_URL") else "memory-only"
    public_url = app.config.get("PUBLIC_BASE_URL")
    print(f"\n[Savlink] Starting in {config_name} mode")
    print(f"[Savlink] Public URL: {public_url}")
    print(f"[Savlink] Backend URL: {app.config.get('BASE_URL')}")
    print(f"[Savlink] Cache: {redis_status}")
    print(f"[Savlink] Railway: {app.config.get('IS_RAILWAY', False)}\n")


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    try:
        limiter.init_app(app)
        storage = "Redis" if app.config.get("REDIS_URL") else "memory"
        logger.info(f"Rate limiter initialized ({storage} storage)")
    except Exception as e:
        logger.error(f"Rate limiter failed: {e}")
        app.config["RATELIMIT_STORAGE_URI"] = "memory://"
        limiter.init_app(app)


def _setup_cors(app: Flask) -> None:
    """Setup CORS configuration"""
    cors_origins = app.config.get("CORS_ORIGINS", ["*"])
    
    # If CORS_ORIGINS is a string, split it
    if isinstance(cors_origins, str):
        cors_origins = [origin.strip() for origin in cors_origins.split(",")]
    
    # Add localhost variants for development
    if app.config.get("FLASK_ENV") == "development" or app.config.get("DEBUG"):
        cors_origins.extend([
            "http://localhost:3000",
            "http://localhost:5173", 
            "https://localhost:3000",
            "https://localhost:5173"
        ])
    
    # Remove duplicates and empty strings
    cors_origins = list(set([origin for origin in cors_origins if origin.strip()]))
    
    logger.info(f"CORS origins: {cors_origins}")
    
    CORS(app, 
         origins=cors_origins,
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
         allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
         supports_credentials=True,
         expose_headers=["Content-Range", "X-Content-Range"],
         send_wildcard=False,
         vary_header=True
    )


def _init_database(app: Flask) -> None:
    try:
        db.session.execute(db.text("SELECT 1"))
        db.session.commit()

        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if len(inspector.get_table_names()) < 2:
            db.create_all()
            logger.info("Database tables created")
        else:
            logger.info("Database connected")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")


def _seed_categories(app: Flask) -> None:
    try:
        from app.models.category import Category
        
        if Category.query.count() > 0:
            return
        
        default_categories = [
            {"name": "Work", "slug": "work", "icon": "briefcase", "color": "#3B82F6"},
            {"name": "Personal", "slug": "personal", "icon": "user", "color": "#10B981"},
            {"name": "Shopping", "slug": "shopping", "icon": "shopping-cart", "color": "#F59E0B"},
            {"name": "Social", "slug": "social", "icon": "users", "color": "#EC4899"},
            {"name": "News", "slug": "news", "icon": "newspaper", "color": "#6366F1"},
            {"name": "Entertainment", "slug": "entertainment", "icon": "film", "color": "#8B5CF6"},
            {"name": "Education", "slug": "education", "icon": "book-open", "color": "#14B8A6"},
            {"name": "Finance", "slug": "finance", "icon": "dollar-sign", "color": "#22C55E"},
            {"name": "Health", "slug": "health", "icon": "heart", "color": "#EF4444"},
            {"name": "Travel", "slug": "travel", "icon": "map", "color": "#06B6D4"},
            {"name": "Food", "slug": "food", "icon": "utensils", "color": "#F97316"},
            {"name": "Technology", "slug": "technology", "icon": "cpu", "color": "#64748B"},
            {"name": "Other", "slug": "other", "icon": "folder", "color": "#94A3B8"},
        ]
        
        for i, cat_data in enumerate(default_categories):
            category = Category(
                name=cat_data["name"],
                slug=cat_data["slug"],
                icon=cat_data["icon"],
                color=cat_data["color"],
                sort_order=i
            )
            db.session.add(category)
        
        db.session.commit()
        logger.info("Default categories seeded")
        
    except Exception as e:
        db.session.rollback()
        logger.warning(f"Category seeding failed: {e}")


def _register_blueprints(app: Flask) -> None:
    from app.routes.auth import auth_bp
    from app.routes.links import links_bp
    from app.routes.redirect import redirect_bp
    from app.routes.folders import folders_bp
    from app.routes.tags import tags_bp
    from app.routes.analytics import analytics_bp
    from app.routes.sharing import sharing_bp
    from app.routes.health import health_bp
    from app.routes.bulk import bulk_bp
    from app.routes.activity import activity_bp
    from app.routes.templates import templates_bp
    from app.routes.categories import categories_bp
    from app.routes.search import search_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(links_bp, url_prefix="/api/links")
    app.register_blueprint(folders_bp, url_prefix="/api/folders")
    app.register_blueprint(tags_bp, url_prefix="/api/tags")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
    app.register_blueprint(sharing_bp, url_prefix="/api/share")
    app.register_blueprint(health_bp, url_prefix="/api/health")
    app.register_blueprint(bulk_bp, url_prefix="/api/bulk")
    app.register_blueprint(activity_bp, url_prefix="/api/activity")
    app.register_blueprint(templates_bp, url_prefix="/api/templates")
    app.register_blueprint(categories_bp, url_prefix="/api/categories")
    app.register_blueprint(search_bp, url_prefix="/api/search")
    app.register_blueprint(redirect_bp)


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def bad_request(e):
        return ApiResponse.error("Invalid request", 400, "BAD_REQUEST")

    @app.errorhandler(401)
    def unauthorized(e):
        return ApiResponse.error("Authentication required", 401, "UNAUTHORIZED")

    @app.errorhandler(403)
    def forbidden(e):
        return ApiResponse.error("Access denied", 403, "FORBIDDEN")

    @app.errorhandler(404)
    def not_found(e):
        return ApiResponse.error("Resource not found", 404, "NOT_FOUND")

    @app.errorhandler(429)
    def rate_limited(e):
        return ApiResponse.error(
            "You're making requests too quickly. Please wait a moment.",
            429,
            "RATE_LIMITED"
        )

    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Internal error: {e}")
        return ApiResponse.error("An unexpected error occurred", 500, "INTERNAL_ERROR")

    @app.errorhandler(503)
    def service_unavailable(e):
        return ApiResponse.error("Service temporarily unavailable", 503, "SERVICE_UNAVAILABLE")


def _setup_logging(app: Flask) -> None:
    level = logging.DEBUG if app.config["DEBUG"] else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def _setup_jwt_callbacks(app: Flask) -> None:
    @jwt.token_in_blocklist_loader
    def check_blocklist(jwt_header, jwt_payload):
        try:
            from app.services.redis_service import RedisService
            return RedisService().is_token_blacklisted(jwt_payload["jti"])
        except Exception:
            return False

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return ApiResponse.error("Your session has expired. Please sign in again.", 401, "TOKEN_EXPIRED")

    @jwt.invalid_token_loader
    def invalid_token(error):
        return ApiResponse.error("Invalid authentication token", 401, "INVALID_TOKEN")

    @jwt.unauthorized_loader
    def missing_token(error):
        return ApiResponse.error("Authentication required", 401, "MISSING_TOKEN")

    @jwt.revoked_token_loader
    def revoked_token(jwt_header, jwt_payload):
        return ApiResponse.error("This session has been signed out", 401, "TOKEN_REVOKED")


def _init_sentry(app: Flask) -> None:
    sentry_dsn = app.config.get("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration

            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[FlaskIntegration()],
                traces_sample_rate=0.1,
                environment=app.config.get("FLASK_ENV", "production")
            )
            logger.info("Sentry initialized")
        except ImportError:
            logger.warning("Sentry SDK not installed")
        except Exception as e:
            logger.error(f"Sentry init failed: {e}")