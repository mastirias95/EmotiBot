from datetime import datetime
from passlib.hash import pbkdf2_sha256
import logging
import uuid
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
logger = logging.getLogger(__name__)

class User(db.Model):
    """User model for authentication."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __init__(self, username, email, password=None, password_hash=None, id=None, 
                 created_at=None, updated_at=None, is_active=True):
        """
        Initialize a user object.
        
        Args:
            username (str): The username
            email (str): The user's email address
            password (str, optional): Plain text password (will be hashed)
            password_hash (str, optional): Pre-hashed password
            id (str, optional): User ID
            created_at (datetime, optional): Creation timestamp
            updated_at (datetime, optional): Last update timestamp
            is_active (bool): Whether the user account is active
        """
        self.id = id or str(uuid.uuid4())
        self.username = username
        self.email = email
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.is_active = is_active
        
        if password:
            self.set_password(password)
        elif password_hash:
            self.password_hash = password_hash
        else:
            self.password_hash = None
    
    def set_password(self, password):
        """
        Hash and set the user's password.
        
        Args:
            password (str): The plain text password
        """
        self.password_hash = pbkdf2_sha256.hash(password)
        self.updated_at = datetime.utcnow()
    
    def verify_password(self, password):
        """
        Verify a password against the stored hash.
        
        Args:
            password (str): The plain text password to verify
            
        Returns:
            bool: True if the password matches, False otherwise
        """
        if not self.password_hash:
            logger.warning(f"User {self.username} has no password set")
            return False
        
        return pbkdf2_sha256.verify(password, self.password_hash)
    
    def to_dict(self):
        """
        Convert user to dictionary (for JSON serialization).
        
        Returns:
            dict: User data without sensitive information
        """
        return {
            'user_id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Create a user instance from dictionary data.
        
        Args:
            data (dict): User data dictionary
            
        Returns:
            User: A new User instance
        """
        created_at = data.get('created_at')
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
            
        updated_at = data.get('updated_at')
        if updated_at and isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
            
        return cls(
            username=data.get('username'),
            email=data.get('email'),
            password_hash=data.get('password_hash'),
            id=data.get('user_id'),
            created_at=created_at,
            updated_at=updated_at,
            is_active=data.get('is_active', True)
        ) 