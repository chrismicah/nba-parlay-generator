import React from 'react';
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AnimatedBackground } from "./components/ui/animated-background";
import { FloatingNav } from "./components/ui/floating-navbar";
import { GlowCard } from "./components/ui/glow-card";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { motion } from "framer-motion";
import { 
  Football, 
  Basketball,
  BarChart3,
  BookOpen,
  TrendingUp,
  Target,
  Brain,
  Zap,
  ArrowRight
} from "lucide-react";

// Navigation items
const navItems = [
  { name: "NFL", link: "/nfl", icon: <Football className="h-4 w-4" /> },
  { name: "NBA", link: "/nba", icon: <Basketball className="h-4 w-4" /> },
  { name: "Dashboard", link: "/dashboard", icon: <BarChart3 className="h-4 w-4" /> },
  { name: "Knowledge", link: "/knowledge", icon: <BookOpen className="h-4 w-4" /> },
];

// Modern Landing Page
const ModernLanding = () => {
  const features = [
    {
      icon: <Brain className="h-8 w-8" />,
      title: "AI-Powered Analysis",
      description: "Advanced ML models with expert knowledge integration",
      color: "blue"
    },
    {
      icon: <Target className="h-8 w-8" />,
      title: "Expert Knowledge",
      description: "1,590+ curated chunks from sports betting experts",
      color: "purple"
    },
    {
      icon: <TrendingUp className="h-8 w-8" />,
      title: "Real-Time Data",
      description: "Live odds monitoring with arbitrage detection",
      color: "orange"
    },
    {
      icon: <Zap className="h-8 w-8" />,
      title: "Performance Optimized",
      description: "Production-ready architecture with monitoring",
      color: "green"
    }
  ];

  const sports = [
    {
      icon: "🏈",
      title: "NFL Parlays",
      description: "Advanced NFL analysis with real game data and expert insights",
      path: "/nfl",
      color: "orange"
    },
    {
      icon: "🏀",
      title: "NBA Parlays",
      description: "ML-enhanced NBA predictions with confidence scoring",
      path: "/nba",
      color: "purple"
    }
  ];

  return (
    <AnimatedBackground>
      <FloatingNav navItems={navItems} />
      
      <div className="pt-32 pb-20 px-4">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center max-w-6xl mx-auto mb-20"
        >
          <motion.h1 
            className="text-6xl md:text-8xl font-bold mb-8 bg-gradient-to-r from-white via-blue-100 to-purple-100 bg-clip-text text-transparent"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.8 }}
          >
            AI-Powered
            <br />
            <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text">
              Parlay Generation
            </span>
          </motion.h1>
          
          <motion.p 
            className="text-xl md:text-2xl text-white/80 mb-12 max-w-3xl mx-auto leading-relaxed"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.8 }}
          >
            Professional sports betting analysis powered by machine learning, 
            expert knowledge base, and real-time data integration
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 0.8 }}
            className="flex flex-col sm:flex-row gap-4 justify-center"
          >
            <Button variant="glow" size="xl" className="group">
              Get Started
              <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </Button>
            <Button variant="outline" size="xl" className="bg-white/10 border-white/20 text-white hover:bg-white/20">
              View Demo
            </Button>
          </motion.div>
        </motion.div>

        {/* Sports Cards */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8, duration: 0.8 }}
          className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto mb-20"
        >
          {sports.map((sport, index) => (
            <GlowCard
              key={index}
              glowColor={sport.color}
              onClick={() => window.location.href = sport.path}
              className="h-full"
            >
              <div className="text-center space-y-4">
                <div className="text-6xl mb-4">{sport.icon}</div>
                <h3 className="text-2xl font-bold text-gray-900">{sport.title}</h3>
                <p className="text-gray-600 leading-relaxed">{sport.description}</p>
                <Button variant={sport.color === "orange" ? "nfl" : "nba"} className="w-full">
                  Generate Parlays
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </GlowCard>
          ))}
        </motion.div>

        {/* Features Grid */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.0, duration: 0.8 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-7xl mx-auto"
        >
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.2 + index * 0.1, duration: 0.6 }}
            >
              <GlowCard glowColor={feature.color} className="h-full">
                <div className="text-center space-y-4">
                  <div className="text-blue-600">{feature.icon}</div>
                  <h3 className="text-lg font-semibold text-gray-900">{feature.title}</h3>
                  <p className="text-gray-600 text-sm leading-relaxed">{feature.description}</p>
                </div>
              </GlowCard>
            </motion.div>
          ))}
        </motion.div>

        {/* Stats Section */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.4, duration: 0.8 }}
          className="mt-20 max-w-4xl mx-auto"
        >
          <Card className="bg-white/10 border-white/20 backdrop-blur-lg">
            <CardHeader>
              <CardTitle className="text-center text-white text-2xl">System Statistics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
                {[
                  { label: "Knowledge Chunks", value: "1,590+" },
                  { label: "ML Models", value: "6+" },
                  { label: "API Endpoints", value: "7+" },
                  { label: "Sports Supported", value: "2" }
                ].map((stat, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 1.6 + index * 0.1, duration: 0.6 }}
                  >
                    <div className="text-3xl font-bold text-white mb-2">{stat.value}</div>
                    <div className="text-white/70 text-sm">{stat.label}</div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </AnimatedBackground>
  );
};

