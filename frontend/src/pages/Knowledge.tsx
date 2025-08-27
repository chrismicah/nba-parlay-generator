import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { 
  Search, 
  Brain, 
  TrendingUp, 
  BookOpen,
  Star,
  Clock,
  Filter,
  ArrowRight
} from "lucide-react";

interface KnowledgeArticle {
  id: string;
  title: string;
  excerpt: string;
  category: string;
  readTime: string;
  rating: number;
  lastUpdated: string;
  tags: string[];
}

const Knowledge = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");

  // Mock knowledge base articles
  const articles: KnowledgeArticle[] = [
    {
      id: "1",
      title: "Understanding Expected Value in Sports Betting",
      excerpt: "Learn how to calculate and identify positive expected value opportunities to maximize your long-term profits.",
      category: "Strategy",
      readTime: "8 min",
      rating: 4.8,
      lastUpdated: "2 days ago",
      tags: ["EV", "Math", "Fundamentals"]
    },
    {
      id: "2",
      title: "NBA Player Props: Advanced Analytics Approach",
      excerpt: "Deep dive into using advanced basketball analytics to identify profitable player prop betting opportunities.",
      category: "NBA",
      readTime: "12 min",
      rating: 4.9,
      lastUpdated: "1 week ago",
      tags: ["NBA", "Props", "Analytics"]
    },
    {
      id: "3",
      title: "Bankroll Management for Parlay Betting",
      excerpt: "Essential strategies for managing your betting bankroll when focusing on parlay combinations.",
      category: "Strategy",
      readTime: "6 min",
      rating: 4.7,
      lastUpdated: "3 days ago",
      tags: ["Bankroll", "Risk", "Management"]
    },
    {
      id: "4",
      title: "NFL Weather Impact on Totals Betting",
      excerpt: "How weather conditions affect NFL game totals and how to capitalize on market inefficiencies.",
      category: "NFL",
      readTime: "10 min",
      rating: 4.6,
      lastUpdated: "5 days ago",
      tags: ["NFL", "Weather", "Totals"]
    },
    {
      id: "5",
      title: "Line Movement and Market Analysis",
      excerpt: "Understanding why betting lines move and how to use this information to your advantage.",
      category: "Strategy",
      readTime: "15 min",
      rating: 4.9,
      lastUpdated: "1 day ago",
      tags: ["Lines", "Market", "Analysis"]
    },
    {
      id: "6",
      title: "Arbitrage Betting: Risk-Free Profits",
      excerpt: "Complete guide to identifying and executing arbitrage opportunities across different sportsbooks.",
      category: "Advanced",
      readTime: "20 min",
      rating: 4.8,
      lastUpdated: "4 days ago",
      tags: ["Arbitrage", "Advanced", "Risk-Free"]
    }
  ];

  const categories = [
    { id: "all", name: "All Categories", count: articles.length },
    { id: "strategy", name: "Strategy", count: 3 },
    { id: "nba", name: "NBA", count: 1 },
    { id: "nfl", name: "NFL", count: 1 },
    { id: "advanced", name: "Advanced", count: 1 }
  ];

  const filteredArticles = articles.filter(article => {
    const matchesSearch = article.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         article.excerpt.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         article.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    
    const matchesCategory = selectedCategory === "all" || 
                           article.category.toLowerCase() === selectedCategory.toLowerCase();
    
    return matchesSearch && matchesCategory;
  });

  const featuredArticles = articles.filter(article => article.rating >= 4.8).slice(0, 3);

  const renderStars = (rating: number) => {
    return Array.from({ length: 5 }, (_, i) => (
      <Star 
        key={i} 
        className={`h-4 w-4 ${
          i < Math.floor(rating) 
            ? "text-primary fill-current" 
            : "text-muted-foreground"
        }`} 
      />
    ));
  };

  return (
    <div className="flex-1 md:ml-64">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center space-x-2">
              <Brain className="h-8 w-8 text-primary" />
              <span>Knowledge Base</span>
            </h1>
            <p className="text-muted-foreground">Learn advanced betting strategies and market analysis</p>
          </div>
          
          <Badge variant="secondary" className="flex items-center space-x-1">
            <BookOpen className="h-4 w-4" />
            <span>{articles.length} articles</span>
          </Badge>
        </div>

        {/* Search and Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col lg:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search articles, strategies, and betting tips..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 form-input"
                />
              </div>
              
              <div className="flex gap-2 flex-wrap">
                {categories.map((category) => (
                  <Button
                    key={category.id}
                    variant={selectedCategory === category.id ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedCategory(category.id)}
                    className="flex items-center space-x-1"
                  >
                    <span>{category.name}</span>
                    <Badge variant="secondary" className="text-xs ml-1">
                      {category.count}
                    </Badge>
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Featured Articles */}
        {selectedCategory === "all" && !searchQuery && (
          <div>
            <h2 className="text-2xl font-bold mb-4 flex items-center space-x-2">
              <Star className="h-6 w-6 text-primary" />
              <span>Featured Articles</span>
            </h2>
            
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
              {featuredArticles.map((article) => (
                <Card key={article.id} className="stat-card-success group cursor-pointer">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary">{article.category}</Badge>
                      <div className="flex items-center space-x-1">
                        {renderStars(article.rating)}
                      </div>
                    </div>
                    <CardTitle className="text-lg group-hover:text-primary smooth-transition">
                      {article.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground text-sm mb-4">{article.excerpt}</p>
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span className="flex items-center space-x-1">
                        <Clock className="h-3 w-3" />
                        <span>{article.readTime}</span>
                      </span>
                      <span>{article.lastUpdated}</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
            
            <Separator />
          </div>
        )}

        {/* All Articles */}
        <div>
          <h2 className="text-2xl font-bold mb-4">
            {searchQuery || selectedCategory !== "all" ? "Search Results" : "All Articles"}
          </h2>
          
          {filteredArticles.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <BookOpen className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                <h3 className="text-lg font-semibold mb-2">No articles found</h3>
                <p className="text-muted-foreground">Try adjusting your search terms or filters</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {filteredArticles.map((article) => (
                <Card key={article.id} className="stat-card group cursor-pointer hover:scale-[1.01]">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <Badge variant="outline">{article.category}</Badge>
                          <div className="flex items-center space-x-1">
                            {renderStars(article.rating)}
                            <span className="text-sm text-muted-foreground ml-1">
                              {article.rating}
                            </span>
                          </div>
                        </div>
                        
                        <h3 className="text-xl font-semibold mb-2 group-hover:text-primary smooth-transition">
                          {article.title}
                        </h3>
                        
                        <p className="text-muted-foreground mb-4">
                          {article.excerpt}
                        </p>
                        
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                            <span className="flex items-center space-x-1">
                              <Clock className="h-4 w-4" />
                              <span>{article.readTime}</span>
                            </span>
                            <span>Updated {article.lastUpdated}</span>
                          </div>
                          
                          <div className="flex items-center space-x-2">
                            {article.tags.map((tag) => (
                              <Badge key={tag} variant="secondary" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </div>
                      
                      <div className="ml-4">
                        <Button variant="ghost" size="sm" className="group-hover:bg-primary group-hover:text-primary-foreground">
                          <ArrowRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Quick Tips */}
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2 text-primary">
              <TrendingUp className="h-5 w-5" />
              <span>Pro Tips</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-start space-x-3">
              <div className="w-2 h-2 bg-primary rounded-full mt-2"></div>
              <div>
                <div className="font-medium">Start with expected value fundamentals</div>
                <div className="text-sm text-muted-foreground">Understanding EV is crucial for long-term profitability</div>
              </div>
            </div>
            
            <div className="flex items-start space-x-3">
              <div className="w-2 h-2 bg-primary rounded-full mt-2"></div>
              <div>
                <div className="font-medium">Focus on bankroll management</div>
                <div className="text-sm text-muted-foreground">Proper bankroll management is often more important than pick quality</div>
              </div>
            </div>
            
            <div className="flex items-start space-x-3">
              <div className="w-2 h-2 bg-primary rounded-full mt-2"></div>
              <div>
                <div className="font-medium">Use data, not emotions</div>
                <div className="text-sm text-muted-foreground">Always base decisions on statistical analysis rather than gut feelings</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Knowledge;