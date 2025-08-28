import React from 'react';
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";

// Enhanced styling constants
const styles = {
  // Layout
  container: {
    minHeight: '100vh',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    margin: 0,
    padding: 0
  },
  
  // Navigation
  nav: {
    background: 'rgba(255, 255, 255, 0.95)',
    backdropFilter: 'blur(10px)',
    padding: '1rem 2rem',
    boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
    position: 'sticky' as const,
    top: 0,
    zIndex: 1000,
    borderBottom: '1px solid rgba(255,255,255,0.2)'
  },
  
  navContent: {
    maxWidth: '1200px',
    margin: '0 auto',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  
  logo: {
    fontSize: '1.5rem',
    fontWeight: '700',
    background: 'linear-gradient(135deg, #667eea, #764ba2)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    textDecoration: 'none'
  },
  
  navLinks: {
    display: 'flex',
    gap: '2rem',
    listStyle: 'none',
    margin: 0,
    padding: 0
  },
  
  navLink: {
    color: '#374151',
    textDecoration: 'none',
    fontWeight: '500',
    padding: '0.5rem 1rem',
    borderRadius: '8px',
    transition: 'all 0.2s',
    border: '1px solid transparent'
  },
  
  // Content areas
  pageContent: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '4rem 2rem'
  },
  
  // Hero section
  hero: {
    textAlign: 'center' as const,
    color: 'white',
    marginBottom: '4rem'
  },
  
  heroTitle: {
    fontSize: 'clamp(2.5rem, 6vw, 4.5rem)',
    fontWeight: '800',
    marginBottom: '1.5rem',
    textShadow: '0 4px 20px rgba(0,0,0,0.3)',
    lineHeight: '1.2'
  },
  
  heroSubtitle: {
    fontSize: '1.25rem',
    opacity: 0.9,
    maxWidth: '600px',
    margin: '0 auto 2rem',
    lineHeight: '1.6'
  },
  
  // Cards
  cardGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '2rem',
    marginBottom: '4rem'
  },
  
  card: {
    background: 'rgba(255, 255, 255, 0.95)',
    backdropFilter: 'blur(10px)',
    borderRadius: '16px',
    padding: '2rem',
    boxShadow: '0 10px 40px rgba(0,0,0,0.1)',
    border: '1px solid rgba(255,255,255,0.2)',
    transition: 'all 0.3s ease',
    cursor: 'pointer',
    textDecoration: 'none',
    color: 'inherit',
    position: 'relative' as const,
    overflow: 'hidden'
  },
  
  cardIcon: {
    fontSize: '3rem',
    marginBottom: '1rem',
    display: 'block'
  },
  
  cardTitle: {
    fontSize: '1.5rem',
    fontWeight: '700',
    marginBottom: '0.5rem',
    color: '#1f2937'
  },
  
  cardDescription: {
    color: '#6b7280',
    lineHeight: '1.5',
    margin: 0
  },
  
  // Buttons
  button: {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: 'white',
    border: 'none',
    padding: '1rem 2rem',
    borderRadius: '12px',
    fontSize: '1.1rem',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)',
    textTransform: 'none' as const
  },
  
  buttonDisabled: {
    background: '#9ca3af',
    cursor: 'not-allowed',
    boxShadow: 'none'
  },
  
  // Status indicators
  statusGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '1rem',
    background: 'rgba(255, 255, 255, 0.1)',
    padding: '2rem',
    borderRadius: '16px',
    backdropFilter: 'blur(10px)'
  },
  
  statusItem: {
    color: 'white',
    textAlign: 'center' as const,
    fontSize: '0.95rem',
    fontWeight: '500'
  },
  
  // Parlay display
  parlayCard: {
    background: 'white',
    borderRadius: '16px',
    padding: '2rem',
    boxShadow: '0 10px 40px rgba(0,0,0,0.1)',
    border: '1px solid #e5e7eb',
    marginTop: '2rem'
  },
  
  parlayHeader: {
    borderBottom: '2px solid #f3f4f6',
    paddingBottom: '1rem',
    marginBottom: '1.5rem'
  },
  
  parlayLeg: {
    background: '#f8fafc',
    padding: '1rem',
    borderRadius: '8px',
    marginBottom: '0.75rem',
    borderLeft: '4px solid #667eea'
  },
  
  alert: {
    background: '#fef3c7',
    border: '1px solid #f59e0b',
    borderRadius: '8px',
    padding: '1rem',
    marginTop: '1rem',
    color: '#92400e'
  }
};

