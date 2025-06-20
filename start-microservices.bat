@echo off
echo ========================================
echo    EmotiBot Microservices Platform
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo ✓ Docker is running
echo.

REM Navigate to microservices directory
cd microservices

REM Check if .env file exists
if not exist .env (
    echo Creating .env file from template...
    copy env.microservices .env
    echo.
    echo ⚠️  IMPORTANT: Please edit .env file with your configuration:
    echo    - JWT_SECRET_KEY (change this!)
    echo    - Database passwords (change these!)
    echo    - GEMINI_API_KEY (optional)
    echo.
    pause
)

echo Starting EmotiBot Microservices Platform...
echo.

REM Build and start all services
echo Building services...
docker-compose -f docker-compose.microservices.yml build

if %errorlevel% neq 0 (
    echo ERROR: Failed to build services!
    pause
    exit /b 1
)

echo.
echo Starting services...
docker-compose -f docker-compose.microservices.yml up -d

if %errorlevel% neq 0 (
    echo ERROR: Failed to start services!
    pause
    exit /b 1
)

echo.
echo ========================================
echo    Services Starting...
echo ========================================
echo.

REM Wait for services to start
echo Waiting for services to initialize...
timeout /t 30 /nobreak >nul

REM Check service status
echo.
echo Checking service status...
docker-compose -f docker-compose.microservices.yml ps

echo.
echo ========================================
echo    Service Health Checks
echo ========================================
echo.

REM Health checks
echo Testing API Gateway...
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ API Gateway is running
) else (
    echo ✗ API Gateway is not responding
)

echo Testing Auth Service...
curl -s http://localhost:8002/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Auth Service is running
) else (
    echo ✗ Auth Service is not responding
)

echo Testing Emotion Service...
curl -s http://localhost:8003/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Emotion Service is running
) else (
    echo ✗ Emotion Service is not responding
)

echo Testing Conversation Service...
curl -s http://localhost:8004/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Conversation Service is running
) else (
    echo ✗ Conversation Service is not responding
)

echo Testing AI Service...
curl -s http://localhost:8005/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ AI Service is running
) else (
    echo ✗ AI Service is not responding
)

echo Testing WebSocket Service...
curl -s http://localhost:8006/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ WebSocket Service is running
) else (
    echo ✗ WebSocket Service is not responding
)

echo.
echo ========================================
echo    Platform Access URLs
echo ========================================
echo.
echo 🌐 API Gateway:        http://localhost:8000
echo 🔐 Auth Service:       http://localhost:8002
echo 😊 Emotion Service:    http://localhost:8003
echo 💬 Conversation Service: http://localhost:8004
echo 🤖 AI Service:         http://localhost:8005
echo 🔌 WebSocket Service:  http://localhost:8006
echo.
echo 📊 Monitoring & Observability:
echo    📈 Grafana Dashboard:  http://localhost:3001 (admin/emotibot123)
echo    📊 Prometheus Metrics: http://localhost:9090
echo    🔍 Jaeger Tracing:     http://localhost:16686
echo    📝 Kibana Logs:        http://localhost:5601
echo.
echo ========================================
echo    Quick Test Commands
echo ========================================
echo.
echo Test API Gateway:
echo   curl http://localhost:8000/health
echo.
echo Test User Registration:
echo   curl -X POST http://localhost:8000/api/auth/register ^
echo     -H "Content-Type: application/json" ^
echo     -d "{\"username\":\"testuser\",\"email\":\"test@example.com\",\"password\":\"password123\"}"
echo.
echo Test Emotion Detection:
echo   curl -X POST http://localhost:8000/api/emotion/detect ^
echo     -H "Content-Type: application/json" ^
echo     -d "{\"text\":\"I am feeling really happy today!\"}"
echo.
echo ========================================
echo    Platform Status: RUNNING
echo ========================================
echo.
echo Press any key to view service logs...
pause >nul

REM Show logs
echo.
echo ========================================
echo    Service Logs (Press Ctrl+C to exit)
echo ========================================
echo.
docker-compose -f docker-compose.microservices.yml logs -f 