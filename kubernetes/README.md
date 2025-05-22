# EmotiBot Kubernetes Deployment

This directory contains Kubernetes manifests for deploying EmotiBot to a Kubernetes cluster.

## Prerequisites

- Kubernetes cluster up and running
- kubectl configured to communicate with your cluster
- Docker image for EmotiBot built and pushed to a container registry

## Components

- **deployment.yaml**: Defines the EmotiBot application deployment with 3 replicas
- **service.yaml**: Creates a ClusterIP service for EmotiBot
- **ingress.yaml**: Sets up an Ingress resource for external access with TLS
- **postgres-deployment.yaml**: Deploys PostgreSQL database
- **postgres-service.yaml**: Creates a service for PostgreSQL
- **postgres-pvc.yaml**: Creates a persistent volume claim for PostgreSQL data
- **secrets.yaml**: Defines secret data for the application (replace with real values)
- **hpa.yaml**: Horizontal Pod Autoscaler configuration for scaling based on CPU/memory usage

## Deployment

1. Update `secrets.yaml` with your actual secrets:
   ```bash
   # Example of how to generate base64 encoded secrets
   echo -n "your-actual-secret" | base64
   ```

2. Update the image reference in `deployment.yaml` to point to your image repository.

3. Run the deployment script:
   ```bash
   ./deploy.sh
   ```

   Or apply each manifest manually:
   ```bash
   kubectl apply -f secrets.yaml
   kubectl apply -f postgres-pvc.yaml
   kubectl apply -f postgres-deployment.yaml
   kubectl apply -f postgres-service.yaml
   kubectl apply -f deployment.yaml
   kubectl apply -f service.yaml
   kubectl apply -f ingress.yaml
   kubectl apply -f hpa.yaml
   ```

4. Verify the deployment:
   ```bash
   kubectl get pods
   kubectl get svc
   kubectl get ingress
   ```

## Updating

To update the EmotiBot application:

1. Build and push a new Docker image
2. Update the image tag in `deployment.yaml`
3. Apply the updated deployment:
   ```bash
   kubectl apply -f deployment.yaml
   ```

## Scaling

The application is configured to scale automatically based on CPU and memory usage through the HPA. 
You can manually scale the deployment if needed:

```bash
kubectl scale deployment/emotibot --replicas=5
```

## Cleanup

To remove all resources:

```bash
kubectl delete -f .
``` 