// Enhanced Navigation Component
const Navigation = () => (
  <nav style={styles.nav}>
    <div style={styles.navContent}>
      <Link to="/" style={styles.logo}>
        SportsBet AI
      </Link>
      <ul style={styles.navLinks}>
        {[
          { path: '/nfl', label: '🏈 NFL' },
          { path: '/nba', label: '🏀 NBA' },
          { path: '/dashboard', label: '📊 Dashboard' },
          { path: '/knowledge', label: '📚 Knowledge' }
        ].map(({ path, label }) => (
          <li key={path}>
            <Link 
              to={path} 
              style={styles.navLink}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'linear-gradient(135deg, #667eea, #764ba2)';
                e.currentTarget.style.color = 'white';
                e.currentTarget.style.transform = 'translateY(-2px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.color = '#374151';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              {label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  </nav>
);

// Enhanced Landing Page
const StyledLanding = () => {
  const cards = [
    { 
      icon: '🏈', 
      title: 'NFL Parlays', 
      description: 'Advanced NFL analysis with real game data and expert insights',
      path: '/nfl',
      gradient: 'linear-gradient(135deg, #f97316, #ea580c)'
    },
    { 
      icon: '🏀', 
      title: 'NBA Parlays', 
      description: 'ML-powered NBA predictions with confidence scoring',
      path: '/nba',
      gradient: 'linear-gradient(135deg, #8b5cf6, #7c3aed)'
    },
    { 
      icon: '📊', 
      title: 'Dashboard', 
      description: 'Real-time system monitoring and performance analytics',
      path: '/dashboard',
      gradient: 'linear-gradient(135deg, #06b6d4, #0891b2)'
    },
    { 
      icon: '📚', 
      title: 'Knowledge Base', 
      description: 'Expert analysis database with 1,590+ curated insights',
      path: '/knowledge',
      gradient: 'linear-gradient(135deg, #10b981, #059669)'
    }
  ];

  return (
    <div style={styles.container}>
      <Navigation />
      <div style={styles.pageContent}>
        <div style={styles.hero}>
          <h1 style={styles.heroTitle}>
            AI-Powered Sports Betting Platform
          </h1>
          <p style={styles.heroSubtitle}>
            Generate profitable parlay combinations with machine learning, expert knowledge, and real-time data analysis
          </p>
        </div>

        <div style={styles.cardGrid}>
          {cards.map((card, index) => (
            <Link 
              key={index}
              to={card.path}
              style={{
                ...styles.card,
                background: `linear-gradient(135deg, rgba(255,255,255,0.95), rgba(255,255,255,0.85))`
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-8px) scale(1.02)';
                e.currentTarget.style.boxShadow = '0 20px 60px rgba(0,0,0,0.15)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0) scale(1)';
                e.currentTarget.style.boxShadow = '0 10px 40px rgba(0,0,0,0.1)';
              }}
            >
              <span style={{...styles.cardIcon, background: card.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'}}>
                {card.icon}
              </span>
              <h3 style={styles.cardTitle}>{card.title}</h3>
              <p style={styles.cardDescription}>{card.description}</p>
            </Link>
          ))}
        </div>

        <div style={styles.statusGrid}>
          <div style={styles.statusItem}>✅ Backend API Active</div>
          <div style={styles.statusItem}>✅ ML Models Loaded</div>
          <div style={styles.statusItem}>✅ Real-time Monitoring</div>
          <div style={styles.statusItem}>✅ Expert Knowledge Ready</div>
        </div>
      </div>
    </div>
  );
};

// Enhanced NFL Page
const StyledNFL = () => {
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [parlay, setParlay] = React.useState(null);

  const generateParlay = async () => {
    setIsGenerating(true);
    try {
      const response = await fetch('http://localhost:8000/generate-nfl-parlay', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_legs: 3, min_total_odds: 2.0 })
      });
      const data = await response.json();
      setParlay(data);
    } catch (error) {
      alert('Error connecting to backend: ' + error.message);
    }
    setIsGenerating(false);
  };

  return (
    <div style={styles.container}>
      <Navigation />
      <div style={styles.pageContent}>
        <div style={styles.hero}>
          <h1 style={{...styles.heroTitle, fontSize: '3rem'}}>🏈 NFL Parlay Generator</h1>
          <p style={styles.heroSubtitle}>
            AI-powered NFL analysis with real game data and expert insights
          </p>
        </div>

        <div style={{textAlign: 'center', marginBottom: '3rem'}}>
          <button 
            onClick={generateParlay}
            disabled={isGenerating}
            style={{
              ...styles.button,
              ...(isGenerating ? styles.buttonDisabled : {}),
              background: isGenerating ? '#9ca3af' : 'linear-gradient(135deg, #f97316, #ea580c)'
            }}
            onMouseEnter={(e) => {
              if (!isGenerating) {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 6px 20px rgba(249, 115, 22, 0.4)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = isGenerating ? 'none' : '0 4px 15px rgba(249, 115, 22, 0.4)';
            }}
          >
            {isGenerating ? '🔄 Generating NFL Parlay...' : '🚀 Generate NFL Parlay'}
          </button>
        </div>

        {parlay && (
          <div style={styles.parlayCard}>
            <div style={styles.parlayHeader}>
              <h3 style={{margin: 0, fontSize: '1.5rem', color: '#1f2937'}}>Generated NFL Parlay</h3>
              <div style={{marginTop: '0.5rem', color: '#6b7280'}}>
                <strong>Confidence:</strong> {parlay.confidence_percentage}% | 
                <strong> Total Odds:</strong> +{Math.round((parlay.total_odds - 1) * 100)} |
                <strong> Expected Value:</strong> {parlay.expected_value?.toFixed(1)}%
              </div>
            </div>
            
            {parlay.legs && parlay.legs.map((leg, index) => (
              <div key={index} style={styles.parlayLeg}>
                <div style={{fontWeight: '600', marginBottom: '0.25rem', color: '#1f2937'}}>
                  {leg.game_info || 'NFL Game'}
                </div>
                <div style={{color: '#4b5563'}}>
                  <strong>{leg.market}:</strong> {leg.selection} 
                  <span style={{float: 'right', fontWeight: '600', color: leg.odds > 0 ? '#059669' : '#dc2626'}}>
                    {leg.odds > 0 ? '+' : ''}{leg.odds}
                  </span>
                </div>
              </div>
            ))}

            {parlay.season_note && (
              <div style={styles.alert}>
                <strong>⚠️ Season Note:</strong> {parlay.season_note}
              </div>
            )}

            {parlay.recommendation && (
              <div style={{...styles.alert, background: '#d1fae5', border: '1px solid #10b981', color: '#065f46'}}>
                <strong>💡 Recommendation:</strong> {parlay.recommendation}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Enhanced NBA Page (similar structure to NFL)
const StyledNBA = () => {
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [parlay, setParlay] = React.useState(null);

  const generateParlay = async () => {
    setIsGenerating(true);
    try {
      const response = await fetch('http://localhost:8000/generate-nba-parlay', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_legs: 3, min_total_odds: 2.0 })
      });
      const data = await response.json();
      setParlay(data);
    } catch (error) {
      alert('Error connecting to backend: ' + error.message);
    }
    setIsGenerating(false);
  };

  return (
    <div style={styles.container}>
      <Navigation />
      <div style={styles.pageContent}>
        <div style={styles.hero}>
          <h1 style={{...styles.heroTitle, fontSize: '3rem'}}>🏀 NBA Parlay Generator</h1>
          <p style={styles.heroSubtitle}>
            ML-enhanced NBA predictions with confidence scoring and expert analysis
          </p>
        </div>

        <div style={{textAlign: 'center', marginBottom: '3rem'}}>
          <button 
            onClick={generateParlay}
            disabled={isGenerating}
            style={{
              ...styles.button,
              ...(isGenerating ? styles.buttonDisabled : {}),
              background: isGenerating ? '#9ca3af' : 'linear-gradient(135deg, #8b5cf6, #7c3aed)'
            }}
            onMouseEnter={(e) => {
              if (!isGenerating) {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 6px 20px rgba(139, 92, 246, 0.4)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = isGenerating ? 'none' : '0 4px 15px rgba(139, 92, 246, 0.4)';
            }}
          >
            {isGenerating ? '🔄 Generating NBA Parlay...' : '🚀 Generate NBA Parlay'}
          </button>
        </div>

        {parlay && (
          <div style={styles.parlayCard}>
            <div style={styles.parlayHeader}>
              <h3 style={{margin: 0, fontSize: '1.5rem', color: '#1f2937'}}>Generated NBA Parlay</h3>
              <div style={{marginTop: '0.5rem', color: '#6b7280'}}>
                <strong>Confidence:</strong> {parlay.confidence_percentage}% | 
                <strong> Total Odds:</strong> +{Math.round((parlay.total_odds - 1) * 100)} |
                <strong> Expected Value:</strong> {parlay.expected_value?.toFixed(1)}%
              </div>
            </div>
            
            {parlay.legs && parlay.legs.map((leg, index) => (
              <div key={index} style={{...styles.parlayLeg, borderLeft: '4px solid #8b5cf6'}}>
                <div style={{fontWeight: '600', marginBottom: '0.25rem', color: '#1f2937'}}>
                  {leg.game_info || 'NBA Game'}
                </div>
                <div style={{color: '#4b5563'}}>
                  <strong>{leg.market}:</strong> {leg.selection} 
                  <span style={{float: 'right', fontWeight: '600', color: leg.odds > 0 ? '#059669' : '#dc2626'}}>
                    {leg.odds > 0 ? '+' : ''}{leg.odds}
                  </span>
                </div>
              </div>
            ))}

            {parlay.recommendation && (
              <div style={{...styles.alert, background: '#d1fae5', border: '1px solid #10b981', color: '#065f46'}}>
                <strong>💡 Recommendation:</strong> {parlay.recommendation}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Enhanced Dashboard
const StyledDashboard = () => {
  const [health, setHealth] = React.useState(null);

  React.useEffect(() => {
    fetch('http://localhost:8000/health')
      .then(res => res.json())
      .then(setHealth)
      .catch(console.error);
  }, []);

  return (
    <div style={styles.container}>
      <Navigation />
      <div style={styles.pageContent}>
        <div style={styles.hero}>
          <h1 style={{...styles.heroTitle, fontSize: '3rem'}}>📊 System Dashboard</h1>
          <p style={styles.heroSubtitle}>
            Real-time monitoring and system performance analytics
          </p>
        </div>

        {health && (
          <div style={styles.parlayCard}>
            <div style={styles.parlayHeader}>
              <h3 style={{margin: 0, fontSize: '1.5rem', color: '#059669'}}>✅ System Health Status</h3>
            </div>
            
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem'}}>
              <div style={{padding: '1rem', background: '#f0fdf4', borderRadius: '8px', border: '1px solid #bbf7d0'}}>
                <div style={{fontWeight: '600', color: '#166534'}}>Status</div>
                <div style={{fontSize: '1.25rem', textTransform: 'capitalize'}}>{health.status}</div>
              </div>
              <div style={{padding: '1rem', background: '#f0f9ff', borderRadius: '8px', border: '1px solid #bae6fd'}}>
                <div style={{fontWeight: '600', color: '#075985'}}>Uptime</div>
                <div style={{fontSize: '1.25rem'}}>{Math.round(health.uptime_seconds / 60)} min</div>
              </div>
              <div style={{padding: '1rem', background: '#fefbf3', borderRadius: '8px', border: '1px solid #fed7aa'}}>
                <div style={{fontWeight: '600', color: '#9a3412'}}>Last Check</div>
                <div style={{fontSize: '1rem'}}>{new Date(health.timestamp).toLocaleTimeString()}</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Enhanced Knowledge Page
const StyledKnowledge = () => {
  return (
    <div style={styles.container}>
      <Navigation />
      <div style={styles.pageContent}>
        <div style={styles.hero}>
          <h1 style={{...styles.heroTitle, fontSize: '3rem'}}>📚 Knowledge Base</h1>
          <p style={styles.heroSubtitle}>
            Expert analysis database with curated sports betting insights
          </p>
        </div>

        <div style={styles.cardGrid}>
          {[
            { icon: '📖', title: '1,590+ Knowledge Chunks', desc: 'Curated expert analysis and insights' },
            { icon: '🤖', title: '6+ ML Models', desc: 'Advanced machine learning algorithms' },
            { icon: '📊', title: 'Real-time Data', desc: 'Live odds monitoring and updates' },
            { icon: '⚡', title: 'AI Analysis Engine', desc: 'Intelligent parlay generation system' }
          ].map((item, index) => (
            <div key={index} style={{...styles.card, cursor: 'default'}}>
              <span style={{...styles.cardIcon, color: '#667eea'}}>{item.icon}</span>
              <h3 style={styles.cardTitle}>{item.title}</h3>
              <p style={styles.cardDescription}>{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Main App Component
const AppStyled = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<StyledLanding />} />
        <Route path="/nfl" element={<StyledNFL />} />
        <Route path="/nba" element={<StyledNBA />} />
        <Route path="/dashboard" element={<StyledDashboard />} />
        <Route path="/knowledge" element={<StyledKnowledge />} />
      </Routes>
    </BrowserRouter>
  );
};

export default AppStyled;



