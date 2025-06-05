# 🚀 EmotiBot Minikube Deployment Guide

Deploy EmotiBot locally on Minikube for testing Kubernetes functionality with full WebSocket support.

## 📋 Prerequisites

### Required Software
- **Docker Desktop** (running)
- **Minikube** (v1.25+)
- **kubectl** (v1.20+)
- **Git** (for cloning)

### Installation Links
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Minikube](https://minikube.sigs.k8s.io/docs/start/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)

### System Requirements
- **RAM**: 4GB+ available for Minikube
- **CPU**: 2+ cores
- **Disk**: 10GB+ free space

## 🚀 Quick Start

### Option 1: Automated Deployment (Recommended)

#### Linux/Mac:
```bash
cd kubernetes
chmod +x deploy-minikube.sh
./deploy-minikube.sh
```

#### Windows:
```cmd
cd kubernetes
deploy-minikube.bat
```

### Option 2: Manual Deployment

#### 1. Start Minikube
```bash
# Start with adequate resources
minikube start --driver=docker --memory=4096 --cpus=2

# Enable required addons
minikube addons enable ingress
minikube addons enable metrics-server
```

#### 2. Build Docker Image
```bash
# Use Minikube's Docker daemon
eval $(minikube docker-env)

# Build the image
docker build -t emotibot:latest .
```

#### 3. Update Secrets
```bash
# Get your Gemini API key from: https://makersuite.google.com/app/apikey
# Encode it to base64
echo -n "your_actual_api_key" | base64

# Update kubernetes/secrets.yaml with the encoded value
```

#### 4. Deploy to Kubernetes
```bash
cd kubernetes

# Apply in order
kubectl apply -f secrets.yaml
kubectl apply -f postgres-pvc.yaml
kubectl apply -f postgres-deployment.yaml
kubectl apply -f postgres-service.yaml

# Wait for PostgreSQL
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s

# Deploy EmotiBot
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml

# Wait for EmotiBot
kubectl wait --for=condition=ready pod -l app=emotibot --timeout=300s
```

## 🌐 Accessing EmotiBot

### Get Access Information
```bash
# Get Minikube IP
MINIKUBE_IP=$(minikube ip)

# Get Ingress port
INGRESS_PORT=$(kubectl get service ingress-nginx-controller -n ingress-nginx -o jsonpath='{.spec.ports[?(@.name=="http")].nodePort}')

echo "Access URL: http://${MINIKUBE_IP}:${INGRESS_PORT}"
```

### Access Methods

#### 1. Direct IP Access
```bash
# Open in browser
http://<MINIKUBE_IP>:<INGRESS_PORT>
```

#### 2. Host-based Access (Optional)
```bash
# Add to /etc/hosts (Linux/Mac)
echo "$(minikube ip) emotibot.local" | sudo tee -a /etc/hosts

# Add to hosts file (Windows - run as Administrator)
echo <MINIKUBE_IP> emotibot.local >> C:\Windows\System32\drivers\etc\hosts

# Then access via
http://emotibot.local
```

## 🔧 Management Commands

### Viewing Resources
```bash
# View all pods
kubectl get pods

# View services
kubectl get services

# View ingress
kubectl get ingress

# View persistent volumes
kubectl get pv,pvc
```

### Monitoring
```bash
# View EmotiBot logs
kubectl logs -l app=emotibot -f

# View PostgreSQL logs
kubectl logs -l app=postgres -f

# Access Kubernetes dashboard
minikube dashboard
```

### Scaling
```bash
# Scale EmotiBot replicas
kubectl scale deployment emotibot --replicas=3

# Check status
kubectl get deployment emotibot
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Minikube Won't Start
```bash
# Check Docker is running
docker info

# Delete and recreate cluster
minikube delete
minikube start --driver=docker --memory=4096 --cpus=2
```

#### 2. Image Not Found
```bash
# Ensure you're using Minikube's Docker daemon
eval $(minikube docker-env)

# Rebuild image
docker build -t emotibot:latest .

# Verify image exists
docker images | grep emotibot
```

#### 3. Pods Not Starting
```bash
# Check pod status
kubectl describe pod -l app=emotibot

# Check events
kubectl get events --sort-by=.metadata.creationTimestamp

# Check resource usage
kubectl top nodes
kubectl top pods
```

#### 4. WebSocket Connection Issues
```bash
# Check ingress configuration
kubectl describe ingress emotibot-ingress

# Verify service endpoints
kubectl get endpoints

# Test direct pod access
kubectl port-forward deployment/emotibot 8080:5001
# Then access http://localhost:8080
```

#### 5. Database Connection Issues
```bash
# Check PostgreSQL status
kubectl get pods -l app=postgres

# Test database connection
kubectl exec -it deployment/postgres -- psql -U emotibot -d emotibotdb -c "SELECT 1;"

# Check database logs
kubectl logs -l app=postgres
```

### Resource Issues
```bash
# Check resource usage
kubectl top nodes
kubectl top pods

# Increase Minikube resources
minikube stop
minikube start --driver=docker --memory=6144 --cpus=3
```

## 🧹 Cleanup

### Remove EmotiBot
```bash
# Delete all resources
kubectl delete -f kubernetes/

# Or delete specific components
kubectl delete deployment emotibot
kubectl delete service emotibot
kubectl delete ingress emotibot-ingress
```

### Stop Minikube
```bash
# Stop cluster
minikube stop

# Delete cluster (removes all data)
minikube delete
```

## 📊 Monitoring & Metrics

### Built-in Monitoring
```bash
# Access Kubernetes dashboard
minikube dashboard

# View metrics
kubectl top nodes
kubectl top pods
```

### Application Metrics
- **Health Check**: `http://<MINIKUBE_IP>:<PORT>/health`
- **Prometheus Metrics**: `http://<MINIKUBE_IP>:<PORT>/metrics`

### Logs
```bash
# Stream all EmotiBot logs
kubectl logs -l app=emotibot -f --tail=100

# View specific pod logs
kubectl logs <pod-name> -f
```

## 🔒 Security Notes

### Development vs Production
- Current setup uses placeholder secrets
- In production, use proper secret management
- Enable RBAC and network policies
- Use TLS/SSL certificates

### Updating Secrets
```bash
# Create new secret
kubectl create secret generic emotibot-secrets \
  --from-literal=gemini-api-key="your_api_key" \
  --from-literal=secret-key="your_secret_key" \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart deployment to pick up new secrets
kubectl rollout restart deployment emotibot
```

## 🎯 Features Tested

✅ **WebSocket Support** - Real-time emotion analysis
✅ **Database Persistence** - PostgreSQL with PVC
✅ **Health Checks** - Kubernetes probes
✅ **Horizontal Scaling** - Multiple replicas
✅ **Service Discovery** - Internal DNS
✅ **Ingress Routing** - External access
✅ **Resource Management** - CPU/Memory limits
✅ **Rolling Updates** - Zero-downtime deployments

## 🚀 Next Steps

1. **Test WebSocket functionality** in the browser
2. **Scale the deployment** to multiple replicas
3. **Monitor resource usage** with `kubectl top`
4. **Experiment with rolling updates**
5. **Try the Kubernetes dashboard**

Your EmotiBot is now running on Kubernetes! 🎉 