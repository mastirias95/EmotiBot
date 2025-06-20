import logging
from functools import wraps
from flask import request, jsonify, g, current_app

logger = logging.getLogger(__name__)

def token_required(f):
    """
    Decorator to protect routes with JWT authentication.
    
    This decorator checks for a valid JWT token in the Authorization header.
    If a valid token is found, it adds the authenticated user to Flask's g object.
    
    Usage:
        @app.route('/protected')
        @token_required
        def protected_route():
            # Access the authenticated user
            user = g.user
            return jsonify({'message': f'Hello, {user.username}!'})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        # Extract token from Authorization header
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
        
        if not token:
            logger.warning("No token provided")
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Authentication token is missing'
            }), 401
        
        # Verify token
        auth_service = current_app.auth_service
        success, message, user = auth_service.verify_token(token)
        
        if not success:
            logger.warning(f"Invalid token: {message}")
            return jsonify({
                'error': 'Unauthorized',
                'message': message
            }), 401
        
        # Store user in Flask's g object
        g.user = user
        
        return f(*args, **kwargs)
    
    return decorated 