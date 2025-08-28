/**
 * Refactored Landing page with modern design and system integration
 */

import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  ArrowRight,
  Basketball,
  Football,
  Brain,
  Target,
  TrendingUp,
  Zap,
  BookOpen,
  Activity,
  CheckCircle,
  Star,
  Users,
  BarChart3
} from 'lucide-react';

// Components
import HealthIndicator from '@/components/system/HealthIndicator';

// Hooks
import { useHealthCheck } from '@/hooks/useApi';

const LandingRefactored: React.FC = () => {
  const navigate = useNavigate();

  const {
    data: healthData,
    loading: healthLoading,
    error: healthError,
    checkHealth
  } = useHealthCheck(false); // Don't auto-refresh on landing

  // Check system health on load
  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  const features = [
    {
      icon: <Brain className="h-8 w-8 text-blue-600" />,
      title: "AI-Powered Analysis",
      description: "Advanced ML models with few-shot learning and expert knowledge integration",
      highlights: ["BioBERT injury classification", "Prop trainer predictions", "RAG knowledge base"]
    },
    {
      icon: <Target className="h-8 w-8 text-green-600" />,
      title: "Expert Knowledge",
      description: "1,590+ curated chunks from Ed Miller and Wayne Winston's sports betting books",
      highlights: ["Expected value calculations", "Kelly criterion optimization", "Market efficiency analysis"]
    },
    {
      icon: <TrendingUp className="h-8 w-8 text-purple-600" />,
      title: "Real-Time Data",
      description: "Live odds monitoring with cross-book arbitrage detection",
      highlights: ["Season-aware analysis", "Line movement tracking", "Multi-book integration"]
    },
    {
      icon: <Zap className="h-8 w-8 text-orange-600" />,
      title: "Performance Optimized",
      description: "Production-ready architecture with comprehensive monitoring",
      highlights: ["Auto-refresh health checks", "Error recovery", "Type-safe APIs"]
    }
  ];

  const sports = [
    {
      icon: <Football className="h-12 w-12 text-orange-600" />,
      name: "NFL",
      description: "Advanced NFL parlay generation with knowledge base insights",
      features: ["Season awareness", "Real game schedules", "Expert strategies"],
      path: "/nfl",
      enabled: healthData?.sports_enabled?.nfl
    },
    {
      icon: <Basketball className="h-12 w-12 text-purple-600" />,
      name: "NBA", 
      description: "ML-enhanced NBA predictions with confidence scoring",
      features: ["Few-shot learning", "Injury analysis", "Prop predictions"],
      path: "/nba",
      enabled: healthData?.sports_enabled?.nba
    }
  ];

  const stats = [
    { label: "Knowledge Chunks", value: "1,590+", icon: <BookOpen className="h-5 w-5" /> },
    { label: "ML Models", value: "6+", icon: <Brain className="h-5 w-5" /> },
    { label: "API Endpoints", value: "7+", icon: <Activity className="h-5 w-5" /> },
    { label: "Sports Supported", value: "2", icon: <Star className="h-5 w-5" /> }
  ];

  const FeatureCard: React.FC<{ feature: typeof features[0] }> = ({ feature }) => (
    <Card className="h-full hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-center space-x-3">
          {feature.icon}
          <CardTitle className="text-xl">{feature.title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-muted-foreground">{feature.description}</p>
        <ul className="space-y-2">
          {feature.highlights.map((highlight, index) => (
            <li key={index} className="flex items-center space-x-2 text-sm">
              <CheckCircle className="h-4 w-4 text-green-500" />
              <span>{highlight}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );

  const SportCard: React.FC<{ sport: typeof sports[0] }> = ({ sport }) => (
    <Card className={`h-full hover:shadow-lg transition-all ${sport.enabled ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-gray-50'}`}>
      <CardContent className="pt-6">
        <div className="text-center space-y-4">
          <div className="flex justify-center">
            {sport.icon}
          </div>
          <div>
            <div className="flex items-center justify-center space-x-2">
              <h3 className="text-2xl font-bold">{sport.name}</h3>
              <Badge variant={sport.enabled ? "default" : "secondary"}>
                {sport.enabled ? "Active" : "Offline"}
              </Badge>
            </div>
            <p className="text-muted-foreground mt-2">{sport.description}</p>
          </div>
          
          <ul className="space-y-1 text-sm">
            {sport.features.map((feature, index) => (
              <li key={index} className="flex items-center justify-center space-x-2">
                <CheckCircle className="h-3 w-3 text-green-500" />
                <span>{feature}</span>
              </li>
            ))}
          </ul>

          <Button 
            className="w-full" 
            onClick={() => navigate(sport.path)}
            disabled={!sport.enabled}
            variant={sport.enabled ? "default" : "outline"}
          >
            {sport.enabled ? "Generate Parlays" : "Coming Soon"}
            <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 py-16 sm:px-6 lg:px-8">
          <div className="text-center space-y-8">
            
            {/* Main Headlines */}
            <div className="space-y-4">
              <h1 className="text-5xl md:text-7xl font-bold text-slate-800 leading-tight">
                AI-Powered
                <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  {" "}Parlay{" "}
                </span>
                Generation
              </h1>
              
              <p className="text-xl md:text-2xl text-slate-600 max-w-4xl mx-auto leading-relaxed">
                Professional sports betting analysis powered by machine learning, 
                expert knowledge base, and real-time data integration
              </p>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-2xl mx-auto">
              {stats.map((stat, index) => (
                <div key={index} className="text-center">
                  <div className="flex items-center justify-center space-x-1 text-muted-foreground mb-1">
                    {stat.icon}
                    <span className="text-sm">{stat.label}</span>
                  </div>
                  <div className="text-2xl font-bold text-slate-800">{stat.value}</div>
                </div>
              ))}
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-4">
              <Button 
                size="lg" 
                className="text-lg px-8 py-6"
                onClick={() => navigate('/dashboard')}
              >
                <Activity className="h-5 w-5 mr-2" />
                View Dashboard
              </Button>
              
              <Button 
                variant="outline" 
                size="lg" 
                className="text-lg px-8 py-6"
                onClick={() => navigate('/knowledge')}
              >
                <BookOpen className="h-5 w-5 mr-2" />
                Explore Knowledge Base
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* System Status */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        <HealthIndicator 
          health={healthData}
          loading={healthLoading}
          error={healthError}
          onRefresh={checkHealth}
          compact={false}
        />
      </div>

      {/* Sports Cards */}
      <div className="max-w-7xl mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold text-slate-800 mb-4">
            Choose Your Sport
          </h2>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Generate AI-powered parlays for NFL and NBA with expert analysis and real-time data
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {sports.map((sport) => (
            <SportCard key={sport.name} sport={sport} />
          ))}
        </div>
      </div>

      {/* Features Section */}
      <div className="bg-slate-50 py-16">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-slate-800 mb-4">
              Advanced Features
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              Built with production-ready architecture and cutting-edge AI technology
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {features.map((feature, index) => (
              <FeatureCard key={index} feature={feature} />
            ))}
          </div>
        </div>
      </div>

      {/* Footer CTA */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 py-16">
        <div className="max-w-4xl mx-auto text-center px-4">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Ready to Start?
          </h2>
          <p className="text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
            Access professional-grade sports betting analysis with AI-powered insights
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-4">
            <Button 
              size="lg" 
              variant="secondary"
              className="text-lg px-8 py-6"
              onClick={() => navigate('/nfl')}
            >
              <Football className="h-5 w-5 mr-2" />
              NFL Parlays
            </Button>
            
            <Button 
              size="lg" 
              variant="secondary"
              className="text-lg px-8 py-6"
              onClick={() => navigate('/nba')}
            >
              <Basketball className="h-5 w-5 mr-2" />
              NBA Parlays
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LandingRefactored;



