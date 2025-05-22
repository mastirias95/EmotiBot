import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from jose import jwt
from models.user import User, db

logger = logging.getLogger(__name__)

class AuthService:
    """Service for handling authentication and authorization."""
    
    def __init__(self, config):
        """
        Initialize the authentication service.
        
        Args:
            config: Application configuration
        """
        self.jwt_secret_key = config.get('JWT_SECRET_KEY')
        self.jwt_algorithm = 'HS256'
        self.jwt_expiration = config.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)  # Default 1 hour
    
    def register_user(self, username, email, password):
        """
        Register a new user.
        
        Args:
            username (str): Username
            email (str): Email address
            password (str): Password
            
        Returns:
            tuple: (success, message, user_data)
        """
        # Input validation
        if not username or not email or not password:
            return False, "Username, email and password are required", None
        
        try:
            # Check if username or email already exists
            existing_username = User.query.filter_by(username=username).first()
            if existing_username:
                return False, "Username already exists", None
            
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                return False, "Email already exists", None
            
            # Create new user
            user = User(
                username=username,
                email=email,
                password=password
            )
            
            # Store user in database
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"User registered: {username} ({user.id})")
            return True, "User registered successfully", user.to_dict()
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error registering user: {str(e)}")
            return False, "Error registering user", None
    
    def authenticate(self, username, password):
        """
        Authenticate a user with username/email and password.
        
        Args:
            username (str): Username or email
            password (str): Password
            
        Returns:
            tuple: (success, message, token)
        """
        try:
            # Find user by username or email
            user = User.query.filter_by(username=username).first()
            
            if not user and '@' in username:
                # Try email
                user = User.query.filter_by(email=username).first()
            
            if not user:
                return False, "Invalid username or password", None
            
            # Check if account is active
            if not user.is_active:
                return False, "Account is disabled", None
            
            # Verify password
            if not user.verify_password(password):
                return False, "Invalid username or password", None
            
            # Generate token
            token = self._generate_token(user)
            
            logger.info(f"User authenticated: {username}")
            return True, "Authentication successful", {
                'access_token': token,
                'token_type': 'bearer',
                'user': user.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False, "Authentication error", None
    
    def get_user_by_id(self, user_id):
        """
        Get a user by ID.
        
        Args:
            user_id (str): User ID
            
        Returns:
            User: User object or None
        """
        return User.query.get(user_id)
    
    def verify_token(self, token):
        """
        Verify a JWT token and return the associated user.
        
        Args:
            token (str): JWT token
            
        Returns:
            tuple: (success, message, user)
        """
        try:
            # Decode token
            payload = jwt.decode(
                token,
                self.jwt_secret_key,
                algorithms=[self.jwt_algorithm]
            )
            
            # Get user ID from token
            user_id = payload.get('sub')
            
            if not user_id:
                return False, "Invalid token", None
            
            # Get user
            user = self.get_user_by_id(user_id)
            
            if not user:
                return False, "User not found", None
            
            # Check if account is active
            if not user.is_active:
                return False, "Account is disabled", None
            
            return True, "Token verified", user
            
        except jwt.ExpiredSignatureError:
            return False, "Token has expired", None
        except jwt.JWTError:
            return False, "Invalid token", None
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            return False, "Token verification error", None
    
    def _generate_token(self, user):
        """
        Generate a JWT token for a user.
        
        Args:
            user (User): User object
            
        Returns:
            str: JWT token
        """
        now = datetime.utcnow()
        expires = now + timedelta(seconds=self.jwt_expiration)
        
        claims = {
            'sub': user.id,
            'username': user.username,
            'email': user.email,
            'iat': now,
            'exp': expires
        }
        
        return jwt.encode(claims, self.jwt_secret_key, algorithm=self.jwt_algorithm) 