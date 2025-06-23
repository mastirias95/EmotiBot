#!/bin/bash

echo "🔧 Fixing EmotiBot deployment issues..."

# Set namespace
NAMESPACE="emotibot-staging"

echo "📋 Creating missing secrets..."
kubectl create secret generic emotibot-secrets \
  --from-literal=auth-db-password="auth_secure_pass_2024" \
  --from-literal=conv-db-password="conv_secure_pass_2024" \
  --from-literal=secret-key="$(openssl rand -base64 32)" \
  --from-literal=jwt-secret-key="$(openssl rand -base64 32)" \
  --from-literal=service-secret="$(openssl rand -base64 32)" \
  --from-literal=gemini-api-key="${GEMINI_API_KEY:-your-gemini-api-key-here}" \
  --namespace=$NAMESPACE \
  --dry-run=client -o yaml | kubectl apply -f -

echo "🚀 Applying frontend configuration..."
kubectl apply -f frontend-config.yaml -n $NAMESPACE

echo "🔄 Redeploying services with fixes..."
kubectl apply -f deployment-microservices.yaml -n $NAMESPACE

echo "⏳ Waiting for deployments to stabilize..."
sleep 30

echo "🔍 Checking deployment status..."
kubectl get deployments -n $NAMESPACE

echo "📊 Checking pod status..."
kubectl get pods -n $NAMESPACE

echo "🌐 Getting service endpoints..."
kubectl get services -n $NAMESPACE

echo "🏥 Testing Kong health..."
KONG_IP=$(kubectl get service emotibot-api-gateway -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ ! -z "$KONG_IP" ]; then
    echo "Kong LoadBalancer IP: $KONG_IP"
    echo "Testing Kong proxy..."
    curl -I http://$KONG_IP:8000/ || echo "Kong proxy test failed"
    echo "Testing Kong admin..."
    curl -I http://$KONG_IP:8001/ || echo "Kong admin test failed"
else
    echo "LoadBalancer IP not yet assigned"
fi

echo "✅ Deployment fix script completed!"
echo "🌐 Access your application at: http://$KONG_IP"
echo "🔧 Kong Admin API: http://$KONG_IP:8001" 