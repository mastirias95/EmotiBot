# 🚀 GitHub Actions CI/CD Setup Guide

## ✅ Step 1: Workflow Files (COMPLETED)
✅ **GitHub Actions workflow files have been created and pushed to your repository.**

The following workflows are now available:
- **`ci.yml`** - Continuous Integration (testing & building)
- **`cd-staging.yml`** - Staging deployment
- **`cd-production.yml`** - Production deployment

## 🔧 Step 2: Configure GitHub Secrets

### **2.1 Navigate to GitHub Secrets**
1. Go to your GitHub repository: `https://github.com/mastirias95/EmotiBot`
2. Click **Settings** (top menu)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**

### **2.2 Add Required Secrets**

#### **Essential Secrets (Required for CI/CD):**
```bash
# Application Secrets
SECRET_KEY=your-secret-key-here-256-chars
JWT_SECRET_KEY=your-jwt-secret-key-here-256-chars
SERVICE_SECRET=your-service-secret-key-here-256-chars
GEMINI_API_KEY=your-gemini-api-key-here

# Database Passwords
AUTH_DB_PASSWORD=your-auth-db-password
CONV_DB_PASSWORD=your-conversation-db-password
```

#### **Production Secrets (For Production Deployment):**
```bash
# Production versions (with PROD_ prefix)
PROD_SECRET_KEY=your-production-secret-key-256-chars
PROD_JWT_SECRET_KEY=your-production-jwt-secret-key-256-chars
PROD_SERVICE_SECRET=your-production-service-secret-key-256-chars
PROD_GEMINI_API_KEY=your-production-gemini-api-key

# Production Database Passwords
PROD_AUTH_DB_PASSWORD=your-production-auth-db-password
PROD_CONV_DB_PASSWORD=your-production-conversation-db-password
```

### **2.3 Generate Secure Keys**

You can generate secure keys using these commands:

```bash
# Generate SECRET_KEY (32 bytes base64)
openssl rand -base64 32

# Generate JWT_SECRET_KEY (32 bytes base64)
openssl rand -base64 32

# Generate SERVICE_SECRET (32 bytes base64)
openssl rand -base64 32

# Generate Database Passwords (16 bytes base64)
openssl rand -base64 16
```

## 🎯 Step 3: Test the CI Pipeline

### **3.1 Trigger CI Pipeline**
The CI pipeline will automatically run when you:
- Push to `main` or `dev` branches
- Create a Pull Request

### **3.2 Test CI Now**
Let's test the CI pipeline:

1. Make a small change to test the pipeline:
```bash
# Add a test commit
echo "# CI/CD Pipeline Active" >> README.md
git add README.md
git commit -m "Test CI/CD pipeline"
git push origin dev
```

2. **Check GitHub Actions:**
   - Go to your repository
   - Click **Actions** tab
   - You should see the "CI - Test & Build" workflow running

### **3.3 What the CI Pipeline Does:**
✅ **Lints all 5 microservices** (auth, emotion, conversation, ai, websocket)  
✅ **Tests service imports** (ensures each service can start)  
✅ **Builds Docker images** for all services  
✅ **Runs integration tests** using your `test-microservices.py`  
✅ **Security scanning** with Trivy  
✅ **Pushes images** to GitHub Container Registry  

## 🏗️ Step 4: Kubernetes Setup (For Deployment)

### **4.1 If You Have Kubernetes Clusters:**

#### **For Staging Deployment:**
1. Get your staging cluster kubeconfig file
2. Base64 encode it:
```bash
cat ~/.kube/config | base64 -w 0
```
3. Add as GitHub secret: `KUBE_CONFIG_STAGING`

#### **For Production Deployment:**
1. Get your production cluster kubeconfig file
2. Base64 encode it:
```bash
cat ~/.kube/config | base64 -w 0
```
3. Add as GitHub secret: `KUBE_CONFIG_PRODUCTION`

### **4.2 If You Don't Have Kubernetes (Alternative Options):**

#### **Option A: Use Docker Compose Deployment**
You can modify the workflows to use Docker Compose instead of Kubernetes:
- Use your existing `docker-compose.microservices.yml`
- Deploy to a VM or cloud instance
- Simpler setup for testing

#### **Option B: Use Minikube for Local Testing**
```bash
# Install Minikube
# Start Minikube
minikube start

# Use existing deployment scripts
cd kubernetes
./deploy-minikube.sh
```

