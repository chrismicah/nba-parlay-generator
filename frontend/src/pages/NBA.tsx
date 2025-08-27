import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import ParlaySlip from "@/components/ParlaySlip";
import { toast } from "@/hooks/use-toast";
import { apiService } from "@/services/api";
import type { ParlayRequest, ParlayResponse } from "@/config/api";
import { 
  RefreshCw, 
  TrendingUp, 
  Filter, 
  Plus,
  Target,
  AlertTriangle,
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
}

const NBA = () => {
  const [parlayLegs, setParlayLegs] = useState<ParlayLeg[]>([]);
  const [numLegs, setNumLegs] = useState(3);
  const [riskLevel, setRiskLevel] = useState("medium");
  const [minEV, setMinEV] = useState(5);
  const [isGenerating, setIsGenerating] = useState(false);
  const [lastGenerated, setLastGenerated] = useState<ParlayResponse | null>(null);
  const [systemHealth, setSystemHealth] = useState<any>(null);

  // Mock NBA betting opportunities
  const opportunities: BettingOpportunity[] = [
    {
      id: "1",
      matchup: "Lakers vs Warriors",
      bet: "Over 228.5 Total Points",
      odds: 110,
      impliedProb: 47.6,
      trueProb: 58.9,
      expectedValue: 12.3,
      confidence: 87,
      bookmaker: "DraftKings"
    },
    {
      id: "2", 
      matchup: "Celtics vs Heat",
      bet: "Jayson Tatum 25+ Points",
      odds: 120,
      impliedProb: 45.5,
      trueProb: 62.1,
      expectedValue: 15.1,
      confidence: 91,
      bookmaker: "FanDuel"
    },
    {
      id: "3",
      matchup: "Nuggets vs Suns",
      bet: "Nikola Jokic Triple-Double",
      odds: 350,
      impliedProb: 22.2,
      trueProb: 31.8,
      expectedValue: 8.7,
      confidence: 73,
      bookmaker: "BetMGM"
    },
    {
      id: "4",
      matchup: "Bucks vs 76ers",
      bet: "Under 225.5 Total Points",
      odds: -105,
      impliedProb: 51.2,
      trueProb: 57.4,
      expectedValue: 6.2,
      confidence: 68,
      bookmaker: "Caesars"
    },
    {
      id: "5",
      matchup: "Clippers vs Mavs",
      bet: "Luka Doncic 30+ Points",
      odds: -120,
      impliedProb: 54.5,
      trueProb: 71.2,
      expectedValue: 9.8,
      confidence: 82,
      bookmaker: "DraftKings"
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
          description: "Unable to connect to the NBA backend system",
          variant: "destructive",
        });
      }
    };
    
    loadSystemHealth();
  }, []);

  const generateParlay = async () => {
    setIsGenerating(true);
    
    try {
      const request: ParlayRequest = {
        target_legs: numLegs,
        min_total_odds: riskLevel === "conservative" ? 3.0 : riskLevel === "medium" ? 5.0 : 8.0,
        include_arbitrage: true,
        sport: "nba"
      };
      
      const response = await apiService.generateNBAParlay(request);
      setLastGenerated(response);
      
      if (response.success && response.parlay.legs) {
        // Convert API response to frontend format
        const newLegs: ParlayLeg[] = response.parlay.legs.map((leg, index) => ({
          id: `api-${index}`,
          team: leg.game,
          bet: leg.selection,
          odds: leg.odds > 1 ? Math.round((leg.odds - 1) * 100) : Math.round(-100 / (leg.odds - 1)),
          expectedValue: response.parlay.expected_value || 0
        }));
        
        setParlayLegs(newLegs);
        
        toast({
          title: "NBA Parlay Generated!",
          description: `Generated ${newLegs.length}-leg parlay with ${response.parlay.confidence}% confidence`,
        });
      } else {
        // Fallback to mock data if API fails
        generateMockParlay();
      }
    } catch (error) {
      console.error('Failed to generate parlay:', error);
      toast({
        title: "Generation Failed",
        description: "Using sample data. Check backend connection.",
        variant: "destructive",
      });
      
      // Fallback to mock data
      generateMockParlay();
    } finally {
      setIsGenerating(false);
    }
  };

  const generateMockParlay = () => {
    // Simple algorithm: take top N opportunities by EV
    const bestOpportunities = filteredOpportunities.slice(0, numLegs);
    const newLegs = bestOpportunities.map(opp => ({
      id: `generated-${opp.id}`,
      team: opp.matchup,
      bet: opp.bet,
      odds: opp.odds,
      expectedValue: opp.expectedValue
    }));
    
    setParlayLegs(newLegs);
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
              <Target className="h-8 w-8 text-primary" />
              <span>NBA Parlay Generator</span>
            </h1>
            <p className="text-muted-foreground">AI-powered NBA betting opportunities with positive expected value</p>
          </div>
          <Button variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh Data
          </Button>
        </div>

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

        {/* System Status & Market Analysis */}
        {systemHealth && (
          <Card className={`border-${systemHealth.components.nba_agent.status === 'ready' ? 'success' : 'warning'}/20 bg-${systemHealth.components.nba_agent.status === 'ready' ? 'success' : 'warning'}/5`}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="h-5 w-5" />
                  <span className="font-medium">System Status:</span>
                  <span>NBA Agent {systemHealth.components.nba_agent.status === 'ready' ? 'Online' : 'Offline'}</span>
                  <Badge variant={systemHealth.components.nba_agent.status === 'ready' ? 'default' : 'destructive'}>
                    {systemHealth.status}
                  </Badge>
                </div>
                {lastGenerated && (
                  <Badge variant="outline" className="text-xs">
                    Last Generated: {new Date(lastGenerated.generated_at).toLocaleTimeString()}
                  </Badge>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Betting Opportunities Table */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Top NBA Opportunities</span>
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

export default NBA;