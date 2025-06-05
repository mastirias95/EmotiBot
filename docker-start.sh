#!/bin/bash

# EmotiBot Docker Startup Script
# This script helps you quickly start EmotiBot with Docker

set -e

echo "🤖 EmotiBot Docker Startup Script"
echo "=================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.template .env
    echo "⚠️  Please edit .env file with your actual API keys before continuing!"
    echo "   Required: GEMINI_API_KEY"
    echo ""
    read -p "Press Enter after you've updated the .env file..."
fi

# Check if GEMINI_API_KEY is set
if grep -q "your_gemini_api_key_here" .env; then
    echo "⚠️  Warning: GEMINI_API_KEY still contains placeholder value"
    echo "   Please update .env with your actual Gemini API key"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Choose deployment type
echo ""
echo "Choose deployment type:"
echo "1) Development (with volume mounts)"
echo "2) Production (optimized)"
echo ""
read -p "Enter choice (1-2): " choice

case $choice in
    1)
        echo "🚀 Starting EmotiBot in development mode..."
        docker-compose up --build
        ;;
    2)
        echo "🏭 Starting EmotiBot in production mode..."
        docker-compose -f docker-compose.prod.yml up -d --build
        echo ""
        echo "✅ EmotiBot started in background!"
        echo "   Access: http://localhost:5001"
        echo "   Logs: docker-compose -f docker-compose.prod.yml logs -f"
        echo "   Stop: docker-compose -f docker-compose.prod.yml down"
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac 