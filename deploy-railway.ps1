# Deploy Survey Data API Gateway to Railway
Write-Host "🚀 Deploying Survey Data API Gateway to Railway..." -ForegroundColor Green

# Check if Railway CLI is installed
try {
    railway --version | Out-Null
    Write-Host "✅ Railway CLI found" -ForegroundColor Green
} catch {
    Write-Host "❌ Railway CLI is not installed. Installing..." -ForegroundColor Red
    npm install -g @railway/cli
}

# Login to Railway (if not already logged in)
Write-Host "🔐 Logging into Railway..." -ForegroundColor Yellow
railway login

# Initialize Railway project (if not already initialized)
if (!(Test-Path ".railway")) {
    Write-Host "📦 Initializing Railway project..." -ForegroundColor Yellow
    railway init
}

# Set environment variables for production
Write-Host "⚙️ Setting production environment variables..." -ForegroundColor Yellow
railway variables set DATABASE_URL="sqlite:///./survey_data.db"
$secretKey = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((New-Guid).ToString()))
railway variables set SECRET_KEY="$secretKey"
railway variables set DEBUG="False"
railway variables set API_TITLE="Survey Data API Gateway"
railway variables set API_VERSION="1.0.0"

# Deploy to Railway
Write-Host "🚀 Deploying to Railway..." -ForegroundColor Green
railway up

Write-Host "✅ Deployment completed!" -ForegroundColor Green
Write-Host "🌐 Your API will be available at the Railway-provided URL" -ForegroundColor Cyan
Write-Host "📚 Access Swagger docs at: [your-railway-url]/docs" -ForegroundColor Cyan
