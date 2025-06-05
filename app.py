import logging
import sys
import os
from flask import Flask, request, jsonify, render_template, g, redirect, url_for
from flask_cors import CORS
from prometheus_flask_exporter import PrometheusMetrics
from services.emotion_service import EmotionService
from services.auth_service import AuthService
from services.conversation_service import ConversationService
from services.gemini_service import GeminiService
# Try to import WebSocket service, but make it optional for now
try:
    from services.websocket_service import WebSocketService
    WEBSOCKET_AVAILABLE = True
    print("✓ WebSocket service import successful")
except ImportError as e:
    WEBSOCKET_AVAILABLE = False
    print(f"✗ WebSocket service import failed: {e}")
    print("Running without real-time features.")
except Exception as e:
    WEBSOCKET_AVAILABLE = False
    print(f"✗ WebSocket service initialization error: {e}")
    print("Running without real-time features.")

from middleware.rate_limiter import RateLimiter
from middleware.auth import token_required
from models.user import db
from config import get_config

# Configure logging to output to console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Force enable metrics in development mode
os.environ['DEBUG_METRICS'] = '1'

def create_app(config_name='default'):
    """Create and configure the Flask application.
    
    Args:
        config_name (str): Configuration environment
        
    Returns:
        Flask: The configured Flask application
    """
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))
    
    # Enable CORS
    CORS(app)
    
    # Set up Prometheus metrics - explicitly set the path and disable default group metrics
    metrics = PrometheusMetrics(app, path='/metrics', group_by_endpoint=False, defaults_prefix='flask')
    
    # Add some default metrics without using automatic endpoint grouping
    @metrics.counter('http_requests_total', 'HTTP requests total')
    @app.before_request
    def before_request():
        pass
        
    # Static information as metric
    metrics.info('app_info', 'Application info', version='1.0.0')
    
    # Set up logging with the configured level
    logging.getLogger().setLevel(app.config.get('LOG_LEVEL', 'DEBUG'))
    
    logger.debug("Creating Flask application...")
    
    # Initialize database
    db.init_app(app)
    
    # Initialize services
    auth_service = AuthService(app.config)
    app.auth_service = auth_service  # Make auth_service available in the app context
    
    conversation_service = ConversationService()
    app.conversation_service = conversation_service  # Make conversation_service available
    
    # Initialize Gemini service
    gemini_service = GeminiService()
    app.gemini_service = gemini_service
    
    # Initialize WebSocket service if available
    if WEBSOCKET_AVAILABLE:
        websocket_service = WebSocketService(app)
        app.websocket_service = websocket_service
        logger.info("WebSocket service initialized successfully")
    else:
        app.websocket_service = None
        logger.warning("WebSocket service not available")
    
    # Create database tables
    with app.app_context():
        db.create_all()
        logger.debug("Database tables created")
    
    # Initialize rate limiter
    rate_limiter = RateLimiter(limit=100, window=60)  # 100 requests per minute
    rate_limit_middleware = rate_limiter()
    
    # Register middleware
    @app.before_request
    def apply_rate_limit():
        # Skip rate limiting for static files
        if request.path.startswith('/static'):
            return None
        
        return rate_limit_middleware()
    
    # Register routes
    
    @app.route('/')
    @metrics.counter('index_requests', 'Number of requests to the index page')
    def index():
        """Render the main page."""
        logger.debug("Rendering index page")
        return render_template('index.html')
    
    @app.route('/login')
    @metrics.counter('login_page_requests', 'Number of requests to the login page')
    def login_page():
        """Render the login page."""
        logger.debug("Rendering login page")
        return render_template('login.html')
    
    @app.route('/register')
    @metrics.counter('register_page_requests', 'Number of requests to the register page')
    def register_page():
        """Render the registration page."""
        logger.debug("Rendering register page")
        return render_template('register.html')
    
    # Authentication routes
    
    @app.route('/api/auth/register', methods=['POST'])
    @metrics.counter('user_registrations', 'Number of user registrations')
    def register():
        """Register a new user."""
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
            
        data = request.get_json()
        
        # Extract required fields
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        # Validate input
        if not username:
            return jsonify({'error': 'Username is required'}), 400
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        if not password:
            return jsonify({'error': 'Password is required'}), 400
        
        # Register user
        success, message, user_data = auth_service.register_user(username, email, password)
        
        if not success:
            return jsonify({'error': message}), 400
        
        return jsonify({
            'message': message,
            'user': user_data
        }), 201
    
    @app.route('/api/auth/login', methods=['POST'])
    @metrics.counter('user_logins', 'Number of user login attempts')
    def login():
        """Authenticate a user and return a JWT token."""
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
            
        data = request.get_json()
        
        # Extract credentials
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validate input
        if not username:
            return jsonify({'error': 'Username or email is required'}), 400
        
        if not password:
            return jsonify({'error': 'Password is required'}), 400
        
        # Authenticate user
        success, message, auth_data = auth_service.authenticate(username, password)
        
        if not success:
            return jsonify({'error': message}), 401
        
        return jsonify({
            'message': message,
            **auth_data
        }), 200
    
    @app.route('/api/auth/me', methods=['GET'])
    @token_required
    @metrics.counter('profile_requests', 'Number of user profile requests')
    def get_user_profile():
        """Get the authenticated user's profile."""
        user = g.user
        return jsonify({
            'user': user.to_dict()
        }), 200
    
    @app.route('/api/conversations/history', methods=['GET'])
    @token_required
    @metrics.counter('history_requests', 'Number of conversation history requests')
    def get_conversation_history():
        """Get the user's conversation history.
        
        This is a protected endpoint that requires authentication.
        """
        user = g.user
        
        # Get conversation history from database
        history = conversation_service.get_user_conversation_history(user.id)
        
        logger.info(f"Retrieved {len(history)} conversation records for user: {user.username}")
        
        return jsonify({
            'history': history
        }), 200
    
    @app.route('/api/conversations/insights', methods=['GET'])
    @token_required
    @metrics.counter('insights_requests', 'Number of mood insights requests')
    def get_mood_insights():
        """Get AI-generated mood insights for the user."""
        user = g.user
        
        # Get conversation history for analysis
        history = conversation_service.get_user_conversation_history(user.id, limit=10)
        
        if not history:
            return jsonify({
                'insights': 'Start chatting with me to get personalized mood insights!'
            }), 200
        
        # Generate insights using Gemini
        insights = app.gemini_service.generate_mood_insights(history)
        
        logger.info(f"Generated mood insights for user: {user.username}")
        
        return jsonify({
            'insights': insights,
            'conversation_count': len(history)
        }), 200
    
    @app.route('/api/analyze', methods=['POST'])
    @metrics.counter('emotion_analysis', 'Number of emotion analysis requests')
    @metrics.histogram('emotion_analysis_latency', 'Latency of emotion analysis requests',
                       labels={'status': lambda r: r.status_code})
    def analyze_emotion():
        """API endpoint to analyze emotions in text."""
        logger.debug("Received analyze request")
        
        if not request.is_json:
            logger.warning("Request is not JSON")
            return jsonify({'error': 'Request must be JSON'}), 400
            
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            logger.warning("Empty text received")
            return jsonify({'error': 'Text is required'}), 400
        
        # Analyze the emotion in the text
        result = EmotionService.detect_emotion(text)
        
        # Generate bot response using Gemini or fallback
        conversation_history = []
        user_id = None
        
        # Check if user is authenticated
        auth_header = request.headers.get('Authorization')
        if auth_header and hasattr(g, 'user') and g.user:
            user_id = g.user.id
            # Get recent conversation history for context
            conversation_history = conversation_service.get_user_conversation_history(user_id, limit=5)
        
        # Generate response using Gemini
        bot_message = app.gemini_service.generate_emotional_response(
            text, 
            result['emotion'], 
            result['confidence'],
            conversation_history
        )
        
        # Save conversation for authenticated users
        if user_id:
            conversation_service.save_conversation(user_id, text, bot_message, result)
        
        logger.info(f"Analyzed text: '{text}', detected emotion: {result['emotion']}")
        
        # Return the analysis result with bot response
        return jsonify({
            **result,
            'bot_message': bot_message
        })
    
    # Health check endpoint for Kubernetes
    @app.route('/health')
    @metrics.counter('health_checks', 'Number of health check requests')
    def health_check():
        """Health check endpoint for Kubernetes."""
        return jsonify({
            'status': 'ok',
            'version': '1.0.0'
        })
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        logger.warning(f"404 error: {error}")
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def server_error(error):
        """Handle 500 errors."""
        logger.error(f"Server error: {error}")
        return jsonify({'error': 'Internal server error'}), 500
    
    logger.debug("Flask application created successfully")
    return app

if __name__ == '__main__':
    logger.debug("Starting application...")
    app = create_app()
    logger.info("EmotiBot is running on http://0.0.0.0:5001")
    
    # Use eventlet as the WebSocket server if available, otherwise use regular Flask
    if WEBSOCKET_AVAILABLE and hasattr(app, 'websocket_service') and app.websocket_service:
        app.websocket_service.socketio.run(app, host='0.0.0.0', port=5001, debug=True)
    else:
        app.run(host='0.0.0.0', port=5001, debug=True) 