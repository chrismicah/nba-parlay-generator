# 🏀🏈 NBA/NFL Parlay System - Complete Backend Architecture & UI Guide

## 🎯 **Core System Architecture**

Your system is a sophisticated multi-sport parlay betting platform with these main components:

### **1. Backend Services Architecture**
- **FastAPI Web Server** (`app/main.py` & `production_main.py`)
- **Multi-Sport Agents** (NFL & NBA parlay strategists)
- **Expert Knowledge Base** (RAG system with 1,590+ chunks from betting books)
- **ML Prediction Layer** (BioBERT, prop predictors, confidence classifiers)
- **Real-time Data Collection** (odds scraping, social media monitoring)
- **Performance Analytics** (SQLite database with comprehensive tracking)

---

## 🌐 **API Endpoints for Your UI**

### **Core API Endpoints**

| Endpoint | Method | Purpose | UI Components Needed |
|----------|--------|---------|---------------------|
| `/` | GET | System status & health | Dashboard status cards |
| `/health` | GET | Detailed system health | System health monitor |
| `/generate-nfl-parlay` | POST | Generate NFL parlay | NFL parlay generator form |
| `/generate-nba-parlay` | POST | Generate NBA parlay | NBA parlay generator form |
| `/knowledge-base/search` | GET | Search expert knowledge | Knowledge search widget |
| `/stats` | GET | System statistics | Analytics dashboard |
| `/scheduled-jobs` | GET | View scheduled jobs | Automation monitoring |
| `/manual-trigger` | POST | Manual parlay trigger | Manual trigger button |

### **Request/Response Data Models**

#### **ParlayRequest Model**
```typescript
interface ParlayRequest {
  target_legs: number;        // Default: 3
  min_total_odds: number;     // Default: 5.0
  include_arbitrage: boolean; // Default: true
  sport?: string;            // Optional: "nfl" | "nba"
}
```

#### **ParlayResponse Model**
```typescript
interface ParlayResponse {
  success: boolean;
  sport: "NFL" | "NBA";
  parlay: {
    legs: ParlayLeg[];
    confidence: number;           // 0.0 - 1.0
    expected_value?: number;
    kelly_percentage?: number;
    knowledge_insights?: string[];
    expert_guidance?: string[];
    reasoning: string;
    value_analysis?: any;
    correlation_warnings?: string[];
    bankroll_recommendations?: any;
  };
  generated_at: string;         // ISO timestamp
  agent_version: string;
}
```

#### **ParlayLeg Model**
```typescript
interface ParlayLeg {
  game_id: string;
  game?: string;              // e.g., "Lakers vs Warriors"
  market_type: string;        // "h2h" | "spreads" | "totals" | "player_props"
  market?: string;            // Display name e.g., "Spread"
  selection_name: string;     // Team/player name
  selection?: string;         // Display selection e.g., "Lakers -3.5"
  bookmaker: string;          // "fanduel" | "draftkings" | etc.
  book?: string;              // Display name
  odds_decimal: number;       // 1.90
  odds?: number;              // Same as odds_decimal
  line?: number;              // Point spread/total line
}
```

#### **HealthResponse Model**
```typescript
interface HealthResponse {
  status: "healthy" | "degraded" | "error";
  timestamp: string;
  uptime_seconds: number;
  components: {
    nfl_agent: {
      status: "ready" | "unavailable";
      enabled: boolean;
    };
    nba_agent: {
      status: "ready" | "unavailable";
      enabled: boolean;
    };
    knowledge_base: {
      status: "ready" | "unavailable";
      chunks: number;
    };
    external_services: {
      qdrant: "connected" | "not_configured";
      redis: "connected" | "not_configured";
    };
  };
}
```

