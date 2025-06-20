# EmotiBot GCP CD Setup Guide

## 🚀 Quick Start: Deploy EmotiBot to Google Cloud Platform

This guide will help you set up **Continuous Deployment (CD)** to Google Cloud Platform using Google Kubernetes Engine (GKE).

## 📋 Prerequisites

1. **Google Cloud Account** with billing enabled
2. **GitHub repository** with admin access
3. **Domain name** (optional, for production)

## 🔧 Step 1: Set Up GCP Infrastructure

### 1.1 Create GCP Project
```bash
# Set your project details
export PROJECT_ID="emotibot-staging"  # Change this!
export REGION="us-central1"
export ZONE="us-central1-a"

# Create project
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID

# Enable billing (required - do this in GCP Console)
# https://console.cloud.google.com/billing
```

### 1.2 Enable Required APIs
```bash
gcloud services enable container.googleapis.com
gcloud services enable sqladmin.googleapis.com  
gcloud services enable redis.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
```

### 1.3 Create GKE Cluster
```bash
# Create GKE cluster (this takes 5-10 minutes)
gcloud container clusters create emotibot-cluster \
    --zone=$ZONE \
    --num-nodes=3 \
    --enable-autoscaling \
    --min-nodes=2 \
    --max-nodes=10 \
    --machine-type=e2-standard-2 \
    --enable-autorepair \
    --enable-autoupgrade

# Get credentials
gcloud container clusters get-credentials emotibot-cluster --zone=$ZONE
```

### 1.4 Create Managed Databases
```bash
# PostgreSQL for Auth Service
gcloud sql instances create emotibot-auth-db \
    --database-version=POSTGRES_13 \
    --tier=db-f1-micro \
    --region=$REGION

# PostgreSQL for Conversation Service  
gcloud sql instances create emotibot-conversation-db \
    --database-version=POSTGRES_13 \
    --tier=db-f1-micro \
    --region=$REGION

# Create databases
gcloud sql databases create authdb --instance=emotibot-auth-db
gcloud sql databases create conversationdb --instance=emotibot-conversation-db

# Create users (replace with secure passwords!)
gcloud sql users create auth_user --instance=emotibot-auth-db --password=CHANGE_THIS_PASSWORD_1
gcloud sql users create conv_user --instance=emotibot-conversation-db --password=CHANGE_THIS_PASSWORD_2
```

### 1.5 Create Redis Cache
```bash
gcloud redis instances create emotibot-redis \
    --size=1 \
    --region=$REGION \
    --redis-version=redis_6_x
```

### 1.6 Create Container Registry
```bash
gcloud artifacts repositories create emotibot-repo \
    --repository-format=docker \
    --location=$REGION
```

## 🔐 Step 2: Set Up GitHub Secrets

### 2.1 Create Service Account
```bash
# Create service account for GitHub Actions
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions Service Account"

# Get service account email
SA_EMAIL=$(gcloud iam service-accounts list --filter="displayName:GitHub Actions Service Account" --format="value(email)")

# Grant required permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/container.developer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/container.clusterViewer"

# Create and download key
gcloud iam service-accounts keys create github-actions-key.json \
    --iam-account=$SA_EMAIL
```

### 2.2 Get Database Connection Details
```bash
# Get database IPs
AUTH_DB_IP=$(gcloud sql instances describe emotibot-auth-db --format="value(ipAddresses[0].ipAddress)")
CONV_DB_IP=$(gcloud sql instances describe emotibot-conversation-db --format="value(ipAddresses[0].ipAddress)")

# Get Redis host
REDIS_HOST=$(gcloud redis instances describe emotibot-redis --region=$REGION --format="value(host)")

echo "📝 Save these values for GitHub Secrets:"
echo "AUTH_DB_IP: $AUTH_DB_IP"
echo "CONV_DB_IP: $CONV_DB_IP" 
echo "REDIS_HOST: $REDIS_HOST"
```

### 2.3 Add GitHub Secrets
Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `GCP_SA_KEY` | Contents of `github-actions-key.json` | Service account key |
| `SECRET_KEY` | Generate with `openssl rand -base64 32` | Flask secret key |
| `JWT_SECRET_KEY` | Generate with `openssl rand -base64 32` | JWT signing key |
| `SERVICE_SECRET` | Generate with `openssl rand -base64 32` | Inter-service auth |
| `GEMINI_API_KEY` | Your Gemini API key | AI service key |
| `GCP_AUTH_DATABASE_URL` | `postgresql://auth_user:PASSWORD@AUTH_DB_IP:5432/authdb` | Auth DB URL |
| `GCP_CONV_DATABASE_URL` | `postgresql://conv_user:PASSWORD@CONV_DB_IP:5432/conversationdb` | Conversation DB URL |
| `GCP_REDIS_HOST` | Redis host from above | Redis connection |

