#!/bin/bash

# EmotiBot Minikube Deployment Script
# This script deploys EmotiBot to a local Minikube cluster

set -e

echo "🚀 EmotiBot Minikube Deployment"
echo "==============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if minikube is installed
if ! command -v minikube &> /dev/null; then
    print_error "Minikube is not installed. Please install it first."
    echo "Visit: https://minikube.sigs.k8s.io/docs/start/"
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed. Please install it first."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Start Minikube if not running
print_info "Checking Minikube status..."
if ! minikube status > /dev/null 2>&1; then
    print_info "Starting Minikube..."
    minikube start --driver=docker --memory=4096 --cpus=2
    print_status "Minikube started"
else
    print_status "Minikube is already running"
fi

# Enable required addons
print_info "Enabling Minikube addons..."
minikube addons enable ingress
minikube addons enable metrics-server
print_status "Addons enabled"

# Set Docker environment to use Minikube's Docker daemon
print_info "Setting up Docker environment..."
eval $(minikube docker-env)
print_status "Docker environment configured"

# Build the Docker image in Minikube
print_info "Building EmotiBot Docker image..."
cd ..
docker build -t emotibot:latest .
print_status "Docker image built"

# Return to kubernetes directory
cd kubernetes

# Check if secrets need to be updated
print_warning "Please ensure you've updated the Gemini API key in secrets.yaml"
echo "To update the secret:"
echo "1. Get your API key from: https://makersuite.google.com/app/apikey"
echo "2. Encode it: echo -n 'your_api_key' | base64"
echo "3. Replace the gemini-api-key value in secrets.yaml"
echo ""
read -p "Have you updated the Gemini API key? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Please update the API key and run the script again"
    exit 1
fi

# Apply Kubernetes manifests
print_info "Deploying to Kubernetes..."

# Apply secrets first
kubectl apply -f secrets.yaml
print_status "Secrets applied"

# Apply PostgreSQL components
kubectl apply -f postgres-pvc.yaml
kubectl apply -f postgres-deployment.yaml
kubectl apply -f postgres-service.yaml
print_status "PostgreSQL deployed"

# Wait for PostgreSQL to be ready
print_info "Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s
print_status "PostgreSQL is ready"

# Apply EmotiBot components
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
print_status "EmotiBot deployed"

# Wait for EmotiBot to be ready
print_info "Waiting for EmotiBot to be ready..."
kubectl wait --for=condition=ready pod -l app=emotibot --timeout=300s
print_status "EmotiBot is ready"

# Get access information
print_info "Getting access information..."
MINIKUBE_IP=$(minikube ip)
INGRESS_PORT=$(kubectl get service ingress-nginx-controller -n ingress-nginx -o jsonpath='{.spec.ports[?(@.name=="http")].nodePort}')

echo ""
echo "🎉 EmotiBot deployed successfully!"
echo "=================================="
echo ""
echo "Access URLs:"
echo "• Direct IP: http://${MINIKUBE_IP}:${INGRESS_PORT}"
echo "• With host: http://emotibot.local (add to /etc/hosts)"
echo ""
echo "To add to /etc/hosts:"
echo "echo '${MINIKUBE_IP} emotibot.local' | sudo tee -a /etc/hosts"
echo ""
echo "Useful commands:"
echo "• View pods: kubectl get pods"
echo "• View services: kubectl get services"
echo "• View logs: kubectl logs -l app=emotibot -f"
echo "• Access dashboard: minikube dashboard"
echo "• Stop: kubectl delete -f ."
echo ""

# Optional: Open in browser
read -p "Open EmotiBot in browser? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v xdg-open &> /dev/null; then
        xdg-open "http://${MINIKUBE_IP}:${INGRESS_PORT}"
    elif command -v open &> /dev/null; then
        open "http://${MINIKUBE_IP}:${INGRESS_PORT}"
    else
        print_info "Please open http://${MINIKUBE_IP}:${INGRESS_PORT} in your browser"
    fi
fi 