#### **SystemStats Model**
```typescript
interface SystemStats {
  system: {
    uptime_hours: number;
    start_time: string;
    container_mode: boolean;
  };
  sports: {
    nfl_enabled: boolean;
    nba_enabled: boolean;
  };
  knowledge_base: {
    available: boolean;
    chunks: number;
  };
  environment: {
    redis_configured: boolean;
    qdrant_configured: boolean;
    nfl_enabled: boolean;
    nba_enabled: boolean;
  };
}
```

---

## 🎨 **UI Components & User Flows**

### **1. Main Dashboard**
**Components needed:**
- **Sport Toggle** (NFL/NBA)
- **System Health Cards**
- **Quick Parlay Generator**
- **Recent Parlays List**
- **Performance Summary**

**Data sources:**
- `GET /` for system status
- `GET /stats` for performance metrics
- Database queries for recent parlays

### **2. Parlay Generator**
**Components needed:**
- **Sport Selector** (NFL/NBA tabs)
- **Configuration Form:**
  - Number of legs (2-5, default 3)
  - Minimum total odds (slider, 2.0-20.0, default 5.0)
  - Include arbitrage toggle
- **Generate Button**
- **Loading State** (with progress indicator)
- **Parlay Results Display**

**User Flow:**
1. Select sport (NFL/NBA)
2. Configure parameters
3. Click "Generate Parlay"
4. Show loading state (2-5 seconds)
5. Display results or error message

### **3. Parlay Results Display**
**Components needed:**
- **Confidence Score** (visual meter 0-100%)
- **Expected Value** (if available)
- **Kelly Bet Size** (if available)
- **Legs Table:**
  - Game
  - Market Type
  - Selection
  - Odds
  - Bookmaker
- **Expert Insights** (expandable section)
- **Reasoning** (AI explanation)
- **Actions:**
  - Save parlay
  - Export to betslip
  - Generate new parlay

### **4. Knowledge Base Search**
**Components needed:**
- **Search Input** (with autocomplete)
- **Search Results:**
  - Content snippet (truncated)
  - Source (Ed Miller/Wayne Winston)
  - Relevance score
- **Full Content Modal**

**User Flow:**
```
Search: "value betting" 
→ GET /knowledge-base/search?query=value betting&top_k=5
→ Display results with expandable content
```

#### **Knowledge Search Response Model**
```typescript
interface KnowledgeSearchResponse {
  query: string;
  results: {
    content: string;              // Truncated to 500 chars
    source: "Ed Miller" | "Wayne Winston";
    relevance_score: number;
  }[];
  insights: string[];
  search_time_ms: number;
}
```

---

## 📊 **Analytics & Performance Dashboard**

### **5. Performance Analytics**
**Components needed:**
- **ROI Chart** (line chart over time)
- **Hit Rate Metrics** (by bet type)
- **Profit/Loss Summary**
- **Recent Bets Table**
- **CLV (Closing Line Value) Tracking**

**Data structures from database:**
```typescript
interface BetRecord {
  bet_id: number;
  parlay_id: string;
  game_id: string;
  leg_description: string;
  odds: number;
  stake: number;
  predicted_outcome: string;
  actual_outcome?: string;
  is_win?: number;           // 1=win, 0=loss, null=open
  created_at: string;
  sport: "nba" | "nfl";
  clv_percentage?: number;   // Closing line value
}
```

**Performance Metrics:**
```typescript
interface PerformanceMetrics {
  overall_roi: number;        // Return on investment %
  hit_rate: number;          // Win percentage
  total_bets: number;
  total_profit: number;
  avg_odds: number;
  by_bet_type: {
    [key: string]: {
      roi: number;
      hit_rate: number;
      count: number;
    };
  };
  by_sport: {
    nfl: PerformanceMetrics;
    nba: PerformanceMetrics;
  };
}
```

### **6. Cost & API Monitoring**
**Components needed:**
- **Daily Cost Tracker** (budget vs used)
- **API Call Limits** (progress bars)
- **Service Status** (health indicators)
- **Cost Trend Charts**

