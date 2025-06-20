import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-development-only'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-dev-only'
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///emotibotdb.sqlite'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'DEBUG'


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    
    # In production, SECRET_KEY and JWT_SECRET_KEY should be properly set in environment
    # and not use default values
    
    # Use PostgreSQL in production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


# Configuration dictionary
config_dict = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name='default'):
    """Get configuration class by name."""
    return config_dict.get(config_name, config_dict['default']) 