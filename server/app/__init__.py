# server/app/__init__.py

import os
import sys
import logging
from datetime import datetime
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from sqlalchemy import inspect, text
from .config import Config
from .extensions import db, migrate, redis_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    initialize_extensions(app)
    
    # Initialize database and Firebase in app context
    with app.app_context():
        initialize_database(app)
        initialize_firebase(app)
    
    # Register middleware
    register_middleware(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register root endpoints
    register_root_endpoints(app)
    
    logger.info(f"Application initialized in {app.config.get('FLASK_ENV', 'production')} mode")
    
    return app

def initialize_extensions(app):
    """Initialize Flask extensions"""
    # Database
    db.init_app(app)
    migrate.init_app(app, db, directory='app/migrations')
    
    # CORS configuration for production
    cors_origins = [
        'http://localhost:3000',
        'http://localhost:5173',
        'http://localhost:5174',
        'https://savlink.vercel.app',
        app.config.get('BASE_URL', 'https://savlink.vercel.app')
    ]
    
    # Remove duplicates and None values
    cors_origins = list(filter(None, list(dict.fromkeys(cors_origins))))
    
    CORS(app,
         resources={r"/*": {"origins": cors_origins}},
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
         expose_headers=['Content-Type', 'Authorization'],
         max_age=3600)
    
    logger.info(f"CORS initialized with origins: {cors_origins}")
    logger.info(f"Redis client: {'Connected' if redis_client else 'Not configured'}")

def initialize_database(app):
    """Initialize database with auto-migration and table creation"""
    try:
        # Import all models to ensure they're registered with SQLAlchemy
        from .models import User, EmergencyToken
        
        # Test database connection
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text('SELECT 1'))
                logger.info("Database connection successful")
        except Exception as conn_error:
            logger.error(f"Database connection failed: {conn_error}")
            if app.config.get('FLASK_ENV') == 'production':
                # In production, this is critical
                raise
            return
        
        # Create tables if they don't exist (safe for production)
        try:
            db.create_all()
            logger.info("Database tables created/verified")
        except Exception as create_error:
            logger.error(f"Error creating tables: {create_error}")
            # Continue anyway - tables might already exist
        
        # Verify tables
        try:
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            logger.info(f"Existing database tables: {tables}")
            
            # Check for required tables
            required_tables = ['users', 'emergency_tokens']
            missing_tables = set(required_tables) - set(tables)
            
            if missing_tables:
                logger.warning(f"Missing required tables: {missing_tables}")
                # Try to create missing tables one more time
                db.create_all()
                
                # Verify again
                inspector = inspect(db.engine)
                tables = inspector.get_table_names()
                still_missing = set(required_tables) - set(tables)
                
                if still_missing:
                    logger.error(f"Failed to create tables: {still_missing}")
                    if app.config.get('FLASK_ENV') == 'production':
                        raise Exception(f"Required tables missing: {still_missing}")
                else:
                    logger.info("Missing tables created successfully")
            else:
                logger.info("All required tables are present")
                
        except Exception as verify_error:
            logger.error(f"Error verifying tables: {verify_error}")
            
    except Exception as e:
        logger.error(f"Database initialization error: {e}", exc_info=True)
        if app.config.get('FLASK_ENV') == 'production':
            # In production, database is critical
            raise

def initialize_firebase(app):
    """Initialize Firebase Admin SDK with error handling"""
    try:
        from .auth.firebase import initialize_firebase as init_firebase
        
        # Check if Firebase config is available
        firebase_config = app.config.get('FIREBASE_CONFIG_JSON')
        if not firebase_config:
            logger.warning("FIREBASE_CONFIG_JSON not configured - Firebase features disabled")
            app.config['FIREBASE_ENABLED'] = False
            return
        
        # Validate it's not a placeholder
        if 'your-' in firebase_config or '...' in firebase_config:
            logger.warning("Firebase config appears to be a placeholder - Firebase features disabled")
            app.config['FIREBASE_ENABLED'] = False
            return
        
        # Initialize Firebase
        try:
            firebase_app = init_firebase()
            if firebase_app:
                logger.info("Firebase Admin SDK initialized successfully")
                app.config['FIREBASE_ENABLED'] = True
            else:
                logger.warning("Firebase Admin SDK initialization returned None")
                app.config['FIREBASE_ENABLED'] = False
                
        except Exception as init_error:
            logger.error(f"Firebase initialization error: {init_error}")
            app.config['FIREBASE_ENABLED'] = False
            
    except ImportError as ie:
        logger.error(f"Firebase module import error: {ie}")
        app.config['FIREBASE_ENABLED'] = False
    except Exception as e:
        logger.error(f"Unexpected Firebase error: {e}")
        app.config['FIREBASE_ENABLED'] = False

def register_middleware(app):
    """Register application middleware"""
    
    @app.before_request
    def before_request():
        """Handle preflight requests and logging"""
        # Handle CORS preflight
        if request.method == 'OPTIONS':
            response = make_response()
            response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS,PATCH')
            response.headers.add('Access-Control-Max-Age', '3600')
            return response
        
        # Log requests in development
        if app.config.get('FLASK_ENV') == 'development':
            logger.debug(f"{request.method} {request.path} from {request.remote_addr}")
    
    @app.after_request
    def after_request(response):
        """Add security headers to all responses"""
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Only add HSTS in production with HTTPS
        if app.config.get('FLASK_ENV') == 'production' and request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Add request ID for tracking (if available)
        request_id = getattr(g, 'request_id', None)
        if request_id:
            response.headers['X-Request-ID'] = request_id
        
        return response

