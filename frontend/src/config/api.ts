// API Configuration
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  ENDPOINTS: {
    NBA_PARLAY: '/generate-nba-parlay',
    NFL_PARLAY: '/generate-nfl-parlay',
    HEALTH: '/health',
    KNOWLEDGE_SEARCH: '/knowledge-base/search'
  }
} as const;

// Request types matching backend
export interface ParlayRequest {
  target_legs: number;
  min_total_odds: number;
  include_arbitrage: boolean;
  sport?: string;
}

export interface ParlayLeg {
  game: string;
  market: string;
  selection: string;
  odds: number;
  book: string;
}

export interface ParlayResponse {
  success: boolean;
  sport: string;
  parlay: {
    legs: ParlayLeg[];
    confidence: number;
    expected_value?: number;
    kelly_percentage?: number;
    reasoning: string;
  };
  generated_at: string;
  agent_version: string;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  components: {
    nfl_agent: { status: string; enabled: boolean };
    nba_agent: { status: string; enabled: boolean };
    knowledge_base: { status: string; chunks: number };
  };
  uptime_seconds: number;
}



