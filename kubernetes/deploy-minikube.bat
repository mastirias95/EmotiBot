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
    echo ⚠ If you see a driver conflict error, we'll delete and recreate the cluster
    minikube start --driver=docker --memory=4096 --cpus=2
    if errorlevel 1 (
        echo ⚠ Minikube start failed, likely due to driver conflict. Deleting existing cluster...
        minikube delete
        echo ℹ Creating new Minikube cluster with Docker driver...
        minikube start --driver=docker --memory=4096 --cpus=2
        if errorlevel 1 (
            echo ❌ Failed to start Minikube. Please check your Docker installation.
            pause
            exit /b 1
        )
    )
    echo ✓ Minikube started
) else (
    echo ✓ Minikube is already running
)

REM Enable required addons
echo ℹ Enabling Minikube addons...
minikube addons enable ingress
if errorlevel 1 (
    echo ❌ Failed to enable ingress addon. Minikube may not be running properly.
    minikube status
    pause
    exit /b 1
)
minikube addons enable metrics-server
if errorlevel 1 (
    echo ❌ Failed to enable metrics-server addon. Minikube may not be running properly.
    minikube status
    pause
    exit /b 1
)
echo ✓ Addons enabled

REM Verify Minikube is running properly
echo ℹ Verifying Minikube cluster...
kubectl cluster-info >nul 2>&1
if errorlevel 1 (
    echo ❌ Cannot connect to Kubernetes cluster. Minikube may not be running properly.
    echo ℹ Checking Minikube status...
    minikube status
    pause
    exit /b 1
)
echo ✓ Kubernetes cluster is accessible

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

REM Get Minikube IP with error checking
FOR /f %%i IN ('minikube ip 2^>nul') DO SET MINIKUBE_IP=%%i

REM Check if we got a valid IP
if "%MINIKUBE_IP%"=="" (
    echo ⚠ Could not get Minikube IP. Checking if Minikube is running...
    minikube status
    echo ❌ Please ensure Minikube is running properly and try again.
    pause
    exit /b 1
)

REM Validate IP format (basic check)
echo %MINIKUBE_IP% | findstr /R "^[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$" >nul
if errorlevel 1 (
    echo ⚠ Invalid IP address received: %MINIKUBE_IP%
    echo ℹ This might be due to encoding issues. Trying alternative method...
    
    REM Try alternative method to get IP
    FOR /f "tokens=2 delims=:" %%i IN ('minikube status ^| findstr "host:"') DO SET MINIKUBE_IP=%%i
    SET MINIKUBE_IP=%MINIKUBE_IP: =%
    
    if "%MINIKUBE_IP%"=="" (
        echo ❌ Could not retrieve valid Minikube IP. Please run 'minikube ip' manually.
        pause
        exit /b 1
    )
)

echo ℹ Minikube IP: %MINIKUBE_IP%

REM For Minikube with ingress addon, the application is accessible on port 80
SET INGRESS_PORT=80

echo.
echo 🎉 EmotiBot deployed successfully!
echo ==================================
echo.
echo Access URLs:
echo • Direct IP with Ingress: http://%MINIKUBE_IP%:%INGRESS_PORT%
echo • With host: http://emotibot.local (add to hosts file)
echo.
echo ⚠ IMPORTANT: For ingress to work, you need to run 'minikube tunnel' as Administrator
echo   in a separate terminal window. The tunnel must stay running.
echo.
echo Alternative: Use NodePort service (no tunnel needed)
set /p useNodePort="Would you like to deploy NodePort service for easier access? (y/N): "
if /i "%useNodePort%"=="y" (
    echo ℹ Deploying NodePort service...
    kubectl apply -f service-nodeport.yaml
    echo ✓ NodePort service deployed
    echo • NodePort URL: http://%MINIKUBE_IP%:30080
    echo.
)
echo.
echo To add to hosts file (run as Administrator):
echo echo %MINIKUBE_IP% emotibot.local ^>^> C:\Windows\System32\drivers\etc\hosts
echo.
echo Useful commands:
echo • View pods: kubectl get pods
echo • View services: kubectl get services
echo • View logs: kubectl logs -l app=emotibot -f
echo • Access dashboard: minikube dashboard
echo • Enable tunnel: minikube tunnel (run as Administrator)
echo • Stop: kubectl delete -f .
echo.

REM Optional: Open in browser
set /p open="Open EmotiBot in browser? (y/N): "
if /i "%open%"=="y" (
    echo ℹ Opening browser...
    if /i "%useNodePort%"=="y" (
        echo ℹ Opening NodePort URL (should work immediately)
        start http://%MINIKUBE_IP%:30080
    ) else (
        echo ⚠ Opening ingress URL - make sure 'minikube tunnel' is running as Administrator
        start http://%MINIKUBE_IP%:%INGRESS_PORT%
    )
)

pause 