"""Flask application factory"""
from flask import Flask, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

from config import config_by_name
from app.routes import recommendations_bp
from app.models import DataManager


def create_app(config_name=None):
    """
    Application factory function
    
    Args:
        config_name: Configuration name (development, production, testing)
        
    Returns:
        Flask application instance
    """
    # Determine config
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    config = config_by_name.get(config_name, config_by_name['development'])
    
    # Load environment variables from .env
    load_dotenv()

    # Create Flask app
    app = Flask(__name__)
    app.config.from_object(config)
    
    # Initialize CORS
    CORS(app, resources={r"/api/*": {"origins": config.CORS_ORIGINS}})
    
    # Load data on startup
    try:
        data_manager = DataManager()
        if not data_manager.is_ready():
            print("⚠️ Warning: Data not loaded properly on startup")
        else:
            print("✓ Data loaded successfully on startup")
    except Exception as e:
        print(f"⚠️ Error loading data on startup: {e}")
    
    # Register blueprints
    app.register_blueprint(recommendations_bp)
    from app.routes import frontend_bp
    app.register_blueprint(frontend_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'message': 'Endpoint not found',
            'status_code': 404
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'message': 'Internal server error',
            'status_code': 500
        }), 500
    
    # El endpoint raíz ahora sirve el frontend.html (ver blueprint frontend)
    
    return app