**Data from daily reports:**
```typescript
interface CostAnalysis {
  total_cost_usd: number;
  total_calls: number;
  avg_cost_per_day: number;
  service_breakdown: ServiceCost[];
  budget_analysis: {
    daily_budget_utilization: number;
    remaining_budget: number;
    budget_status: "OK" | "WARNING" | "OVER";
    projected_monthly_cost: number;
  };
  daily_costs: Record<string, number>;
  limits: Record<string, number>;
}

interface ServiceCost {
  service: string;
  total_calls: number;
  successful_calls: number;
  success_rate: number;
  total_cost_usd: number;
  avg_cost_per_call: number;
  total_data_kb: number;
  daily_limit: number;
  limit_utilization: number;
}
```

---

## 🚀 **Real-time Features**

### **7. Live System Monitoring**
**Components needed:**
- **System Health Dashboard**
- **Live Parlay Generation Status**
- **Scheduled Jobs Monitor**
- **Real-time Notifications**

**WebSocket or polling endpoints:**
- `/health` (poll every 30 seconds)
- `/stats` (poll every 60 seconds)
- `/scheduled-jobs` (poll every 5 minutes)

### **8. Automated Scheduling**
**Components needed:**
- **Schedule Overview** (NFL: Thu/Sun/Mon, NBA: Daily)
- **Next Parlay Generation** (countdown timer)
- **Manual Trigger** (emergency button)
- **Job History** (success/failure logs)

**Scheduled Jobs Response:**
```typescript
interface ScheduledJobsResponse {
  scheduler_status: "running" | "stopped";
  total_jobs: number;
  jobs: ScheduledJob[];
}

interface ScheduledJob {
  id: string;
  name: string;
  sport: "nfl" | "nba";
  next_run: string;        // ISO timestamp
  last_run?: string;
  status: "scheduled" | "running" | "completed" | "failed";
  trigger_type: "cron" | "interval" | "date";
}
```

---

## 🏗️ **Advanced Features for UI**

### **9. Arbitrage Opportunities**
**Components needed:**
- **Arbitrage Alert Banner**
- **Arbitrage Table:**
  - Profit margin
  - Risk-adjusted profit
  - Execution time window
  - Required stakes per book
- **Arbitrage Calculator**

**Data structure:**
```typescript
interface ArbitrageOpportunity {
  arbitrage: boolean;
  type: "2-way" | "3-way" | "n-way";
  profit_margin: number;
  risk_adjusted_profit: number;
  expected_edge: number;
  total_stake: number;
  legs: ArbitrageLeg[];
  execution_time_window: number;
  confidence_level: "high" | "medium" | "low";
  detection_timestamp: string;
  expires_at: string;
}

interface ArbitrageLeg {
  book: string;
  market: string;
  team: string;
  odds: number;
  adjusted_odds: number;
  stake_ratio: number;
  stake_amount: number;
  expected_return: number;
  execution_confidence: number;
}
```

### **10. ML Insights**
**Components needed:**
- **Prediction Confidence** (visual indicators)
- **Model Performance** (accuracy over time)
- **Feature Importance** (charts)
- **Drift Detection** (alerts)

**ML Insights Data:**
```typescript
interface MLInsights {
  model_accuracy: number;
  confidence_distribution: number[];
  feature_importance: {
    feature: string;
    importance: number;
  }[];
  drift_detected: boolean;
  drift_magnitude: "low" | "medium" | "high";
  last_retrained: string;
}
```

### **11. Betting Simulation**
**Components needed:**
- **Baseline ROI** (random vs intelligent)
- **Simulation Results** (10,000+ parlay outcomes)
- **Strategy Comparison** (charts)

**Simulation Data:**
```typescript
interface SimulationResults {
  total_parlays: number;
  total_stake: number;
  total_profit: number;
  roi_percent: number;
  hit_rate: number;
  avg_legs: number;
  avg_odds: number;
  profit_stats: {
    min: number;
    max: number;
    mean: number;
    median: number;
  };
  segments: {
    regular: SimulationSegment;
    summer?: SimulationSegment;
  };
}

interface SimulationSegment {
  count: number;
  total_stake: number;
  total_profit: number;
  roi_percent: number;
  hit_rate: number;
}
```

