import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { 
  BarChart3, 
  Brain, 
  DollarSign, 
  Home, 
  Menu, 
  Search, 
  Settings, 
  Zap,
  Target,
  TrendingUp
} from "lucide-react";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: Home },
  { name: "NBA Parlays", href: "/nba", icon: Target },
  { name: "NFL Parlays", href: "/nfl", icon: Zap },
  { name: "Analytics", href: "/analytics", icon: BarChart3 },
  { name: "Knowledge Base", href: "/knowledge", icon: Brain },
  { name: "Arbitrage", href: "/arbitrage", icon: TrendingUp, badge: "Pro" },
];

const Navigation = () => {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();

  const NavItems = () => (
    <>
      {navigation.map((item) => {
        const isActive = location.pathname === item.href;
        return (
          <NavLink
            key={item.name}
            to={item.href}
            className={`flex items-center space-x-3 px-3 py-2 rounded-lg smooth-transition ${
              isActive 
                ? "nav-link-active" 
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
            }`}
            onClick={() => setIsOpen(false)}
          >
            <item.icon className="h-5 w-5" />
            <span className="font-medium">{item.name}</span>
            {item.badge && (
              <Badge variant="secondary" className="ml-auto text-xs">
                {item.badge}
              </Badge>
            )}
          </NavLink>
        );
      })}
    </>
  );

  return (
    <>
      {/* Desktop Navigation */}
      <nav className="hidden md:flex md:flex-col md:w-64 md:fixed md:inset-y-0 md:border-r md:bg-card/50 md:backdrop-blur-sm">
        <div className="flex flex-col h-full">
          <div className="flex items-center h-16 px-6 border-b">
            <DollarSign className="h-8 w-8 text-primary" />
            <span className="ml-2 text-xl font-bold">SportsBet AI</span>
          </div>
          
          <div className="flex-1 flex flex-col overflow-y-auto p-4 space-y-1">
            <NavItems />
          </div>
          
          <div className="p-4 border-t">
            <NavLink
              to="/settings"
              className={`flex items-center space-x-3 px-3 py-2 rounded-lg smooth-transition ${
                location.pathname === "/settings"
                  ? "nav-link-active"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
              }`}
            >
              <Settings className="h-5 w-5" />
              <span className="font-medium">Settings</span>
            </NavLink>
          </div>
        </div>
      </nav>

      {/* Mobile Navigation */}
      <div className="md:hidden flex items-center justify-between p-4 border-b bg-card/50 backdrop-blur-sm">
        <div className="flex items-center">
          <DollarSign className="h-8 w-8 text-primary" />
          <span className="ml-2 text-xl font-bold">SportsBet AI</span>
        </div>
        
        <Sheet open={isOpen} onOpenChange={setIsOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon">
              <Menu className="h-6 w-6" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-64 p-0">
            <div className="flex flex-col h-full">
              <div className="flex items-center h-16 px-6 border-b">
                <DollarSign className="h-8 w-8 text-primary" />
                <span className="ml-2 text-xl font-bold">SportsBet AI</span>
              </div>
              
              <div className="flex-1 flex flex-col overflow-y-auto p-4 space-y-1">
                <NavItems />
              </div>
              
              <div className="p-4 border-t">
                <NavLink
                  to="/settings"
                  className={`flex items-center space-x-3 px-3 py-2 rounded-lg smooth-transition ${
                    location.pathname === "/settings"
                      ? "nav-link-active"
                      : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                  }`}
                  onClick={() => setIsOpen(false)}
                >
                  <Settings className="h-5 w-5" />
                  <span className="font-medium">Settings</span>
                </NavLink>
              </div>
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
};

export default Navigation;