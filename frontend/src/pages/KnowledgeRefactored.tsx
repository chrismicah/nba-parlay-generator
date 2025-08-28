/**
 * Refactored Knowledge Base page with comprehensive RAG interface
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  BookOpen,
  Brain,
  Lightbulb,
  Search,
  TrendingUp,
  Target,
  Calculator,
  BarChart3,
  Users,
  Clock,
  Star
} from 'lucide-react';

// Components
import KnowledgeSearch from '@/components/knowledge/KnowledgeSearch';
import HealthIndicator from '@/components/system/HealthIndicator';

// Hooks
import { useHealthCheck } from '@/hooks/useApi';

const KnowledgeRefactored: React.FC = () => {
  const [activeTab, setActiveTab] = useState('search');

  const {
    data: healthData,
    loading: healthLoading,
    error: healthError,
    checkHealth,
    lastCheck
  } = useHealthCheck(true, 60000); // Check every minute

  // Knowledge base topics and quick searches
  const knowledgeTopics = [
    {
      category: "Value Betting",
      icon: <Target className="h-5 w-5 text-green-600" />,
      description: "Finding positive expected value opportunities",
      queries: ["expected value calculation", "value betting strategy", "edge detection"]
    },
    {
      category: "Kelly Criterion",
      icon: <Calculator className="h-5 w-5 text-blue-600" />,
      description: "Optimal betting size determination",
      queries: ["kelly criterion formula", "bankroll management", "optimal bet sizing"]
    },
    {
      category: "Line Movement",
      icon: <TrendingUp className="h-5 w-5 text-purple-600" />,
      description: "Understanding odds movements and market signals",
      queries: ["line movement analysis", "steam moves", "market efficiency"]
    },
    {
      category: "Arbitrage",
      icon: <BarChart3 className="h-5 w-5 text-orange-600" />,
      description: "Risk-free profit opportunities",
      queries: ["arbitrage betting", "sure bets", "cross-book opportunities"]
    },
    {
      category: "Public Betting",
      icon: <Users className="h-5 w-5 text-red-600" />,
      description: "Contrarian strategies and public bias",
      queries: ["fade the public", "contrarian betting", "public betting patterns"]
    },
    {
      category: "Advanced Metrics",
      icon: <Brain className="h-5 w-5 text-cyan-600" />,
      description: "Statistical analysis and modeling",
      queries: ["regression analysis", "statistical significance", "predictive modeling"]
    }
  ];

  const expertSources = [
    {
      title: "The Logic of Sports Betting",
      author: "Ed Miller",
      description: "Mathematical foundations and value betting principles",
      chapters: 12,
      chunks: 800
    },
    {
      title: "Mathletics",
      author: "Wayne Winston", 
      description: "Statistical analysis and mathematical modeling in sports",
      chapters: 15,
      chunks: 790
    }
  ];

  const TopicCard: React.FC<{
    topic: typeof knowledgeTopics[0];
    onQueryClick: (query: string) => void;
  }> = ({ topic, onQueryClick }) => (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          {topic.icon}
          <span>{topic.category}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">{topic.description}</p>
        <div className="space-y-2">
          <div className="text-xs font-medium text-muted-foreground">Quick searches:</div>
          <div className="flex flex-wrap gap-1">
            {topic.queries.map((query) => (
              <Button
                key={query}
                variant="outline"
                size="sm"
                className="text-xs h-7"
                onClick={() => onQueryClick(query)}
              >
                {query}
              </Button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );

  const SourceCard: React.FC<{ source: typeof expertSources[0] }> = ({ source }) => (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="font-medium">{source.title}</div>
            <div className="text-sm text-muted-foreground">by {source.author}</div>
            <div className="text-xs text-muted-foreground">{source.description}</div>
          </div>
          <div className="text-right space-y-1">
            <Badge variant="outline">{source.chunks} chunks</Badge>
            <div className="text-xs text-muted-foreground">{source.chapters} chapters</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );

  const handleQuickSearch = (query: string) => {
    setActiveTab('search');
    // The KnowledgeSearch component will handle the actual search
    // This would trigger a search in the component if we passed a ref
  };

  return (
    <div className="flex-1 p-6 bg-gradient-to-br from-blue-50 to-indigo-50 min-h-screen">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center space-x-3">
            <BookOpen className="h-8 w-8 text-blue-600" />
            <h1 className="text-4xl font-bold text-slate-800">Knowledge Base</h1>
          </div>
          <p className="text-slate-600 max-w-3xl mx-auto">
            Explore expert sports betting knowledge from Ed Miller's "The Logic of Sports Betting" 
            and Wayne Winston's "Mathletics" through our advanced RAG search system.
          </p>
        </div>

        {/* System Status */}
        <div className="max-w-2xl mx-auto">
          <HealthIndicator 
            health={healthData}
            loading={healthLoading}
            error={healthError}
            onRefresh={checkHealth}
            lastCheck={lastCheck}
            compact
          />
        </div>

        {/* Main Content */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="search" className="flex items-center space-x-2">
              <Search className="h-4 w-4" />
              <span>Search</span>
            </TabsTrigger>
            <TabsTrigger value="topics" className="flex items-center space-x-2">
              <Lightbulb className="h-4 w-4" />
              <span>Topics</span>
            </TabsTrigger>
            <TabsTrigger value="sources" className="flex items-center space-x-2">
              <BookOpen className="h-4 w-4" />
              <span>Sources</span>
            </TabsTrigger>
            <TabsTrigger value="insights" className="flex items-center space-x-2">
              <Star className="h-4 w-4" />
              <span>Key Insights</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="search" className="mt-6">
            <KnowledgeSearch 
              placeholder="Search for sports betting strategies, mathematical concepts, or expert insights..."
              maxResults={10}
              autoFocus={true}
            />
          </TabsContent>

          <TabsContent value="topics" className="mt-6">
            <div className="space-y-6">
              <div className="text-center">
                <h2 className="text-2xl font-bold mb-2">Explore Key Topics</h2>
                <p className="text-muted-foreground">
                  Browse curated topics from our expert knowledge base
                </p>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {knowledgeTopics.map((topic) => (
                  <TopicCard 
                    key={topic.category}
                    topic={topic}
                    onQueryClick={handleQuickSearch}
                  />
                ))}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="sources" className="mt-6">
            <div className="space-y-6">
              <div className="text-center">
                <h2 className="text-2xl font-bold mb-2">Expert Sources</h2>
                <p className="text-muted-foreground">
                  Our knowledge base is built from these authoritative sports betting texts
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {expertSources.map((source) => (
                  <SourceCard key={source.title} source={source} />
                ))}
              </div>

              <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
                <CardContent className="pt-6">
                  <div className="flex items-center space-x-4">
                    <Brain className="h-12 w-12 text-blue-600" />
                    <div>
                      <h3 className="text-lg font-semibold text-blue-900">RAG System Overview</h3>
                      <p className="text-blue-700 text-sm mt-1">
                        Our Retrieval-Augmented Generation system processes over 1,590 knowledge chunks
                        to provide contextually relevant insights for your sports betting queries.
                      </p>
                      <div className="flex space-x-4 mt-2">
                        <Badge variant="outline" className="bg-white">
                          1,590+ chunks indexed
                        </Badge>
                        <Badge variant="outline" className="bg-white">
                          Vector similarity search
                        </Badge>
                        <Badge variant="outline" className="bg-white">
                          Expert-curated content
                        </Badge>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="insights" className="mt-6">
            <div className="space-y-6">
              <div className="text-center">
                <h2 className="text-2xl font-bold mb-2">Key Insights</h2>
                <p className="text-muted-foreground">
                  Essential concepts and strategies from our expert knowledge base
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="border-l-4 border-l-green-500">
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Target className="h-5 w-5 text-green-600" />
                      <span>Expected Value</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground mb-3">
                      The fundamental concept for profitable betting - only bet when you have a positive expected value.
                    </p>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => handleQuickSearch("expected value calculation")}
                    >
                      Learn More
                    </Button>
                  </CardContent>
                </Card>

                <Card className="border-l-4 border-l-blue-500">
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Calculator className="h-5 w-5 text-blue-600" />
                      <span>Kelly Criterion</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground mb-3">
                      Mathematical formula for optimal bet sizing to maximize long-term growth.
                    </p>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => handleQuickSearch("kelly criterion formula")}
                    >
                      Learn More
                    </Button>
                  </CardContent>
                </Card>

                <Card className="border-l-4 border-l-purple-500">
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <TrendingUp className="h-5 w-5 text-purple-600" />
                      <span>Line Movement</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground mb-3">
                      Understanding how betting lines move and what it signals about smart money.
                    </p>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => handleQuickSearch("line movement analysis")}
                    >
                      Learn More
                    </Button>
                  </CardContent>
                </Card>

                <Card className="border-l-4 border-l-orange-500">
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <BarChart3 className="h-5 w-5 text-orange-600" />
                      <span>Market Efficiency</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground mb-3">
                      How efficient are betting markets and where to find the best opportunities.
                    </p>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => handleQuickSearch("market efficiency")}
                    >
                      Learn More
                    </Button>
                  </CardContent>
                </Card>
              </div>

              <Card className="bg-gradient-to-r from-yellow-50 to-orange-50 border-yellow-200">
                <CardContent className="pt-6">
                  <div className="flex items-start space-x-4">
                    <Lightbulb className="h-8 w-8 text-yellow-600 mt-1" />
                    <div>
                      <h3 className="text-lg font-semibold text-yellow-900 mb-2">Pro Tip</h3>
                      <p className="text-yellow-800 text-sm">
                        Use specific, detailed queries to get the most relevant results from our knowledge base. 
                        For example, instead of searching "betting", try "expected value calculation for parlays" 
                        or "kelly criterion with correlated outcomes".
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default KnowledgeRefactored;