---

## 🎯 **Recommended UI Framework & Architecture**

### **Frontend Tech Stack**
```typescript
// Recommended stack
- React/Next.js or Vue/Nuxt
- TypeScript for type safety
- TailwindCSS for styling
- Chart.js/Recharts for analytics
- Socket.io for real-time features
- React Query/SWR for API state management
- Framer Motion for animations
```

### **Page Structure**
```
/                     # Dashboard
/generate/nfl         # NFL Parlay Generator
/generate/nba         # NBA Parlay Generator  
/analytics            # Performance Dashboard
/knowledge            # Expert Knowledge Search
/arbitrage            # Arbitrage Opportunities
/settings             # System Configuration
/simulation           # Betting Simulation
/monitoring           # System Health & Jobs
```

### **Key UI Patterns**
1. **Loading States** - All parlay generation has 2-5 second delays
2. **Error Handling** - Clear error messages for failed generations
3. **Real-time Updates** - Polling-based updates for live data
4. **Progressive Disclosure** - Expandable sections for detailed data
5. **Mobile Responsive** - Betting is often done on mobile

---

## 🔧 **Development Integration**

### **Environment Variables**
```bash
# API Base URL
REACT_APP_API_URL=http://localhost:8000

# Polling intervals
REACT_APP_HEALTH_POLL_INTERVAL=30000
REACT_APP_STATS_POLL_INTERVAL=60000

# Feature flags
REACT_APP_ENABLE_NFL=true
REACT_APP_ENABLE_NBA=true
REACT_APP_ENABLE_ARBITRAGE=true
REACT_APP_ENABLE_KNOWLEDGE_BASE=true
```

### **API Client Example**
```typescript
// api/parlay.ts
export const generateParlay = async (
  sport: 'nfl' | 'nba', 
  params: ParlayRequest
): Promise<ParlayResponse> => {
  const response = await fetch(`${API_BASE_URL}/generate-${sport}-parlay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  return response.json();
};

export const searchKnowledge = async (
  query: string, 
  topK: number = 5
): Promise<KnowledgeSearchResponse> => {
  const response = await fetch(
    `${API_BASE_URL}/knowledge-base/search?query=${encodeURIComponent(query)}&top_k=${topK}`
  );
  return response.json();
};

export const getSystemHealth = async (): Promise<HealthResponse> => {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.json();
};

export const getSystemStats = async (): Promise<SystemStats> => {
  const response = await fetch(`${API_BASE_URL}/stats`);
  return response.json();
};
```

### **React Hooks Example**
```typescript
// hooks/useParlay.ts
import { useState } from 'react';
import { generateParlay } from '../api/parlay';

export const useParlay = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [parlay, setParlay] = useState<ParlayResponse | null>(null);

  const generate = async (sport: 'nfl' | 'nba', params: ParlayRequest) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await generateParlay(sport, params);
      setParlay(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate parlay');
    } finally {
      setLoading(false);
    }
  };

  return { generate, loading, error, parlay };
};
```

---

## 🎨 **UI/UX Best Practices**

### **Visual Design**
- **Dark mode** (common in trading/betting apps)
- **Green/Red indicators** (profit/loss, win/loss)
- **Confidence meters** (circular progress, color-coded)
- **Clean typography** (numbers should be highly readable)
- **Card-based layouts** (for parlays, insights, stats)

### **Color Scheme Recommendations**
```css
/* Color palette for betting UI */
:root {
  --primary: #1f2937;      /* Dark gray */
  --secondary: #374151;    /* Medium gray */
  --accent: #3b82f6;       /* Blue */
  --success: #10b981;      /* Green */
  --warning: #f59e0b;      /* Amber */
  --error: #ef4444;        /* Red */
  --text-primary: #f9fafb; /* Light gray */
  --text-secondary: #d1d5db; /* Medium light gray */
}
```

### **User Experience**
- **One-click generation** (minimize friction)
- **Clear feedback** (loading states, success/error messages)
- **Contextual help** (tooltips for betting terms)
- **Quick actions** (save, export, regenerate)
- **Persistent preferences** (remember user settings)

### **Mobile Considerations**
- **Touch-friendly buttons** (44px minimum)
- **Swipe gestures** (for navigating parlays)
- **Responsive tables** (horizontal scroll or stacked layout)
- **Bottom navigation** (easy thumb access)

---

## 📱 **Component Examples**

### **Parlay Card Component**
```tsx
interface ParlayCardProps {
  parlay: ParlayResponse;
  onSave?: () => void;
  onExport?: () => void;
}

