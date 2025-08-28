/**
 * Refactored NBA page with production-ready architecture
 * Fully aligned with backend API structure and best practices
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from '@/components/ui/use-toast';
import { 
  Basketball, 
  TrendingUp, 
  Activity, 
  AlertTriangle,
  Clock,
  Zap,
  Brain,
  Target,
  BarChart
} from 'lucide-react';

// Components
import ParlayGenerationForm from '@/components/parlay/ParlayGenerationForm';
import ParlayCard from '@/components/parlay/ParlayCard';
import HealthIndicator from '@/components/system/HealthIndicator';

// Hooks
import { useParlayGeneration, useHealthCheck, useSystemStats } from '@/hooks/useApi';
import { ParlayRequest } from '@/types/api';
import { formatUptime, formatPercentage } from '@/lib/formatters';

const NBARefactored: React.FC = () => {
  const [activeTab, setActiveTab] = useState('generate');
  
  // API hooks with proper state management
  const { 
    data: parlayData, 
    loading: generationLoading, 
    error: generationError,
    generateParlay,
    retry,
    reset: resetParlay
  } = useParlayGeneration('nba');

  const {
    data: healthData,
    loading: healthLoading,
    error: healthError,
    checkHealth,
    lastCheck
  } = useHealthCheck(true, 30000); // Auto-refresh every 30 seconds

  const {
    data: statsData,
    loading: statsLoading,
    getStats
  } = useSystemStats(true, 60000); // Auto-refresh every minute

  // Handle parlay generation
  const handleGenerateParlay = async (request: ParlayRequest) => {
    try {
      const result = await generateParlay(request);
      
      if (result.success) {
        toast({
          title: "NBA Parlay Generated!",
          description: `Created ${result.parlay.legs.length}-leg parlay with ${(result.parlay.confidence * 100).toFixed(0)}% confidence`,
        });
        setActiveTab('result');
      } else {
        toast({
          title: "Generation Notice",
          description: result.message || "Unable to generate parlay with current parameters",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Generation Failed",
        description: error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive",
      });
    }
  };

  // Handle parlay actions
  const handleShare = () => {
    if (parlayData && parlayData.success) {
      const shareText = `NBA Parlay: ${parlayData.parlay.legs.length} legs, ${(parlayData.parlay.confidence * 100).toFixed(0)}% confidence`;
      if (navigator.share) {
        navigator.share({
          title: 'NBA Parlay',
          text: shareText,
          url: window.location.href,
        });
      } else {
        navigator.clipboard.writeText(shareText);
        toast({ title: "Copied to clipboard!" });
      }
    }
  };

  const handleCopy = () => {
    if (parlayData && parlayData.success) {
      const parlayText = parlayData.parlay.legs
        .map(leg => `${leg.game}: ${leg.selection} (${leg.odds})`)
        .join('\n');
      
      navigator.clipboard.writeText(parlayText);
      toast({ title: "Parlay copied to clipboard!" });
    }
  };

  const handleRetry = async () => {
    if (parlayData && generationError) {
      try {
        const lastRequest: ParlayRequest = {
          target_legs: parlayData.parlay.legs.length || 3,
          min_total_odds: 5.0,
          include_arbitrage: true,
          sport: 'nba'
        };
        
        await retry(lastRequest);
        toast({ title: "Retry successful!" });
      } catch (error) {
        toast({
          title: "Retry failed",
          description: "Maximum retry attempts reached",
          variant: "destructive",
        });
      }
    }
  };

  // NBA season status (NBA season is typically active)
  const renderSeasonStatus = () => {
    const currentDate = new Date();
    const month = currentDate.getMonth() + 1; // 0-indexed
    
    // NBA season runs roughly October through June
    const isNBAActive = month >= 10 || month <= 6;
    
    if (isNBAActive) {
      return (
        <Card className="border-green-200 bg-green-50">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2 text-green-700">
              <Zap className="h-5 w-5" />
              <div>
                <div className="font-medium">NBA Season Active</div>
                <div className="text-sm">Real-time data and ML predictions available</div>
              </div>
            </div>
          </CardContent>
        </Card>
      );
    } else {
      return (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2 text-yellow-700">
              <Clock className="h-5 w-5" />
              <div>
                <div className="font-medium">NBA Offseason</div>
                <div className="text-sm">Historical data and demo predictions available</div>
              </div>
            </div>
          </CardContent>
        </Card>
      );
    }
  };

  // System stats display
  const renderSystemStats = () => {
    if (!statsData) return null;

    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <BarChart className="h-5 w-5" />
            <span>System Performance</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm text-muted-foreground">Uptime</div>
              <div className="font-medium">{formatUptime(statsData.uptime_seconds)}</div>
            </div>
            {statsData.performance_metrics && (
              <>
                <div>
                  <div className="text-sm text-muted-foreground">Success Rate</div>
                  <div className="font-medium">
                    {formatPercentage(statsData.performance_metrics.success_rate)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Avg Response</div>
                  <div className="font-medium">{statsData.performance_metrics.avg_response_time_ms}ms</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Total Requests</div>
                  <div className="font-medium">{statsData.performance_metrics.total_requests.toLocaleString()}</div>
                </div>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 p-4">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center space-x-3">
            <Basketball className="h-8 w-8 text-purple-600" />
            <h1 className="text-4xl font-bold text-slate-800">NBA Parlay Generator</h1>
          </div>
          <p className="text-slate-600 max-w-2xl mx-auto">
            AI-powered NBA parlay generation with ML predictions, few-shot learning, 
            and expert knowledge base insights for optimal betting strategies.
          </p>
        </div>

        {/* System Status Bar */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <HealthIndicator 
            health={healthData}
            loading={healthLoading}
            error={healthError}
            onRefresh={checkHealth}
            lastCheck={lastCheck}
            compact
          />
          <div className="lg:col-span-2">
            {renderSeasonStatus()}
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left Column - Generation Form */}
          <div className="lg:col-span-1 space-y-6">
            <ParlayGenerationForm
              sport="nba"
              onGenerate={handleGenerateParlay}
              loading={generationLoading}
              error={generationError}
              disabled={healthError !== null}
            />
            
            {/* System Stats Card */}
            {renderSystemStats()}
          </div>

          {/* Right Column - Results */}
          <div className="lg:col-span-2">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="generate" className="flex items-center space-x-2">
                  <TrendingUp className="h-4 w-4" />
                  <span>Generate</span>
                </TabsTrigger>
                <TabsTrigger value="result" className="flex items-center space-x-2">
                  <Brain className="h-4 w-4" />
                  <span>Result</span>
                  {parlayData && parlayData.success && (
                    <Badge variant="secondary" className="ml-1">
                      {parlayData.parlay.legs.length}
                    </Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger value="analysis" className="flex items-center space-x-2">
                  <Activity className="h-4 w-4" />
                  <span>Analysis</span>
                </TabsTrigger>
                <TabsTrigger value="ml" className="flex items-center space-x-2">
                  <Target className="h-4 w-4" />
                  <span>ML Insights</span>
                </TabsTrigger>
              </TabsList>

              <TabsContent value="generate" className="mt-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Welcome to NBA Parlay Generation</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-muted-foreground">
                      Use the form on the left to generate AI-powered NBA parlays. Our system features:
                    </p>
                    <ul className="space-y-2 text-sm">
                      <li className="flex items-center space-x-2">
                        <Badge variant="outline">✓</Badge>
                        <span>ML-enhanced predictions with prop trainers</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <Badge variant="outline">✓</Badge>
                        <span>Few-shot learning from high-confidence examples</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <Badge variant="outline">✓</Badge>
                        <span>Expert sports betting knowledge base</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <Badge variant="outline">✓</Badge>
                        <span>BioBERT injury classification</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <Badge variant="outline">✓</Badge>
                        <span>Expected value and Kelly criterion calculations</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <Badge variant="outline">✓</Badge>
                        <span>Cross-book arbitrage detection</span>
                      </li>
                    </ul>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="result" className="mt-6">
                {parlayData ? (
                  <ParlayCard
                    parlay={parlayData}
                    onShare={handleShare}
                    onCopy={handleCopy}
                    onViewDetails={() => setActiveTab('analysis')}
                  />
                ) : (
                  <Card>
                    <CardContent className="pt-6 text-center">
                      <div className="text-muted-foreground">
                        No parlay generated yet. Use the form to create your first NBA parlay with ML predictions.
                      </div>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="analysis" className="mt-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Detailed Analysis</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {parlayData && parlayData.success ? (
                      <>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <div className="text-sm text-muted-foreground">Agent Version</div>
                            <div className="font-medium">{parlayData.agent_version}</div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground">Generated</div>
                            <div className="font-medium">
                              {new Date(parlayData.generated_at).toLocaleString()}
                            </div>
                          </div>
                          {parlayData.parlay.expected_value !== undefined && (
                            <div>
                              <div className="text-sm text-muted-foreground">Expected Value</div>
                              <div className={`font-medium ${parlayData.parlay.expected_value >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {formatPercentage(parlayData.parlay.expected_value)}
                              </div>
                            </div>
                          )}
                          {parlayData.parlay.kelly_percentage !== undefined && (
                            <div>
                              <div className="text-sm text-muted-foreground">Kelly Percentage</div>
                              <div className="font-medium">
                                {formatPercentage(parlayData.parlay.kelly_percentage)}
                              </div>
                            </div>
                          )}
                        </div>
                        
                        {parlayData.parlay.knowledge_insights && parlayData.parlay.knowledge_insights.length > 0 && (
                          <div>
                            <div className="text-sm font-medium mb-2">Knowledge Base Insights</div>
                            <ul className="space-y-1">
                              {parlayData.parlay.knowledge_insights.map((insight, index) => (
                                <li key={index} className="text-sm text-muted-foreground">
                                  • {insight}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {parlayData.parlay.expert_guidance && parlayData.parlay.expert_guidance.length > 0 && (
                          <div>
                            <div className="text-sm font-medium mb-2">Expert Guidance</div>
                            <ul className="space-y-1">
                              {parlayData.parlay.expert_guidance.map((guidance, index) => (
                                <li key={index} className="text-sm text-muted-foreground">
                                  • {guidance}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="text-center text-muted-foreground">
                        Generate a parlay to see detailed analysis with ML insights
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="ml" className="mt-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Brain className="h-5 w-5" />
                      <span>ML & AI Insights</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {healthData && healthData.components?.nba_agent ? (
                      <div className="space-y-4">
                        <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
                          <h4 className="font-medium text-blue-800 mb-2">NBA Agent Status</h4>
                          <div className="text-sm text-blue-700">
                            The NBA agent uses FewShotEnhancedParlayStrategistAgent with ML prop trainers 
                            and BioBERT injury classification for enhanced predictions.
                          </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="bg-green-50 border border-green-200 p-3 rounded-lg">
                            <div className="font-medium text-green-800">Few-Shot Learning</div>
                            <div className="text-sm text-green-700 mt-1">
                              Uses successful historical examples to improve recommendations
                            </div>
                          </div>
                          
                          <div className="bg-purple-50 border border-purple-200 p-3 rounded-lg">
                            <div className="font-medium text-purple-800">Prop Trainers</div>
                            <div className="text-sm text-purple-700 mt-1">
                              ML models trained on NBA prop data for EV-based selection
                            </div>
                          </div>
                          
                          <div className="bg-orange-50 border border-orange-200 p-3 rounded-lg">
                            <div className="font-medium text-orange-800">Injury Analysis</div>
                            <div className="text-sm text-orange-700 mt-1">
                              BioBERT classifier analyzes injury reports and impacts
                            </div>
                          </div>
                          
                          <div className="bg-cyan-50 border border-cyan-200 p-3 rounded-lg">
                            <div className="font-medium text-cyan-800">Knowledge Base</div>
                            <div className="text-sm text-cyan-700 mt-1">
                              RAG system with 1,590+ sports betting knowledge chunks
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center text-muted-foreground">
                        <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-yellow-500" />
                        NBA ML agent not available. Check system health for details.
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NBARefactored;



