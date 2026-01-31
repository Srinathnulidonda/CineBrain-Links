# server/run.py

"""
CinBrainLinks Application Entry Point
For local development only. Use wsgi.py for production.
"""

import os
from app import create_app

# Determine environment
env = os.environ.get("FLASK_ENV", "development")

# Create application instance
app = create_app(env)

if __name__ == "__main__":
    # Development server only
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = env == "development"
    
    print(f"""
    ╔═══════════════════════════════════════════════════════════════╗
    ║              CinBrainLinks - Development Server               ║
    ╠═══════════════════════════════════════════════════════════════╣
    ║  Host:  {host:<54}                                            ║
    ║  Port:  {port:<54}                                            ║
    ║  Debug: {str(debug):<54}                                      ║
    ╚═══════════════════════════════════════════════════════════════╝
    
    ⚠️  For production, use: gunicorn wsgi:app
    """)
    
    app.run(host=host, port=port, debug=debug)