@echo off
REM EmotiBot Docker Startup Script for Windows
REM This script helps you quickly start EmotiBot with Docker

echo 🤖 EmotiBot Docker Startup Script
echo ==================================

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo 📝 Creating .env file from template...
    copy env.template .env
    echo ⚠️  Please edit .env file with your actual API keys before continuing!
    echo    Required: GEMINI_API_KEY
    echo.
    pause
)

REM Check if GEMINI_API_KEY is set
findstr /C:"your_gemini_api_key_here" .env >nul
if not errorlevel 1 (
    echo ⚠️  Warning: GEMINI_API_KEY still contains placeholder value
    echo    Please update .env with your actual Gemini API key
    echo.
    set /p continue="Continue anyway? (y/N): "
    if /i not "%continue%"=="y" exit /b 1
)

REM Choose deployment type
echo.
echo Choose deployment type:
echo 1^) Development ^(with volume mounts^)
echo 2^) Production ^(optimized^)
echo.
set /p choice="Enter choice (1-2): "

if "%choice%"=="1" (
    echo 🚀 Starting EmotiBot in development mode...
    docker-compose up --build
) else if "%choice%"=="2" (
    echo 🏭 Starting EmotiBot in production mode...
    docker-compose -f docker-compose.prod.yml up -d --build
    echo.
    echo ✅ EmotiBot started in background!
    echo    Access: http://localhost:5001
    echo    Logs: docker-compose -f docker-compose.prod.yml logs -f
    echo    Stop: docker-compose -f docker-compose.prod.yml down
    pause
) else (
    echo ❌ Invalid choice
    pause
    exit /b 1
) 