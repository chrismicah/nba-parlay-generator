import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Trash2, TrendingUp, ShoppingCart } from "lucide-react";

interface ParlayLeg {
  id: string;
  team: string;
  bet: string;
  odds: number;
  expectedValue: number;
}

interface ParlaySlipProps {
  legs: ParlayLeg[];
  onRemoveLeg: (id: string) => void;
  onClearSlip: () => void;
}

const ParlaySlip = ({ legs, onRemoveLeg, onClearSlip }: ParlaySlipProps) => {
  const [wager, setWager] = useState<number>(25);
  const [isOpen, setIsOpen] = useState(false);

  const totalOdds = legs.reduce((total, leg) => total * (leg.odds > 0 ? leg.odds / 100 + 1 : 100 / Math.abs(leg.odds) + 1), 1);
  const americanOdds = totalOdds >= 2 ? Math.round((totalOdds - 1) * 100) : Math.round(-100 / (totalOdds - 1));
  const potentialPayout = wager * totalOdds;
  const avgExpectedValue = legs.length > 0 ? legs.reduce((sum, leg) => sum + leg.expectedValue, 0) / legs.length : 0;

  const formatOdds = (odds: number) => {
    return odds > 0 ? `+${odds}` : `${odds}`;
  };

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger asChild>
        <Button 
          className="fixed bottom-4 right-4 md:bottom-8 md:right-8 z-50 shadow-elevated"
          size="lg"
          disabled={legs.length === 0}
        >
          <ShoppingCart className="h-5 w-5 mr-2" />
          Parlay Slip ({legs.length})
        </Button>
      </SheetTrigger>
      
      <SheetContent side="right" className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle className="flex items-center justify-between">
            <span>Parlay Slip</span>
            {legs.length > 0 && (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={onClearSlip}
                className="text-destructive hover:text-destructive"
              >
                Clear All
              </Button>
            )}
          </SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-4">
          {legs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <ShoppingCart className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No bets added yet</p>
              <p className="text-sm">Add bets from the parlay generators</p>
            </div>
          ) : (
            <>
              {/* Parlay Legs */}
              <div className="space-y-3">
                {legs.map((leg) => (
                  <Card key={leg.id} className="p-3">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="font-medium text-sm">{leg.team}</div>
                        <div className="text-xs text-muted-foreground">{leg.bet}</div>
                        <div className="flex items-center mt-1 space-x-2">
                          <span className="text-sm font-mono">{formatOdds(leg.odds)}</span>
                          <Badge 
                            variant={leg.expectedValue > 0 ? "default" : "secondary"}
                            className="text-xs"
                          >
                            EV: {leg.expectedValue > 0 ? "+" : ""}{leg.expectedValue.toFixed(1)}%
                          </Badge>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onRemoveLeg(leg.id)}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>

              <Separator />

              {/* Wager Input */}
              <div className="space-y-2">
                <Label htmlFor="wager">Wager Amount</Label>
                <Input
                  id="wager"
                  type="number"
                  value={wager}
                  onChange={(e) => setWager(Number(e.target.value))}
                  className="form-input"
                  min="1"
                  max="10000"
                />
              </div>

              {/* Parlay Summary */}
              <Card className="p-4 bg-gradient-surface">
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Total Odds:</span>
                    <span className="font-mono font-medium">{formatOdds(americanOdds)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Potential Payout:</span>
                    <span className="font-medium">${potentialPayout.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Expected Value:</span>
                    <Badge 
                      variant={avgExpectedValue > 0 ? "default" : "secondary"}
                      className="font-mono"
                    >
                      {avgExpectedValue > 0 ? "+" : ""}{avgExpectedValue.toFixed(1)}%
                    </Badge>
                  </div>
                </div>
              </Card>

              {/* Place Bet Button */}
              <Button 
                className="w-full success-gradient"
                size="lg"
                disabled={avgExpectedValue <= 0}
              >
                <TrendingUp className="h-5 w-5 mr-2" />
                Place Parlay Bet
              </Button>
              
              {avgExpectedValue <= 0 && (
                <p className="text-xs text-destructive text-center">
                  Negative expected value - consider adjusting your picks
                </p>
              )}
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default ParlaySlip;