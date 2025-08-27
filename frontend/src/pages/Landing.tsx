import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  ArrowRight, 
  BarChart3, 
  Brain, 
  CheckCircle, 
  DollarSign, 
  Star, 
  Target, 
  TrendingUp, 
  Zap
} from "lucide-react";
import { NavLink } from "react-router-dom";

const Landing = () => {
  const features = [
    {
      icon: <Brain className="h-8 w-8" />,
      title: "AI-Powered Analysis",
      description: "Advanced machine learning models analyze thousands of data points to identify profitable opportunities."
    },
    {
      icon: <TrendingUp className="h-8 w-8" />,
      title: "Expected Value Focus",
      description: "Every recommendation comes with calculated expected value - bet smart, not on vibes."
    },
    {
      icon: <Target className="h-8 w-8" />,
      title: "Smart Parlays",
      description: "Generate optimized parlay combinations with positive EV across NBA, NFL, and more."
    },
    {
      icon: <BarChart3 className="h-8 w-8" />,
      title: "Performance Analytics",
      description: "Track your ROI, hit rates, and bankroll growth with detailed analytics dashboards."
    }
  ];

  const pricingTiers = [
    {
      name: "Free",
      price: "$0",
      period: "forever",
      description: "Perfect for getting started",
      features: [
        "2 parlays per day",
        "10 knowledge searches",
        "Basic analytics",
        "NBA & NFL coverage"
      ],
      limitations: [
        "No arbitrage opportunities",
        "Limited historical data"
      ]
    },
    {
      name: "Pro",
      price: "$29.99",
      period: "month",
      description: "For serious bettors",
      features: [
        "50 parlays per day",
        "100 knowledge searches",
        "Advanced analytics",
        "Arbitrage opportunities",
        "All sports coverage",
        "Priority support"
      ],
      popular: true
    },
    {
      name: "Enterprise",
      price: "$199.99",
      period: "month",
      description: "For professional operations",
      features: [
        "Unlimited parlays",
        "Unlimited searches",
        "API access",
        "Custom models",
        "White-label options",
        "Dedicated support"
      ]
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-hero">
      {/* Header */}
      <header className="border-b bg-card/50 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <DollarSign className="h-8 w-8 text-primary" />
            <span className="text-xl font-bold">SportsBet AI</span>
          </div>
          
          <div className="flex items-center space-x-4">
            <NavLink to="/dashboard">
              <Button variant="ghost">Dashboard</Button>
            </NavLink>
            <NavLink to="/pricing">
              <Button>Get Started</Button>
            </NavLink>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20 px-4">
        <div className="container mx-auto text-center">
          <Badge className="mb-6 success-gradient" variant="secondary">
            <Zap className="h-4 w-4 mr-1" />
            Powered by Advanced AI
          </Badge>
          
          <h1 className="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-transparent">
            Smart NBA Parlays
          </h1>
          
          <p className="text-xl md:text-2xl text-success font-semibold mb-4">
            Backed by Stats, Not Vibes
          </p>
          
          <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
            Stop betting on gut feelings. Our AI analyzes thousands of data points to generate 
            profitable parlay combinations with positive expected value.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <NavLink to="/dashboard">
              <Button size="lg" className="success-gradient success-glow">
                <Target className="h-5 w-5 mr-2" />
                Generate Parlays
                <ArrowRight className="h-5 w-5 ml-2" />
              </Button>
            </NavLink>
            <NavLink to="/analytics">
              <Button size="lg" variant="outline">
                <BarChart3 className="h-5 w-5 mr-2" />
                View Analytics
              </Button>
            </NavLink>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4 bg-card/20 backdrop-blur-sm">
        <div className="container mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Why Choose SportsBet AI?
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Professional-grade tools that give you the edge over sportsbooks
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <Card key={index} className="stat-card group hover:scale-105">
                <CardHeader className="text-center">
                  <div className="mx-auto mb-4 p-3 rounded-lg bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground smooth-transition">
                    {feature.icon}
                  </div>
                  <CardTitle className="text-xl">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground text-center">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section className="py-16 px-4">
        <div className="container mx-auto text-center">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="space-y-2">
              <div className="text-3xl font-bold text-primary">18.7%</div>
              <div className="text-muted-foreground">Average Monthly ROI</div>
            </div>
            <div className="space-y-2">
              <div className="text-3xl font-bold text-primary">10,000+</div>
              <div className="text-muted-foreground">Winning Parlays Generated</div>
            </div>
            <div className="space-y-2">
              <div className="text-3xl font-bold text-primary">64%</div>
              <div className="text-muted-foreground">Average Hit Rate</div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-20 px-4 bg-card/20 backdrop-blur-sm">
        <div className="container mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Choose Your Plan
            </h2>
            <p className="text-lg text-muted-foreground">
              Start free, upgrade when you're ready to maximize profits
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {pricingTiers.map((tier, index) => (
              <Card key={index} className={`relative ${tier.popular ? 'stat-card-success' : 'stat-card'}`}>
                {tier.popular && (
                  <Badge className="absolute -top-2 left-1/2 transform -translate-x-1/2 success-gradient">
                    <Star className="h-4 w-4 mr-1" />
                    Most Popular
                  </Badge>
                )}
                
                <CardHeader className="text-center">
                  <CardTitle className="text-2xl">{tier.name}</CardTitle>
                  <div className="mt-4">
                    <span className="text-4xl font-bold">{tier.price}</span>
                    <span className="text-muted-foreground">/{tier.period}</span>
                  </div>
                  <p className="text-muted-foreground">{tier.description}</p>
                </CardHeader>
                
                <CardContent className="space-y-4">
                  <ul className="space-y-3">
                    {tier.features.map((feature, featureIndex) => (
                      <li key={featureIndex} className="flex items-center space-x-2">
                        <CheckCircle className="h-5 w-5 text-success" />
                        <span>{feature}</span>
                      </li>
                    ))}
                    {tier.limitations?.map((limitation, limitIndex) => (
                      <li key={limitIndex} className="flex items-center space-x-2 text-muted-foreground">
                        <div className="h-5 w-5 rounded-full border-2 border-muted-foreground/30" />
                        <span>{limitation}</span>
                      </li>
                    ))}
                  </ul>
                  
                  <NavLink to="/dashboard" className="block">
                    <Button 
                      className={`w-full ${tier.popular ? 'success-gradient' : ''}`}
                      variant={tier.popular ? "default" : "outline"}
                    >
                      {tier.price === "$0" ? "Start Free" : "Subscribe Now"}
                    </Button>
                  </NavLink>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4">
        <div className="container mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Ready to Beat the Books?
          </h2>
          <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
            Join thousands of smart bettors who've switched from guessing to winning with data-driven parlays.
          </p>
          
          <NavLink to="/dashboard">
            <Button size="lg" className="success-gradient success-glow">
              <Zap className="h-5 w-5 mr-2" />
              Start Winning Today
              <ArrowRight className="h-5 w-5 ml-2" />
            </Button>
          </NavLink>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t bg-card/50 backdrop-blur-sm py-8 px-4">
        <div className="container mx-auto text-center text-muted-foreground">
          <p>&copy; 2024 SportsBet AI. Built with data, powered by intelligence.</p>
        </div>
      </footer>
    </div>
  );
};

export default Landing;