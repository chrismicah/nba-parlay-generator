// Complete API types based on backend schema analysis

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

export interface ReasoningFactor {
  factor_type: 'injury' | 'line_movement' | 'matchup' | 'public_betting' | 'weather' | 'rest';
  description: string;
  confidence: number; // 0.0 to 1.0
  impact: 'positive' | 'negative' | 'neutral';
  weight: number;
}

export interface ParlayReasoning {
  parlay_id: string;
  reasoning_text: string;
  confidence_score: number;
  reasoning_factors: ReasoningFactor[];
  generated_at: string;
  strategist_version: string;
}

export interface ParlayData {
  legs: ParlayLeg[];
  confidence: number;
  expected_value?: number;
  kelly_percentage?: number;
  knowledge_insights?: string[];
  expert_guidance?: string[];
  reasoning: string;
  total_odds?: number;
  recommendation?: string;
}

export interface ParlayResponse {
  success: boolean;
  sport: string;
  parlay: ParlayData;
  generated_at: string;
  agent_version: string;
  message?: string;
}

export interface KnowledgeChunk {
  content: string;
  source: string;
  chunk_id: number;
  relevance_score: number;
  metadata?: Record<string, any>;
}

export interface KnowledgeSearchResponse {
  query: string;
  chunks: KnowledgeChunk[];
  total_chunks_searched: number;
  search_time_ms: number;
  insights: string[];
}

export interface HealthComponent {
  status: string;
  details?: string;
  last_check?: string;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  components: {
    nfl_agent?: HealthComponent;
    nba_agent?: HealthComponent;
    knowledge_base?: HealthComponent;
    ml_models?: HealthComponent;
    database?: HealthComponent;
    redis?: HealthComponent;
    web_server?: HealthComponent;
    minimal_mode?: boolean;
  };
  uptime_seconds: number;
  message?: string;
  version?: string;
  sports_enabled?: {
    nfl: boolean;
    nba: boolean;
  };
  mode?: string;
}

export interface SystemStats {
  uptime_seconds: number;
  timestamp: string;
  performance_metrics?: {
    avg_response_time_ms: number;
    total_requests: number;
    success_rate: number;
  };
  agent_status?: {
    nfl_ready: boolean;
    nba_ready: boolean;
    knowledge_base_ready: boolean;
  };
}

export interface SeasonStatusResponse {
  current_date: string;
  current_month: number;
  current_day: number;
  nfl_season_start: string;
  before_season: boolean;
  should_block_nfl: boolean;
}

// API Error types
export interface APIError {
  detail: string;
  status_code?: number;
}

// Loading and UI state types
export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export interface ParlayGenerationState extends AsyncState<ParlayResponse> {
  lastGenerated?: Date;
  retryCount?: number;
}

export interface HealthCheckState extends AsyncState<HealthResponse> {
  lastCheck?: Date;
  autoRefresh?: boolean;
}

export interface KnowledgeSearchState extends AsyncState<KnowledgeSearchResponse> {
  query?: string;
  hasSearched?: boolean;
}



