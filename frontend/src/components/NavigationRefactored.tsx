/**
 * Refactored Navigation component with system integration
 */

import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Home,
  Activity,
  Basketball,
  Football,
  BookOpen,
  Settings,
  ChevronLeft,
  ChevronRight,
  Zap
} from 'lucide-react';

// Components
import HealthIndicator from '@/components/system/HealthIndicator';

// Hooks
import { useHealthCheck } from '@/hooks/useApi';

interface NavigationProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

const NavigationRefactored: React.FC<NavigationProps> = ({ 
  collapsed = false, 
  onToggle 
}) => {
  const location = useLocation();

  const {
    data: healthData,
    loading: healthLoading,
    error: healthError,
    checkHealth
  } = useHealthCheck(true, 60000); // Check every minute

  const navItems = [
    {
      to: '/',
      icon: <Home className="h-5 w-5" />,
      label: 'Home',
      description: 'Landing page'
    },
    {
      to: '/dashboard',
      icon: <Activity className="h-5 w-5" />,
      label: 'Dashboard',
      description: 'System overview'
    },
    {
      to: '/nfl',
      icon: <Football className="h-5 w-5" />,
      label: 'NFL',
      description: 'NFL parlay generation',
      enabled: healthData?.sports_enabled?.nfl
    },
    {
      to: '/nba',
      icon: <Basketball className="h-5 w-5" />,
      label: 'NBA',
      description: 'NBA parlay generation',
      enabled: healthData?.sports_enabled?.nba
    },
    {
      to: '/knowledge',
      icon: <BookOpen className="h-5 w-5" />,
      label: 'Knowledge',
      description: 'Expert knowledge base'
    },
    {
      to: '/settings',
      icon: <Settings className="h-5 w-5" />,
      label: 'Settings',
      description: 'App configuration'
    }
  ];

  const NavItem: React.FC<{ item: typeof navItems[0] }> = ({ item }) => {
    const isActive = location.pathname === item.to;
    const isEnabled = item.enabled !== false;

    return (
      <NavLink
        to={item.to}
        className={({ isActive }) => `
          flex items-center space-x-3 p-3 rounded-lg transition-all
          ${isActive 
            ? 'bg-primary text-primary-foreground shadow-md' 
            : isEnabled 
              ? 'hover:bg-muted text-muted-foreground hover:text-foreground' 
              : 'text-muted-foreground/50 cursor-not-allowed'
          }
          ${collapsed ? 'justify-center' : ''}
        `}
      >
        <div className="flex items-center space-x-3">
          {item.icon}
          {!collapsed && (
            <div className="flex-1">
              <div className="font-medium">{item.label}</div>
              {item.description && (
                <div className="text-xs opacity-70">{item.description}</div>
              )}
            </div>
          )}
          {!collapsed && item.enabled === false && (
            <Badge variant="secondary" className="text-xs">
              Offline
            </Badge>
          )}
        </div>
      </NavLink>
    );
  };

  return (
    <Card className={`${collapsed ? 'w-16' : 'w-64'} h-screen sticky top-0 transition-all duration-300`}>
      <CardContent className="p-4 h-full flex flex-col">
        
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          {!collapsed && (
            <div className="flex items-center space-x-2">
              <Zap className="h-6 w-6 text-primary" />
              <span className="font-bold text-lg">Parlay AI</span>
            </div>
          )}
          
          {onToggle && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onToggle}
              className="p-2"
            >
              {collapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <ChevronLeft className="h-4 w-4" />
              )}
            </Button>
          )}
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 space-y-2">
          {navItems.map((item) => (
            <NavItem key={item.to} item={item} />
          ))}
        </nav>

        {/* Health Status */}
        <div className="mt-auto pt-4 border-t">
          {collapsed ? (
            <div className="flex justify-center">
              <div className={`w-3 h-3 rounded-full ${
                healthError 
                  ? 'bg-red-500' 
                  : healthData?.status === 'healthy' 
                    ? 'bg-green-500' 
                    : 'bg-yellow-500'
              }`} />
            </div>
          ) : (
            <HealthIndicator 
              health={healthData}
              loading={healthLoading}
              error={healthError}
              onRefresh={checkHealth}
              compact={true}
            />
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default NavigationRefactored;



