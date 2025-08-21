#!/bin/bash

echo "🚀 Starting NBA/NFL Parlay System in Production Mode"
echo "====================================================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please create .env file with your API keys:"
    echo ""
    echo "THE_ODDS_API_KEY=your_odds_api_key"
    echo "BALLDONTLIE_API_KEY=your_nba_api_key"
    echo "api-football=your_nfl_api_key"
    echo "FIRECRAWL_API_KEY=your_firecrawl_key"
    echo "twitter_key=your_twitter_key"
    echo "APIFY_TOKEN=your_apify_token"
    echo "ENABLE_NFL=true"
    echo "ENABLE_NBA=true"
    exit 1
fi

echo "✅ Found .env file"

# Stop existing container if running
if docker ps -q --filter "name=nba-nfl-production" | grep -q .; then
    echo "🛑 Stopping existing production container..."
    docker stop nba-nfl-production
    docker rm nba-nfl-production
fi

# Start production container with .env file
echo "🚀 Starting production container with your .env file..."
docker run -d \
  --name nba-nfl-production \
  --env-file .env \
  -p 8000:8000 \
  -v "$(pwd)/models:/app/models" \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/logs:/app/logs" \
  --restart unless-stopped \
  nba-nfl-parlay-simple

# Wait for startup
echo "⏳ Waiting for system to start..."
sleep 10

# Check if it's healthy
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Production system is running successfully!"
    echo ""
    echo "🌐 Access Points:"
    echo "   Main API:      http://localhost:8000"
    echo "   Health Check:  http://localhost:8000/health"
    echo "   API Docs:      http://localhost:8000/docs"
    echo ""
    echo "🎯 Your API keys from .env are automatically loaded!"
    echo "🔄 Container will auto-restart if it stops"
    echo ""
    echo "📋 Management:"
    echo "   View logs:     docker logs -f nba-nfl-production"
    echo "   Stop system:   docker stop nba-nfl-production"
    echo "   Restart:       ./start_production.sh"
else
    echo "❌ System failed to start properly"
    echo "📋 Check logs: docker logs nba-nfl-production"
fi
