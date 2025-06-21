# 🚀 EmotiBot GCP Setup Script - PowerShell Version
# This script will set up your complete EmotiBot infrastructure on Google Cloud Platform

param(
    [string]$ProjectId = "",
    [string]$GeminiApiKey = ""
)

# Configuration
$Region = "us-central1"
$Zone = "us-central1-a"
$ClusterName = "emotibot-cluster"

Write-Host "=================================="
Write-Host "🤖 EmotiBot GCP Setup (Windows)"
Write-Host "=================================="
Write-Host ""

# Check if gcloud is installed
$gcloudPath = Get-Command gcloud -ErrorAction SilentlyContinue
if (-not $gcloudPath) {
    # Try common installation paths
    $possiblePaths = @(
        "$env:USERPROFILE\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "$env:ProgramFiles\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "$env:ProgramFiles(x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $gcloudPath = $path
            break
        }
    }
    
    if (-not $gcloudPath) {
        Write-Host "❌ gcloud CLI not found!" -ForegroundColor Red
        Write-Host "Please install Google Cloud SDK from: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
        Write-Host "After installation, restart PowerShell and run this script again." -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "✅ Found gcloud at: $gcloudPath" -ForegroundColor Green

# Function to run gcloud commands
function Invoke-Gcloud {
    param([string]$Arguments)
    $cmd = "& `"$gcloudPath`" $Arguments"
    Invoke-Expression $cmd
}

# Get project ID if not provided
if (-not $ProjectId) {
    $ProjectId = Read-Host "Enter your GCP project ID (or press Enter for auto-generated)"
    if (-not $ProjectId) {
        $timestamp = [int][double]::Parse((Get-Date -UFormat %s))
        $ProjectId = "emotibot-$timestamp"
    }
}

# Get Gemini API key if not provided
if (-not $GeminiApiKey) {
    $GeminiApiKey = Read-Host "Enter your Gemini API Key"
    if (-not $GeminiApiKey) {
        Write-Host "❌ Gemini API Key is required!" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "🔧 Configuration:" -ForegroundColor Blue
Write-Host "Project ID: $ProjectId"
Write-Host "Region: $Region"
Write-Host "Zone: $Zone"
Write-Host ""

# Confirm setup
$confirm = Read-Host "Continue with setup? This will create billable resources (~$125-150/month) (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Setup cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "🚀 Starting setup..." -ForegroundColor Green

# Generate secure secrets
Write-Host "📝 Generating secure secrets..." -ForegroundColor Blue
$SecretKey = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes([System.Guid]::NewGuid().ToString()))
$JwtSecretKey = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes([System.Guid]::NewGuid().ToString()))
$ServiceSecret = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes([System.Guid]::NewGuid().ToString()))
$AuthDbPassword = -join ((1..16) | ForEach {Get-Random -input ([char[]]([char]'a'..[char]'z') + ([char]'A'..[char]'Z') + ([char]'0'..[char]'9'))})
$ConvDbPassword = -join ((1..16) | ForEach {Get-Random -input ([char[]]([char]'a'..[char]'z') + ([char]'A'..[char]'Z') + ([char]'0'..[char]'9'))})

Write-Host "✅ Secrets generated!" -ForegroundColor Green

# Set active project
Write-Host "🔧 Setting active project..." -ForegroundColor Blue
try {
    Invoke-Gcloud "config set project $ProjectId"
    Write-Host "✅ Project set to: $ProjectId" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to set project. Make sure the project exists and you have access." -ForegroundColor Red
    Write-Host "Create project manually at: https://console.cloud.google.com/projectcreate" -ForegroundColor Yellow
    exit 1
}

# Enable APIs
Write-Host "🔧 Enabling required APIs..." -ForegroundColor Blue
$apis = @(
    "container.googleapis.com",
    "sqladmin.googleapis.com", 
    "redis.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudresourcemanager.googleapis.com"
)

foreach ($api in $apis) {
    Write-Host "Enabling $api..."
    try {
        Invoke-Gcloud "services enable $api --quiet"
    } catch {
        Write-Host "⚠️ Warning: Failed to enable $api" -ForegroundColor Yellow
    }
}
Write-Host "✅ APIs enabled!" -ForegroundColor Green

# Create container registry
Write-Host "🔧 Setting up container registry..." -ForegroundColor Blue
try {
    Invoke-Gcloud "artifacts repositories create emotibot-repo --repository-format=docker --location=$Region --quiet"
    Invoke-Gcloud "auth configure-docker $Region-docker.pkg.dev --quiet"
    Write-Host "✅ Container registry ready!" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Container registry might already exist or failed to create" -ForegroundColor Yellow
}

# Create service account
Write-Host "🔧 Creating service account..." -ForegroundColor Blue
try {
    Invoke-Gcloud "iam service-accounts create github-actions --display-name=`"GitHub Actions Service Account`" --quiet"
    
    $saEmail = (Invoke-Gcloud "iam service-accounts list --filter=`"displayName:GitHub Actions Service Account`" --format=`"value(email)`"").Trim()
    
    # Grant permissions
    Invoke-Gcloud "projects add-iam-policy-binding $ProjectId --member=`"serviceAccount:$saEmail`" --role=`"roles/container.developer`" --quiet"
    Invoke-Gcloud "projects add-iam-policy-binding $ProjectId --member=`"serviceAccount:$saEmail`" --role=`"roles/artifactregistry.writer`" --quiet"
    Invoke-Gcloud "projects add-iam-policy-binding $ProjectId --member=`"serviceAccount:$saEmail`" --role=`"roles/container.clusterViewer`" --quiet"
    
    # Create service account key
    Invoke-Gcloud "iam service-accounts keys create github-actions-key.json --iam-account=$saEmail --quiet"
    
    Write-Host "✅ Service account created!" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Service account creation failed or already exists" -ForegroundColor Yellow
}

# Create environment file with what we have so far
$envContent = @"
# GCP Project Configuration
PROJECT_ID=$ProjectId
REGION=$Region
ZONE=$Zone
CLUSTER_NAME=$ClusterName

# Application Secrets
SECRET_KEY=$SecretKey
JWT_SECRET_KEY=$JwtSecretKey
SERVICE_SECRET=$ServiceSecret
GEMINI_API_KEY=$GeminiApiKey

# Database Passwords
AUTH_DB_PASSWORD=$AuthDbPassword
CONV_DB_PASSWORD=$ConvDbPassword

# Note: Database URLs will be added after infrastructure is created
"@

$envContent | Out-File -FilePath ".env.gcp" -Encoding UTF8
Write-Host "✅ Environment file created: .env.gcp" -ForegroundColor Green

# Show next steps
Write-Host ""
Write-Host "🎉 Basic setup completed!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. 🌐 Create GKE cluster manually (this takes 5-10 minutes):"
Write-Host "   Visit: https://console.cloud.google.com/kubernetes/clusters?project=$ProjectId"
Write-Host "   Click 'Create' → 'GKE Standard'"
Write-Host "   Name: $ClusterName"
Write-Host "   Zone: $Zone"
Write-Host "   Node pool: e2-standard-2, 3 nodes"
Write-Host ""
Write-Host "2. 🗄️ Create databases manually:"
Write-Host "   Visit: https://console.cloud.google.com/sql/instances?project=$ProjectId"
Write-Host "   Create two PostgreSQL 13 instances:"
Write-Host "   - emotibot-auth-db (db-f1-micro)"
Write-Host "   - emotibot-conversation-db (db-f1-micro)"
Write-Host ""
Write-Host "3. 🔴 Create Redis cache:"
Write-Host "   Visit: https://console.cloud.google.com/memorystore/redis/instances?project=$ProjectId"
Write-Host "   Create instance: emotibot-redis (1GB, $Region)"
Write-Host ""
Write-Host "4. 🔐 Add GitHub secrets:"
if (Test-Path "github-actions-key.json") {
    $serviceAccountKey = Get-Content "github-actions-key.json" | ConvertTo-Json -Compress
    Write-Host "   GCP_SA_KEY: $serviceAccountKey"
} else {
    Write-Host "   GCP_SA_KEY: (Create service account key manually)"
}
Write-Host "   SECRET_KEY: $SecretKey"
Write-Host "   JWT_SECRET_KEY: $JwtSecretKey"
Write-Host "   SERVICE_SECRET: $ServiceSecret"
Write-Host "   GEMINI_API_KEY: $GeminiApiKey"
Write-Host ""
Write-Host "5. 🚀 Deploy your application:"
Write-Host "   Push to main branch or manually trigger the CD workflow"
Write-Host ""
Write-Host "💾 Files created:" -ForegroundColor Blue
Write-Host "• .env.gcp - Environment configuration"
if (Test-Path "github-actions-key.json") {
    Write-Host "• github-actions-key.json - Service account key"
}
Write-Host ""
Write-Host "🌐 GCP Console: https://console.cloud.google.com/?project=$ProjectId" -ForegroundColor Cyan
Write-Host ""
Write-Host "Your EmotiBot setup is ready for the next steps! 🤖✨" -ForegroundColor Green 