const ParlayCard: React.FC<ParlayCardProps> = ({ parlay, onSave, onExport }) => {
  return (
    <div className="bg-gray-800 rounded-lg p-6 space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <span className="text-lg font-bold">{parlay.sport} Parlay</span>
          <ConfidenceMeter value={parlay.parlay.confidence} />
        </div>
        <div className="flex space-x-2">
          <button onClick={onSave} className="btn-secondary">Save</button>
          <button onClick={onExport} className="btn-primary">Export</button>
        </div>
      </div>

      {/* Legs */}
      <div className="space-y-2">
        {parlay.parlay.legs.map((leg, index) => (
          <LegRow key={index} leg={leg} />
        ))}
      </div>

      {/* Insights */}
      {parlay.parlay.knowledge_insights && (
        <ExpandableSection title="Expert Insights">
          {parlay.parlay.knowledge_insights.map((insight, index) => (
            <p key={index} className="text-sm text-gray-300">{insight}</p>
          ))}
        </ExpandableSection>
      )}

      {/* Reasoning */}
      <div className="bg-gray-700 rounded p-4">
        <h4 className="font-semibold mb-2">AI Reasoning</h4>
        <p className="text-sm text-gray-300">{parlay.parlay.reasoning}</p>
      </div>
    </div>
  );
};
```

### **System Health Component**
```tsx
const SystemHealth: React.FC = () => {
  const { data: health, isLoading } = useQuery(
    'health',
    getSystemHealth,
    { refetchInterval: 30000 }
  );

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <HealthCard
        title="NFL Agent"
        status={health.components.nfl_agent.status}
        enabled={health.components.nfl_agent.enabled}
      />
      <HealthCard
        title="NBA Agent"
        status={health.components.nba_agent.status}
        enabled={health.components.nba_agent.enabled}
      />
      <HealthCard
        title="Knowledge Base"
        status={health.components.knowledge_base.status}
        subtitle={`${health.components.knowledge_base.chunks} chunks`}
      />
      <HealthCard
        title="System"
        status={health.status}
        subtitle={`Uptime: ${Math.round(health.uptime_seconds / 3600)}h`}
      />
    </div>
  );
};
```

---

## 🚀 **Getting Started Checklist**

### **Backend Setup**
- [ ] Start the FastAPI server: `python production_main.py --web-server`
- [ ] Verify all endpoints are accessible
- [ ] Check system health at `/health`

### **Frontend Development**
- [ ] Set up React/TypeScript project
- [ ] Install required dependencies (charts, UI components)
- [ ] Configure API client with proper base URL
- [ ] Implement core components (dashboard, parlay generator)
- [ ] Add real-time polling for live updates
- [ ] Test all user flows end-to-end

### **Production Deployment**
- [ ] Configure environment variables
- [ ] Set up CI/CD pipeline
- [ ] Implement proper error handling and logging
- [ ] Add performance monitoring
- [ ] Test mobile responsiveness

This comprehensive backend provides everything you need for a sophisticated sports betting UI. The system handles all the complex ML, arbitrage detection, knowledge retrieval, and performance tracking - your UI just needs to present this data in an intuitive, actionable way for users.
