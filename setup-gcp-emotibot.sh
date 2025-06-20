#!/bin/bash

# 🚀 EmotiBot GCP Setup Script
# This script will set up your complete EmotiBot infrastructure on Google Cloud Platform

set -e

# Color codes for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${PURPLE}"
    echo "=================================="
    echo "🤖 EmotiBot GCP Setup"
    echo "=================================="
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}[STEP $1]${NC} $2"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Configuration
PROJECT_ID="emotibot-$(date +%s)"  # Unique project ID
REGION="us-central1"
ZONE="us-central1-a"
CLUSTER_NAME="emotibot-cluster"

print_header

echo "This script will:"
echo "1. Create a new GCP project"
echo "2. Set up GKE cluster"
echo "3. Create managed databases"
echo "4. Set up container registry"
echo "5. Generate all necessary secrets"
echo ""
echo -e "${YELLOW}Estimated cost: ~$125-150/month${NC}"
echo ""

# Check prerequisites
print_step "1" "Checking prerequisites..."

if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI not found. Please install Google Cloud SDK first:"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    print_error "kubectl not found. Please install kubectl first:"
    echo "https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

print_success "All prerequisites met!"

# Get user confirmation
echo ""
print_warning "This will create billable resources on Google Cloud Platform."
read -p "Do you want to continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 1
fi

# Get API keys
echo ""
print_step "2" "Collecting API keys..."

read -p "Enter your Gemini API Key: " GEMINI_API_KEY
if [ -z "$GEMINI_API_KEY" ]; then
    print_error "Gemini API Key is required!"
    exit 1
fi

# Generate secure secrets
print_info "Generating secure secrets..."
SECRET_KEY=$(openssl rand -base64 32)
JWT_SECRET_KEY=$(openssl rand -base64 32)
SERVICE_SECRET=$(openssl rand -base64 32)
AUTH_DB_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
CONV_DB_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)

print_success "Secrets generated!"

# Create project
print_step "3" "Creating GCP project: $PROJECT_ID"

if gcloud projects create $PROJECT_ID --quiet; then
    print_success "Project created successfully!"
else
    print_error "Failed to create project. It might already exist."
    read -p "Enter existing project ID or press Enter to continue with $PROJECT_ID: " EXISTING_PROJECT
    if [ ! -z "$EXISTING_PROJECT" ]; then
        PROJECT_ID=$EXISTING_PROJECT
    fi
fi

gcloud config set project $PROJECT_ID
print_info "Active project: $PROJECT_ID"

# Enable billing check
print_warning "IMPORTANT: Make sure billing is enabled for project $PROJECT_ID"
print_info "Visit: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
read -p "Press Enter when billing is enabled..."

# Enable APIs
print_step "4" "Enabling required APIs..."
gcloud services enable container.googleapis.com --quiet
gcloud services enable sqladmin.googleapis.com --quiet
gcloud services enable redis.googleapis.com --quiet
gcloud services enable artifactregistry.googleapis.com --quiet
gcloud services enable cloudresourcemanager.googleapis.com --quiet
print_success "APIs enabled!"

# Create GKE cluster
print_step "5" "Creating GKE cluster (this takes 5-10 minutes)..."
gcloud container clusters create $CLUSTER_NAME \
    --zone=$ZONE \
    --num-nodes=3 \
    --enable-autoscaling \
    --min-nodes=2 \
    --max-nodes=10 \
    --machine-type=e2-standard-2 \
    --enable-autorepair \
    --enable-autoupgrade \
    --quiet

gcloud container clusters get-credentials $CLUSTER_NAME --zone=$ZONE
print_success "GKE cluster created and configured!"

# Create databases
print_step "6" "Creating managed databases..."

# Auth database
gcloud sql instances create emotibot-auth-db \
    --database-version=POSTGRES_13 \
    --tier=db-f1-micro \
    --region=$REGION \
    --quiet

gcloud sql databases create authdb --instance=emotibot-auth-db --quiet
gcloud sql users create auth_user --instance=emotibot-auth-db --password=$AUTH_DB_PASSWORD --quiet

# Conversation database
gcloud sql instances create emotibot-conversation-db \
    --database-version=POSTGRES_13 \
    --tier=db-f1-micro \
    --region=$REGION \
    --quiet

gcloud sql databases create conversationdb --instance=emotibot-conversation-db --quiet
gcloud sql users create conv_user --instance=emotibot-conversation-db --password=$CONV_DB_PASSWORD --quiet

