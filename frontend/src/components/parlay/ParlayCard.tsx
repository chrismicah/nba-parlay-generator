/**
 * Enhanced ParlayCard component aligned with backend ParlayResponse schema
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { 
  TrendingUp, 
  TrendingDown, 
  Target, 
  Brain, 
  Calendar,
  ExternalLink,
  Copy,
  Share
} from 'lucide-react';
import { ParlayResponse, ParlayLeg } from '@/types/api';
import { formatOdds, formatCurrency, formatPercentage } from '@/lib/formatters';

interface ParlayCardProps {
  parlay: ParlayResponse;
  onShare?: () => void;
  onCopy?: () => void;
  onViewDetails?: () => void;
}

const ParlayCard: React.FC<ParlayCardProps> = ({ 
  parlay, 
  onShare, 
  onCopy, 
  onViewDetails 
}) => {
  const { success, sport, parlay: parlayData, generated_at, agent_version } = parlay;

  if (!success) {
    return (
      <Card className="border-destructive/20 bg-destructive/5">
        <CardContent className="pt-6">
          <div className="flex items-center space-x-2 text-destructive">
            <TrendingDown className="h-5 w-5" />
            <span className="font-medium">Generation Failed</span>
            <span>{parlay.message || 'No viable parlay found'}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  const confidenceColor = parlayData.confidence >= 0.7 
    ? 'text-green-600 bg-green-100' 
    : parlayData.confidence >= 0.5 
    ? 'text-yellow-600 bg-yellow-100'
    : 'text-red-600 bg-red-100';

  const evColor = parlayData.expected_value && parlayData.expected_value > 0
    ? 'text-green-600'
    : 'text-red-600';

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            <Target className="h-5 w-5" />
            <span>{sport.toUpperCase()} Parlay</span>
            <Badge variant="outline">{parlayData.legs.length} legs</Badge>
          </CardTitle>
          
          <div className="flex items-center space-x-2">
            {parlayData.total_odds && (
              <Badge variant="secondary">
                {formatOdds(parlayData.total_odds)} odds
              </Badge>
            )}
            <Badge className={confidenceColor}>
              {formatPercentage(parlayData.confidence)} confidence
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Parlay Legs */}
        <div className="space-y-3">
          {parlayData.legs.map((leg: ParlayLeg, index: number) => (
            <div key={index} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
              <div className="flex-1">
                <div className="font-medium text-sm">{leg.game}</div>
                <div className="text-muted-foreground text-xs">
                  {leg.market}: {leg.selection}
                </div>
              </div>
              <div className="text-right">
                <div className="font-medium">{formatOdds(leg.odds)}</div>
                <div className="text-xs text-muted-foreground">{leg.book}</div>
              </div>
            </div>
          ))}
        </div>

        <Separator />

        {/* Expected Value & Kelly */}
        {(parlayData.expected_value !== undefined || parlayData.kelly_percentage !== undefined) && (
          <div className="grid grid-cols-2 gap-4">
            {parlayData.expected_value !== undefined && (
              <div className="text-center">
                <div className="text-sm text-muted-foreground">Expected Value</div>
                <div className={`font-medium ${evColor}`}>
                  {parlayData.expected_value > 0 ? '+' : ''}{formatPercentage(parlayData.expected_value)}
                </div>
              </div>
            )}
            {parlayData.kelly_percentage !== undefined && (
              <div className="text-center">
                <div className="text-sm text-muted-foreground">Kelly %</div>
                <div className="font-medium">
                  {formatPercentage(parlayData.kelly_percentage)}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Reasoning */}
        {parlayData.reasoning && (
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <Brain className="h-4 w-4" />
              <span className="text-sm font-medium">AI Analysis</span>
            </div>
            <p className="text-sm text-muted-foreground bg-muted/30 p-3 rounded-lg">
              {parlayData.reasoning}
            </p>
          </div>
        )}

        {/* Knowledge Insights */}
        {parlayData.knowledge_insights && parlayData.knowledge_insights.length > 0 && (
          <div className="space-y-2">
            <div className="text-sm font-medium">Expert Insights</div>
            <ul className="space-y-1">
              {parlayData.knowledge_insights.map((insight, index) => (
                <li key={index} className="text-sm text-muted-foreground flex items-start space-x-2">
                  <TrendingUp className="h-3 w-3 mt-0.5 text-blue-500" />
                  <span>{insight}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recommendation */}
        {parlayData.recommendation && (
          <div className="bg-blue-50 border border-blue-200 p-3 rounded-lg">
            <div className="text-sm font-medium text-blue-800">Recommendation</div>
            <div className="text-sm text-blue-700 mt-1">{parlayData.recommendation}</div>
          </div>
        )}

        <Separator />

        {/* Actions */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-xs text-muted-foreground">
            <Calendar className="h-3 w-3" />
            <span>Generated {new Date(generated_at).toLocaleString()}</span>
          </div>
          
          <div className="flex items-center space-x-2">
            {onCopy && (
              <Button variant="outline" size="sm" onClick={onCopy}>
                <Copy className="h-3 w-3 mr-1" />
                Copy
              </Button>
            )}
            {onShare && (
              <Button variant="outline" size="sm" onClick={onShare}>
                <Share className="h-3 w-3 mr-1" />
                Share
              </Button>
            )}
            {onViewDetails && (
              <Button variant="default" size="sm" onClick={onViewDetails}>
                <ExternalLink className="h-3 w-3 mr-1" />
                Details
              </Button>
            )}
          </div>
        </div>

        {/* Agent Version */}
        <div className="text-xs text-muted-foreground text-center">
          Generated by {agent_version}
        </div>
      </CardContent>
    </Card>
  );
};

export default ParlayCard;



