/**
 * Fixed Landing page - simplified version that works reliably
 */

import React from 'react';
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
  Star
} from 'lucide-react';

const LandingFixed: React.FC = () => {
  const navigate = useNavigate();

  const features = [
    {
      icon: <Brain className="h-8 w-8 text-blue-600" />,
      title: "AI-Powered Analysis",
      description: "Advanced ML models with expert knowledge integration"
    },
    {
      icon: <Target className="h-8 w-8 text-green-600" />,
      title: "Expert Knowledge",
      description: "1,590+ curated chunks from sports betting experts"
    },
    {
      icon: <TrendingUp className="h-8 w-8 text-purple-600" />,
      title: "Real-Time Data",
      description: "Live odds monitoring with arbitrage detection"
    },
    {
      icon: <Zap className="h-8 w-8 text-orange-600" />,
      title: "Performance Optimized",
      description: "Production-ready architecture with monitoring"
    }
  ];

  const sports = [
    {
      icon: <Football className="h-12 w-12 text-orange-600" />,
      name: "NFL",
      description: "Advanced NFL parlay generation with knowledge base insights",
      path: "/nfl"
    },
    {
      icon: <Basketball className="h-12 w-12 text-purple-600" />,
      name: "NBA", 
      description: "ML-enhanced NBA predictions with confidence scoring",
      path: "/nba"
    }
  ];

  const stats = [
    { label: "Knowledge Chunks", value: "1,590+" },
    { label: "ML Models", value: "6+" },
    { label: "API Endpoints", value: "7+" },
    { label: "Sports Supported", value: "2" }
  ];

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
                  <div className="text-sm text-muted-foreground mb-1">{stat.label}</div>
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
            <Card key={sport.name} className="h-full hover:shadow-lg transition-all">
              <CardContent className="pt-6">
                <div className="text-center space-y-4">
                  <div className="flex justify-center">
                    {sport.icon}
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold">{sport.name}</h3>
                    <p className="text-muted-foreground mt-2">{sport.description}</p>
                  </div>

                  <Button 
                    className="w-full" 
                    onClick={() => navigate(sport.path)}
                  >
                    Generate Parlays
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </div>
              </CardContent>
            </Card>
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
              <Card key={index} className="h-full">
                <CardHeader>
                  <div className="flex items-center space-x-3">
                    {feature.icon}
                    <CardTitle className="text-xl">{feature.title}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">{feature.description}</p>
                </CardContent>
              </Card>
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

export default LandingFixed;



