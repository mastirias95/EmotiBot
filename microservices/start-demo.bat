@echo off
echo ========================================
echo  Starting EmotiBot Microservices Demo
echo ========================================

echo.
echo Checking Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not running!
    echo Please install Docker Desktop and ensure it's running.
    pause
    exit /b 1
)

echo Docker is available!

echo.
echo Stopping any existing containers...
docker-compose -f docker-compose.demo.yml down -v 2>nul

echo.
echo Building and starting EmotiBot services...
echo This may take a few minutes on first run...

docker-compose -f docker-compose.demo.yml up --build -d

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to start services!
    echo Check the error messages above.
    pause
    exit /b 1
)

echo.
echo ========================================
echo  EmotiBot Demo Started Successfully!
echo ========================================
echo.
echo Services starting up... Please wait 30-60 seconds for all services to be ready.
echo.
echo Access the demo at: http://localhost:8080
echo.
echo Service endpoints:
echo - Auth Service:         http://localhost:8002
echo - Emotion Service:      http://localhost:8003
echo - Conversation Service: http://localhost:8004
echo - AI Service:           http://localhost:8005
echo - WebSocket Service:    http://localhost:8006
echo.
echo To stop the demo, run: docker-compose -f docker-compose.demo.yml down
echo.
echo Opening demo in browser...
start http://localhost:8080

pause 