@echo off
REM EmotiBot Microservices Startup Script
REM This script starts all microservices with proper environment configuration

echo.
echo ========================================
echo    EmotiBot Microservices Startup
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running. Please start Docker first.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist "env.microservices" (
    echo ERROR: env.microservices file not found.
    echo Please ensure the environment configuration file exists.
    pause
    exit /b 1
)

REM Load environment variables
echo Loading environment configuration...
for /f "tokens=1,* delims==" %%a in (env.microservices) do (
    if not "%%a"=="" if not "%%a:~0,1%"=="#" (
        set "%%a=%%b"
    )
)

REM Set RabbitMQ environment variables
set RABBITMQ_HOST=rabbitmq
set RABBITMQ_PORT=5672
set RABBITMQ_USER=emotibot
set RABBITMQ_PASS=emotibot_pass
set RABBITMQ_VHOST=/

echo Environment loaded successfully.
echo.

REM Stop any existing containers
echo Stopping existing containers...
docker-compose -f microservices/docker-compose.microservices.yml down
if %errorlevel% neq 0 (
    echo WARNING: Failed to stop existing containers. Continuing...
)

echo.

REM Start services in order
echo Starting core infrastructure services...

REM Start databases and Redis first
echo 1. Starting databases and Redis...
docker-compose -f microservices/docker-compose.microservices.yml up -d auth-db conversation-db redis
if %errorlevel% neq 0 (
    echo ERROR: Failed to start databases and Redis.
    pause
    exit /b 1
)

REM Wait for databases to be ready
echo Waiting for databases to be ready...
timeout /t 10 /nobreak >nul

REM Start RabbitMQ
echo 2. Starting RabbitMQ...
docker-compose -f microservices/docker-compose.microservices.yml up -d rabbitmq
if %errorlevel% neq 0 (
    echo ERROR: Failed to start RabbitMQ.
    pause
    exit /b 1
)

REM Wait for RabbitMQ to be ready
echo Waiting for RabbitMQ to be ready...
timeout /t 15 /nobreak >nul

REM Start monitoring services
echo 3. Starting monitoring services...
docker-compose -f microservices/docker-compose.microservices.yml up -d prometheus grafana jaeger elasticsearch logstash kibana consul
if %errorlevel% neq 0 (
    echo WARNING: Some monitoring services failed to start. Continuing...
)

REM Start microservices
echo 4. Starting microservices...
docker-compose -f microservices/docker-compose.microservices.yml up -d auth-service emotion-service conversation-service ai-service websocket-service
if %errorlevel% neq 0 (
    echo ERROR: Failed to start microservices.
    pause
    exit /b 1
)

REM Wait for services to be ready
echo Waiting for services to be ready...
timeout /t 20 /nobreak >nul

REM Start API Gateway
echo 5. Starting API Gateway...
docker-compose -f microservices/docker-compose.microservices.yml up -d api-gateway
if %errorlevel% neq 0 (
    echo ERROR: Failed to start API Gateway.
    pause
    exit /b 1
)

REM Start frontend (if exists)
echo 6. Starting frontend...
docker-compose -f microservices/docker-compose.microservices.yml up -d web-frontend
if %errorlevel% neq 0 (
    echo WARNING: Frontend service not found or failed to start. Continuing...
)

echo.
echo ========================================
echo    Services Started Successfully!
echo ========================================
echo.

REM Display service status
echo Checking service status...
docker-compose -f microservices/docker-compose.microservices.yml ps

echo.
echo ========================================
echo    Access URLs
echo ========================================
echo.
echo API Gateway:        http://localhost:8000
echo Auth Service:       http://localhost:8002
echo Emotion Service:    http://localhost:8003
echo Conversation Svc:   http://localhost:8004
echo AI Service:         http://localhost:8005
echo WebSocket Service:  http://localhost:8006
echo.
echo Monitoring:
echo Prometheus:         http://localhost:9090
echo Grafana:            http://localhost:3001 (admin/admin)
echo Jaeger:             http://localhost:16686
echo Kibana:             http://localhost:5601
echo Consul:             http://localhost:8500
echo.
echo RabbitMQ Management: http://localhost:15672 (emotibot/emotibot_pass)
echo.

REM Run health checks
echo Running health checks...
python test-microservices.py

echo.
echo ========================================
echo    Startup Complete!
echo ========================================
echo.
echo To stop all services, run:
echo docker-compose -f microservices/docker-compose.microservices.yml down
echo.
echo To view logs, run:
echo docker-compose -f microservices/docker-compose.microservices.yml logs -f
echo.

pause 