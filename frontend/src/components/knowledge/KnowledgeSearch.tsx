/**
 * Knowledge Base Search component aligned with backend RAG system
 */

import React, { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { 
  Search, 
  Loader2, 
  BookOpen,
  Brain,
  Lightbulb,
  Clock,
  TrendingUp
} from 'lucide-react';
import { useKnowledgeSearch } from '@/hooks/useApi';
import { KnowledgeChunk } from '@/types/api';
import { formatDuration } from '@/lib/formatters';

interface KnowledgeSearchProps {
  placeholder?: string;
  maxResults?: number;
  autoFocus?: boolean;
}

const KnowledgeSearch: React.FC<KnowledgeSearchProps> = ({
  placeholder = "Search sports betting knowledge...",
  maxResults = 5,
  autoFocus = false,
}) => {
  const [query, setQuery] = useState('');
  const { 
    data: searchResults, 
    loading, 
    error, 
    hasSearched,
    search, 
    reset 
  } = useKnowledgeSearch();

  const handleSearch = useCallback(async (searchQuery?: string) => {
    const queryToUse = searchQuery || query;
    if (!queryToUse.trim()) return;

    try {
      await search(queryToUse, maxResults);
    } catch (error) {
      // Error is handled by the hook
    }
  }, [query, search, maxResults]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSearch();
  };

  const handleQuickSearch = (quickQuery: string) => {
    setQuery(quickQuery);
    handleSearch(quickQuery);
  };

  const renderChunk = (chunk: KnowledgeChunk, index: number) => (
    <Card key={index} className="border-l-4 border-l-blue-500">
      <CardContent className="pt-4">
        <div className="flex items-start justify-between mb-2">
          <Badge variant="outline" className="text-xs">
            {chunk.source}
          </Badge>
          <Badge variant="secondary" className="text-xs">
            {(chunk.relevance_score * 100).toFixed(0)}% match
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground leading-relaxed">
          {chunk.content}
        </p>
        {chunk.metadata && (
          <div className="mt-2 text-xs text-muted-foreground">
            Chunk #{chunk.chunk_id}
          </div>
        )}
      </CardContent>
    </Card>
  );

  const quickSearchQueries = [
    "value betting",
    "parlay strategy", 
    "kelly criterion",
    "expected value",
    "line movement",
    "arbitrage opportunities"
  ];

  return (
    <div className="space-y-6">
      {/* Search Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <BookOpen className="h-5 w-5" />
            <span>Knowledge Base Search</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={handleSubmit} className="flex space-x-2">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={placeholder}
              autoFocus={autoFocus}
              disabled={loading}
              className="flex-1"
            />
            <Button 
              type="submit" 
              disabled={loading || !query.trim()}
              className="px-6"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
            </Button>
          </form>

          {/* Quick Search Options */}
          <div className="space-y-2">
            <div className="text-sm font-medium">Quick searches:</div>
            <div className="flex flex-wrap gap-2">
              {quickSearchQueries.map((quickQuery) => (
                <Button
                  key={quickQuery}
                  variant="outline"
                  size="sm"
                  onClick={() => handleQuickSearch(quickQuery)}
                  disabled={loading}
                  className="text-xs"
                >
                  {quickQuery}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Search Results */}
      {hasSearched && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center space-x-2">
                <Brain className="h-5 w-5" />
                <span>Search Results</span>
              </CardTitle>
              {searchResults && (
                <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                  <div className="flex items-center space-x-1">
                    <Clock className="h-3 w-3" />
                    <span>{formatDuration(searchResults.search_time_ms)}</span>
                  </div>
                  <div>{searchResults.total_chunks_searched} chunks searched</div>
                </div>
              )}
            </div>
          </CardHeader>

          <CardContent className="space-y-4">
            {error && (
              <div className="bg-red-50 border border-red-200 p-3 rounded-lg">
                <div className="text-sm text-red-800">{error}</div>
              </div>
            )}

            {loading && (
              <div className="text-center py-8">
                <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
                <div className="text-muted-foreground">Searching knowledge base...</div>
              </div>
            )}

            {searchResults && !loading && (
              <>
                {/* Search Summary */}
                <div className="bg-blue-50 border border-blue-200 p-3 rounded-lg">
                  <div className="text-sm text-blue-800">
                    Found <strong>{searchResults.chunks.length}</strong> relevant results 
                    for "<strong>{searchResults.query}</strong>"
                  </div>
                </div>

                {/* AI Insights */}
                {searchResults.insights && searchResults.insights.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Lightbulb className="h-4 w-4 text-yellow-500" />
                      <span className="text-sm font-medium">Key Insights</span>
                    </div>
                    <ul className="space-y-1">
                      {searchResults.insights.map((insight, index) => (
                        <li key={index} className="text-sm text-muted-foreground flex items-start space-x-2">
                          <TrendingUp className="h-3 w-3 mt-0.5 text-blue-500" />
                          <span>{insight}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <Separator />

                {/* Knowledge Chunks */}
                {searchResults.chunks.length > 0 ? (
                  <div className="space-y-3">
                    {searchResults.chunks.map((chunk, index) => renderChunk(chunk, index))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    No results found. Try different keywords or browse quick searches above.
                  </div>
                )}

                {/* Clear Results */}
                <div className="flex justify-center pt-4">
                  <Button variant="outline" onClick={reset} size="sm">
                    Clear Results
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default KnowledgeSearch;



