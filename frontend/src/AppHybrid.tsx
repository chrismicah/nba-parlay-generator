import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";

// Simple but beautiful styles
const styles = {
  page: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  },
  
  nav: {
    position: 'fixed' as const,
    top: '20px',
    left: '50%',
    transform: 'translateX(-50%)',
    background: 'rgba(255, 255, 255, 0.95)',
    backdropFilter: 'blur(10px)',
    borderRadius: '50px',
    padding: '12px 24px',
    boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
    zIndex: 1000,
    display: 'flex',
    alignItems: 'center',
    gap: '24px'
  },

  navLogo: {
    fontWeight: '700',
    fontSize: '1.1rem',
    background: 'linear-gradient(135deg, #667eea, #764ba2)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    textDecoration: 'none'
  },

  navLink: {
    color: '#374151',
    textDecoration: 'none',
    padding: '8px 16px',
    borderRadius: '25px',
    transition: 'all 0.3s ease',
    fontWeight: '500',
    fontSize: '14px'
  },

  content: {
    paddingTop: '120px',
    paddingBottom: '60px',
    paddingLeft: '20px',
    paddingRight: '20px',
    maxWidth: '1200px',
    margin: '0 auto'
  },

  hero: {
    textAlign: 'center' as const,
    marginBottom: '60px'
  },

  heroTitle: {
    fontSize: 'clamp(3rem, 8vw, 6rem)',
    fontWeight: '800',
    background: 'linear-gradient(135deg, #ffffff, #e2e8f0)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    marginBottom: '24px',
    lineHeight: '1.1'
  },

  heroSubtitle: {
    fontSize: '1.25rem',
    color: 'rgba(255,255,255,0.9)',
    marginBottom: '40px',
    maxWidth: '600px',
    margin: '0 auto 40px'
  },

  cardGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '24px',
    marginBottom: '60px'
  },

  card: {
    background: 'rgba(255,255,255,0.95)',
    backdropFilter: 'blur(10px)',
    borderRadius: '20px',
    padding: '40px',
    boxShadow: '0 20px 60px rgba(0,0,0,0.1)',
    border: '1px solid rgba(255,255,255,0.3)',
    textAlign: 'center' as const,
    transition: 'all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
    cursor: 'pointer',
    textDecoration: 'none',
    color: 'inherit',
    position: 'relative' as const,
    overflow: 'hidden'
  },

  cardIcon: {
    fontSize: '4rem',
    marginBottom: '20px',
    display: 'block'
  },

  cardTitle: {
    fontSize: '1.5rem',
    fontWeight: '700',
    marginBottom: '12px',
    color: '#1f2937'
  },

  cardDesc: {
    color: '#6b7280',
    lineHeight: '1.6',
    marginBottom: '24px'
  },

  button: {
    background: 'linear-gradient(135deg, #667eea, #764ba2)',
    color: 'white',
    border: 'none',
    padding: '16px 32px',
    borderRadius: '50px',
    fontSize: '1rem',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    boxShadow: '0 4px 20px rgba(102, 126, 234, 0.4)',
    width: '100%'
  },

  buttonNFL: {
    background: 'linear-gradient(135deg, #f97316, #ea580c)',
    boxShadow: '0 4px 20px rgba(249, 115, 22, 0.4)'
  },

  buttonNBA: {
    background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
    boxShadow: '0 4px 20px rgba(139, 92, 246, 0.4)'
  },

  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
    gap: '20px',
    background: 'rgba(255,255,255,0.1)',
    padding: '30px',
    borderRadius: '20px',
    backdropFilter: 'blur(10px)'
  },

  statItem: {
    textAlign: 'center' as const,
    color: 'white'
  },

  statValue: {
    fontSize: '2rem',
    fontWeight: '800',
    marginBottom: '8px'
  },

  statLabel: {
    fontSize: '0.9rem',
    opacity: 0.8
  },

  parlayCard: {
    background: 'rgba(255,255,255,0.95)',
    backdropFilter: 'blur(10px)',
    borderRadius: '20px',
    padding: '30px',
    boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
    border: '1px solid rgba(255,255,255,0.3)',
    marginTop: '30px'
  },

  parlayLeg: {
    background: '#f8fafc',
    padding: '16px',
    borderRadius: '12px',
    marginBottom: '12px',
    borderLeft: '4px solid #667eea'
  }
};

