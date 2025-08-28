/**
 * Production-ready API client aligned with backend architecture
 * Supports all discovered endpoints with proper error handling and typing
 */

import { 
  ParlayRequest, 
  ParlayResponse, 
  HealthResponse, 
  KnowledgeSearchResponse, 
  SystemStats,
  SeasonStatusResponse,
  APIError 
} from '../types/api';

export class APIClient {
  private baseURL: string;
  private timeout: number;

  constructor(baseURL: string = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000', timeout: number = 30000) {
    this.baseURL = baseURL;
    this.timeout = timeout;
  }

  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      signal: controller.signal,
      ...options,
    };

    try {
      const response = await fetch(url, config);
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({})) as APIError;
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new Error('Request timeout - please try again');
        }
        throw error;
      }
      
      throw new Error('Unknown error occurred');
    }
  }

  // System endpoints
  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health');
  }

  async getSystemStats(): Promise<SystemStats> {
    return this.request<SystemStats>('/stats');
  }

  async getSeasonStatus(): Promise<SeasonStatusResponse> {
    return this.request<SeasonStatusResponse>('/season-status');
  }

  async getSystemHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/system-health');
  }

  // Parlay generation endpoints
  async generateNFLParlay(request: ParlayRequest): Promise<ParlayResponse> {
    return this.request<ParlayResponse>('/generate-nfl-parlay', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async generateNBAParlay(request: ParlayRequest): Promise<ParlayResponse> {
    return this.request<ParlayResponse>('/generate-nba-parlay', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Knowledge base endpoints
  async searchKnowledgeBase(query: string, topK: number = 5): Promise<KnowledgeSearchResponse> {
    const params = new URLSearchParams({
      query,
      top_k: topK.toString(),
    });
    
    return this.request<KnowledgeSearchResponse>(`/knowledge-base/search?${params}`);
  }

  // Root endpoint
  async getRoot(): Promise<any> {
    return this.request<any>('/');
  }
}

// Singleton instance
export const apiClient = new APIClient();

// Export individual methods for convenience
export const api = {
  health: () => apiClient.getHealth(),
  stats: () => apiClient.getSystemStats(),
  seasonStatus: () => apiClient.getSeasonStatus(),
  systemHealth: () => apiClient.getSystemHealth(),
  generateNFLParlay: (request: ParlayRequest) => apiClient.generateNFLParlay(request),
  generateNBAParlay: (request: ParlayRequest) => apiClient.generateNBAParlay(request),
  searchKnowledge: (query: string, topK?: number) => apiClient.searchKnowledgeBase(query, topK),
  root: () => apiClient.getRoot(),
} as const;



