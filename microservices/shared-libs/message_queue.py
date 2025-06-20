"""
Message Queue Client Library
Provides standardized methods for RabbitMQ communication in the EmotiBot microservices platform.
"""

import pika
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, Callable
import threading
import time

logger = logging.getLogger(__name__)

class MessageQueueClient:
    """Base class for RabbitMQ communication."""
    
    def __init__(self, service_name: str, queue_config: Dict = None):
        self.service_name = service_name
        self.queue_config = queue_config or {}
        self.connection = None
        self.channel = None
        self.consumers = {}
        
        # RabbitMQ connection parameters
        self.rabbitmq_host = os.environ.get('RABBITMQ_HOST', 'rabbitmq')
        self.rabbitmq_port = int(os.environ.get('RABBITMQ_PORT', 5672))
        self.rabbitmq_user = os.environ.get('RABBITMQ_USER', 'emotibot')
        self.rabbitmq_pass = os.environ.get('RABBITMQ_PASS', 'emotibot_pass')
        self.rabbitmq_vhost = os.environ.get('RABBITMQ_VHOST', '/')
        
        # Connection retry settings
        self.max_retries = 5
        self.retry_delay = 5
        
    def connect(self) -> bool:
        """Establish connection to RabbitMQ."""
        try:
            credentials = pika.PlainCredentials(self.rabbitmq_user, self.rabbitmq_pass)
            parameters = pika.ConnectionParameters(
                host=self.rabbitmq_host,
                port=self.rabbitmq_port,
                virtual_host=self.rabbitmq_vhost,
                credentials=credentials,
                heartbeat=60,
                blocked_connection_timeout=30
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare exchanges
            self.channel.exchange_declare(
                exchange='emotibot.events',
                exchange_type='topic',
                durable=True
            )
            self.channel.exchange_declare(
                exchange='emotibot.notifications',
                exchange_type='fanout',
                durable=True
            )
            self.channel.exchange_declare(
                exchange='emotibot.analytics',
                exchange_type='direct',
                durable=True
            )
            
            logger.info(f"{self.service_name} connected to RabbitMQ")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def ensure_connection(self):
        """Ensure connection is established with retry logic."""
        if self.connection is None or self.connection.is_closed:
            for attempt in range(self.max_retries):
                if self.connect():
                    return True
                logger.warning(f"Connection attempt {attempt + 1} failed, retrying in {self.retry_delay} seconds")
                time.sleep(self.retry_delay)
            return False
        return True
    
    def publish_event(self, routing_key: str, message: Dict, exchange: str = 'emotibot.events') -> bool:
        """Publish event message to RabbitMQ."""
        if not self.ensure_connection():
            return False
        
        try:
            # Add metadata to message
            message_with_metadata = {
                'data': message,
                'metadata': {
                    'service': self.service_name,
                    'timestamp': datetime.utcnow().isoformat(),
                    'routing_key': routing_key
                }
            }
            
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=json.dumps(message_with_metadata),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            logger.info(f"{self.service_name} published event: {routing_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event {routing_key}: {e}")
            return False
    
    def publish_notification(self, message: Dict) -> bool:
        """Publish notification message to fanout exchange."""
        return self.publish_event('', message, 'emotibot.notifications')
    
    def publish_analytics(self, event_type: str, data: Dict) -> bool:
        """Publish analytics event."""
        message = {
            'event_type': event_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        return self.publish_event('analytics.event', message, 'emotibot.analytics')
    
    def consume_queue(self, queue_name: str, callback: Callable, auto_ack: bool = False):
        """Start consuming messages from a queue."""
        if not self.ensure_connection():
            return False
        
        try:
            # Declare queue
            self.channel.queue_declare(queue=queue_name, durable=True)
            
            # Set up consumer
            def message_handler(ch, method, properties, body):
                try:
                    message = json.loads(body)
                    logger.info(f"{self.service_name} received message from {queue_name}")
                    
                    # Process message
                    result = callback(message)
                    
                    # Acknowledge message
                    if auto_ack or result:
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    else:
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                        
                except Exception as e:
                    logger.error(f"Error processing message from {queue_name}: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
            # Start consuming
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=message_handler,
                auto_ack=auto_ack
            )
            
            self.consumers[queue_name] = True
            logger.info(f"{self.service_name} started consuming from {queue_name}")
            
            # Start consuming in a separate thread
            def consume_loop():
                try:
                    self.channel.start_consuming()
                except KeyboardInterrupt:
                    self.channel.stop_consuming()
                except Exception as e:
                    logger.error(f"Consumer loop error: {e}")
            
            consumer_thread = threading.Thread(target=consume_loop, daemon=True)
            consumer_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start consuming from {queue_name}: {e}")
            return False
    
    def stop_consuming(self, queue_name: str):
        """Stop consuming from a specific queue."""
        if queue_name in self.consumers:
            try:
                self.channel.stop_consuming()
                self.consumers.pop(queue_name)
                logger.info(f"{self.service_name} stopped consuming from {queue_name}")
            except Exception as e:
                logger.error(f"Error stopping consumer for {queue_name}: {e}")
    
    def close(self):
        """Close RabbitMQ connection."""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                logger.info(f"{self.service_name} disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")

class AuthServiceQueueClient(MessageQueueClient):
    """Queue client for Auth Service."""
    
    def __init__(self):
        super().__init__('auth-service')
    
    def publish_user_registered(self, user_data: Dict):
        """Publish user registration event."""
        return self.publish_event('user.registered', user_data)
    
    def publish_user_login(self, user_data: Dict):
        """Publish user login event."""
        return self.publish_event('user.login', user_data)
    
    def publish_user_logout(self, user_data: Dict):
        """Publish user logout event."""
        return self.publish_event('user.logout', user_data)

class EmotionServiceQueueClient(MessageQueueClient):
    """Queue client for Emotion Service."""
    
    def __init__(self):
        super().__init__('emotion-service')
    
    def publish_emotion_analyzed(self, analysis_data: Dict):
        """Publish emotion analysis result."""
        return self.publish_event('emotion.analyzed', analysis_data)
    
    def publish_emotion_stats_updated(self, stats_data: Dict):
        """Publish emotion statistics update."""
        return self.publish_event('emotion.stats.updated', stats_data)

class ConversationServiceQueueClient(MessageQueueClient):
    """Queue client for Conversation Service."""
    
    def __init__(self):
        super().__init__('conversation-service')
    
    def publish_conversation_created(self, conversation_data: Dict):
        """Publish conversation creation event."""
        return self.publish_event('conversation.created', conversation_data)
    
    def publish_message_sent(self, message_data: Dict):
        """Publish message sent event."""
        return self.publish_event('message.sent', message_data)
    
    def publish_conversation_updated(self, conversation_data: Dict):
        """Publish conversation update event."""
        return self.publish_event('conversation.updated', conversation_data)

class AIServiceQueueClient(MessageQueueClient):
    """Queue client for AI Service."""
    
    def __init__(self):
        super().__init__('ai-service')
    
    def publish_response_generated(self, response_data: Dict):
        """Publish AI response generation event."""
        return self.publish_event('ai.response.generated', response_data)
    
    def publish_model_updated(self, model_data: Dict):
        """Publish AI model update event."""
        return self.publish_event('ai.model.updated', model_data)

class WebSocketServiceQueueClient(MessageQueueClient):
    """Queue client for WebSocket Service."""
    
    def __init__(self):
        super().__init__('websocket-service')
    
    def publish_notification(self, notification_data: Dict):
        """Publish WebSocket notification."""
        return self.publish_notification(notification_data)
    
    def publish_connection_event(self, connection_data: Dict):
        """Publish connection event."""
        return self.publish_event('websocket.connection', connection_data)

# Factory function to get appropriate queue client
def get_queue_client(service_name: str) -> MessageQueueClient:
    """Get queue client for specific service."""
    clients = {
        'auth-service': AuthServiceQueueClient,
        'emotion-service': EmotionServiceQueueClient,
        'conversation-service': ConversationServiceQueueClient,
        'ai-service': AIServiceQueueClient,
        'websocket-service': WebSocketServiceQueueClient
    }
    
    client_class = clients.get(service_name, MessageQueueClient)
    return client_class() 