import { API_CONFIG, ParlayRequest, ParlayResponse, HealthResponse } from '../config/api';

class ApiService {
  private baseURL: string;

  constructor() {
    this.baseURL = API_CONFIG.BASE_URL;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Generate NBA Parlay
  async generateNBAParlay(request: ParlayRequest): Promise<ParlayResponse> {
    return this.request<ParlayResponse>(API_CONFIG.ENDPOINTS.NBA_PARLAY, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Generate NFL Parlay  
  async generateNFLParlay(request: ParlayRequest): Promise<ParlayResponse> {
    return this.request<ParlayResponse>(API_CONFIG.ENDPOINTS.NFL_PARLAY, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Health Check
  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>(API_CONFIG.ENDPOINTS.HEALTH);
  }

  // Knowledge Base Search
  async searchKnowledgeBase(query: string, topK: number = 5): Promise<any> {
    return this.request<any>(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_SEARCH}?query=${encodeURIComponent(query)}&top_k=${topK}`);
  }

  // System Status
  async getSystemStatus(): Promise<any> {
    return this.request<any>('/');
  }
}

export const apiService = new ApiService();
export default apiService;