print_success "Databases created!"

# Create Redis
print_step "7" "Creating Redis cache..."
gcloud redis instances create emotibot-redis \
    --size=1 \
    --region=$REGION \
    --redis-version=redis_6_x \
    --quiet

print_success "Redis created!"

# Create container registry
print_step "8" "Setting up container registry..."
gcloud artifacts repositories create emotibot-repo \
    --repository-format=docker \
    --location=$REGION \
    --quiet

gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
print_success "Container registry ready!"

# Create service account
print_step "9" "Creating service account for GitHub Actions..."
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions Service Account" \
    --quiet

SA_EMAIL=$(gcloud iam service-accounts list --filter="displayName:GitHub Actions Service Account" --format="value(email)")

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/container.developer" \
    --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/artifactregistry.writer" \
    --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/container.clusterViewer" \
    --quiet

# Create service account key
gcloud iam service-accounts keys create github-actions-key.json \
    --iam-account=$SA_EMAIL \
    --quiet

print_success "Service account created!"

# Get connection details
print_step "10" "Getting connection details..."
AUTH_DB_IP=$(gcloud sql instances describe emotibot-auth-db --format="value(ipAddresses[0].ipAddress)")
CONV_DB_IP=$(gcloud sql instances describe emotibot-conversation-db --format="value(ipAddresses[0].ipAddress)")
REDIS_HOST=$(gcloud redis instances describe emotibot-redis --region=$REGION --format="value(host)")

# Create environment file
cat > .env.gcp << EOF
# GCP Project Configuration
PROJECT_ID=$PROJECT_ID
REGION=$REGION
ZONE=$ZONE
CLUSTER_NAME=$CLUSTER_NAME

# Database Connection URLs
GCP_AUTH_DATABASE_URL=postgresql://auth_user:$AUTH_DB_PASSWORD@$AUTH_DB_IP:5432/authdb
GCP_CONV_DATABASE_URL=postgresql://conv_user:$CONV_DB_PASSWORD@$CONV_DB_IP:5432/conversationdb
GCP_REDIS_HOST=$REDIS_HOST

# Application Secrets
SECRET_KEY=$SECRET_KEY
JWT_SECRET_KEY=$JWT_SECRET_KEY
SERVICE_SECRET=$SERVICE_SECRET
GEMINI_API_KEY=$GEMINI_API_KEY

# Database Passwords
AUTH_DB_PASSWORD=$AUTH_DB_PASSWORD
CONV_DB_PASSWORD=$CONV_DB_PASSWORD
EOF

print_success "Setup completed successfully!"

# Final instructions
echo ""
echo -e "${GREEN}🎉 EmotiBot GCP Infrastructure Ready!${NC}"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo ""
echo "1. 🔐 Add these secrets to your GitHub repository:"
echo "   Go to: Settings → Secrets and variables → Actions"
echo ""
echo "   Required secrets:"
echo "   • GCP_SA_KEY: $(cat github-actions-key.json | base64 -w 0)"
echo "   • SECRET_KEY: $SECRET_KEY"
echo "   • JWT_SECRET_KEY: $JWT_SECRET_KEY"
echo "   • SERVICE_SECRET: $SERVICE_SECRET"
echo "   • GEMINI_API_KEY: $GEMINI_API_KEY"
echo "   • GCP_AUTH_DATABASE_URL: postgresql://auth_user:$AUTH_DB_PASSWORD@$AUTH_DB_IP:5432/authdb"
echo "   • GCP_CONV_DATABASE_URL: postgresql://conv_user:$CONV_DB_PASSWORD@$CONV_DB_IP:5432/conversationdb"
echo "   • GCP_REDIS_HOST: $REDIS_HOST"
echo ""
echo "2. 🚀 Deploy your application:"
echo "   • Push to main branch, or"
echo "   • Manually trigger 'CD - Deploy to GCP Staging' workflow"
echo ""
echo "3. 🌐 Access your application:"
echo "   • Get external IP: kubectl get service emotibot-frontend"
echo "   • Visit: http://EXTERNAL_IP"
echo ""
echo -e "${BLUE}💾 Important files created:${NC}"
echo "• .env.gcp - Environment configuration"
echo "• github-actions-key.json - Service account key (keep secure!)"
echo ""
echo -e "${YELLOW}💰 Estimated monthly cost: ~$125-150${NC}"
echo ""
echo -e "${GREEN}Your EmotiBot is ready to deploy! 🤖✨${NC}" 