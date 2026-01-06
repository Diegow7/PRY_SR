"""Main entry point for Flask application"""
import os
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app

if __name__ == '__main__':
    # Get environment
    env = os.environ.get('FLASK_ENV', 'development')
    
    # Create app
    app = create_app(env)
    
    # Run app
    print(f"Starting Flask app in {env} mode...")
    print(f"Server running on http://localhost:5000")
    print(f"API documentation available at /api/recommendations/info")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=(env == 'development'),
        use_reloader=(env == 'development')
    )
