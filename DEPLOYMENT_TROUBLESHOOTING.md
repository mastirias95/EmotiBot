# EmotiBot Deployment Troubleshooting Guide

## 🚨 Current Issues Identified

### 1. **Kong API Gateway Not Accessible**
**Problem**: Ports 8000 and 8001 return "Connection refused"
**Root Cause**: Missing infrastructure components (Redis, PostgreSQL) causing Kong to fail initialization

### 2. **Database Connection Failures**
**Problem**: Services trying to connect to external PostgreSQL databases that timeout
**Root Cause**: External database IPs (34.77.198.214) are not accessible or configured incorrectly

### 3. **Missing Redis Service**
**Problem**: All services failing to connect to Redis
**Root Cause**: Redis deployment was missing from Kubernetes configuration

### 4. **Multiple Pod Versions**
**Problem**: Multiple versions of same service running simultaneously
**Root Cause**: Deployment updates creating new ReplicaSets without terminating old ones

## 🔧 Comprehensive Fix Applied

### Fixed Components:

1. **✅ Added Redis Deployment**
   - Redis 7 Alpine with persistent storage
   - Proper health checks and resource limits
   - Connected to all microservices

2. **✅ Added Local PostgreSQL Databases**
   - Separate databases for Auth and Conversation services
   - Proper secret management for passwords
   - Health checks and persistent storage

3. **✅ Fixed Database Connection Strings**
   - Updated from external IPs to local service names
   - Proper environment variable configuration
   - Secure password management via secrets

4. **✅ Enhanced Kong Configuration**
   - Added proper logging configuration
   - Improved health checks
   - Better error handling

5. **✅ Added Frontend Service**
   - Nginx-based frontend with proper routing
   - API proxy configuration
   - Beautiful status page

## 🚀 How to Apply the Fix

### Option 1: Run the Fix Script (Recommended)

```bash
# Navigate to kubernetes directory
cd kubernetes

# Make script executable (Linux/Mac)
chmod +x fix-deployment.sh
./fix-deployment.sh

# Or run PowerShell script (Windows)
.\fix-deployment.ps1
```

### Option 2: Manual Application

```bash
# 1. Apply frontend configuration
kubectl apply -f kubernetes/frontend-config.yaml -n emotibot-staging

# 2. Apply updated deployments
kubectl apply -f kubernetes/deployment-microservices.yaml -n emotibot-staging

# 3. Update secrets (replace with your actual Gemini API key)
kubectl create secret generic emotibot-secrets \
  --from-literal=auth-db-password="auth_secure_pass_2024" \
  --from-literal=conv-db-password="conv_secure_pass_2024" \
  --from-literal=secret-key="$(openssl rand -base64 32)" \
  --from-literal=jwt-secret-key="$(openssl rand -base64 32)" \
  --from-literal=service-secret="$(openssl rand -base64 32)" \
  --from-literal=gemini-api-key="YOUR_ACTUAL_GEMINI_API_KEY" \
  --namespace=emotibot-staging \
  --dry-run=client -o yaml | kubectl apply -f -
```

## 📊 Expected Results After Fix

### Deployment Status
```
NAME                            READY   UP-TO-DATE   AVAILABLE
emotibot-ai-service             2/2     2            2
emotibot-api-gateway            1/1     1            1
emotibot-auth-service           2/2     2            2
emotibot-conversation-service   2/2     2            2
emotibot-emotion-service        2/2     2            2
emotibot-websocket-service      2/2     2            2
emotibot-frontend               1/1     1            1
redis                           1/1     1            1
auth-db                         1/1     1            1
conversation-db                 1/1     1            1
```

### Service Accessibility
- **Frontend**: http://35.241.206.85 (LoadBalancer IP)
- **Kong Proxy**: http://35.241.206.85:8000
- **Kong Admin**: http://35.241.206.85:8001
- **API Endpoints**: All accessible through Kong routing

## 🔍 Verification Steps

### 1. Check Pod Health
```bash
kubectl get pods -n emotibot-staging
# All pods should show "Running" status with 1/1 or 2/2 ready
```

### 2. Test Kong Connectivity
```bash
# Test Kong proxy
curl -I http://35.241.206.85:8000/

# Test Kong admin
curl -I http://35.241.206.85:8001/
```

### 3. Test API Endpoints
```bash
# Test health endpoints through Kong
curl http://35.241.206.85:8000/auth/health
curl http://35.241.206.85:8000/emotion/health
curl http://35.241.206.85:8000/conversation/health
curl http://35.241.206.85:8000/ai/health
curl http://35.241.206.85:8000/websocket/health
```

### 4. Check Database Connectivity
```bash
# Check if services can connect to databases
kubectl logs -n emotibot-staging deployment/emotibot-auth-service
kubectl logs -n emotibot-staging deployment/emotibot-conversation-service
```

## 🐛 Common Issues and Solutions

### Issue: "Connection refused" on Kong ports
**Solution**: Check if Kong pod is running and ConfigMap is properly mounted
```bash
kubectl describe pod -n emotibot-staging -l app=emotibot-api-gateway
kubectl logs -n emotibot-staging -l app=emotibot-api-gateway
```

### Issue: Database connection timeouts
**Solution**: Verify PostgreSQL pods are running and secrets are correct
```bash
kubectl get pods -n emotibot-staging -l app=auth-db
kubectl get pods -n emotibot-staging -l app=conversation-db
kubectl get secrets -n emotibot-staging emotibot-secrets -o yaml
```

### Issue: Redis connection failures
**Solution**: Check Redis pod status and service connectivity
```bash
kubectl get pods -n emotibot-staging -l app=redis
kubectl exec -it -n emotibot-staging deployment/redis -- redis-cli ping
```

### Issue: Services stuck in "ContainerCreating"
**Solution**: Check for resource constraints or image pull issues
```bash
kubectl describe pods -n emotibot-staging
kubectl get nodes
```

## 📈 Performance Optimization

### Resource Allocation
- **Kong**: 300m CPU, 256Mi RAM
- **Databases**: 500m CPU, 512Mi RAM each
- **Microservices**: 500m CPU, 512Mi RAM each
- **Redis**: 200m CPU, 256Mi RAM

### Scaling Recommendations
```bash
# Scale services based on load
kubectl scale deployment emotibot-auth-service --replicas=3 -n emotibot-staging
kubectl scale deployment emotibot-conversation-service --replicas=3 -n emotibot-staging
```

## 🔒 Security Considerations

1. **Secrets Management**: All sensitive data stored in Kubernetes secrets
2. **Network Policies**: Consider implementing network policies for service isolation
3. **RBAC**: Ensure proper role-based access control
4. **TLS**: Consider adding TLS termination at Kong level

## 📞 Support

If issues persist after applying these fixes:

1. **Check logs**: `kubectl logs -n emotibot-staging <pod-name>`
2. **Describe resources**: `kubectl describe <resource-type> <resource-name> -n emotibot-staging`
3. **Check events**: `kubectl get events -n emotibot-staging --sort-by='.lastTimestamp'`

The fix addresses all major issues and should result in a fully functional EmotiBot deployment with all services accessible through the Kong API Gateway. 