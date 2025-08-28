import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing";
import LandingRefactored from "./pages/LandingRefactored";
import LandingFixed from "./pages/LandingFixed";
import LandingMinimal from "./pages/LandingMinimal";
import LandingUltraSimple from "./pages/LandingUltraSimple";
import Dashboard from "./pages/Dashboard";
import DashboardRefactored from "./pages/DashboardRefactored";
import NBA from "./pages/NBA";
import NBARefactored from "./pages/NBARefactored";
import NFL from "./pages/NFL";
import NFLRefactored from "./pages/NFLRefactored";
import Analytics from "./pages/Analytics";
import Knowledge from "./pages/Knowledge";
import KnowledgeRefactored from "./pages/KnowledgeRefactored";
import Settings from "./pages/Settings";
import Navigation from "./components/Navigation";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <div className="min-h-screen bg-background">
            <Routes>
              <Route path="/" element={<LandingUltraSimple />} />
              <Route path="/landing-old" element={<Landing />} />
              <Route path="/landing-new" element={<LandingRefactored />} />
              <Route 
                path="/dashboard" 
                element={<DashboardRefactored />}
              />
              <Route 
                path="/dashboard-old" 
                element={
                  <div className="flex">
                    <Navigation />
                    <Dashboard />
                  </div>
                } 
              />
              <Route 
                path="/nba" 
                element={<NBARefactored />}
              />
              <Route 
                path="/nba-old" 
                element={
                  <div className="flex">
                    <Navigation />
                    <NBA />
                  </div>
                } 
              />
              <Route 
                path="/nfl" 
                element={<NFLRefactored />}
              />
              <Route 
                path="/nfl-old" 
                element={
                  <div className="flex">
                    <Navigation />
                    <NFL />
                  </div>
                } 
              />
              <Route 
                path="/analytics" 
                element={
                  <div className="flex">
                    <Navigation />
                    <Analytics />
                  </div>
                } 
              />
              <Route 
                path="/knowledge" 
                element={<KnowledgeRefactored />}
              />
              <Route 
                path="/knowledge-old" 
                element={
                  <div className="flex">
                    <Navigation />
                    <Knowledge />
                  </div>
                } 
              />
              <Route 
                path="/settings" 
                element={
                  <div className="flex">
                    <Navigation />
                    <Settings />
                  </div>
                } 
              />
              {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </div>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
);

export default App;
