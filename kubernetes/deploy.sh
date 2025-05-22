#!/bin/bash
set -e

# Apply secrets first
kubectl apply -f secrets.yaml

# Apply database resources
kubectl apply -f postgres-pvc.yaml
kubectl apply -f postgres-deployment.yaml
kubectl apply -f postgres-service.yaml

# Wait for postgres to be ready
echo "Waiting for postgres deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/postgres

# Apply application resources
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
kubectl apply -f hpa.yaml

echo "Deployment complete!"
echo "Check status with: kubectl get pods" 