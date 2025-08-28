# 🔧 Backend Integration - Final Definitive Answers

## 🎯 **1. Parlay Generation Endpoint Consistency**

### **Current Backend Implementation Analysis**

Based on the actual codebase analysis:

**Available Endpoints:**
- `POST /generate-nfl-parlay` - Generates **1 NFL parlay** with user parameters
- `POST /generate-nba-parlay` - Generates **1 NBA parlay** with user parameters  
- `POST /manual-trigger` - Triggers background batch generation (returns immediately)

### **Recommended UI Implementation**

```typescript
// For Quick Generate Button (Dashboard Widget)
const quickGenerateParlay = async (sport: 'nfl' | 'nba') => {
  // Use single endpoint with preset "moderate" configuration
  return await fetch(`/generate-${sport}-parlay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      target_legs: 3,
      min_total_odds: 5.0,
      include_arbitrage: true
    })
  });
};

// For Custom Parlay Form
const generateCustomParlay = async (sport: 'nfl' | 'nba', params: ParlayRequest) => {
  // Use single endpoint with user's custom parameters
  return await fetch(`/generate-${sport}-parlay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
};
```

**Answer:**
- **Quick Generate**: Use `/generate-{sport}-parlay` with preset "moderate" config (gets 1 parlay)
- **Custom Form**: Use `/generate-{sport}-parlay` with user parameters (gets 1 parlay)
- **Batch Generation**: Use `/manual-trigger` for background processing (admin feature)

---

## 🔄 **2. Manual-Trigger Response Format**

### **Current Implementation**

```python
# From production_main.py - line 286-296
@self.app.post("/manual-trigger")
async def manual_trigger(background_tasks: BackgroundTasks):
    """Manually trigger NFL parlay generation."""
    if not self.scheduler_integration:
        raise HTTPException(status_code=503, detail="Scheduler not available")
    
    # Run in background
    background_tasks.add_task(
        self.scheduler_integration.trigger_manual_generation,
        game_day="manual",
        game_time="triggered"
    )
    
    return {"message": "Manual NFL parlay generation triggered"}
```

### **Actual Response Format**

```typescript
// POST /manual-trigger response
interface ManualTriggerResponse {
  message: string; // "Manual NFL parlay generation triggered"
}

// The endpoint returns IMMEDIATELY and does NOT return the generated parlays
// Parlays are generated in background and logged to console/database
```

### **For AutomatedParlayFeed Component**

```typescript
// Since /manual-trigger doesn't return parlays, you need to:
// 1. Call /manual-trigger to start generation
// 2. Poll for new parlays using a different method

const triggerAndWaitForParlays = async () => {
  // 1. Trigger generation
  await fetch('/manual-trigger', { method: 'POST' });
  
  // 2. Poll for new parlays (you'll need to build this endpoint)
  const beforeTimestamp = new Date().toISOString();
  
  // Wait a few seconds for generation to complete
  await new Promise(resolve => setTimeout(resolve, 5000));
  
  // 3. Fetch new parlays created after trigger
  const newParlays = await fetchRecentParlays(beforeTimestamp);
  return newParlays;
};
```

**Answer:** `/manual-trigger` returns immediately with a success message. It does NOT return the generated parlays. You need a separate mechanism to retrieve the results.

---

## 👥 **3. User-Specific vs. Global Automated Parlays**

### **Current Implementation Analysis**

Based on the scheduler code in `multi_sport_scheduler_integration.py`:

```python
# Lines 231-260 show automated generation
async def _generate_nfl_parlays(self, game_day: str, game_time: str) -> None:
    """Generate NFL parlays using the NFL agent."""
    # Generate multiple NFL parlays for different risk levels
    risk_configs = [
        {"target_legs": 2, "min_odds": 3.0, "name": "Conservative"},
        {"target_legs": 3, "min_odds": 5.0, "name": "Moderate"},
        {"target_legs": 4, "min_odds": 10.0, "name": "Aggressive"}
    ]
    
    # Generated parlays are the same for all users
    for config in risk_configs:
        recommendation = await self.nfl_agent.generate_nfl_parlay_recommendation(...)
```

### **Current Architecture: Global Parlays**

**Answer: A) Global and the same for every user**

- Automated parlays are generated **once per schedule trigger**
- **Same 3 conservative/moderate/aggressive parlays** shown to all users
- No user-specific personalization in current implementation
- Cost-efficient approach (generates 6 parlays/day vs 6 × users parlays/day)

### **UI Implementation Strategy**

```typescript
// Global parlay cache - same data for all users
interface AutomatedParlayCache {
  last_updated: string;
  parlays: {
    nfl: ExtendedParlayResponse[];     // 3 parlays (conservative, moderate, aggressive)
    nba: ExtendedParlayResponse[];     // 3 parlays (conservative, moderate, aggressive)
  };
}

// GET /parlays endpoint should be global, not user-scoped
// Cache aggressively since data is the same for everyone
const fetchGlobalAutomatedParlays = async () => {
  const response = await fetch('/parlays?source=automated&limit=6');
  return response.json();
};
```

---

## 🗄️ **4. BetsLogger Schema Integration**

### **Current State Analysis**

**Database Schema:** ✅ Exists (`bets` table in SQLite)
**API Endpoint:** ❌ Does NOT exist yet

```sql
-- Current schema (from bets_logger.py)
CREATE TABLE bets (
    bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parlay_id TEXT NOT NULL,
    leg_description TEXT NOT NULL,
    odds REAL NOT NULL,
    sport TEXT DEFAULT 'nba',
    created_at TEXT NOT NULL,
    -- ... other fields
);
```

### **Missing API Layer**

```typescript
// This endpoint DOES NOT EXIST YET in the backend
GET /parlays  // ❌ Not implemented

// You need to either:
// 1. Build this endpoint as part of UI work
// 2. Query the database directly in your frontend API layer
// 3. Start with mock data and add real endpoint later
```

### **Recommended Implementation Strategy**

```typescript
// Option 1: Build the missing API endpoint (recommended)
// Add to FastAPI app:

@app.get("/parlays")
async def get_parlays(
    source: Optional[str] = None,      # "automated" | "user_requested"
    sport: Optional[str] = None,       # "nfl" | "nba"
    since: Optional[str] = None,       # ISO timestamp
    limit: int = 10
) -> ParlaysResponse:
    """Get parlays from database with filtering."""
    # Query bets table and group by parlay_id
    # Transform to ExtendedParlayResponse format
    pass

// Option 2: Frontend transformation (interim solution)
const transformBetsToParlay = (bets: BetRecord[]): ExtendedParlayResponse => {
  const groupedByParlay = groupBy(bets, 'parlay_id');
  
  return Object.entries(groupedByParlay).map(([parlayId, legs]) => ({
    success: true,
    sport: legs[0].sport.toUpperCase(),
    parlay: {
      parlay_id: parlayId,
      legs: legs.map(transformBetToLeg),
      confidence: 0.75, // Mock or calculate
      reasoning: "Generated parlay"
    },
    generation_type: inferGenerationType(parlayId),
    sport_type: legs[0].sport.toUpperCase(),
    created_at: legs[0].created_at
  }));
};
```

**Answer:** The `GET /parlays` endpoint does NOT exist yet. You'll need to either build it or use direct database queries transformed on the frontend.

---

## 👤 **5. GET /users/me/usage Endpoint**

### **Current State: Not Implemented**

```typescript
// This endpoint DOES NOT EXIST in the current backend
GET /users/me/usage  // ❌ Not implemented

// No user authentication/management system visible in codebase
// No usage tracking beyond API cost monitoring
```

### **Implementation Priority Decision**

**Option A: Mock Initially (Recommended for MVP)**
```typescript
// Mock the usage data for initial UI development
const mockUserUsage = (): UserUsageResponse => ({
  user_tier: "free",
  limits: {
    parlay_requests_per_day: 2,
    knowledge_searches_per_day: 10,
    arbitrage_alerts: false
  },
  usage: {
    parlays_requested_today: 0,
    knowledge_searches_today: 0,
    last_parlay_request: null
  },
  remaining: {
    parlay_requests: 2,
    knowledge_searches: 10
  }
});
```

**Option B: Build User System (Future Enhancement)**
```typescript
// Add to backend:
// 1. User authentication (JWT tokens)
// 2. User database table
// 3. Usage tracking middleware
// 4. /users/me/usage endpoint

// This is a significant backend addition beyond current scope
```

**Answer:** The usage endpoint does NOT exist. Mock it initially for UI development, then build the user system as a Phase 2 enhancement.

---

## 🏗️ **Complete Data Flow Strategy**

### **Phase 1: MVP with Current Backend**

```typescript
// What works TODAY with existing backend:
✅ POST /generate-nfl-parlay (single parlay)
✅ POST /generate-nba-parlay (single parlay)  
✅ POST /manual-trigger (background batch)
✅ GET /health (system status)
✅ GET /stats (system statistics)
✅ GET /knowledge-base/search (expert knowledge)

// What needs to be built:
❌ GET /parlays (fetch stored parlays)
❌ GET /users/me/usage (user limits)
❌ User authentication system
❌ Automated parlay storage/retrieval
```

### **Phase 2: Enhanced Features**

```typescript
// Add missing API endpoints:
✅ GET /parlays?source=automated&sport=nfl&since=timestamp
✅ GET /users/me/usage
✅ POST /users/me/parlays (save user parlays)
✅ GET /users/me/parlays (fetch user parlay history)

// Add user system:
✅ JWT authentication
✅ User tiers (free/pro/enterprise)
✅ Usage tracking middleware
```

### **Recommended Development Approach**

```typescript
// Start with what exists, mock what doesn't
const ApiClient = {
  // Real endpoints
  generateParlay: (sport, params) => fetch(`/generate-${sport}-parlay`, ...),
  searchKnowledge: (query) => fetch(`/knowledge-base/search?query=${query}`, ...),
  getSystemHealth: () => fetch('/health'),
  
  // Mock endpoints (replace with real ones later)
  getUserUsage: () => Promise.resolve(mockUserUsage()),
  getParlays: (filters) => Promise.resolve(mockParlays(filters)),
  
  // Hybrid approach for automated parlays
  getAutomatedParlays: async () => {
    // Since no storage exists, generate fresh ones
    const nflParlay = await this.generateParlay('nfl', MODERATE_CONFIG);
    const nbaParlay = await this.generateParlay('nba', MODERATE_CONFIG);
    return [nflParlay, nbaParlay];
  }
};
```

## ✅ **Final Implementation Recommendations**

1. **Quick Generate**: Use single endpoints with preset configs
2. **Manual Trigger**: Background task only - don't rely on response data
3. **Automated Parlays**: Global for all users, cache aggressively  
4. **Parlay History**: Build missing `/parlays` endpoint or mock initially
5. **User Limits**: Mock the usage system for MVP, build real system later

This approach lets you build a functional UI with the existing backend while planning for future enhancements.

