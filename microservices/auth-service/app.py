"""
Auth Service - Handles authentication and authorization for EmotiBot microservices.
Provides user registration, login, token verification, and user management.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import os
from datetime import datetime, timedelta
import logging
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from prometheus_flask_exporter import PrometheusMetrics
import redis
import json
import sys

# Add shared-libs to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared-libs'))

# Try to import message queue, handle gracefully if not available
try:
    from message_queue import get_queue_client
    RABBITMQ_AVAILABLE = True
except ImportError:
    RABBITMQ_AVAILABLE = False
    get_queue_client = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not RABBITMQ_AVAILABLE:
    logger.warning("Message queue library not available, running without RabbitMQ")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key')

# Enable CORS for all routes
CORS(app, origins=["http://localhost:8080"], supports_credentials=True)

# Prometheus metrics
metrics = PrometheusMetrics(app)

# Database setup
DATABASE_URL = os.environ.get('AUTH_DATABASE_URL', 'postgresql://auth_user:auth_pass@auth-db:5432/authdb')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis setup for caching
try:
    redis_client = redis.Redis(
        host=os.environ.get('REDIS_HOST', 'redis'),
        port=int(os.environ.get('REDIS_PORT', 6379)),
        decode_responses=True
    )
    redis_client.ping()
    logger.info("Connected to Redis")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}")
    redis_client = None

# RabbitMQ setup
if RABBITMQ_AVAILABLE and get_queue_client:
    try:
        queue_client = get_queue_client('auth-service')
        logger.info("Connected to RabbitMQ")
    except Exception as e:
        logger.warning(f"RabbitMQ connection failed: {e}")
        queue_client = None
else:
    queue_client = None
    logger.info("RabbitMQ not available - running in standalone mode")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def validate_service_token():
    """Validate service-to-service authentication token."""
    auth_header = request.headers.get('Authorization')
    service_name = request.headers.get('X-Service-Name')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return False
    
    token = auth_header.split(' ')[1]
    service_secret = os.environ.get('SERVICE_SECRET', 'default-service-secret')
    
    try:
        payload = jwt.decode(token, service_secret, algorithms=['HS256'])
        return payload.get('service') == service_name
    except jwt.InvalidTokenError:
        return False

@app.route('/health', methods=['GET'])
@metrics.counter('health_checks', 'Number of health check requests')
def health_check():
    """Health check endpoint."""
    queue_healthy = queue_client.ensure_connection() if queue_client else False
    
    return jsonify({
        'service': 'auth-service',
        'status': 'healthy',
        'queue_connection': queue_healthy,
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/api/auth/register', methods=['POST'])
@metrics.counter('user_registrations', 'Number of user registrations')
def register():
    """Register a new user."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
    
    # Validation
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not all([username, email, password]):
        return jsonify({'error': 'Username, email, and password are required'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long'}), 400
    
    db = SessionLocal()
    try:
        # Check if user exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            if existing_user.username == username:
                return jsonify({'error': 'Username already exists'}), 409
            else:
                return jsonify({'error': 'Email already exists'}), 409
        
        # Create new user
        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"New user registered: {username}")
        
        # Publish user registration event to RabbitMQ
        if queue_client:
            try:
                queue_client.publish_user_registered(new_user.to_dict())
                logger.info(f"Published user registration event for {username}")
            except Exception as e:
                logger.error(f"Failed to publish user registration event: {e}")
        
        return jsonify({
            'message': 'User created successfully',
            'user': new_user.to_dict()
        }), 201
        
    except Exception as e:
        db.rollback()
        logger.error(f"Registration failed: {e}")
        return jsonify({'error': 'Registration failed'}), 500
    finally:
        db.close()

@app.route('/api/auth/login', methods=['POST'])
@metrics.counter('user_logins', 'Number of user login attempts')
def login():
    """Login user and return JWT token."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not all([username, password]):
        return jsonify({'error': 'Username and password are required'}), 400
    
    db = SessionLocal()
    try:
        # Find user by username or email
        user = db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user or not check_password_hash(user.hashed_password, password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # Generate JWT token
        payload = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        
        token = jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm='HS256')
        
        # Publish user login event to RabbitMQ
        if queue_client:
            try:
                queue_client.publish_user_login({
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'login_time': datetime.utcnow().isoformat()
                })
                logger.info(f"Published user login event for {username}")
            except Exception as e:
                logger.error(f"Failed to publish user login event: {e}")
        
        logger.info(f"User logged in: {username}")
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Login failed: {e}")
        return jsonify({'error': 'Login failed'}), 500
    finally:
        db.close()

@app.route('/api/auth/verify', methods=['POST'])
@metrics.counter('token_verifications', 'Number of token verification requests')
def verify_token():
    """Verify JWT token and return user information."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
    
    token = data.get('token', '')
    
    if not token:
        return jsonify({'error': 'Token required'}), 400
    
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        
        # Check if token is expired
        if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
            return jsonify({'error': 'Token expired'}), 401
        
        # Get user from database
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == payload['user_id']).first()
            
            if not user or not user.is_active:
                return jsonify({'error': 'User not found or inactive'}), 401
            
            return jsonify({
                'valid': True,
                'user': user.to_dict()
            }), 200
            
        finally:
            db.close()
            
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return jsonify({'error': 'Token verification failed'}), 500

@app.route('/api/auth/refresh', methods=['POST'])
@metrics.counter('token_refreshes', 'Number of token refresh requests')
def refresh_token():
    """Refresh JWT token."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
    
    token = data.get('token', '')
    
    if not token:
        return jsonify({'error': 'Token required'}), 400
    
    try:
        # Decode token without expiration check
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'], options={'verify_exp': False})
        
        # Get user from database
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == payload['user_id']).first()
            
            if not user or not user.is_active:
                return jsonify({'error': 'User not found or inactive'}), 401
            
            # Generate new token
            new_payload = {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(hours=24)
            }
            
            new_token = jwt.encode(new_payload, app.config['JWT_SECRET_KEY'], algorithm='HS256')
            
            return jsonify({
                'message': 'Token refreshed successfully',
                'token': new_token,
                'user': user.to_dict()
            }), 200
            
        finally:
            db.close()
            
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        return jsonify({'error': 'Token refresh failed'}), 500

@app.route('/api/auth/user/<int:user_id>', methods=['GET'])
@metrics.counter('user_profile_requests', 'Number of user profile requests')
def get_user_profile(user_id):
    """Get user profile by ID."""
    if not validate_service_token():
        return jsonify({'error': 'Unauthorized'}), 401
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Get user profile failed: {e}")
        return jsonify({'error': 'Failed to get user profile'}), 500
    finally:
        db.close()

@app.route('/api/auth/logout', methods=['POST'])
@metrics.counter('user_logouts', 'Number of user logout requests')
def logout():
    """Logout user."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
    
    token = data.get('token', '')
    
    if not token:
        return jsonify({'error': 'Token required'}), 400
    
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        
        # Publish user logout event to RabbitMQ
        if queue_client:
            try:
                queue_client.publish_user_logout({
                    'user_id': payload['user_id'],
                    'username': payload['username'],
                    'email': payload['email'],
                    'logout_time': datetime.utcnow().isoformat()
                })
                logger.info(f"Published user logout event for {payload['username']}")
            except Exception as e:
                logger.error(f"Failed to publish user logout event: {e}")
        
        logger.info(f"User logged out: {payload['username']}")
        
        return jsonify({
            'message': 'Logout successful'
        }), 200
        
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        return jsonify({'error': 'Logout failed'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8002, debug=False)