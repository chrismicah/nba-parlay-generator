import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import StatCard from "@/components/StatCard";
import { 
  BarChart3, 
  TrendingUp, 
  Target, 
  DollarSign,
  Calendar,
  Download,
  Filter
} from "lucide-react";
import { 
  LineChart, 
  Line, 
  AreaChart, 
  Area, 
  PieChart, 
  Pie, 
  Cell, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from "recharts";

const Analytics = () => {
  // Mock analytics data
  const roiData = [
    { date: "Jan", roi: 12.3, bankroll: 1000 },
    { date: "Feb", roi: 15.7, bankroll: 1157 },
    { date: "Mar", roi: 18.2, bankroll: 1368 },
    { date: "Apr", roi: 16.8, bankroll: 1598 },
    { date: "May", roi: 22.1, bankroll: 1951 },
    { date: "Jun", roi: 18.7, bankroll: 2315 },
  ];

  const hitRateData = [
    { name: "2-Leg", wins: 45, losses: 25, rate: 64.3 },
    { name: "3-Leg", wins: 38, losses: 32, rate: 54.3 },
    { name: "4-Leg", wins: 22, losses: 28, rate: 44.0 },
    { name: "5-Leg", wins: 12, losses: 18, rate: 40.0 },
    { name: "6+ Leg", wins: 8, losses: 22, rate: 26.7 },
  ];

  const sportDistribution = [
    { name: "NBA", value: 45, profit: 1250 },
    { name: "NFL", value: 35, profit: 890 },
    { name: "MLB", value: 15, profit: 320 },
    { name: "NHL", value: 5, profit: 145 },
  ];

  const COLORS = ['hsl(var(--primary))', 'hsl(var(--success))', 'hsl(var(--warning))', 'hsl(var(--destructive))'];

  const monthlyStats = [
    { label: "Parlays Placed", value: "247", change: "+23", changeType: "positive" as const },
    { label: "Total Wagered", value: "$12,450", change: "+$2,100", changeType: "positive" as const },
    { label: "Net Profit", value: "+$2,315", change: "+$485", changeType: "positive" as const },
    { label: "Best Streak", value: "7 wins", change: "Current", changeType: "positive" as const },
  ];

  return (
    <div className="flex-1 md:ml-64">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center space-x-2">
              <BarChart3 className="h-8 w-8 text-primary" />
              <span>Performance Analytics</span>
            </h1>
            <p className="text-muted-foreground">Track your betting performance and identify profitable strategies</p>
          </div>
          
          <div className="flex items-center space-x-2">
            <Select defaultValue="30d">
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7d">Last 7 days</SelectItem>
                <SelectItem value="30d">Last 30 days</SelectItem>
                <SelectItem value="90d">Last 3 months</SelectItem>
                <SelectItem value="1y">Last year</SelectItem>
              </SelectContent>
            </Select>
            
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {monthlyStats.map((stat, index) => (
            <StatCard
              key={index}
              title={stat.label}
              value={stat.value}
              change={stat.change}
              changeType={stat.changeType}
            />
          ))}
        </div>

        {/* Charts Row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* ROI Trend */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <TrendingUp className="h-5 w-5" />
                <span>ROI & Bankroll Growth</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={roiData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" />
                  <YAxis stroke="hsl(var(--muted-foreground))" />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px"
                    }}
                  />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="roi" 
                    stroke="hsl(var(--primary))" 
                    strokeWidth={3}
                    name="ROI %"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="bankroll" 
                    stroke="hsl(var(--success))" 
                    strokeWidth={2}
                    name="Bankroll ($)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Sports Distribution */}
          <Card>
            <CardHeader>
              <CardTitle>Profit by Sport</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={sportDistribution}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value, profit }) => `${name}: $${profit}`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {sportDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px"
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* Charts Row 2 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Hit Rate by Parlay Size */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Target className="h-5 w-5" />
                <span>Hit Rate by Parlay Size</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={hitRateData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" />
                  <YAxis stroke="hsl(var(--muted-foreground))" />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px"
                    }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="rate" 
                    stroke="hsl(var(--primary))" 
                    fill="hsl(var(--primary) / 0.2)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Recent Performance Summary */}
          <Card>
            <CardHeader>
              <CardTitle>Performance Insights</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-3 rounded-lg bg-success/10 border border-success/20">
                <div>
                  <div className="font-medium text-success">Best Strategy</div>
                  <div className="text-sm text-muted-foreground">3-leg NBA player props</div>
                </div>
                <Badge variant="default">+24.7% ROI</Badge>
              </div>
              
              <div className="flex items-center justify-between p-3 rounded-lg bg-warning/10 border border-warning/20">
                <div>
                  <div className="font-medium text-warning">Improvement Area</div>
                  <div className="text-sm text-muted-foreground">5+ leg parlays</div>
                </div>
                <Badge variant="secondary">-8.2% ROI</Badge>
              </div>
              
              <div className="flex items-center justify-between p-3 rounded-lg bg-primary/10 border border-primary/20">
                <div>
                  <div className="font-medium text-primary">Hot Streak</div>
                  <div className="text-sm text-muted-foreground">Current winning streak</div>
                </div>
                <Badge variant="default">7 parlays</Badge>
              </div>
              
              <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/50">
                <div>
                  <div className="font-medium">Avg Stake</div>
                  <div className="text-sm text-muted-foreground">Per parlay</div>
                </div>
                <span className="font-medium">$42.50</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* AI Recommendations */}
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2 text-primary">
              <TrendingUp className="h-5 w-5" />
              <span>AI Recommendations</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-start space-x-3">
              <div className="w-2 h-2 bg-primary rounded-full mt-2"></div>
              <div>
                <div className="font-medium">Focus on 3-leg parlays</div>
                <div className="text-sm text-muted-foreground">Your 3-leg parlays have a 54% hit rate with +18% average ROI</div>
              </div>
            </div>
            
            <div className="flex items-start space-x-3">
              <div className="w-2 h-2 bg-primary rounded-full mt-2"></div>
              <div>
                <div className="font-medium">Reduce stake on 5+ leg parlays</div>
                <div className="text-sm text-muted-foreground">Consider lowering your average stake from $45 to $25 on high-leg parlays</div>
              </div>
            </div>
            
            <div className="flex items-start space-x-3">
              <div className="w-2 h-2 bg-primary rounded-full mt-2"></div>
              <div>
                <div className="font-medium">NBA player props show strong performance</div>
                <div className="text-sm text-muted-foreground">Consider increasing allocation to NBA player prop parlays based on your +24% ROI</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Analytics;