// Modern NFL Page
const ModernNFL = () => {
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [parlay, setParlay] = React.useState(null);

  const generateParlay = async () => {
    setIsGenerating(true);
    try {
      const response = await fetch('http://localhost:8000/generate-nfl-parlay', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_legs: 3, min_total_odds: 2.0 })
      });
      const data = await response.json();
      setParlay(data);
    } catch (error) {
      console.error('Error:', error);
    }
    setIsGenerating(false);
  };

  return (
    <AnimatedBackground>
      <FloatingNav navItems={navItems} />
      
      <div className="pt-32 pb-20 px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center max-w-4xl mx-auto mb-12"
        >
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-orange-400 to-red-400 bg-clip-text text-transparent">
            🏈 NFL Parlay Generator
          </h1>
          <p className="text-xl text-white/80 mb-8">
            AI-powered NFL analysis with real game data and expert insights
          </p>
          
          <Button
            variant="nfl"
            size="xl"
            onClick={generateParlay}
            disabled={isGenerating}
            className="relative"
          >
            {isGenerating ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="mr-2"
              >
                ⚡
              </motion.div>
            ) : (
              <Football className="mr-2 h-6 w-6" />
            )}
            {isGenerating ? 'Generating NFL Parlay...' : 'Generate NFL Parlay'}
          </Button>
        </motion.div>

        {parlay && (
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="max-w-4xl mx-auto"
          >
            <GlowCard glowColor="orange" className="mb-8">
              <div className="space-y-6">
                <div className="border-b border-gray-200 pb-4">
                  <h3 className="text-2xl font-bold text-gray-900 mb-2">Generated NFL Parlay</h3>
                  <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                    <span><strong>Confidence:</strong> {parlay.confidence_percentage}%</span>
                    <span><strong>Total Odds:</strong> +{Math.round((parlay.total_odds - 1) * 100)}</span>
                    <span><strong>Expected Value:</strong> {parlay.expected_value?.toFixed(1)}%</span>
                  </div>
                </div>
                
                <div className="space-y-3">
                  {parlay.legs?.map((leg, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="bg-orange-50 border-l-4 border-orange-500 p-4 rounded-r-lg"
                    >
                      <div className="font-semibold text-gray-900 mb-1">
                        {leg.game_info || 'NFL Game'}
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-700">
                          <strong>{leg.market}:</strong> {leg.selection}
                        </span>
                        <span className={`font-bold ${leg.odds > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {leg.odds > 0 ? '+' : ''}{leg.odds}
                        </span>
                      </div>
                    </motion.div>
                  ))}
                </div>

                {parlay.season_note && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <div className="flex items-start">
                      <span className="text-yellow-600 mr-2">⚠️</span>
                      <div>
                        <strong className="text-yellow-800">Season Note:</strong>
                        <p className="text-yellow-700 mt-1">{parlay.season_note}</p>
                      </div>
                    </div>
                  </div>
                )}

                {parlay.recommendation && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="flex items-start">
                      <span className="text-green-600 mr-2">💡</span>
                      <div>
                        <strong className="text-green-800">Recommendation:</strong>
                        <p className="text-green-700 mt-1">{parlay.recommendation}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </GlowCard>
          </motion.div>
        )}
      </div>
    </AnimatedBackground>
  );
};

// Modern NBA Page (similar structure)
const ModernNBA = () => {
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [parlay, setParlay] = React.useState(null);

  const generateParlay = async () => {
    setIsGenerating(true);
    try {
      const response = await fetch('http://localhost:8000/generate-nba-parlay', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_legs: 3, min_total_odds: 2.0 })
      });
      const data = await response.json();
      setParlay(data);
    } catch (error) {
      console.error('Error:', error);
    }
    setIsGenerating(false);
  };

  return (
    <AnimatedBackground>
      <FloatingNav navItems={navItems} />
      
      <div className="pt-32 pb-20 px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center max-w-4xl mx-auto mb-12"
        >
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            🏀 NBA Parlay Generator
          </h1>
          <p className="text-xl text-white/80 mb-8">
            ML-enhanced NBA predictions with confidence scoring and expert analysis
          </p>
          
          <Button
            variant="nba"
            size="xl"
            onClick={generateParlay}
            disabled={isGenerating}
            className="relative"
          >
            {isGenerating ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="mr-2"
              >
                ⚡
              </motion.div>
            ) : (
              <Basketball className="mr-2 h-6 w-6" />
            )}
            {isGenerating ? 'Generating NBA Parlay...' : 'Generate NBA Parlay'}
          </Button>
        </motion.div>

        {parlay && (
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="max-w-4xl mx-auto"
          >
            <GlowCard glowColor="purple" className="mb-8">
              <div className="space-y-6">
                <div className="border-b border-gray-200 pb-4">
                  <h3 className="text-2xl font-bold text-gray-900 mb-2">Generated NBA Parlay</h3>
                  <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                    <span><strong>Confidence:</strong> {parlay.confidence_percentage}%</span>
                    <span><strong>Total Odds:</strong> +{Math.round((parlay.total_odds - 1) * 100)}</span>
                    <span><strong>Expected Value:</strong> {parlay.expected_value?.toFixed(1)}%</span>
                  </div>
                </div>
                
                <div className="space-y-3">
                  {parlay.legs?.map((leg, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="bg-purple-50 border-l-4 border-purple-500 p-4 rounded-r-lg"
                    >
                      <div className="font-semibold text-gray-900 mb-1">
                        {leg.game_info || 'NBA Game'}
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-700">
                          <strong>{leg.market}:</strong> {leg.selection}
                        </span>
                        <span className={`font-bold ${leg.odds > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {leg.odds > 0 ? '+' : ''}{leg.odds}
                        </span>
                      </div>
                    </motion.div>
                  ))}
                </div>

                {parlay.recommendation && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="flex items-start">
                      <span className="text-green-600 mr-2">💡</span>
                      <div>
                        <strong className="text-green-800">Recommendation:</strong>
                        <p className="text-green-700 mt-1">{parlay.recommendation}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </GlowCard>
          </motion.div>
        )}
      </div>
    </AnimatedBackground>
  );
};

// Modern Dashboard
const ModernDashboard = () => {
  const [health, setHealth] = React.useState(null);

  React.useEffect(() => {
    fetch('http://localhost:8000/health')
      .then(res => res.json())
      .then(setHealth)
      .catch(console.error);
  }, []);

  return (
    <AnimatedBackground>
      <FloatingNav navItems={navItems} />
      
      <div className="pt-32 pb-20 px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center max-w-4xl mx-auto mb-12"
        >
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
            📊 System Dashboard
          </h1>
          <p className="text-xl text-white/80 mb-8">
            Real-time monitoring and system performance analytics
          </p>
        </motion.div>

        {health && (
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="max-w-4xl mx-auto"
          >
            <GlowCard glowColor="blue">
              <div className="space-y-6">
                <div className="border-b border-gray-200 pb-4">
                  <h3 className="text-2xl font-bold text-green-700">✅ System Health Status</h3>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-green-700 mb-1 capitalize">{health.status}</div>
                    <div className="text-green-600 text-sm">System Status</div>
                  </div>
                  
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-blue-700 mb-1">
                      {Math.round(health.uptime_seconds / 60)} min
                    </div>
                    <div className="text-blue-600 text-sm">Uptime</div>
                  </div>
                  
                  <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 text-center">
                    <div className="text-lg font-bold text-orange-700 mb-1">
                      {new Date(health.timestamp).toLocaleTimeString()}
                    </div>
                    <div className="text-orange-600 text-sm">Last Check</div>
                  </div>
                </div>
              </div>
            </GlowCard>
          </motion.div>
        )}
      </div>
    </AnimatedBackground>
  );
};

// Modern Knowledge Page
const ModernKnowledge = () => {
  const knowledgeItems = [
    { icon: '📖', title: '1,590+ Knowledge Chunks', desc: 'Curated expert analysis and insights', color: 'blue' },
    { icon: '🤖', title: '6+ ML Models', desc: 'Advanced machine learning algorithms', color: 'purple' },
    { icon: '📊', title: 'Real-time Data', desc: 'Live odds monitoring and updates', color: 'orange' },
    { icon: '⚡', title: 'AI Analysis Engine', desc: 'Intelligent parlay generation system', color: 'green' }
  ];

  return (
    <AnimatedBackground>
      <FloatingNav navItems={navItems} />
      
      <div className="pt-32 pb-20 px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center max-w-4xl mx-auto mb-12"
        >
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-green-400 to-emerald-400 bg-clip-text text-transparent">
            📚 Knowledge Base
          </h1>
          <p className="text-xl text-white/80 mb-8">
            Expert analysis database with curated sports betting insights
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-6xl mx-auto">
          {knowledgeItems.map((item, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.2, duration: 0.6 }}
            >
              <GlowCard glowColor={item.color} className="h-full">
                <div className="text-center space-y-4">
                  <div className="text-6xl mb-4">{item.icon}</div>
                  <h3 className="text-xl font-bold text-gray-900">{item.title}</h3>
                  <p className="text-gray-600 leading-relaxed">{item.desc}</p>
                </div>
              </GlowCard>
            </motion.div>
          ))}
        </div>
      </div>
    </AnimatedBackground>
  );
};

// Main App Component
const AppModern = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ModernLanding />} />
        <Route path="/nfl" element={<ModernNFL />} />
        <Route path="/nba" element={<ModernNBA />} />
        <Route path="/dashboard" element={<ModernDashboard />} />
        <Route path="/knowledge" element={<ModernKnowledge />} />
      </Routes>
    </BrowserRouter>
  );
};

export default AppModern;



