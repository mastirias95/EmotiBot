# 🐳 EmotiBot Docker Deployment Guide

This guide will help you deploy EmotiBot using Docker with full WebSocket support.

## 📋 Prerequisites

- Docker installed (version 20.10+)
- Docker Compose installed (version 2.0+)
- Your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

## 🚀 Quick Start (Development)

### 1. Clone and Setup
```bash
git clone <your-repo>
cd EmotiBot
```

### 2. Configure Environment
```bash
# Copy the environment template
cp env.template .env

# Edit the .env file with your API key
nano .env  # or use your preferred editor
```

### 3. Build and Run
```bash
# Build and start the application
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### 4. Access the Application
- **Main App**: http://localhost:5001
- **Health Check**: http://localhost:5001/health
- **Metrics**: http://localhost:5001/metrics

## 🏭 Production Deployment

### 1. Setup Environment Variables
```bash
# Copy and configure environment
cp env.template .env

# Edit with production values
nano .env
```

**Required Environment Variables:**
```bash
GEMINI_API_KEY=your_actual_gemini_api_key
SECRET_KEY=your_super_secure_secret_key_32_chars_min
JWT_SECRET_KEY=your_jwt_secret_key_32_chars_min
POSTGRES_PASSWORD=your_secure_database_password
```

### 2. Production Deployment
```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d --build
```

## 🔧 Docker Commands

### Basic Operations
```bash
# Build the application
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f web

# Stop services
docker-compose down

# Restart a service
docker-compose restart web
```

### Database Operations
```bash
# Access database
docker-compose exec db psql -U emotibot -d emotibotdb

# Backup database
docker-compose exec db pg_dump -U emotibot emotibotdb > backup.sql

# Restore database
docker-compose exec -T db psql -U emotibot emotibotdb < backup.sql
```

### Maintenance
```bash
# View container status
docker-compose ps

# Check resource usage
docker stats

# Clean up unused images
docker system prune -a

# Update application
git pull
docker-compose down
docker-compose up -d --build
```

## 🔍 Troubleshooting

### WebSocket Connection Issues
```bash
# Check if WebSocket service is running
docker-compose logs web | grep "WebSocket"

# Should see: "✓ WebSocket service initialized"
```

### Database Connection Issues
```bash
# Check database health
docker-compose exec db pg_isready -U emotibot

# View database logs
docker-compose logs db
```

### API Key Issues
```bash
# Check if API key is loaded
docker-compose logs web | grep "Gemini"

# Should see: "Gemini service initialized successfully"
```

### Performance Issues
```bash
# Monitor resource usage
docker stats

# Check application logs
docker-compose logs -f web
```

## 📊 Monitoring

### Health Checks
The application includes built-in health checks:
- **Application**: http://localhost:5001/health
- **Database**: Automatic PostgreSQL health check
- **Docker Health**: `docker-compose ps` shows health status

### Logs
```bash
# Application logs
docker-compose logs -f web

# Database logs
docker-compose logs -f db

# All services
docker-compose logs -f
```

## 🔒 Security Considerations

### Production Security
1. **Change default passwords** in `.env`
2. **Use strong secret keys** (32+ characters)
3. **Enable HTTPS** with reverse proxy
4. **Regular updates** of base images
5. **Network isolation** using Docker networks

### Environment Variables
Never commit `.env` files to version control. Use:
```bash
# Add to .gitignore
echo ".env" >> .gitignore
```

## 🌐 Scaling

### Horizontal Scaling
```bash
# Scale web service
docker-compose up -d --scale web=3
```

### Load Balancer
For production, add a load balancer (nginx/traefik) in front of the web services.

## 📝 Configuration Files

- `Dockerfile` - Application container definition
- `docker-compose.yml` - Development environment
- `docker-compose.prod.yml` - Production environment
- `env.template` - Environment variables template
- `.dockerignore` - Files to exclude from build

## 🆘 Support

If you encounter issues:
1. Check the logs: `docker-compose logs -f`
2. Verify environment variables in `.env`
3. Ensure Docker and Docker Compose are up to date
4. Check port availability (5001, 5432)

## 🎯 Features Included

✅ **WebSocket Support** - Real-time emotion analysis
✅ **Database Persistence** - PostgreSQL with health checks
✅ **Health Monitoring** - Built-in health endpoints
✅ **Security** - Non-root user, environment isolation
✅ **Scalability** - Ready for horizontal scaling
✅ **Production Ready** - Optimized for deployment 