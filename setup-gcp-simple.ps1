# EmotiBot GCP Setup Script - Simple PowerShell Version
param(
    [string]$ProjectId = "emotibot-project",
    [string]$GeminiApiKey = ""
)

Write-Host "EmotiBot GCP Setup (Windows)" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan

# Get Gemini API key
if (-not $GeminiApiKey) {
    $GeminiApiKey = Read-Host "Enter your Gemini API Key"
}

# Generate secrets
Write-Host "Generating secure secrets..." -ForegroundColor Yellow
$SecretKey = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes([System.Guid]::NewGuid().ToString()))
$JwtSecretKey = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes([System.Guid]::NewGuid().ToString()))
$ServiceSecret = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes([System.Guid]::NewGuid().ToString()))

# Create environment file
$envContent = @"
# GCP Project Configuration
PROJECT_ID=$ProjectId
REGION=us-central1
ZONE=us-central1-a

# Application Secrets
SECRET_KEY=$SecretKey
JWT_SECRET_KEY=$JwtSecretKey
SERVICE_SECRET=$ServiceSecret
GEMINI_API_KEY=$GeminiApiKey
"@

$envContent | Out-File -FilePath ".env.gcp" -Encoding UTF8

Write-Host "Environment file created: .env.gcp" -ForegroundColor Green
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Go to: https://console.cloud.google.com/projectcreate"
Write-Host "2. Create project with ID: $ProjectId"
Write-Host "3. Enable billing for the project"
Write-Host "4. Follow the manual setup guide below"
Write-Host ""
Write-Host "Manual Setup Guide:" -ForegroundColor Cyan
Write-Host "==================="
Write-Host "1. GKE Cluster: https://console.cloud.google.com/kubernetes/clusters?project=$ProjectId"
Write-Host "2. Databases: https://console.cloud.google.com/sql/instances?project=$ProjectId"
Write-Host "3. Redis: https://console.cloud.google.com/memorystore/redis/instances?project=$ProjectId"
Write-Host ""
Write-Host "GitHub Secrets to add:" -ForegroundColor Magenta
Write-Host "SECRET_KEY: $SecretKey"
Write-Host "JWT_SECRET_KEY: $JwtSecretKey" 
Write-Host "SERVICE_SECRET: $ServiceSecret"
Write-Host "GEMINI_API_KEY: $GeminiApiKey" 