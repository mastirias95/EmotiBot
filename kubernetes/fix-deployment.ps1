Write-Host "🔧 Fixing EmotiBot deployment issues..." -ForegroundColor Yellow

# Set namespace
$NAMESPACE = "emotibot-staging"

Write-Host "📋 Creating missing secrets..." -ForegroundColor Cyan

# Generate random passwords and keys
$authDbPassword = "auth_secure_pass_2024"
$convDbPassword = "conv_secure_pass_2024"
$secretKey = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((New-Guid).ToString()))
$jwtSecretKey = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((New-Guid).ToString()))
$serviceSecret = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((New-Guid).ToString()))
$geminiApiKey = if ($env:GEMINI_API_KEY) { $env:GEMINI_API_KEY } else { "your-gemini-api-key-here" }

# Create secrets
kubectl create secret generic emotibot-secrets `
  --from-literal=auth-db-password="$authDbPassword" `
  --from-literal=conv-db-password="$convDbPassword" `
  --from-literal=secret-key="$secretKey" `
  --from-literal=jwt-secret-key="$jwtSecretKey" `
  --from-literal=service-secret="$serviceSecret" `
  --from-literal=gemini-api-key="$geminiApiKey" `
  --namespace=$NAMESPACE `
  --dry-run=client -o yaml | kubectl apply -f -

Write-Host "🚀 Applying frontend configuration..." -ForegroundColor Green
kubectl apply -f frontend-config.yaml -n $NAMESPACE

Write-Host "🔄 Redeploying services with fixes..." -ForegroundColor Green
kubectl apply -f deployment-microservices.yaml -n $NAMESPACE

Write-Host "⏳ Waiting for deployments to stabilize..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "🔍 Checking deployment status..." -ForegroundColor Cyan
kubectl get deployments -n $NAMESPACE

Write-Host "📊 Checking pod status..." -ForegroundColor Cyan
kubectl get pods -n $NAMESPACE

Write-Host "🌐 Getting service endpoints..." -ForegroundColor Cyan
kubectl get services -n $NAMESPACE

Write-Host "🏥 Testing Kong health..." -ForegroundColor Magenta
$KONG_IP = kubectl get service emotibot-api-gateway -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

if ($KONG_IP) {
    Write-Host "Kong LoadBalancer IP: $KONG_IP" -ForegroundColor Green
    Write-Host "Testing Kong proxy..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "http://$KONG_IP:8000/" -Method Head -TimeoutSec 10
        Write-Host "Kong proxy is responding: $($response.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "Kong proxy test failed: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host "Testing Kong admin..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "http://$KONG_IP:8001/" -Method Head -TimeoutSec 10
        Write-Host "Kong admin is responding: $($response.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "Kong admin test failed: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "LoadBalancer IP not yet assigned" -ForegroundColor Yellow
}

Write-Host "✅ Deployment fix script completed!" -ForegroundColor Green
Write-Host "🌐 Access your application at: http://$KONG_IP" -ForegroundColor Cyan
Write-Host "Kong Admin API: http://$KONG_IP:8001" -ForegroundColor Cyan 