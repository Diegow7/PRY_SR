# Flask Configuration
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

class Config:
    """Base configuration"""
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    DEBUG = False
    TESTING = False
    JSON_SORT_KEYS = False
    
    # Data paths
    DATA_DIR = BASE_DIR / 'datos_procesados.pkl'
    CARRERAS_EPN_CSV = BASE_DIR / 'carreras_epn' / 'carreras_epn.csv'
    OFERTAS_BASE_DIR = BASE_DIR / 'todas_las_plataformas'
    
    # API settings
    MAX_RECOMMENDATIONS = 10
    DEFAULT_RECOMMENDATIONS = 5
    
    # CORS settings
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5173', 'http://localhost:5000']


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False


# Configuration by environment
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
