/**
 * React hooks for API state management
 * Provides loading, error, and data states for all API operations
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { 
  ParlayRequest, 
  ParlayResponse, 
  HealthResponse, 
  KnowledgeSearchResponse,
  SystemStats,
  AsyncState,
  ParlayGenerationState,
  HealthCheckState,
  KnowledgeSearchState
} from '../types/api';
import { api } from '../services/apiClient';

// Generic hook for async operations
export function useAsyncOperation<T>() {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = useCallback(async (operation: () => Promise<T>) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const data = await operation();
      setState({ data, loading: false, error: null });
      return data;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      setState(prev => ({ ...prev, loading: false, error: errorMessage }));
      throw error;
    }
  }, []);

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  return { ...state, execute, reset };
}

// Health check hook with auto-refresh
export function useHealthCheck(autoRefresh: boolean = false, interval: number = 30000) {
  const [state, setState] = useState<HealthCheckState>({
    data: null,
    loading: false,
    error: null,
    autoRefresh,
  });

  const intervalRef = useRef<NodeJS.Timeout>();

  const checkHealth = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const data = await api.health();
      setState(prev => ({ 
        ...prev, 
        data, 
        loading: false, 
        error: null, 
        lastCheck: new Date() 
      }));
      return data;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Health check failed';
      setState(prev => ({ 
        ...prev, 
        loading: false, 
        error: errorMessage,
        lastCheck: new Date()
      }));
      throw error;
    }
  }, []);

  useEffect(() => {
    // Initial health check
    checkHealth();

    // Set up auto-refresh if enabled
    if (autoRefresh) {
      intervalRef.current = setInterval(checkHealth, interval);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh, interval, checkHealth]);

  const toggleAutoRefresh = useCallback(() => {
    setState(prev => ({ ...prev, autoRefresh: !prev.autoRefresh }));
  }, []);

  return { ...state, checkHealth, toggleAutoRefresh };
}

// Parlay generation hook
export function useParlayGeneration(sport: 'nfl' | 'nba') {
  const [state, setState] = useState<ParlayGenerationState>({
    data: null,
    loading: false,
    error: null,
    retryCount: 0,
  });

  const generateParlay = useCallback(async (request: ParlayRequest) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const apiMethod = sport === 'nfl' ? api.generateNFLParlay : api.generateNBAParlay;
      const data = await apiMethod(request);
      
      setState(prev => ({ 
        ...prev, 
        data, 
        loading: false, 
        error: null,
        lastGenerated: new Date(),
        retryCount: 0
      }));
      
      return data;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Parlay generation failed';
      setState(prev => ({ 
        ...prev, 
        loading: false, 
        error: errorMessage,
        retryCount: prev.retryCount ? prev.retryCount + 1 : 1
      }));
      throw error;
    }
  }, [sport]);

  const retry = useCallback(async (request: ParlayRequest) => {
    if (state.retryCount && state.retryCount >= 3) {
      throw new Error('Maximum retry attempts reached');
    }
    return generateParlay(request);
  }, [generateParlay, state.retryCount]);

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null, retryCount: 0 });
  }, []);

  return { ...state, generateParlay, retry, reset };
}

// Knowledge search hook
export function useKnowledgeSearch() {
  const [state, setState] = useState<KnowledgeSearchState>({
    data: null,
    loading: false,
    error: null,
    hasSearched: false,
  });

  const search = useCallback(async (query: string, topK: number = 5) => {
    if (!query.trim()) {
      throw new Error('Search query cannot be empty');
    }

    setState(prev => ({ ...prev, loading: true, error: null, query }));
    
    try {
      const data = await api.searchKnowledge(query, topK);
      setState(prev => ({ 
        ...prev, 
        data, 
        loading: false, 
        error: null,
        hasSearched: true
      }));
      return data;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Knowledge search failed';
      setState(prev => ({ 
        ...prev, 
        loading: false, 
        error: errorMessage,
        hasSearched: true
      }));
      throw error;
    }
  }, []);

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null, hasSearched: false });
  }, []);

  return { ...state, search, reset };
}

// System stats hook
export function useSystemStats(autoRefresh: boolean = false, interval: number = 60000) {
  const { data, loading, error, execute } = useAsyncOperation<SystemStats>();
  const intervalRef = useRef<NodeJS.Timeout>();

  const getStats = useCallback(() => execute(api.stats), [execute]);

  useEffect(() => {
    // Initial load
    getStats();

    // Set up auto-refresh if enabled
    if (autoRefresh) {
      intervalRef.current = setInterval(getStats, interval);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh, interval, getStats]);

  return { data, loading, error, getStats };
}

// Season status hook
export function useSeasonStatus() {
  const { data, loading, error, execute } = useAsyncOperation<any>();
  
  const getSeasonStatus = useCallback(() => execute(api.seasonStatus), [execute]);

  useEffect(() => {
    getSeasonStatus();
  }, [getSeasonStatus]);

  return { data, loading, error, getSeasonStatus };
}



