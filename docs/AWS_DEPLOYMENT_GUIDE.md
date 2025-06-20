# EmotiBot AWS Deployment Guide

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Docker** installed locally
4. **kubectl** installed locally
5. **eksctl** installed locally

## Step 1: Initial AWS Setup

```bash
# Set environment variables
export AWS_REGION="us-east-1"
export CLUSTER_NAME="emotibot-cluster"
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

## Step 2: Create EKS Cluster

```bash
# Create EKS cluster using eksctl
eksctl create cluster \
    --name $CLUSTER_NAME \
    --region $AWS_REGION \
    --nodes 3 \
    --nodes-min 2 \
    --nodes-max 10 \
    --node-type t3.medium \
    --managed

# Update kubeconfig
aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME
```

## Step 3: Set Up RDS Databases

```bash
# Create DB subnet group
aws rds create-db-subnet-group \
    --db-subnet-group-name emotibot-subnet-group \
    --db-subnet-group-description "Subnet group for EmotiBot databases" \
    --subnet-ids subnet-xxx subnet-yyy  # Replace with your subnet IDs

# Create PostgreSQL instance for auth service
aws rds create-db-instance \
    --db-instance-identifier emotibot-auth-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 13.7 \
    --allocated-storage 20 \
    --db-name authdb \
    --master-username auth_user \
    --master-user-password "SECURE_PASSWORD_1" \
    --db-subnet-group-name emotibot-subnet-group \
    --vpc-security-group-ids sg-xxx  # Replace with your security group

# Create PostgreSQL instance for conversation service
aws rds create-db-instance \
    --db-instance-identifier emotibot-conversation-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 13.7 \
    --allocated-storage 20 \
    --db-name conversationdb \
    --master-username conv_user \
    --master-user-password "SECURE_PASSWORD_2" \
    --db-subnet-group-name emotibot-subnet-group \
    --vpc-security-group-ids sg-xxx  # Replace with your security group
```

## Step 4: Set Up ElastiCache Redis

```bash
# Create Redis subnet group
aws elasticache create-cache-subnet-group \
    --cache-subnet-group-name emotibot-redis-subnet-group \
    --cache-subnet-group-description "Subnet group for EmotiBot Redis" \
    --subnet-ids subnet-xxx subnet-yyy  # Replace with your subnet IDs

# Create Redis cluster
aws elasticache create-cache-cluster \
    --cache-cluster-id emotibot-redis \
    --cache-node-type cache.t3.micro \
    --engine redis \
    --num-cache-nodes 1 \
    --cache-subnet-group-name emotibot-redis-subnet-group \
    --security-group-ids sg-xxx  # Replace with your security group
```

## Step 5: Set Up ECR (Container Registry)

```bash
# Create ECR repositories for each service
aws ecr create-repository --repository-name emotibot/auth-service
aws ecr create-repository --repository-name emotibot/emotion-service
aws ecr create-repository --repository-name emotibot/conversation-service
aws ecr create-repository --repository-name emotibot/ai-service
aws ecr create-repository --repository-name emotibot/websocket-service

# Get login token for Docker
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

## Step 6: Build and Push Docker Images

```bash
# Set registry path
export ECR_REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

cd microservices

# Build and push each service
services=("auth-service" "emotion-service" "conversation-service" "ai-service" "websocket-service")

for service in "${services[@]}"; do
    echo "Building and pushing $service..."
    docker build -t $service ./$service
    docker tag $service:latest $ECR_REGISTRY/emotibot/$service:latest
    docker push $ECR_REGISTRY/emotibot/$service:latest
done
```

## Step 7: Configure Kubernetes Secrets

```bash
# Get database endpoints
AUTH_DB_ENDPOINT=$(aws rds describe-db-instances --db-instance-identifier emotibot-auth-db --query 'DBInstances[0].Endpoint.Address' --output text)
CONV_DB_ENDPOINT=$(aws rds describe-db-instances --db-instance-identifier emotibot-conversation-db --query 'DBInstances[0].Endpoint.Address' --output text)
REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters --cache-cluster-id emotibot-redis --show-cache-node-info --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' --output text)

# Create Kubernetes secrets
kubectl create secret generic emotibot-secrets \
    --from-literal=auth-database-url="postgresql://auth_user:SECURE_PASSWORD_1@${AUTH_DB_ENDPOINT}:5432/authdb" \
    --from-literal=conversation-database-url="postgresql://conv_user:SECURE_PASSWORD_2@${CONV_DB_ENDPOINT}:5432/conversationdb" \
    --from-literal=redis-host="${REDIS_ENDPOINT}" \
    --from-literal=secret-key="YOUR_SECRET_KEY_HERE" \
    --from-literal=jwt-secret-key="YOUR_JWT_SECRET_KEY_HERE" \
    --from-literal=service-secret="YOUR_SERVICE_SECRET_HERE" \
    --from-literal=gemini-api-key="YOUR_GEMINI_API_KEY_HERE"
```

## Step 8: Update Kubernetes Manifests for AWS

Create `kubernetes/deployment-aws.yaml`:

```yaml
# Update image references to use ECR
# Example for auth-service:
spec:
  containers:
  - name: auth-service
    image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/emotibot/auth-service:latest
    imagePullPolicy: Always
```

## Step 9: Deploy to EKS

```bash
# Deploy all services
kubectl apply -f ../kubernetes/deployment-aws.yaml
kubectl apply -f ../kubernetes/services-microservices.yaml

# Check deployment status
kubectl get pods
kubectl get services
```

## Step 10: Set Up Application Load Balancer

```bash
# Install AWS Load Balancer Controller
curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.4.4/docs/install/iam_policy.json

aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://iam_policy.json

# Create service account
eksctl create iamserviceaccount \
  --cluster=$CLUSTER_NAME \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --role-name "AmazonEKSLoadBalancerControllerRole" \
  --attach-policy-arn=arn:aws:iam::$AWS_ACCOUNT_ID:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve

# Install the controller
kubectl apply -k https://github.com/aws/eks-charts/stable/aws-load-balancer-controller/crds
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=$CLUSTER_NAME \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

## Step 11: Configure SSL and Domain

```bash
# Request SSL certificate via ACM
aws acm request-certificate \
    --domain-name yourdomain.com \
    --domain-name www.yourdomain.com \
    --validation-method DNS \
    --region $AWS_REGION
```

## Cost Estimation (Monthly)

- **EKS Cluster**: $73 (control plane) + ~$150-300 (nodes)
- **RDS (2 instances)**: $30-60
- **ElastiCache Redis**: $15-30
- **Application Load Balancer**: $20
- **Data Transfer**: $10-50
- **Total**: ~$298-533/month

## Monitoring and Logging

```bash
# Install CloudWatch Container Insights
curl https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml | sed "s/{{cluster_name}}/$CLUSTER_NAME/;s/{{region_name}}/$AWS_REGION/" | kubectl apply -f -
```

## Security Best Practices

1. **IAM Roles**: Use least-privilege IAM roles
2. **VPC**: Deploy in private subnets
3. **Security Groups**: Restrict traffic appropriately
4. **Secrets**: Use AWS Secrets Manager for sensitive data
5. **Network Policies**: Implement Kubernetes network policies

## Troubleshooting

```bash
# Check EKS cluster status
aws eks describe-cluster --name $CLUSTER_NAME

# Check node status
kubectl get nodes

# Check pod logs
kubectl logs -l app=emotibot-auth-service

# Check AWS resources
aws rds describe-db-instances
aws elasticache describe-cache-clusters
``` 