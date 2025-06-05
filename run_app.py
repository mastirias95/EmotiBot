#!/usr/bin/env python3
"""
EmotiBot Application Launcher
Ensures proper WebSocket initialization
"""

import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main application launcher."""
    logger.info("Starting EmotiBot...")
    
    # Test WebSocket dependencies
    try:
        import eventlet
        logger.info("✓ Eventlet available")
    except ImportError:
        logger.error("✗ Eventlet not available. Install with: pip install eventlet")
        sys.exit(1)
    
    try:
        import flask_socketio
        logger.info("✓ Flask-SocketIO available")
    except ImportError:
        logger.error("✗ Flask-SocketIO not available. Install with: pip install flask-socketio")
        sys.exit(1)
    
    # Import and create the app
    try:
        from app import create_app
        app = create_app()
        logger.info("✓ Application created successfully")
        
        # Check if WebSocket service is available
        if hasattr(app, 'websocket_service') and app.websocket_service:
            logger.info("✓ WebSocket service initialized - starting with real-time features")
            # Run with WebSocket support
            try:
                app.websocket_service.socketio.run(
                    app, 
                    host='0.0.0.0', 
                    port=5001, 
                    debug=True,
                    use_reloader=False  # Disable reloader to avoid import issues
                )
            except KeyboardInterrupt:
                logger.info("🛑 Server stopped by user")
        else:
            logger.warning("⚠ WebSocket service not available - starting without real-time features")
            # Run without WebSocket support
            try:
                app.run(host='0.0.0.0', port=5001, debug=True)
            except KeyboardInterrupt:
                logger.info("🛑 Server stopped by user")
            
    except Exception as e:
        logger.error(f"✗ Failed to start application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 