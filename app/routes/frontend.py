from flask import Blueprint, send_from_directory
import os

frontend_bp = Blueprint('frontend', __name__)

@frontend_bp.route('/frontend')
def serve_frontend():
    # Sirve el archivo frontend.html desde el directorio raíz del proyecto
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    return send_from_directory(root_dir, 'frontend.html')

@frontend_bp.route('/')
def serve_root():
    # Redirige la raíz al frontend
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    return send_from_directory(root_dir, 'frontend.html')
