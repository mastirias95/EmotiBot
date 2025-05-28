@echo off
REM EmotiBot Minikube Deployment Script for Windows
REM This script deploys EmotiBot to a local Minikube cluster

echo 🚀 EmotiBot Minikube Deployment
echo ===============================

REM Check if minikube is installed
minikube version >nul 2>&1
if errorlevel 1 (
    echo ❌ Minikube is not installed. Please install it first.
    echo Visit: https://minikube.sigs.k8s.io/docs/start/
    pause
    exit /b 1
)

REM Check if kubectl is installed
kubectl version --client >nul 2>&1
if errorlevel 1 (
    echo ❌ kubectl is not installed. Please install it first.
    pause
    exit /b 1
)

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

REM Start Minikube if not running
echo ℹ Checking Minikube status...
minikube status >nul 2>&1
if errorlevel 1 (
    echo ℹ Starting Minikube...
    minikube start --driver=docker --memory=4096 --cpus=2
    echo ✓ Minikube started
) else (
    echo ✓ Minikube is already running
)

REM Enable required addons
echo ℹ Enabling Minikube addons...
minikube addons enable ingress
minikube addons enable metrics-server
echo ✓ Addons enabled

REM Set Docker environment to use Minikube's Docker daemon
echo ℹ Setting up Docker environment...
FOR /f "tokens=*" %%i IN ('minikube docker-env --shell cmd') DO %%i
echo ✓ Docker environment configured

REM Build the Docker image in Minikube
echo ℹ Building EmotiBot Docker image...
cd ..
docker build -t emotibot:latest .
echo ✓ Docker image built

REM Return to kubernetes directory
cd kubernetes

REM Check if secrets need to be updated
echo ⚠ Please ensure you've updated the Gemini API key in secrets.yaml
echo To update the secret:
echo 1. Get your API key from: https://makersuite.google.com/app/apikey
echo 2. Encode it using online base64 encoder or PowerShell:
echo    [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("your_api_key"))
echo 3. Replace the gemini-api-key value in secrets.yaml
echo.
set /p updated="Have you updated the Gemini API key? (y/N): "
if /i not "%updated%"=="y" (
    echo ⚠ Please update the API key and run the script again
    pause
    exit /b 1
)

REM Apply Kubernetes manifests
echo ℹ Deploying to Kubernetes...

REM Apply secrets first
kubectl apply -f secrets.yaml
echo ✓ Secrets applied

REM Apply PostgreSQL components
kubectl apply -f postgres-pvc.yaml
kubectl apply -f postgres-deployment.yaml
kubectl apply -f postgres-service.yaml
echo ✓ PostgreSQL deployed

REM Wait for PostgreSQL to be ready
echo ℹ Waiting for PostgreSQL to be ready...
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s
echo ✓ PostgreSQL is ready

REM Apply EmotiBot components
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
echo ✓ EmotiBot deployed

REM Wait for EmotiBot to be ready
echo ℹ Waiting for EmotiBot to be ready...
kubectl wait --for=condition=ready pod -l app=emotibot --timeout=300s
echo ✓ EmotiBot is ready

REM Get access information
echo ℹ Getting access information...
FOR /f %%i IN ('minikube ip') DO SET MINIKUBE_IP=%%i
FOR /f %%i IN ('kubectl get service ingress-nginx-controller -n ingress-nginx -o jsonpath^="{.spec.ports[?(@.name==\"http\")].nodePort}"') DO SET INGRESS_PORT=%%i

echo.
echo 🎉 EmotiBot deployed successfully!
echo ==================================
echo.
echo Access URLs:
echo • Direct IP: http://%MINIKUBE_IP%:%INGRESS_PORT%
echo • With host: http://emotibot.local (add to hosts file)
echo.
echo To add to hosts file (run as Administrator):
echo echo %MINIKUBE_IP% emotibot.local ^>^> C:\Windows\System32\drivers\etc\hosts
echo.
echo Useful commands:
echo • View pods: kubectl get pods
echo • View services: kubectl get services
echo • View logs: kubectl logs -l app=emotibot -f
echo • Access dashboard: minikube dashboard
echo • Stop: kubectl delete -f .
echo.

REM Optional: Open in browser
set /p open="Open EmotiBot in browser? (y/N): "
if /i "%open%"=="y" (
    start http://%MINIKUBE_IP%:%INGRESS_PORT%
)

pause 