## 🚀 Step 3: Deploy!

### 3.1 Trigger Deployment
1. **Push to main branch** - This will trigger the CD pipeline automatically
2. **Or manually trigger** - Go to Actions tab → "CD - Deploy to GCP Staging" → Run workflow

### 3.2 Monitor Deployment
1. Check GitHub Actions for progress
2. Monitor GCP Console:
   - **GKE**: https://console.cloud.google.com/kubernetes
   - **Load Balancers**: https://console.cloud.google.com/net-services/loadbalancing

### 3.3 Get Your Application URL
```bash
# Get the external IP (may take a few minutes)
kubectl get service kong -n emotibot-staging

# Or watch until ready
kubectl get service kong -n emotibot-staging -w
```

## 🌐 Step 4: Access Your Application

Once deployed, your EmotiBot will be available at:
- **Main App**: `http://EXTERNAL_IP/`
- **Kong Admin**: `http://EXTERNAL_IP:8001/`

### API Endpoints:
- **Auth Service**: `http://EXTERNAL_IP/auth/`
- **Emotion Service**: `http://EXTERNAL_IP/emotion/`
- **Conversation Service**: `http://EXTERNAL_IP/conversation/`
- **AI Service**: `http://EXTERNAL_IP/ai/`
- **WebSocket Service**: `http://EXTERNAL_IP/ws/`

## 📊 Step 5: Monitoring & Management

### View Logs
```bash
# View all pods
kubectl get pods -n emotibot-staging

# View logs for specific service
kubectl logs -f deployment/auth-service -n emotibot-staging
```

### Scale Services
```bash
# Scale a service
kubectl scale deployment auth-service --replicas=3 -n emotibot-staging
```

### Update Application
Simply push to the `main` branch - the CD pipeline will automatically:
1. Build new Docker images
2. Push to Artifact Registry  
3. Update Kubernetes deployments
4. Perform rolling updates with zero downtime

## 💰 Cost Optimization

### Development/Staging (Low Cost)
- **GKE**: e2-standard-2 nodes (2-3 nodes) ≈ $50-75/month
- **Cloud SQL**: db-f1-micro instances ≈ $15-20/month each
- **Redis**: 1GB instance ≈ $25/month
- **Load Balancer**: ≈ $18/month
- **Total**: ~$125-150/month

### Production (Optimized)
- Use committed use discounts
- Enable cluster autoscaling
- Use preemptible nodes for non-critical workloads

## 🔒 Security Best Practices

1. **Enable Private GKE cluster** for production
2. **Use Cloud Armor** for DDoS protection
3. **Enable Binary Authorization** for container security
4. **Set up Cloud KMS** for secret encryption
5. **Configure VPC firewall rules**

## 🚨 Troubleshooting

### Common Issues:

**"Cluster not found"**
```bash
gcloud container clusters get-credentials emotibot-cluster --zone=us-central1-a
```

**"Permission denied"**
- Check service account has correct IAM roles
- Verify `GCP_SA_KEY` secret is correctly formatted JSON

**"Database connection failed"**
- Verify database IPs in secrets
- Check database passwords
- Ensure GKE cluster can reach Cloud SQL (add authorized networks if needed)

**"LoadBalancer pending"**
- Wait 5-10 minutes for GCP to provision
- Check GCP quotas in Console

## 🎉 Success!

Your EmotiBot microservices platform is now running on Google Cloud with:
- ✅ **Auto-scaling Kubernetes cluster**
- ✅ **Managed PostgreSQL databases** 
- ✅ **Redis caching**
- ✅ **Load balancer with external IP**
- ✅ **Continuous deployment pipeline**
- ✅ **Production-ready infrastructure**

## 📞 Support

If you encounter issues:
1. Check GitHub Actions logs
2. Review GCP Console for resource status
3. Use `kubectl` commands to debug Kubernetes issues
4. Check the troubleshooting section above

Your CD pipeline is now **production-ready**! 🚀 