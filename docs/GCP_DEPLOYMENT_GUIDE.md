# EmotiBot GCP Deployment Guide

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **Google Cloud SDK** installed locally
3. **Docker** installed locally
4. **kubectl** installed locally

## Step 1: Initial GCP Setup

### Create Project and Enable APIs
```bash
# Set your project ID
export PROJECT_ID="emotibot-production"
export REGION="us-central1"
export ZONE="us-central1-a"

# Create project
gcloud projects create $PROJECT_ID

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable container.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable redis.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
```

## Step 2: Create GKE Cluster

```bash
# Create GKE cluster
gcloud container clusters create emotibot-cluster \
    --zone=$ZONE \
    --num-nodes=3 \
    --enable-autoscaling \
    --min-nodes=2 \
    --max-nodes=10 \
    --machine-type=e2-standard-2 \
    --enable-autorepair \
    --enable-autoupgrade

# Get cluster credentials
gcloud container clusters get-credentials emotibot-cluster --zone=$ZONE
```

## Step 3: Set Up Managed Databases

### PostgreSQL Databases
```bash
# Create Cloud SQL instances
gcloud sql instances create emotibot-auth-db \
    --database-version=POSTGRES_13 \
    --tier=db-f1-micro \
    --region=$REGION

gcloud sql instances create emotibot-conversation-db \
    --database-version=POSTGRES_13 \
    --tier=db-f1-micro \
    --region=$REGION

# Create databases
gcloud sql databases create authdb --instance=emotibot-auth-db
gcloud sql databases create conversationdb --instance=emotibot-conversation-db

# Create users (replace passwords with secure ones)
gcloud sql users create auth_user --instance=emotibot-auth-db --password=SECURE_PASSWORD_1
gcloud sql users create conv_user --instance=emotibot-conversation-db --password=SECURE_PASSWORD_2
```

### Redis Cache
```bash
# Create Redis instance
gcloud redis instances create emotibot-redis \
    --size=1 \
    --region=$REGION \
    --redis-version=redis_6_x
```

## Step 4: Container Registry Setup

```bash
# Create Artifact Registry repository
gcloud artifacts repositories create emotibot-repo \
    --repository-format=docker \
    --location=$REGION

# Configure Docker authentication
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

## Step 5: Build and Push Images

```bash
# Set registry path
export REGISTRY_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/emotibot-repo"

# Build and push each service
cd microservices

# Auth Service
docker build -t ${REGISTRY_PATH}/auth-service:latest ./auth-service
docker push ${REGISTRY_PATH}/auth-service:latest

# Emotion Service
docker build -t ${REGISTRY_PATH}/emotion-service:latest ./emotion-service
docker push ${REGISTRY_PATH}/emotion-service:latest

# Conversation Service
docker build -t ${REGISTRY_PATH}/conversation-service:latest ./conversation-service
docker push ${REGISTRY_PATH}/conversation-service:latest

# AI Service
docker build -t ${REGISTRY_PATH}/ai-service:latest ./ai-service
docker push ${REGISTRY_PATH}/ai-service:latest

# WebSocket Service
docker build -t ${REGISTRY_PATH}/websocket-service:latest ./websocket-service
docker push ${REGISTRY_PATH}/websocket-service:latest
```

## Step 6: Configure Kubernetes Secrets

```bash
# Get database connection strings
AUTH_DB_IP=$(gcloud sql instances describe emotibot-auth-db --format="value(ipAddresses[0].ipAddress)")
CONV_DB_IP=$(gcloud sql instances describe emotibot-conversation-db --format="value(ipAddresses[0].ipAddress)")
REDIS_IP=$(gcloud redis instances describe emotibot-redis --region=$REGION --format="value(host)")

# Create secrets
kubectl create secret generic emotibot-secrets \
    --from-literal=auth-database-url="postgresql://auth_user:SECURE_PASSWORD_1@${AUTH_DB_IP}:5432/authdb" \
    --from-literal=conversation-database-url="postgresql://conv_user:SECURE_PASSWORD_2@${CONV_DB_IP}:5432/conversationdb" \
    --from-literal=redis-host="${REDIS_IP}" \
    --from-literal=secret-key="YOUR_SECRET_KEY_HERE" \
    --from-literal=jwt-secret-key="YOUR_JWT_SECRET_KEY_HERE" \
    --from-literal=service-secret="YOUR_SERVICE_SECRET_HERE" \
    --from-literal=gemini-api-key="YOUR_GEMINI_API_KEY_HERE"
```

## Step 7: Deploy to Kubernetes

```bash
# Deploy all services
kubectl apply -f ../kubernetes/deployment-microservices.yaml
kubectl apply -f ../kubernetes/services-microservices.yaml

# Check deployment status
kubectl get pods
kubectl get services
```

## Step 8: Set Up Load Balancer and Ingress

```bash
# Create static IP
gcloud compute addresses create emotibot-ip --global

# Get the IP address
gcloud compute addresses describe emotibot-ip --global --format="value(address)"
```

## Step 9: Configure Domain and SSL

1. Point your domain to the static IP
2. Create SSL certificate:

```bash
gcloud compute ssl-certificates create emotibot-ssl \
    --domains=yourdomain.com,www.yourdomain.com \
    --global
```

## Step 10: Monitoring and Logging

```bash
# Enable monitoring
gcloud services enable monitoring.googleapis.com
gcloud services enable logging.googleapis.com

# Deploy monitoring stack (optional but recommended)
kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/bundle.yaml
```

## Environment Variables Summary

Create a `.env.production` file:
```bash
PROJECT_ID=emotibot-production
REGION=us-central1
ZONE=us-central1-a
REGISTRY_PATH=us-central1-docker.pkg.dev/emotibot-production/emotibot-repo

# Database URLs (get from Step 6)
AUTH_DATABASE_URL=postgresql://auth_user:PASSWORD@IP:5432/authdb
CONVERSATION_DATABASE_URL=postgresql://conv_user:PASSWORD@IP:5432/conversationdb

# Redis
REDIS_HOST=REDIS_IP_FROM_STEP_6
REDIS_PORT=6379

# Secrets
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
SERVICE_SECRET=your-service-secret
GEMINI_API_KEY=your-gemini-api-key
```

## Cost Estimation (Monthly)

- **GKE Cluster**: $200-400
- **Cloud SQL (2 instances)**: $50-100
- **Redis**: $30-50
- **Load Balancer**: $20
- **Container Registry**: $10
- **Total**: ~$310-580/month

## Scaling Considerations

1. **Auto-scaling**: Your GKE cluster is configured with auto-scaling
2. **Database scaling**: Upgrade Cloud SQL tiers as needed
3. **Redis scaling**: Increase Redis memory as needed
4. **Monitoring**: Use Google Cloud Monitoring for performance insights

## Security Best Practices

1. **Network Security**: Use VPC and firewall rules
2. **Secrets Management**: Never hardcode secrets
3. **Service Mesh**: Consider Istio for advanced traffic management
4. **Regular Updates**: Keep all components updated

## Troubleshooting

```bash
# Check pod logs
kubectl logs -l app=emotibot-auth-service

# Check service connectivity
kubectl exec -it POD_NAME -- curl http://service-name:port/health

# Monitor resource usage
kubectl top pods
kubectl top nodes
``` 