/**
 * Refactored Dashboard with comprehensive system overview
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Dashboard as DashboardIcon,
  Activity, 
  TrendingUp, 
  Users,
  Server,
  Brain,
  Database,
  Zap,
  AlertTriangle,
  CheckCircle,
  Clock,
  BarChart3,
  Cpu,
  HardDrive,
  Network
} from 'lucide-react';

// Components
import HealthIndicator from '@/components/system/HealthIndicator';
import KnowledgeSearch from '@/components/knowledge/KnowledgeSearch';

// Hooks
import { useHealthCheck, useSystemStats } from '@/hooks/useApi';
import { formatUptime, formatPercentage, formatCompactNumber } from '@/lib/formatters';

const DashboardRefactored: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview');

  // API hooks
  const {
    data: healthData,
    loading: healthLoading,
    error: healthError,
    checkHealth,
    lastCheck
  } = useHealthCheck(true, 30000);

  const {
    data: statsData,
    loading: statsLoading,
    getStats
  } = useSystemStats(true, 60000);

  // Component status overview
  const getComponentStatus = () => {
    if (!healthData?.components) return {};

    return {
      nfl_agent: healthData.components.nfl_agent?.status || 'unknown',
      nba_agent: healthData.components.nba_agent?.status || 'unknown',
      knowledge_base: healthData.components.knowledge_base?.status || 'unknown',
      ml_models: healthData.components.ml_models?.status || 'unknown',
      database: healthData.components.database?.status || 'unknown',
      web_server: healthData.components.web_server || 'unknown'
    };
  };

  const componentStatus = getComponentStatus();

  const StatusCard: React.FC<{
    title: string;
    status: string;
    icon: React.ReactNode;
    description: string;
  }> = ({ title, status, icon, description }) => {
    const isHealthy = status === 'healthy' || status === 'ready' || status === 'connected' || status === 'running';
    const statusColor = isHealthy ? 'text-green-600' : 'text-red-600';
    const bgColor = isHealthy ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200';

    return (
      <Card className={bgColor}>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className={statusColor}>{icon}</div>
              <div>
                <div className="font-medium">{title}</div>
                <div className="text-sm text-muted-foreground">{description}</div>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              {isHealthy ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-red-600" />
              )}
              <Badge variant={isHealthy ? "default" : "destructive"}>
                {status}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };

  const MetricCard: React.FC<{
    title: string;
    value: string | number;
    description?: string;
    trend?: 'up' | 'down' | 'neutral';
    icon: React.ReactNode;
  }> = ({ title, value, description, trend, icon }) => (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-muted-foreground">{title}</div>
            <div className="text-2xl font-bold">{value}</div>
            {description && (
              <div className="text-xs text-muted-foreground">{description}</div>
            )}
          </div>
          <div className="flex items-center space-x-2">
            {icon}
            {trend && (
              <TrendingUp className={`h-4 w-4 ${
                trend === 'up' ? 'text-green-500' : 
                trend === 'down' ? 'text-red-500' : 'text-gray-500'
              }`} />
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="flex-1 p-6 bg-gradient-to-br from-slate-50 to-gray-100 min-h-screen">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center space-x-3">
              <DashboardIcon className="h-8 w-8 text-blue-600" />
              <h1 className="text-3xl font-bold text-slate-800">System Dashboard</h1>
            </div>
            <p className="text-slate-600 mt-1">
              Monitor system health, performance metrics, and component status
            </p>
          </div>
          
          <div className="flex items-center space-x-2">
            {lastCheck && (
              <div className="text-sm text-muted-foreground">
                Last updated: {lastCheck.toLocaleTimeString()}
              </div>
            )}
            <Button 
              variant="outline" 
              onClick={checkHealth}
              disabled={healthLoading}
            >
              <Activity className={`h-4 w-4 mr-2 ${healthLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Main Status */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3">
            <HealthIndicator 
              health={healthData}
              loading={healthLoading}
              error={healthError}
              onRefresh={checkHealth}
              lastCheck={lastCheck}
            />
          </div>
          
          <div className="space-y-4">
            {statsData && (
              <MetricCard
                title="System Uptime"
                value={formatUptime(statsData.uptime_seconds)}
                description="Continuous operation"
                icon={<Clock className="h-5 w-5 text-blue-500" />}
                trend="neutral"
              />
            )}
            
            {healthData?.sports_enabled && (
              <Card>
                <CardContent className="pt-6">
                  <div className="text-sm font-medium mb-2">Sports Available</div>
                  <div className="space-y-2">
                    <Badge variant={healthData.sports_enabled.nfl ? "default" : "secondary"}>
                      🏈 NFL {healthData.sports_enabled.nfl ? 'Active' : 'Inactive'}
                    </Badge>
                    <Badge variant={healthData.sports_enabled.nba ? "default" : "secondary"}>
                      🏀 NBA {healthData.sports_enabled.nba ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>

        {/* Detailed Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="components">Components</TabsTrigger>
            <TabsTrigger value="performance">Performance</TabsTrigger>
            <TabsTrigger value="knowledge">Knowledge Base</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="mt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {statsData?.performance_metrics && (
                <>
                  <MetricCard
                    title="Success Rate"
                    value={formatPercentage(statsData.performance_metrics.success_rate)}
                    description="API request success"
                    icon={<CheckCircle className="h-5 w-5 text-green-500" />}
                    trend="up"
                  />
                  
                  <MetricCard
                    title="Avg Response"
                    value={`${statsData.performance_metrics.avg_response_time_ms}ms`}
                    description="API response time"
                    icon={<Zap className="h-5 w-5 text-yellow-500" />}
                    trend="neutral"
                  />
                  
                  <MetricCard
                    title="Total Requests"
                    value={formatCompactNumber(statsData.performance_metrics.total_requests)}
                    description="Lifetime requests"
                    icon={<BarChart3 className="h-5 w-5 text-purple-500" />}
                    trend="up"
                  />
                </>
              )}
              
              <MetricCard
                title="Components"
                value={`${Object.values(componentStatus).filter(s => s === 'healthy' || s === 'ready' || s === 'running').length}/${Object.keys(componentStatus).length}`}
                description="Healthy components"
                icon={<Server className="h-5 w-5 text-blue-500" />}
                trend="neutral"
              />
            </div>
          </TabsContent>

          <TabsContent value="components" className="mt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <StatusCard
                title="NFL Agent"
                status={componentStatus.nfl_agent}
                icon={<Brain className="h-6 w-6" />}
                description="NFL parlay generation with knowledge base"
              />
              
              <StatusCard
                title="NBA Agent"
                status={componentStatus.nba_agent}
                icon={<Brain className="h-6 w-6" />}
                description="NBA parlay generation with ML predictions"
              />
              
              <StatusCard
                title="Knowledge Base"
                status={componentStatus.knowledge_base}
                icon={<Database className="h-6 w-6" />}
                description="RAG system with 1,590+ expert chunks"
              />
              
              <StatusCard
                title="ML Models"
                status={componentStatus.ml_models}
                icon={<Cpu className="h-6 w-6" />}
                description="Prop trainers and injury classifiers"
              />
              
              <StatusCard
                title="Database"
                status={componentStatus.database}
                icon={<HardDrive className="h-6 w-6" />}
                description="Historical data and model storage"
              />
              
              <StatusCard
                title="Web Server"
                status={componentStatus.web_server}
                icon={<Network className="h-6 w-6" />}
                description="FastAPI application server"
              />
            </div>
          </TabsContent>

          <TabsContent value="performance" className="mt-6">
            <div className="space-y-6">
              {statsData ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Card>
                    <CardHeader>
                      <CardTitle>System Metrics</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div>
                        <div className="text-sm text-muted-foreground">Uptime</div>
                        <div className="text-lg font-semibold">{formatUptime(statsData.uptime_seconds)}</div>
                      </div>
                      
                      <div>
                        <div className="text-sm text-muted-foreground">Last Restart</div>
                        <div className="text-lg font-semibold">
                          {new Date(Date.now() - statsData.uptime_seconds * 1000).toLocaleDateString()}
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  {statsData.performance_metrics && (
                    <>
                      <Card>
                        <CardHeader>
                          <CardTitle>API Performance</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <div>
                            <div className="text-sm text-muted-foreground">Success Rate</div>
                            <div className="text-lg font-semibold text-green-600">
                              {formatPercentage(statsData.performance_metrics.success_rate)}
                            </div>
                          </div>
                          
                          <div>
                            <div className="text-sm text-muted-foreground">Avg Response Time</div>
                            <div className="text-lg font-semibold">
                              {statsData.performance_metrics.avg_response_time_ms}ms
                            </div>
                          </div>
                        </CardContent>
                      </Card>

                      <Card>
                        <CardHeader>
                          <CardTitle>Usage Statistics</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <div>
                            <div className="text-sm text-muted-foreground">Total Requests</div>
                            <div className="text-lg font-semibold">
                              {statsData.performance_metrics.total_requests.toLocaleString()}
                            </div>
                          </div>
                          
                          <div>
                            <div className="text-sm text-muted-foreground">Requests/Hour</div>
                            <div className="text-lg font-semibold">
                              {Math.round(statsData.performance_metrics.total_requests / (statsData.uptime_seconds / 3600)).toLocaleString()}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </>
                  )}
                </div>
              ) : (
                <Card>
                  <CardContent className="pt-6 text-center">
                    <div className="text-muted-foreground">
                      {statsLoading ? 'Loading performance metrics...' : 'Performance metrics not available'}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          <TabsContent value="knowledge" className="mt-6">
            <KnowledgeSearch 
              placeholder="Search sports betting knowledge base..."
              maxResults={10}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default DashboardRefactored;



