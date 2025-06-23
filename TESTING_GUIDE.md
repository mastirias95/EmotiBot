# 🧪 EmotiBot Functionality Testing Guide

## Quick Test Commands

### 1. Frontend Interface Test
```bash
# Test main website
curl -I http://34.52.173.192
# Should return: HTTP/1.1 200 OK

# Check content size (should be ~21KB for full interface)
curl -s http://34.52.173.192 | wc -c
```

### 2. Health Endpoint Test
```bash
curl http://34.52.173.192/health
# Expected: {"status": "healthy", "timestamp": "..."}
```

### 3. Kong API Gateway Test
```bash
curl -I http://35.241.206.85:8000
# Should return: HTTP/1.1 404 Not Found (normal for root path)
```

### 4. Emotion Detection API Test
```bash
curl -X POST http://34.52.173.192/api/emotion/detect \
  -H "Content-Type: application/json" \
  -d '{"text": "I am very happy today!"}'
# Expected: Emotion analysis response with sentiment scores
```

### 5. Authentication API Test
```bash
curl -X POST http://34.52.173.192/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "password123"}'
```

### 6. Kubernetes Pods Status
```bash
kubectl get pods -n emotibot-staging
# All pods should show "Running" status
```

## PowerShell Tests (Windows)

### Frontend Test
```powershell
Invoke-WebRequest -Uri "http://34.52.173.192" -Method Get | Select-Object StatusCode, ContentLength
```

### Health Test
```powershell
Invoke-WebRequest -Uri "http://34.52.173.192/health" -Method Get
```

### Emotion API Test
```powershell
$body = @{ text = "I am very happy today!" } | ConvertTo-Json
Invoke-WebRequest -Uri "http://34.52.173.192/api/emotion/detect" -Method POST -ContentType "application/json" -Body $body
```

## Automated Testing

### Run Python Test Script
```bash
# Using virtual environment
venv\Scripts\python.exe test_emotibot.py

# Or using batch file
test_emotibot.bat
```

## Manual Browser Testing

### 1. Open Frontend
- Navigate to: http://34.52.173.192
- Verify: Full EmotiBot chat interface loads (not just status page)
- Check: Login/Register forms are visible
- Check: Chat input area is present

### 2. Test Chat Interface
- Try typing in chat input
- Verify: Emotion analysis section appears
- Check: WebSocket connection status

### 3. Test Registration
- Click "Register" tab
- Fill in test credentials
- Submit form
- Verify: Success/error message

### 4. Test Login
- Use registered credentials
- Verify: Login success
- Check: Chat functionality unlocks

## Expected Results Summary

### ✅ Working Components
1. **Frontend Interface**: 21,817 bytes interactive HTML
2. **Health Endpoint**: Returns JSON health status
3. **Kong Gateway**: Routes API requests correctly
4. **Emotion Detection**: Processes text without authentication
5. **Database Connections**: Auth service connects to GCP PostgreSQL
6. **Kubernetes Deployment**: All pods running successfully

### 🔧 Configuration Status
- **Authentication**: Bypassed for emotion service (demo mode)
- **Database**: Using external GCP PostgreSQL instances
- **Redis**: Configured for session management
- **API Gateway**: Kong routing all services correctly

### 📊 Service Endpoints
- **Frontend**: http://34.52.173.192
- **Kong Gateway**: http://35.241.206.85:8000
- **Kong Admin**: http://35.241.206.85:8001

### 🗄️ Database Connections
- **Auth DB**: postgresql://postgres:***@34.77.96.235:5432/emotibotdb
- **Conversation DB**: postgresql://postgres:***@34.77.198.214:5432/emotibotdb

## Troubleshooting

### If Frontend Shows Basic Status Page
- Check ConfigMap: `kubectl get configmap frontend-html -n emotibot-staging -o yaml`
- Verify content length is ~21KB not ~4KB

### If APIs Return 404
- Check Kong routes: `curl http://35.241.206.85:8001/routes`
- Restart Kong: `kubectl rollout restart deployment kong -n emotibot-staging`

### If Database Connection Fails
- Check secrets: `kubectl get secret emotibot-secrets -n emotibot-staging -o yaml`
- Verify environment variables in service deployments

### If Pods Not Running
- Check pod status: `kubectl get pods -n emotibot-staging`
- View logs: `kubectl logs <pod-name> -n emotibot-staging`
- Check resources: `kubectl describe pod <pod-name> -n emotibot-staging`

## Performance Testing

### Load Testing with curl
```bash
# Simple load test
for i in {1..10}; do
  curl -s -o /dev/null -w "%{http_code} %{time_total}\n" http://34.52.173.192
done
```

### Concurrent API Testing
```bash
# Test emotion API concurrency
for i in {1..5}; do
  curl -X POST http://34.52.173.192/api/emotion/detect \
    -H "Content-Type: application/json" \
    -d '{"text": "Test message '$i'"}' &
done
wait
```

## Security Testing

### Test Authentication Bypass
```bash
# Should work without auth (demo mode)
curl -X POST http://34.52.173.192/api/emotion/detect \
  -H "Content-Type: application/json" \
  -d '{"text": "Security test"}'
```

### Test CORS Headers
```bash
curl -H "Origin: http://example.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: X-Requested-With" \
  -X OPTIONS http://34.52.173.192/api/emotion/detect
``` 