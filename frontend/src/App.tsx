import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import NBA from "./pages/NBA";
import NFL from "./pages/NFL";
import Analytics from "./pages/Analytics";
import Knowledge from "./pages/Knowledge";
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
              <Route path="/" element={<Landing />} />
              <Route 
                path="/dashboard" 
                element={
                  <div className="flex">
                    <Navigation />
                    <Dashboard />
                  </div>
                } 
              />
              <Route 
                path="/nba" 
                element={
                  <div className="flex">
                    <Navigation />
                    <NBA />
                  </div>
                } 
              />
              <Route 
                path="/nfl" 
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