#### **Option C: Cloud Deployment**
Use your existing cloud deployment scripts:
```bash
# For GCP
./deploy-to-cloud.sh gcp

# For AWS
./deploy-to-cloud.sh aws
```

## 🚀 Step 5: Enable Environments (Optional but Recommended)

### **5.1 Create GitHub Environments:**
1. Go to repository **Settings**
2. Click **Environments** in left sidebar
3. Click **New environment**
4. Create two environments:
   - `staging` (for automatic staging deployments)
   - `production` (for manual production deployments with approval)

### **5.2 Configure Environment Protection:**
For the `production` environment:
1. Enable **Required reviewers**
2. Add yourself as a reviewer
3. Enable **Wait timer** (optional, e.g., 5 minutes)

## 🧪 Step 6: Test the Complete Pipeline

### **6.1 Test CI Pipeline (Automatic):**
```bash
# Make a change and push to dev
git checkout dev
echo "Testing CI pipeline" >> test-file.txt
git add test-file.txt
git commit -m "Test CI pipeline"
git push origin dev
```

### **6.2 Test Staging Deployment (When you merge to main):**
```bash
# Create PR from dev to main
git checkout main
git merge dev
git push origin main
```
This will trigger staging deployment automatically.

### **6.3 Test Production Deployment (Manual):**
1. Go to GitHub **Actions** tab
2. Click **CD - Deploy to Production**
3. Click **Run workflow**
4. Fill in:
   - Version: `main` (or specific tag)
   - Confirmation: `PRODUCTION`
5. Click **Run workflow**

## 📊 Step 7: Monitor Your Pipeline

### **7.1 View Pipeline Status:**
- **GitHub Actions tab** - See all workflow runs
- **Repository badges** (optional) - Add status badges to README

### **7.2 Check Logs:**
- Click on any workflow run
- View logs for each job/step
- Debug any failures

### **7.3 View Built Images:**
- Go to repository main page
- Click **Packages** in right sidebar
- See all built Docker images

## 🚨 Troubleshooting

### **Common Issues:**

#### **1. Secrets Not Found Error:**
```
Error: Secret GEMINI_API_KEY not found
```
**Solution:** Add the missing secret in GitHub repository settings.

#### **2. Docker Build Failures:**
```
Error: Failed to build Docker image
```
**Solution:** Check the Dockerfile and requirements.txt in each service.

#### **3. Integration Tests Failing:**
```
Error: Service health check failed  
```
**Solution:** Check if services are starting properly and ports are correct.

#### **4. Kubernetes Deployment Failing:**
```
Error: kubectl command not found
```
**Solution:** Add `KUBE_CONFIG_STAGING` or `KUBE_CONFIG_PRODUCTION` secrets.

## 🎯 Next Steps After Setup

### **1. Add Unit Tests (Recommended):**
Create test files for each service:
```bash
# Example for auth service
mkdir -p microservices/auth-service/tests
# Add test_auth_service.py
```

### **2. Set Up Monitoring:**
- Enable Prometheus metrics collection
- Set up Grafana dashboards
- Configure alerting

### **3. Load Testing:**
- Extend `test-microservices.py` for load testing
- Add performance benchmarks

## 📋 Quick Checklist

### **Before First Run:**
- [ ] All secrets added to GitHub
- [ ] `GEMINI_API_KEY` configured
- [ ] Database passwords set
- [ ] Kubernetes config added (if using K8s)

### **After First Successful CI Run:**
- [ ] All 5 Docker images built successfully
- [ ] Integration tests passed
- [ ] No security vulnerabilities found
- [ ] Images pushed to GitHub Container Registry

### **For Production Deployment:**
- [ ] Staging environment tested
- [ ] Production secrets configured
- [ ] Kubernetes production cluster ready
- [ ] Monitoring and alerting configured

---

## 🆘 Need Help?

### **Check These First:**
1. **GitHub Actions logs** - Most detailed error information
2. **Service health endpoints** - `http://localhost:800X/health`
3. **Docker logs** - `docker logs <container-name>`

### **Common Commands:**
```bash
# Check workflow status
gh run list

# View specific workflow run
gh run view <run-id>

# Re-run failed workflow
gh run rerun <run-id>
```

Your CI/CD pipeline is now set up! The next push to your repository will trigger the automated testing and deployment process. 🚀 