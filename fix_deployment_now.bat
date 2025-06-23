@echo off
echo 🔧 Fixing EmotiBot Deployment Issues...

echo.
echo 📝 Step 1: Updating ConfigMaps with new HTML content...
kubectl delete configmap frontend-html -n emotibot-staging --ignore-not-found
kubectl create configmap frontend-html --from-file=microservices/frontend/index.html -n emotibot-staging

echo.
echo 🔄 Step 2: Force restart auth service...
kubectl delete pods -l app=emotibot-auth-service -n emotibot-staging
timeout /t 10 /nobreak

echo.
echo 🔄 Step 3: Force restart frontend...
kubectl delete pods -l app=emotibot-frontend -n emotibot-staging
timeout /t 10 /nobreak

echo.
echo 📊 Step 4: Checking deployment status...
kubectl get pods -n emotibot-staging

echo.
echo ✅ Deployment fix completed!
echo 🌐 Check your application at: http://34.52.173.192/
echo 🔧 API Gateway: http://35.241.206.85:8000/ 