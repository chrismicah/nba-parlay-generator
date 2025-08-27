import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import StatCard from "@/components/StatCard";
import ParlaySlip from "@/components/ParlaySlip";
import { Badge } from "@/components/ui/badge";
import { 
  TrendingUp, 
  DollarSign, 
  Target, 
  BarChart3, 
  Zap,
  ArrowRight,
  Clock,
  Star
} from "lucide-react";
import { NavLink } from "react-router-dom";

interface ParlayLeg {
  id: string;
  team: string;
  bet: string;
  odds: number;
  expectedValue: number;
}

const Dashboard = () => {
  const [parlayLegs, setParlayLegs] = useState<ParlayLeg[]>([]);

  const removeLeg = (id: string) => {
    setParlayLegs(legs => legs.filter(leg => leg.id !== id));
  };

  const clearSlip = () => {
    setParlayLegs([]);
  };

  // Mock data for dashboard widgets
  const recentParlays = [
    { id: 1, legs: 4, odds: "+1250", status: "won", payout: "$312.50", sport: "NBA" },
    { id: 2, legs: 3, odds: "+650", status: "pending", payout: "$162.50", sport: "NFL" },
    { id: 3, legs: 5, odds: "+2100", status: "lost", payout: "$0.00", sport: "NBA" },
  ];

  const topOpportunities = [
    { team: "Lakers vs Warriors", bet: "Over 228.5", odds: "+110", ev: "+12.3", sport: "NBA" },
    { team: "Chiefs vs Bills", bet: "Mahomes 275+ Yards", odds: "-105", ev: "+8.7", sport: "NFL" },
    { team: "Celtics vs Heat", bet: "Tatum 25+ Pts", odds: "+120", ev: "+15.1", sport: "NBA" },
  ];

  return (
    <div className="flex-1 md:ml-64">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Dashboard</h1>
            <p className="text-muted-foreground">Welcome back! Here's your betting overview.</p>
          </div>
          <Badge variant="secondary" className="flex items-center space-x-1">
            <Clock className="h-4 w-4" />
            <span>Last updated: 2 mins ago</span>
          </Badge>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Total Bankroll"
            value="$2,450.00"
            change="+12.5%"
            changeType="positive"
            icon={<DollarSign className="h-5 w-5 text-primary" />}
          />
          <StatCard
            title="ROI This Month"
            value="18.7%"
            change="+3.2%"
            changeType="positive"
            icon={<TrendingUp className="h-5 w-5 text-success" />}
          />
          <StatCard
            title="Hit Rate"
            value="64.2%"
            change="-2.1%"
            changeType="negative"
            icon={<Target className="h-5 w-5 text-warning" />}
          />
          <StatCard
            title="Active Parlays"
            value="3"
            badge="Pending"
            icon={<Zap className="h-5 w-5 text-primary" />}
          />
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Parlay Generators */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Target className="h-5 w-5" />
                <span>Quick Parlay Generators</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <NavLink to="/nba">
                <Button className="w-full justify-between group hover:scale-[1.02] smooth-transition">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-primary rounded-full"></div>
                    <span>NBA Parlays</span>
                  </div>
                  <ArrowRight className="h-4 w-4 group-hover:translate-x-1 smooth-transition" />
                </Button>
              </NavLink>
              <NavLink to="/nfl">
                <Button variant="secondary" className="w-full justify-between group hover:scale-[1.02] smooth-transition">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-secondary-foreground rounded-full"></div>
                    <span>NFL Parlays</span>
                  </div>
                  <ArrowRight className="h-4 w-4 group-hover:translate-x-1 smooth-transition" />
                </Button>
              </NavLink>
            </CardContent>
          </Card>

          {/* System Health */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <BarChart3 className="h-5 w-5" />
                <span>System Health</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm">Data Freshness</span>
                <Badge variant="default" className="success-gradient">Live</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">AI Model Status</span>
                <Badge variant="default">Optimal</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Market Coverage</span>
                <Badge variant="secondary">98.7%</Badge>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Activity & Opportunities */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Parlays */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Parlays</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentParlays.map((parlay) => (
                  <div key={parlay.id} className="flex items-center justify-between p-3 rounded-lg border bg-secondary/20">
                    <div className="flex items-center space-x-3">
                      <Badge variant="outline">{parlay.sport}</Badge>
                      <div>
                        <div className="font-medium">{parlay.legs}-leg parlay</div>
                        <div className="text-sm text-muted-foreground">{parlay.odds} odds</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`font-medium ${
                        parlay.status === "won" ? "text-success" :
                        parlay.status === "lost" ? "text-destructive" :
                        "text-muted-foreground"
                      }`}>
                        {parlay.payout}
                      </div>
                      <Badge 
                        variant={parlay.status === "won" ? "default" : parlay.status === "lost" ? "destructive" : "secondary"}
                        className="text-xs"
                      >
                        {parlay.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Top +EV Opportunities */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Star className="h-5 w-5 text-primary" />
                <span>Top +EV Opportunities</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {topOpportunities.map((opp, index) => (
                  <div key={index} className="flex items-center justify-between p-3 rounded-lg border bg-success/5 border-success/20">
                    <div className="flex items-center space-x-3">
                      <Badge variant="outline">{opp.sport}</Badge>
                      <div>
                        <div className="font-medium">{opp.team}</div>
                        <div className="text-sm text-muted-foreground">{opp.bet}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-mono text-sm">{opp.odds}</div>
                      <Badge variant="default" className="text-xs">
                        EV: {opp.ev}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <ParlaySlip 
        legs={parlayLegs} 
        onRemoveLeg={removeLeg} 
        onClearSlip={clearSlip} 
      />
    </div>
  );
};

export default Dashboard;