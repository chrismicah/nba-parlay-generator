# NBA/NFL Parlay Backend System - Complete Technical Overview

## Production System Architecture Summary

The NBA/NFL Parlay backend production system is a sophisticated **FastAPI-based microservices architecture** that runs primarily **NFL-focused parlay generation with MultiSportSchedulerIntegration, automated APScheduler triggers, and comprehensive knowledge base RAG integration** featuring Ed Miller's "The Logic of Sports Betting" and Wayne Winston's "Mathletics" with 1,590+ knowledge chunks. The production system (`production_main.py`) currently implements **only NFL parlay generation endpoints** with NFLParlayStrategistAgent while NBA functionality exists in the development system (`app/main.py`) using FewShotEnhancedParlayStrategistAgent with BioBERT injury classifiers and few-shot learning capabilities. **Production deployment features automated scheduling via APScheduler, manual trigger endpoints, knowledge base search endpoints, comprehensive health monitoring, and system statistics tracking** with real-time NFL parlay generation based on scheduled triggers and manual requests. The backend utilizes **PostgreSQL/Supabase database integration with 7 core tables** (users, parlays, payments, user_usage, parlay_logs, knowledge_queries, arbitrage_opportunities) for data persistence and **real-time data sources including The Odds API, Twitter scraping, and sports journalism content** from The Ringer, NBA.com, and other sources. **The production system focuses on NFL operations with automated parlay generation, knowledge-enhanced decision making, arbitrage detection, bankroll management recommendations, and comprehensive performance tracking** through value betting analysis and correlation warnings.

## Technical Stack Components

### **Core Framework & APIs**
- **FastAPI** (v0.109.2) - REST API framework with automatic OpenAPI documentation
- **Uvicorn** (v0.27.1) - ASGI server for production deployment  
- **Pydantic** (v2.11.7) - Data validation and serialization
- **APScheduler** - Automated task scheduling for parlay generation
- **Supabase/PostgreSQL** - Primary database with 7 tables (users, parlays, payments, user_usage, parlay_logs, knowledge_queries, arbitrage_opportunities)

### **Machine Learning & AI Stack**
- **BioBERT Injury Classifier** - Transformer model for injury severity analysis from tweets/news
- **Few-Shot Learning Agents** - Enhanced parlay strategist using historical successful examples
- **Sentence Transformers** (v3.0.1) - Text embeddings for semantic similarity
- **Bayesian Confidence Scoring** - Statistical models for parlay outcome prediction
- **LangChain** (v0.3.27) - LLM orchestration and prompt engineering
- **Qdrant Client** (v1.11.2) - Vector database for knowledge base RAG system

### **Data Collection & Processing**
- **NBA API** (v1.10.0) - Official NBA statistics and game data
- **The Odds API** - Real-time betting odds from multiple sportsbooks
- **Twitter/X API (Tweepy v4.14.0)** - Social media sentiment and injury reports
- **Web Scraping Stack**: BeautifulSoup4, Playwright, Crawl4AI, Firecrawl-py for sports journalism
- **Data Sources**: The Ringer, NBA.com, Action Network, ClutchPoints articles

### **Analytics & Optimization**
- **Arbitrage Detection** - Cross-sportsbook opportunity identification
- **Market Discrepancy Monitor** - Price inefficiency detection
- **Correlation Models** - Statistical relationships between betting markets
- **Performance Tracking** - Closing Line Value (CLV) analysis and parlay outcome logging
- **ML Feedback Loops** - Continuous model improvement from bet results

### **Production Infrastructure**  
- **Docker** containerization with docker-compose orchestration
- **MLflow** experiment tracking and model versioning
- **Comprehensive Logging** - Structured logging with performance metrics
- **Health Monitoring** - Real-time system status and component health checks
- **Environment Management** - Secure API key handling and configuration management

