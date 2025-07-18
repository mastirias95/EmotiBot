# 🤖 EmotiBot - AI-Powered Emotion Recognition Chat Platform

[![CI/CD Pipeline](https://github.com/mastirias95/EmotiBot/actions/workflows/ci.yml/badge.svg)](https://github.com/mastirias95/EmotiBot/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/kubernetes-%23326ce5.svg?style=flat&logo=kubernetes&logoColor=white)](https://kubernetes.io/)

EmotiBot is a modern, cloud-native emotion recognition chat platform that combines real-time emotion analysis with interactive AI conversations. Built with a microservices architecture and deployed on Google Kubernetes Engine (GKE), it provides users with an engaging chat experience featuring dynamic SVG avatars that respond to detected emotions.

## 🌟 Features

### 🎭 **Real-Time Emotion Detection**
- **Live Analysis**: Emotions detected while typing (after 3+ characters)
- **8 Emotion Types**: Happy, Sad, Angry, Surprised, Fear, Love, Confused, Neutral
- **Visual Feedback**: Dynamic SVG robot avatar with emotion-based expressions
- **WebSocket Integration**: Real-time updates without page refresh

### 🤖 **Interactive AI Chat**
- **Google Gemini Integration**: Powered by advanced AI for natural conversations
- **Context Awareness**: Maintains conversation history and context
- **Personalized Responses**: AI adapts to user's emotional state
- **Multi-turn Conversations**: Supports extended dialogue sessions

### 👤 **User Management & GDPR Compliance**
- **Secure Authentication**: JWT-based user registration and login
- **Account Management**: Complete user profile and settings control
- **GDPR Rights**: Data export, deletion, and access rights
- **Chat History**: Export conversations in JSON format
- **Privacy Controls**: Clear chat history and account deletion options

### 🎨 **Modern UI/UX**
- **Responsive Design**: Works seamlessly across desktop and mobile
- **Professional SVG Avatars**: Custom-designed robot with dynamic expressions
- **Smooth Animations**: Emotion transitions and typing indicators
- **Intuitive Interface**: Clean, modern design with excellent UX

## 🏗️ Architecture

EmotiBot follows a **microservices architecture** deployed on **Google Kubernetes Engine (GKE)**:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │  API Gateway    │    │  Load Balancer  │
│   (Nginx)       │◄──►│   (Kong)        │◄──►│   (GKE)         │
│   Port: 80      │    │   Port: 8000    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │  Auth Service   │ │ Emotion Service │ │Conversation Svc │
    │   Port: 8002    │ │   Port: 8003    │ │   Port: 8004    │
    └─────────────────┘ └─────────────────┘ └─────────────────┘
                │               │               │
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │  Auth Database  │ │   Redis Cache   │ │  Conv Database  │
    │  (Cloud SQL)    │ │   (Memory)      │ │  (Cloud SQL)    │
    └─────────────────┘ └─────────────────┘ └─────────────────┘
                                │
                    ┌─────────────────┐ ┌─────────────────┐
                    │   AI Service    │ │ WebSocket Svc   │
                    │   Port: 8005    │ │   Port: 8080    │
                    └─────────────────┘ └─────────────────┘
```

### 🔧 **Core Services**

| Service | Purpose | Technology | Port |
|---------|---------|------------|------|
| **Frontend** | Web UI & Static Assets | Nginx, HTML5, CSS3, JavaScript | 80 |
| **API Gateway** | Request routing & Rate limiting | Kong | 8000 |
| **Auth Service** | User authentication & JWT management | Flask, SQLAlchemy, PostgreSQL | 8002 |
| **Emotion Service** | Real-time emotion analysis | Flask, TextBlob, NLTK, scikit-learn | 8003 |
| **Conversation Service** | Chat history & conversation management | Flask, SQLAlchemy, PostgreSQL | 8004 |
| **AI Service** | Google Gemini integration | Flask, Google AI | 8005 |
| **WebSocket Service** | Real-time communication | WebSocket, Redis | 8080 |

## 🚀 Quick Start

### Prerequisites

- **Docker** and **Docker Compose**
- **Python 3.11+**
- **Node.js 18+** (for development)
- **kubectl** (for Kubernetes deployment)
- **Google Cloud SDK** (for GKE deployment)

### 🐳 Local Development with Docker Compose

1. **Clone the repository**
   ```bash
   git clone https://github.com/mastirias95/EmotiBot.git
   cd EmotiBot
   ```

2. **Set up environment variables**
   ```bash
   cp microservices/env.microservices microservices/.env
   # Edit .env file with your configuration
   ```

3. **Start all services**
   ```bash
   cd microservices
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - API Gateway: http://localhost:8000
   - Individual services: http://localhost:800X

### ☸️ Kubernetes Deployment (GKE)

1. **Set up GKE cluster**
   ```bash
   gcloud container clusters create emotibot-cluster \
     --zone=europe-west1-b \
     --num-nodes=3 \
     --machine-type=e2-medium
   ```

2. **Configure kubectl**
   ```bash
   gcloud container clusters get-credentials emotibot-cluster \
     --zone=europe-west1-b
   ```

3. **Deploy to Kubernetes**
   ```bash
   # Apply secrets
   kubectl apply -f kubernetes/secrets-cloud-databases.yaml
   
   # Deploy all services
   kubectl apply -f kubernetes/deployment-microservices.yaml
   kubectl apply -f kubernetes/services.yaml
   
   # Deploy Kong API Gateway
   kubectl apply -f kubernetes/kong-deployment.yaml
   ```

4. **Access your deployment**
   ```bash
   kubectl get services
   # Use the external IP addresses to access your services
   ```

## 🧪 Testing

### Unit Tests

Each microservice includes comprehensive unit tests:

```bash
# Run all tests
pytest microservices/*/test_*.py -v

# Run specific service tests
cd microservices/auth-service
python -m pytest test_auth_service.py -v

cd microservices/conversation-service  
python -m pytest test_conversation_service.py -v
```

### Test Coverage

- **Auth Service**: Authentication, JWT tokens, user management
- **Conversation Service**: Chat history, GDPR compliance, data export
- **Emotion Service**: Emotion detection algorithms, real-time analysis
- **Integration Tests**: Service-to-service communication, end-to-end workflows

### CI/CD Pipeline

The project uses **GitHub Actions** for continuous integration:

- ✅ **Code Linting**: flake8 for Python code quality
- ✅ **Unit Testing**: pytest with coverage reporting  
- ✅ **Docker Builds**: Multi-architecture container images
- ✅ **Security Scanning**: Dependency vulnerability checks
- ✅ **Integration Testing**: Service health and connectivity tests
- ✅ **Automated Deployment**: Direct deployment to GKE on main branch

## 📊 Monitoring & Observability

### Metrics & Monitoring
- **Prometheus**: Metrics collection from all services
- **Grafana**: Real-time dashboards and visualization
- **Health Checks**: Comprehensive service health monitoring
- **Logging**: Centralized logging with structured JSON format

### Performance Metrics
- **Request Latency**: P50, P95, P99 response times
- **Error Rates**: 4xx/5xx error tracking
- **Throughput**: Requests per second per service
- **Resource Usage**: CPU, memory, and disk utilization

## 🔒 Security

### Authentication & Authorization
- **JWT Tokens**: Secure, stateless authentication
- **Password Hashing**: bcrypt with salt for secure password storage
- **CORS**: Configured cross-origin resource sharing
- **Rate Limiting**: API rate limiting via Kong gateway

### Data Protection
- **GDPR Compliance**: Full user data rights implementation
- **Data Encryption**: TLS/SSL for all communications
- **Database Security**: Cloud SQL with private IPs
- **Secret Management**: Kubernetes secrets for sensitive data

## 🌍 Deployment Environments

### Production (GKE)
- **URL**: http://34.52.173.192/
- **API Gateway**: http://35.241.206.85:8000/
- **Environment**: Google Kubernetes Engine
- **Database**: Google Cloud SQL (PostgreSQL)
- **Caching**: Redis cluster

### Staging
- **Namespace**: emotibot-staging
- **Auto-deployment**: From main branch
- **Testing**: Automated integration tests

## 📚 API Documentation

### Authentication Endpoints
```
POST /api/auth/register    # User registration
POST /api/auth/login       # User login  
POST /api/auth/verify      # Token verification
GET  /api/auth/health      # Service health check
```

### Conversation Endpoints
```
GET    /api/conversations           # Get user conversations
POST   /api/conversations           # Create new conversation
GET    /api/conversations/export    # Export chat data (GDPR)
DELETE /api/conversations/clear     # Clear chat history
```

### Emotion Analysis
```
POST /api/emotion/analyze    # Analyze text emotion
GET  /api/emotion/health     # Service health check
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Add tests** for new functionality
5. **Run the test suite**
   ```bash
   pytest microservices/*/test_*.py -v
   ```
6. **Submit a pull request**

### Code Style
- **Python**: Follow PEP 8, use flake8 for linting
- **JavaScript**: ES6+, consistent formatting
- **Documentation**: Clear docstrings and comments

## 📋 Roadmap

### Upcoming Features
- [ ] **Voice Emotion Recognition**: Audio-based emotion detection
- [ ] **Multi-language Support**: Internationalization (i18n)
- [ ] **Advanced Analytics**: Emotion trends and insights
- [ ] **Mobile App**: React Native mobile application
- [ ] **Webhook Integration**: External service integrations
- [ ] **Advanced AI Models**: Custom emotion detection models

### Performance Improvements
- [ ] **Caching Layer**: Redis-based response caching
- [ ] **Database Optimization**: Query optimization and indexing
- [ ] **CDN Integration**: Static asset delivery optimization
- [ ] **Auto-scaling**: Horizontal pod autoscaling (HPA)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google Gemini AI** for powerful language processing
- **TextBlob & NLTK** for emotion analysis capabilities  
- **Kong** for robust API gateway functionality
- **Kubernetes** community for excellent orchestration tools
- **Open Source Community** for the amazing tools and libraries

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/mastirias95/EmotiBot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mastirias95/EmotiBot/discussions)
- **Documentation**: [Wiki](https://github.com/mastirias95/EmotiBot/wiki)

---

**Made with ❤️ by the EmotiBot Team**

*EmotiBot - Where emotions meet artificial intelligence* 🤖💭

## 📚 Documentation

- **[Microservices Architecture](MICROSERVICES_ARCHITECTURE.md)** - Complete architecture documentation
- **[Quick Start Guide](MICROSERVICES_QUICKSTART.md)** - Detailed setup instructions
- **[Research Document](LO1_RESEARCH_DOCUMENT.md)** - Academic research and analysis

## 🔧 Key Features

### ✅ Enterprise Architecture
- **Microservices Design** - 6 independent, deployable services
- **API Gateway** - Kong for routing, security, and load balancing
- **Service-to-Service Communication** - HTTP REST APIs with JWT authentication
- **Distributed Caching** - Redis for performance optimization

### ✅ DevOps & Deployment
- **Docker Containerization** - Each service in its own container
- **Docker Compose Orchestration** - Complete platform deployment
- **Kubernetes Ready** - Production deployment configurations
- **Health Monitoring** - Comprehensive health checks and metrics

### ✅ Security & Reliability
- **JWT Authentication** - Secure user authentication with refresh tokens
- **Service-to-Service Security** - Encrypted inter-service communication
- **Rate Limiting** - API protection and abuse prevention
- **Circuit Breakers** - Fault tolerance and graceful degradation

### ✅ Monitoring & Observability
- **Prometheus Metrics** - Comprehensive metrics collection
- **Grafana Dashboards** - Real-time monitoring and alerting
- **Jaeger Tracing** - Distributed request tracing
- **ELK Stack** - Centralized logging and analysis

## 🎯 Use Cases

- **Emotion-Aware Chatbots** - AI responses based on user emotions
- **Mental Health Support** - Empathetic conversation systems
- **Customer Service** - Emotion-aware customer interactions
- **Educational Platforms** - Adaptive learning based on emotional state

## 🏆 Academic Value

This project demonstrates:

- **Enterprise Architecture Patterns** - Microservices, API Gateway, Service Mesh
- **Distributed Systems** - Inter-service communication, fault tolerance
- **DevOps Practices** - Containerization, orchestration, monitoring
- **Security Implementation** - Authentication, authorization, encryption
- **Production Readiness** - Health checks, logging, metrics, alerting

Perfect for **Enterprise Architecture**, **Software Engineering**, and **DevOps** courses.

## 📊 Technology Stack

- **Backend:** Python Flask microservices
- **Databases:** PostgreSQL (per service), Redis (caching)
- **API Gateway:** Kong
- **Monitoring:** Prometheus, Grafana, Jaeger, Kibana
- **Containerization:** Docker, Docker Compose
- **Orchestration:** Kubernetes ready
- **AI Integration:** Google Gemini API

## 🤝 Contributing

This is an academic project demonstrating enterprise microservices architecture. The codebase is production-ready and showcases industry best practices.

## 📄 License

Academic project - suitable for educational and portfolio use.