def register_blueprints(app):
    """Register all application blueprints"""
    # Auth blueprint
    from .auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    logger.info("Auth blueprint registered at /auth")
    
    # Future blueprints can be added here
    # from .links import links_bp
    # app.register_blueprint(links_bp, url_prefix='/api/links')
    # logger.info("Links blueprint registered at /api/links")
    
    # from .analytics import analytics_bp
    # app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    # logger.info("Analytics blueprint registered at /api/analytics")

def register_error_handlers(app):
    """Register error handlers for the application"""
    
    @app.errorhandler(400)
    def bad_request(error):
        logger.warning(f"Bad request: {error}")
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'success': False,
            'error': 'Unauthorized',
            'message': 'Authentication required'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource'
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'success': False,
            'error': 'Method not allowed',
            'message': f'The {request.method} method is not allowed for this endpoint'
        }), 405
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({
            'success': False,
            'error': 'Too many requests',
            'message': 'Rate limit exceeded. Please try again later'
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred. Please try again later.'
        }), 500
    
    @app.errorhandler(502)
    def bad_gateway(error):
        logger.error(f"Bad gateway error: {error}")
        return jsonify({
            'success': False,
            'error': 'Bad gateway',
            'message': 'Service temporarily unavailable'
        }), 502
    
    @app.errorhandler(503)
    def service_unavailable(error):
        logger.error(f"Service unavailable: {error}")
        return jsonify({
            'success': False,
            'error': 'Service unavailable',
            'message': 'Service is temporarily unavailable. Please try again later.'
        }), 503
    
    @app.errorhandler(Exception)
    def unhandled_exception(error):
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        
        # Don't expose internal errors in production
        if app.config.get('FLASK_ENV') == 'production':
            return jsonify({
                'success': False,
                'error': 'Server error',
                'message': 'An unexpected error occurred'
            }), 500
        else:
            return jsonify({
                'success': False,
                'error': type(error).__name__,
                'message': str(error)
            }), 500

def register_root_endpoints(app):
    """Register root-level endpoints"""
    
    @app.route('/')
    def index():
        """Root endpoint - API information"""
        return jsonify({
            'service': 'savlink-backend',
            'version': '1.0.0',
            'status': 'online',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'environment': app.config.get('FLASK_ENV', 'production'),
            'features': {
                'firebase': app.config.get('FIREBASE_ENABLED', False),
                'redis': redis_client is not None
            },
            'endpoints': {
                'health': '/health',
                'ready': '/ready',
                'auth': {
                    'base': '/auth',
                    'current_user': 'GET /auth/me',
                    'session': 'GET /auth/session',
                    'emergency_request': 'POST /auth/emergency/request',
                    'emergency_verify': 'POST /auth/emergency/verify'
                }
            },
            'docs': 'https://docs.savlink.com'
        })
    
    @app.route('/health')
    def health_check():
        """Health check endpoint for monitoring"""
        health_status = {
            'status': 'healthy',
            'service': 'savlink-backend',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'version': '1.0.0',
            'checks': {}
        }
        
        # Check database
        try:
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            health_status['checks']['database'] = {
                'status': 'healthy',
                'response_time_ms': 0  # You could measure this
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_status['checks']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'
        
        # Check Redis
        if redis_client:
            try:
                start_time = datetime.utcnow()
                redis_client.ping()
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                health_status['checks']['redis'] = {
                    'status': 'healthy',
                    'response_time_ms': round(response_time, 2)
                }
            except Exception as e:
                logger.error(f"Redis health check failed: {e}")
                health_status['checks']['redis'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                health_status['status'] = 'degraded'
        else:
            health_status['checks']['redis'] = {
                'status': 'not_configured'
            }
        
        # Check Firebase
        health_status['checks']['firebase'] = {
            'status': 'healthy' if app.config.get('FIREBASE_ENABLED') else 'not_configured'
        }
        
        # Return appropriate status code
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
    
    @app.route('/ready')
    def readiness_check():
        """Readiness check for deployment platforms (K8s, etc)"""
        try:
            # Check critical dependencies
            checks = {
                'database': False,
                'firebase': False
            }
            
            # Database must be accessible
            try:
                db.session.execute(text('SELECT 1'))
                db.session.commit()
                checks['database'] = True
            except Exception as e:
                logger.error(f"Readiness check - database failed: {e}")
            
            # Firebase should be initialized (if configured)
            if app.config.get('FIREBASE_CONFIG_JSON'):
                checks['firebase'] = app.config.get('FIREBASE_ENABLED', False)
            else:
                checks['firebase'] = True  # Not required if not configured
            
            # All critical checks must pass
            is_ready = all(checks.values())
            
            response = {
                'ready': is_ready,
                'service': 'savlink-backend',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'checks': checks
            }
            
            return jsonify(response), 200 if is_ready else 503
            
        except Exception as e:
            logger.error(f"Readiness check failed: {e}", exc_info=True)
            return jsonify({
                'ready': False,
                'service': 'savlink-backend',
                'error': str(e)
            }), 503
    
    @app.route('/ping')
    def ping():
        """Simple ping endpoint"""
        return jsonify({
            'pong': True,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })

# Import g for request context
from flask import g
import uuid

# Add request ID middleware
@app.before_request
def assign_request_id():
    """Assign a unique ID to each request for tracking"""
    g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))