// Navigation Component
const Navigation = () => {
  const location = useLocation();
  
  const navItems = [
    { name: '🏈 NFL', path: '/nfl' },
    { name: '🏀 NBA', path: '/nba' },
    { name: '📊 Dashboard', path: '/dashboard' },
    { name: '📚 Knowledge', path: '/knowledge' }
  ];

  return (
    <nav style={styles.nav}>
      <Link to="/" style={styles.navLogo}>
        SportsBet AI
      </Link>
      {navItems.map(item => (
        <Link
          key={item.path}
          to={item.path}
          style={{
            ...styles.navLink,
            ...(location.pathname === item.path ? {
              background: 'linear-gradient(135deg, #667eea, #764ba2)',
              color: 'white'
            } : {})
          }}
          onMouseEnter={(e) => {
            if (location.pathname !== item.path) {
              e.currentTarget.style.background = 'linear-gradient(135deg, #667eea, #764ba2)';
              e.currentTarget.style.color = 'white';
            }
          }}
          onMouseLeave={(e) => {
            if (location.pathname !== item.path) {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = '#374151';
            }
          }}
        >
          {item.name}
        </Link>
      ))}
    </nav>
  );
};

// Landing Page
const HybridLanding = () => {
  const sports = [
    {
      icon: '🏈',
      title: 'NFL Parlays',
      description: 'Advanced NFL analysis with real game data and expert insights',
      path: '/nfl',
      buttonStyle: styles.buttonNFL
    },
    {
      icon: '🏀',
      title: 'NBA Parlays',
      description: 'ML-enhanced NBA predictions with confidence scoring',
      path: '/nba',
      buttonStyle: styles.buttonNBA
    }
  ];

  const stats = [
    { label: 'Knowledge Chunks', value: '1,590+' },
    { label: 'ML Models', value: '6+' },
    { label: 'API Endpoints', value: '7+' },
    { label: 'Sports Supported', value: '2' }
  ];

  return (
    <div style={styles.page}>
      <Navigation />
      <div style={styles.content}>
        <div style={styles.hero}>
          <h1 style={styles.heroTitle}>
            AI-Powered Sports Betting Platform
          </h1>
          <p style={styles.heroSubtitle}>
            Generate profitable parlay combinations with machine learning, expert knowledge, and real-time data analysis
          </p>
        </div>

        <div style={styles.cardGrid}>
          {sports.map((sport, index) => (
            <Link
              key={index}
              to={sport.path}
              style={styles.card}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-8px) scale(1.02)';
                e.currentTarget.style.boxShadow = '0 30px 80px rgba(0,0,0,0.15)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0) scale(1)';
                e.currentTarget.style.boxShadow = '0 20px 60px rgba(0,0,0,0.1)';
              }}
            >
              <span style={styles.cardIcon}>{sport.icon}</span>
              <h3 style={styles.cardTitle}>{sport.title}</h3>
              <p style={styles.cardDesc}>{sport.description}</p>
              <button style={{...styles.button, ...sport.buttonStyle}}>
                Generate Parlays →
              </button>
            </Link>
          ))}
        </div>

        <div style={styles.statsGrid}>
          {stats.map((stat, index) => (
            <div key={index} style={styles.statItem}>
              <div style={styles.statValue}>{stat.value}</div>
              <div style={styles.statLabel}>{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// NFL Page
const HybridNFL = () => {
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [parlay, setParlay] = React.useState(null);
  const [error, setError] = React.useState(null);

  const generateParlay = async () => {
    console.log('Generate parlay button clicked!');
    setIsGenerating(true);
    setError(null);
    
    try {
      console.log('Making API request...');
      const response = await fetch('http://localhost:8000/generate-nfl-parlay', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ target_legs: 3, min_total_odds: 2.0 })
      });
      
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Received data:', data);
      
      // Extract parlay from the response structure
      if (data.success && data.parlay) {
        setParlay(data.parlay);
      } else {
        setParlay(data); // Fallback if structure is different
      }
      
    } catch (error) {
      console.error('Detailed error:', error);
      setError(error.message);
      alert(`Error generating parlay: ${error.message}`);
    }
    setIsGenerating(false);
  };

  return (
    <div style={styles.page}>
      <Navigation />
      <div style={styles.content}>
        <div style={styles.hero}>
          <h1 style={{...styles.heroTitle, background: 'linear-gradient(135deg, #f97316, #ffffff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'}}>
            🏈 NFL Parlay Generator
          </h1>
          <p style={styles.heroSubtitle}>
            AI-powered NFL analysis with real game data and expert insights
          </p>
          
          <div style={{textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '16px', alignItems: 'center'}}>
            <button
              onClick={generateParlay}
              disabled={isGenerating}
              style={{
                ...styles.button,
                ...styles.buttonNFL,
                ...(isGenerating ? { background: '#9ca3af', cursor: 'not-allowed' } : {}),
                maxWidth: '300px'
              }}
            >
              {isGenerating ? '⚡ Generating...' : '🚀 Generate NFL Parlay'}
            </button>
            
            <button
              onClick={() => alert('Test button works!')}
              style={{
                ...styles.button,
                background: '#6b7280',
                maxWidth: '200px',
                fontSize: '0.9rem'
              }}
            >
              🧪 Test Click
            </button>
          </div>
        </div>

        {parlay && (
          <div style={styles.parlayCard}>
            <h3 style={{fontSize: '1.5rem', fontWeight: '700', marginBottom: '20px', color: '#1f2937'}}>
              Generated NFL Parlay
            </h3>
            
            <div style={{marginBottom: '20px', color: '#6b7280', fontSize: '0.95rem'}}>
              <strong>Confidence:</strong> {(parlay.confidence * 100)?.toFixed(0) || parlay.confidence_percentage}% | 
              <strong> Total Odds:</strong> +{Math.round((parlay.total_odds - 1) * 100)} |
              <strong> Expected Value:</strong> {parlay.expected_value?.toFixed(1)}%
            </div>
            
            {parlay.legs?.map((leg, index) => (
              <div key={index} style={{...styles.parlayLeg, borderLeftColor: '#f97316'}}>
                <div style={{fontWeight: '600', marginBottom: '4px', color: '#1f2937'}}>
                  {leg.game || leg.game_info || 'NFL Game'}
                </div>
                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                  <span style={{color: '#4b5563'}}>
                    <strong>{leg.market}:</strong> {leg.selection}
                  </span>
                  <span style={{fontWeight: '600', color: leg.odds > 0 ? '#059669' : '#dc2626'}}>
                    {leg.odds > 0 ? '+' : ''}{leg.odds}
                  </span>
                </div>
                {leg.book && (
                  <div style={{fontSize: '0.8rem', color: '#9ca3af', marginTop: '4px'}}>
                    Book: {leg.book}
                  </div>
                )}
              </div>
            ))}

            {parlay.season_note && (
              <div style={{background: '#fef3c7', border: '1px solid #f59e0b', borderRadius: '8px', padding: '16px', marginTop: '16px'}}>
                <strong style={{color: '#92400e'}}>⚠️ Season Note:</strong>
                <p style={{color: '#92400e', margin: '4px 0 0'}}>{parlay.season_note}</p>
              </div>
            )}

            {parlay.recommendation && (
              <div style={{background: '#d1fae5', border: '1px solid #10b981', borderRadius: '8px', padding: '16px', marginTop: '16px'}}>
                <strong style={{color: '#065f46'}}>💡 Recommendation:</strong>
                <p style={{color: '#065f46', margin: '4px 0 0'}}>{parlay.recommendation}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// NBA Page (similar structure)
const HybridNBA = () => {
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [parlay, setParlay] = React.useState(null);
  const [error, setError] = React.useState(null);

  const generateParlay = async () => {
    console.log('Generate NBA parlay button clicked!');
    setIsGenerating(true);
    setError(null);
    
    try {
      console.log('Making NBA API request...');
      const response = await fetch('http://localhost:8000/generate-nba-parlay', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ target_legs: 3, min_total_odds: 2.0 })
      });
      
      console.log('NBA Response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('NBA Received data:', data);
      
      // Extract parlay from the response structure
      if (data.success && data.parlay) {
        setParlay(data.parlay);
      } else {
        setParlay(data); // Fallback if structure is different
      }
      
    } catch (error) {
      console.error('NBA Detailed error:', error);
      setError(error.message);
      alert(`Error generating NBA parlay: ${error.message}`);
    }
    setIsGenerating(false);
  };

  return (
    <div style={styles.page}>
      <Navigation />
      <div style={styles.content}>
        <div style={styles.hero}>
          <h1 style={{...styles.heroTitle, background: 'linear-gradient(135deg, #8b5cf6, #ffffff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'}}>
            🏀 NBA Parlay Generator
          </h1>
          <p style={styles.heroSubtitle}>
            ML-enhanced NBA predictions with confidence scoring and expert analysis
          </p>
          
          <div style={{textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '16px', alignItems: 'center'}}>
            <button
              onClick={generateParlay}
              disabled={isGenerating}
              style={{
                ...styles.button,
                ...styles.buttonNBA,
                ...(isGenerating ? { background: '#9ca3af', cursor: 'not-allowed' } : {}),
                maxWidth: '300px'
              }}
            >
              {isGenerating ? '⚡ Generating...' : '🚀 Generate NBA Parlay'}
            </button>
            
            <button
              onClick={() => alert('NBA test button works!')}
              style={{
                ...styles.button,
                background: '#6b7280',
                maxWidth: '200px',
                fontSize: '0.9rem'
              }}
            >
              🧪 Test NBA Click
            </button>
          </div>
        </div>

        {parlay && (
          <div style={styles.parlayCard}>
            <h3 style={{fontSize: '1.5rem', fontWeight: '700', marginBottom: '20px', color: '#1f2937'}}>
              Generated NBA Parlay
            </h3>
            
            <div style={{marginBottom: '20px', color: '#6b7280', fontSize: '0.95rem'}}>
              <strong>Confidence:</strong> {(parlay.confidence * 100)?.toFixed(0) || parlay.confidence_percentage}% | 
              <strong> Total Odds:</strong> +{Math.round((parlay.total_odds - 1) * 100)} |
              <strong> Expected Value:</strong> {parlay.expected_value?.toFixed(1)}%
            </div>
            
            {parlay.legs?.map((leg, index) => (
              <div key={index} style={{...styles.parlayLeg, borderLeftColor: '#8b5cf6'}}>
                <div style={{fontWeight: '600', marginBottom: '4px', color: '#1f2937'}}>
                  {leg.game || leg.game_info || 'NBA Game'}
                </div>
                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                  <span style={{color: '#4b5563'}}>
                    <strong>{leg.market}:</strong> {leg.selection}
                  </span>
                  <span style={{fontWeight: '600', color: leg.odds > 0 ? '#059669' : '#dc2626'}}>
                    {leg.odds > 0 ? '+' : ''}{leg.odds}
                  </span>
                </div>
                {leg.book && (
                  <div style={{fontSize: '0.8rem', color: '#9ca3af', marginTop: '4px'}}>
                    Book: {leg.book}
                  </div>
                )}
              </div>
            ))}

            {parlay.recommendation && (
              <div style={{background: '#d1fae5', border: '1px solid #10b981', borderRadius: '8px', padding: '16px', marginTop: '16px'}}>
                <strong style={{color: '#065f46'}}>💡 Recommendation:</strong>
                <p style={{color: '#065f46', margin: '4px 0 0'}}>{parlay.recommendation}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Dashboard Page
const HybridDashboard = () => {
  const [health, setHealth] = React.useState(null);

  React.useEffect(() => {
    fetch('http://localhost:8000/health')
      .then(res => res.json())
      .then(setHealth)
      .catch(console.error);
  }, []);

  return (
    <div style={styles.page}>
      <Navigation />
      <div style={styles.content}>
        <div style={styles.hero}>
          <h1 style={{...styles.heroTitle, background: 'linear-gradient(135deg, #06b6d4, #ffffff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'}}>
            📊 System Dashboard
          </h1>
          <p style={styles.heroSubtitle}>
            Real-time monitoring and system performance analytics
          </p>
        </div>

        {health && (
          <div style={styles.parlayCard}>
            <h3 style={{fontSize: '1.5rem', fontWeight: '700', marginBottom: '20px', color: '#059669'}}>
              ✅ System Health Status
            </h3>
            
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px'}}>
              <div style={{background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '12px', padding: '20px', textAlign: 'center'}}>
                <div style={{fontSize: '1.5rem', fontWeight: '700', color: '#166534', textTransform: 'capitalize'}}>{health.status}</div>
                <div style={{color: '#166534', fontSize: '0.9rem'}}>System Status</div>
              </div>
              
              <div style={{background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: '12px', padding: '20px', textAlign: 'center'}}>
                <div style={{fontSize: '1.5rem', fontWeight: '700', color: '#075985'}}>{Math.round(health.uptime_seconds / 60)} min</div>
                <div style={{color: '#075985', fontSize: '0.9rem'}}>Uptime</div>
              </div>
              
              <div style={{background: '#fefbf3', border: '1px solid #fed7aa', borderRadius: '12px', padding: '20px', textAlign: 'center'}}>
                <div style={{fontSize: '1rem', fontWeight: '700', color: '#9a3412'}}>{new Date(health.timestamp).toLocaleTimeString()}</div>
                <div style={{color: '#9a3412', fontSize: '0.9rem'}}>Last Check</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Knowledge Page
const HybridKnowledge = () => {
  const items = [
    { icon: '📖', title: '1,590+ Knowledge Chunks', desc: 'Curated expert analysis and insights' },
    { icon: '🤖', title: '6+ ML Models', desc: 'Advanced machine learning algorithms' },
    { icon: '📊', title: 'Real-time Data', desc: 'Live odds monitoring and updates' },
    { icon: '⚡', title: 'AI Analysis Engine', desc: 'Intelligent parlay generation system' }
  ];

  return (
    <div style={styles.page}>
      <Navigation />
      <div style={styles.content}>
        <div style={styles.hero}>
          <h1 style={{...styles.heroTitle, background: 'linear-gradient(135deg, #10b981, #ffffff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'}}>
            📚 Knowledge Base
          </h1>
          <p style={styles.heroSubtitle}>
            Expert analysis database with curated sports betting insights
          </p>
        </div>

        <div style={styles.cardGrid}>
          {items.map((item, index) => (
            <div key={index} style={{...styles.card, cursor: 'default'}}>
              <span style={styles.cardIcon}>{item.icon}</span>
              <h3 style={styles.cardTitle}>{item.title}</h3>
              <p style={styles.cardDesc}>{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Main App
const AppHybrid = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HybridLanding />} />
        <Route path="/nfl" element={<HybridNFL />} />
        <Route path="/nba" element={<HybridNBA />} />
        <Route path="/dashboard" element={<HybridDashboard />} />
        <Route path="/knowledge" element={<HybridKnowledge />} />
      </Routes>
    </BrowserRouter>
  );
};

export default AppHybrid;
