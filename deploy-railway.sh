#!/bin/bash

# Deploy Survey Data API Gateway to Railway
echo "🚀 Deploying Survey Data API Gateway to Railway..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI is not installed. Installing..."
    npm install -g @railway/cli
fi

# Login to Railway (if not already logged in)
echo "🔐 Logging into Railway..."
railway login

# Initialize Railway project (if not already initialized)
if [ ! -f ".railway" ]; then
    echo "📦 Initializing Railway project..."
    railway init
fi

# Set environment variables for production
echo "⚙️ Setting production environment variables..."
railway variables set DATABASE_URL="sqlite:///./survey_data.db"
railway variables set SECRET_KEY=$(openssl rand -base64 32)
railway variables set DEBUG="False"
railway variables set API_TITLE="Survey Data API Gateway"
railway variables set API_VERSION="1.0.0"

# Deploy to Railway
echo "🚀 Deploying to Railway..."
railway up

echo "✅ Deployment completed!"
echo "🌐 Your API will be available at the Railway-provided URL"
echo "📚 Access Swagger docs at: [your-railway-url]/docs"
