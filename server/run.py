# server/run.py

import os
from app import create_app

env = os.environ.get("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = env == "development"
    
    print(f"\n[Savlink] Development server starting...")
    print(f"[Savlink] http://{host}:{port}")
    print(f"[Savlink] Debug: {debug}\n")
    print("Note: For production, use: gunicorn wsgi:app\n")
    
    app.run(host=host, port=port, debug=debug)