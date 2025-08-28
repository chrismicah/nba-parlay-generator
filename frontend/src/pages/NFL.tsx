import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "@/components/ui/use-toast";
import ParlaySlip from "@/components/ParlaySlip";
import { apiService } from "../services/api";
import { ParlayResponse } from "../config/api";
import { 
  RefreshCw, 
  TrendingUp, 
  Filter, 
  Plus,
  Zap,
  AlertTriangle,
  Clock,
  Loader2
} from "lucide-react";

interface ParlayLeg {
  id: string;
  team: string;
  bet: string;
  odds: number;
  expectedValue: number;
}

interface BettingOpportunity {
  id: string;
  matchup: string;
  bet: string;
  odds: number;
  impliedProb: number;
  trueProb: number;
  expectedValue: number;
  confidence: number;
  bookmaker: string;
  gameTime: string;
}

const NFL = () => {
  const [parlayLegs, setParlayLegs] = useState<ParlayLeg[]>([]);
  const [numLegs, setNumLegs] = useState(3);
  const [riskLevel, setRiskLevel] = useState("medium");
  const [minEV, setMinEV] = useState(5);
  const [isGenerating, setIsGenerating] = useState(false);
  const [lastGenerated, setLastGenerated] = useState<ParlayResponse | null>(null);
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [seasonStatus, setSeasonStatus] = useState<any>(null);

  // Mock NFL betting opportunities
  const opportunities: BettingOpportunity[] = [
    {
      id: "1",
      matchup: "Chiefs vs Bills",
      bet: "Patrick Mahomes 275+ Passing Yards",
      odds: -105,
      impliedProb: 51.2,
      trueProb: 60.5,
      expectedValue: 8.7,
      confidence: 84,
      bookmaker: "DraftKings",
      gameTime: "Sunday 1:00 PM"
    },
    {
      id: "2", 
      matchup: "Cowboys vs Eagles",
      bet: "Over 52.5 Total Points",
      odds: 110,
      impliedProb: 47.6,
      trueProb: 59.2,
      expectedValue: 11.4,
      confidence: 78,
      bookmaker: "FanDuel",
      gameTime: "Sunday 4:25 PM"
    },
    {
      id: "3",
      matchup: "Rams vs 49ers",
      bet: "Cooper Kupp Anytime TD",
      odds: 165,
      impliedProb: 37.7,
      trueProb: 48.3,
      expectedValue: 14.2,
      confidence: 71,
      bookmaker: "BetMGM",
      gameTime: "Monday 8:15 PM"
    },
    {
      id: "4",
      matchup: "Ravens vs Steelers",
      bet: "Under 44.5 Total Points",
      odds: -110,
      impliedProb: 52.4,
      trueProb: 61.8,
      expectedValue: 9.1,
      confidence: 82,
      bookmaker: "Caesars",
      gameTime: "Sunday 1:00 PM"
    },
    {
      id: "5",
      matchup: "Packers vs Bears",
      bet: "Jordan Love 2+ Passing TDs",
      odds: -140,
      impliedProb: 58.3,
      trueProb: 71.5,
      expectedValue: 7.8,
      confidence: 76,
      bookmaker: "ESPN BET",
      gameTime: "Sunday 1:00 PM"
    },
    {
      id: "6",
      matchup: "Dolphins vs Jets",
      bet: "Tua Tagovailoa Under 1.5 INTs",
      odds: -180,
      impliedProb: 64.3,
      trueProb: 79.2,
      expectedValue: 12.1,
      confidence: 88,
      bookmaker: "DraftKings",
      gameTime: "Sunday 1:00 PM"
    }
  ];

  const filteredOpportunities = opportunities
    .filter(opp => opp.expectedValue >= minEV)
    .sort((a, b) => b.expectedValue - a.expectedValue);

  const addToParlaySlip = (opportunity: BettingOpportunity) => {
    const newLeg: ParlayLeg = {
      id: opportunity.id,
      team: opportunity.matchup,
      bet: opportunity.bet,
      odds: opportunity.odds,
      expectedValue: opportunity.expectedValue
    };
    
    setParlayLegs(prev => [...prev, newLeg]);
  };

  const removeLeg = (id: string) => {
    setParlayLegs(legs => legs.filter(leg => leg.id !== id));
  };

  const clearSlip = () => {
    setParlayLegs([]);
  };

  // Load system health on component mount
  useEffect(() => {
    const loadSystemHealth = async () => {
      try {
        const health = await apiService.getHealth();
        setSystemHealth(health);
      } catch (error) {
        console.error('Failed to load system health:', error);
        toast({
          title: "Connection Error",
          description: "Unable to connect to the NFL backend system",
          variant: "destructive",
        });
      }
    };

    loadSystemHealth();
  }, []);

  const generateParlay = async () => {
    setIsGenerating(true);
    
    try {
      const response = await apiService.generateNFLParlay({
        target_legs: numLegs,
        min_total_odds: 5.0,
        include_arbitrage: true
      });

      setLastGenerated(response);

      if (response.success) {
        // Convert API response to frontend format
        const newLegs = response.parlay.legs.map((leg, index) => ({
          id: `generated-${index}`,
          team: leg.game,
          bet: `${leg.market}: ${leg.selection}`,
          odds: leg.odds,
          expectedValue: response.parlay.expected_value || 0
        }));
        
        setParlayLegs(newLegs);
        
        toast({
          title: "NFL Parlay Generated!",
          description: `Created ${newLegs.length}-leg parlay with ${response.parlay.confidence}% confidence`,
        });
      } else {
        // Handle season-aware response
        setParlayLegs([]);
        setSeasonStatus(response);
        
        toast({
          title: "NFL Season Status",
          description: response.parlay?.reasoning || "NFL regular season hasn't started yet",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error('Failed to generate NFL parlay:', error);
      
      // Fallback to mock data if API fails
      const bestOpportunities = filteredOpportunities.slice(0, numLegs);
      const mockLegs = bestOpportunities.map(opp => ({
        id: `mock-${opp.id}`,
        team: opp.matchup,
        bet: opp.bet,
        odds: opp.odds,
        expectedValue: opp.expectedValue
      }));
      
      setParlayLegs(mockLegs);
      
      toast({
        title: "Using Demo Data",
        description: "Connected to demo mode - NFL backend unavailable",
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const formatOdds = (odds: number) => {
    return odds > 0 ? `+${odds}` : `${odds}`;
  };

  const getEVBadgeVariant = (ev: number) => {
    if (ev >= 10) return "default";
    if (ev >= 5) return "secondary";
    return "outline";
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return "text-success";
    if (confidence >= 60) return "text-warning";
    return "text-destructive";
  };

  return (
    <div className="flex-1 md:ml-64">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center space-x-2">
              <Zap className="h-8 w-8 text-primary" />
              <span>NFL Parlay Generator</span>
            </h1>
            <p className="text-muted-foreground">AI-powered NFL betting opportunities with positive expected value</p>
          </div>
          <Button variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh Data
          </Button>
        </div>

        {/* Week Info Alert */}
        <Card className="border-primary/20 bg-primary/5">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2 text-primary">
              <Clock className="h-5 w-5" />
              <span className="font-medium">Week 12 NFL:</span>
              <span>14 games analyzed • Best opportunities updated every 5 minutes</span>
            </div>
          </CardContent>
        </Card>

        {/* Parlay Configuration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Filter className="h-5 w-5" />
              <span>Parlay Configuration</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label htmlFor="legs">Number of Legs</Label>
                <Select value={numLegs.toString()} onValueChange={(value) => setNumLegs(Number(value))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="2">2 Legs</SelectItem>
                    <SelectItem value="3">3 Legs</SelectItem>
                    <SelectItem value="4">4 Legs</SelectItem>
                    <SelectItem value="5">5 Legs</SelectItem>
                    <SelectItem value="6">6 Legs</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="risk">Risk Level</Label>
                <Select value={riskLevel} onValueChange={setRiskLevel}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="conservative">Conservative</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="aggressive">Aggressive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="minev">Min Expected Value (%)</Label>
                <Input
                  type="number"
                  value={minEV}
                  onChange={(e) => setMinEV(Number(e.target.value))}
                  min="0"
                  max="50"
                  className="form-input"
                />
              </div>
              
              <div className="flex items-end">
                <Button 
                  onClick={generateParlay} 
                  disabled={isGenerating}
                  className="w-full success-gradient"
                >
                  {isGenerating ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <TrendingUp className="h-4 w-4 mr-2" />
                  )}
                  {isGenerating ? 'Generating...' : 'Generate Parlay'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Season Status Alert */}
        {seasonStatus && !seasonStatus.success ? (
          <Card className="border-destructive/20 bg-destructive/5">
            <CardContent className="pt-6">
              <div className="flex items-center space-x-2 text-destructive">
                <Clock className="h-5 w-5" />
                <span className="font-medium">NFL Season Status:</span>
                <span>{seasonStatus.parlay?.reasoning || "NFL regular season hasn't started yet"}</span>
              </div>
            </CardContent>
          </Card>
        ) : systemHealth && (
          <Card className={`border-${systemHealth.components ? 'success' : 'warning'}/20 bg-${systemHealth.components ? 'success' : 'warning'}/5`}>
            <CardContent className="pt-6">
              <div className="flex items-center space-x-2 text-success">
                <Zap className="h-5 w-5" />
                <span className="font-medium">System Status:</span>
                <span>NFL analysis system connected and ready</span>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Betting Opportunities Table */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Top NFL Opportunities</span>
              <Badge variant="secondary">{filteredOpportunities.length} matches found</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Matchup</TableHead>
                    <TableHead>Bet</TableHead>
                    <TableHead>Game Time</TableHead>
                    <TableHead>Odds</TableHead>
                    <TableHead>Expected Value</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Book</TableHead>
                    <TableHead>Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredOpportunities.map((opp) => (
                    <TableRow 
                      key={opp.id} 
                      className={`data-row ${opp.expectedValue >= 10 ? 'positive-ev' : ''}`}
                    >
                      <TableCell className="font-medium">{opp.matchup}</TableCell>
                      <TableCell>{opp.bet}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{opp.gameTime}</TableCell>
                      <TableCell className="font-mono">{formatOdds(opp.odds)}</TableCell>
                      <TableCell>
                        <Badge variant={getEVBadgeVariant(opp.expectedValue)}>
                          +{opp.expectedValue.toFixed(1)}%
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className={getConfidenceColor(opp.confidence)}>
                          {opp.confidence}%
                        </span>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{opp.bookmaker}</TableCell>
                      <TableCell>
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => addToParlaySlip(opp)}
                          disabled={parlayLegs.some(leg => leg.id === opp.id)}
                        >
                          <Plus className="h-4 w-4 mr-1" />
                          Add
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>

      <ParlaySlip 
        legs={parlayLegs} 
        onRemoveLeg={removeLeg} 
        onClearSlip={clearSlip} 
      />
    </div>
  );
};

export default NFL;