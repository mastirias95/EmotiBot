import time
import logging
from collections import defaultdict
from flask import request, jsonify

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate limiter middleware to prevent abuse.
    
    This is a simple in-memory rate limiter. In production, you would use
    Redis or another distributed system to handle rate limiting across
    multiple application instances.
    """
    
    def __init__(self, limit=60, window=60):
        """
        Initialize the rate limiter.
        
        Args:
            limit (int): Maximum number of requests per window
            window (int): Time window in seconds
        """
        self.limit = limit
        self.window = window
        self.requests = defaultdict(list)  # IP -> list of request timestamps
    
    def __call__(self):
        """Register the rate limiter middleware function."""
        
        def middleware(*args, **kwargs):
            """Rate limiter middleware function."""
            # Get client IP
            client_ip = request.remote_addr
            
            # Current time
            now = time.time()
            
            # Remove old requests
            self.requests[client_ip] = [
                ts for ts in self.requests[client_ip] if now - ts < self.window
            ]
            
            # Check rate limit
            if len(self.requests[client_ip]) >= self.limit:
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                response = jsonify({
                    'error': 'Too many requests',
                    'message': f'Rate limit of {self.limit} requests per {self.window} seconds exceeded'
                })
                response.status_code = 429
                return response
            
            # Add current request
            self.requests[client_ip].append(now)
            
            # Continue with request
            return None
        
        return middleware
    
    def cleanup(self):
        """Cleanup old request data."""
        now = time.time()
        for ip in list(self.requests.keys()):
            self.requests[ip] = [ts for ts in self.requests[ip] if now - ts < self.window]
            if not self.requests[ip]:
                del self.requests[ip] 