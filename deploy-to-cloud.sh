#!/bin/bash

# EmotiBot Cloud Deployment Script
# Usage: ./deploy-to-cloud.sh [gcp|aws]

set -e

PLATFORM=${1:-gcp}
PROJECT_NAME="emotibot"

echo "🚀 Starting EmotiBot deployment to $PLATFORM"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    if [ "$PLATFORM" = "gcp" ]; then
        if ! command -v gcloud &> /dev/null; then
            print_error "gcloud CLI is not installed. Please install Google Cloud SDK first."
            exit 1
        fi
    elif [ "$PLATFORM" = "aws" ]; then
        if ! command -v aws &> /dev/null; then
            print_error "AWS CLI is not installed. Please install AWS CLI first."
            exit 1
        fi
        
        if ! command -v eksctl &> /dev/null; then
            print_error "eksctl is not installed. Please install eksctl first."
            exit 1
        fi
    fi
    
    print_success "All prerequisites met!"
}

# Set environment variables
set_environment() {
    print_status "Setting up environment variables..."
    
    if [ "$PLATFORM" = "gcp" ]; then
        export PROJECT_ID="${PROJECT_NAME}-production"
        export REGION="us-central1"
        export ZONE="us-central1-a"
        export REGISTRY_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${PROJECT_NAME}-repo"
    elif [ "$PLATFORM" = "aws" ]; then
        export AWS_REGION="us-east-1"
        export CLUSTER_NAME="${PROJECT_NAME}-cluster"
        export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
        if [ -z "$AWS_ACCOUNT_ID" ]; then
            print_error "Could not get AWS Account ID. Please configure AWS CLI with 'aws configure'"
            exit 1
        fi
        export ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    fi
    
    print_success "Environment variables set for $PLATFORM"
}

# Create environment file
create_env_file() {
    print_status "Creating environment configuration file..."
    
    # Check if secrets are provided
    if [ -z "$GEMINI_API_KEY" ]; then
        print_warning "GEMINI_API_KEY not set. Please set it before deploying:"
        echo "export GEMINI_API_KEY='your-gemini-api-key'"
        read -p "Enter your Gemini API Key: " GEMINI_API_KEY
        export GEMINI_API_KEY
    fi
    
    # Generate secure random secrets if not provided
    SECRET_KEY=${SECRET_KEY:-$(openssl rand -base64 32)}
    JWT_SECRET_KEY=${JWT_SECRET_KEY:-$(openssl rand -base64 32)}
    SERVICE_SECRET=${SERVICE_SECRET:-$(openssl rand -base64 32)}
    
    # Create .env file
    cat > .env.production << EOF
# Platform Configuration
PLATFORM=$PLATFORM

# API Keys
GEMINI_API_KEY=$GEMINI_API_KEY

# Security
SECRET_KEY=$SECRET_KEY
JWT_SECRET_KEY=$JWT_SECRET_KEY
SERVICE_SECRET=$SERVICE_SECRET

# Database Passwords (change these!)
AUTH_DB_PASSWORD=$(openssl rand -base64 16)
CONV_DB_PASSWORD=$(openssl rand -base64 16)
EOF
    
    print_success "Environment file created at .env.production"
    print_warning "⚠️  IMPORTANT: Save the .env.production file securely!"
}

# Build and push Docker images
build_and_push_images() {
    print_status "Building and pushing Docker images..."
    
    cd microservices
    
    services=("auth-service" "emotion-service" "conversation-service" "ai-service" "websocket-service")
    
    for service in "${services[@]}"; do
        print_status "Building $service..."
        
        if [ "$PLATFORM" = "gcp" ]; then
            docker build -t ${REGISTRY_PATH}/${service}:latest ./${service}
            docker push ${REGISTRY_PATH}/${service}:latest
        elif [ "$PLATFORM" = "aws" ]; then
            docker build -t ${service}:latest ./${service}
            docker tag ${service}:latest ${ECR_REGISTRY}/${PROJECT_NAME}/${service}:latest
            docker push ${ECR_REGISTRY}/${PROJECT_NAME}/${service}:latest
        fi
        
        print_success "$service built and pushed"
    done
    
    cd ../
}

# Main execution
main() {
    print_status "🤖 EmotiBot Cloud Deployment Starting..."
    
    # Check if platform is supported
    if [[ "$PLATFORM" != "gcp" && "$PLATFORM" != "aws" ]]; then
        print_error "Unsupported platform: $PLATFORM"
        echo "Usage: $0 [gcp|aws]"
        exit 1
    fi
    
    check_prerequisites
    set_environment
    create_env_file
    
    print_status "🎯 Next steps:"
    echo "1. Review the deployment guide: docs/${PLATFORM^^}_DEPLOYMENT_GUIDE.md"
    echo "2. Secure your .env.production file"
    echo "3. Follow the step-by-step deployment guide"
    
    print_warning "Ready to proceed with image building? (y/N)"
    read -p "Continue? " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        build_and_push_images
        print_success "🎉 Images built and pushed successfully!"
        print_status "Now follow the remaining steps in the deployment guide."
    else
        print_status "Deployment preparation complete. Run the script again when ready to build images."
    fi
}

# Execute main function
main 