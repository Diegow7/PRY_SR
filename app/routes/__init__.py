"""Routes init file"""

from app.routes.recommendations import recommendations_bp
from app.routes.frontend import frontend_bp

__all__ = ['recommendations_bp', 'frontend_bp']
