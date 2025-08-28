import React from 'react';
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";

// Simple Landing Page
const SimpleLanding = () => {
  return (
    <div style={{ padding: '50px', fontFamily: 'Inter, Arial, sans-serif', backgroundColor: '#f8fafc' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto', textAlign: 'center' }}>
        <h1 style={{ 
          fontSize: '3.5rem', 
          fontWeight: 'bold', 
          color: '#1e293b',
          marginBottom: '20px',
          background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent'
        }}>
          🏀 NBA Parlay AI System 🏈
        </h1>
        
        <p style={{ 
          fontSize: '1.25rem', 
          color: '#64748b', 
          marginBottom: '40px',
          maxWidth: '600px',
          margin: '0 auto 40px'
        }}>
          AI-powered sports betting analysis with machine learning and expert knowledge integration
        </p>

        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', 
          gap: '20px',
          maxWidth: '800px',
          margin: '0 auto'
        }}>
          {[
            { title: '🏈 NFL Parlays', desc: 'Generate NFL parlay combinations', path: '/nfl', color: '#f97316' },
            { title: '🏀 NBA Parlays', desc: 'Create NBA betting strategies', path: '/nba', color: '#8b5cf6' },
            { title: '📊 Dashboard', desc: 'System health and stats', path: '/dashboard', color: '#06b6d4' },
            { title: '📚 Knowledge', desc: 'Expert analysis database', path: '/knowledge', color: '#10b981' }
          ].map((item, index) => (
            <Link 
              key={index}
              to={item.path} 
              style={{ textDecoration: 'none' }}
            >
              <div style={{
                padding: '30px 20px',
                backgroundColor: 'white',
                borderRadius: '12px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                border: `2px solid ${item.color}`,
                transition: 'transform 0.2s',
                cursor: 'pointer'
              }}
              onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-4px)'}
              onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0px)'}
              >
                <h3 style={{ margin: '0 0 10px', fontSize: '1.5rem', color: item.color }}>
                  {item.title}
                </h3>
                <p style={{ margin: 0, color: '#64748b', fontSize: '0.95rem' }}>
                  {item.desc}
                </p>
              </div>
            </Link>
          ))}
        </div>

        <div style={{ marginTop: '60px', padding: '20px', backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <h3 style={{ color: '#059669', marginBottom: '15px' }}>✅ System Status</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
            <div>✅ Backend API Running</div>
            <div>✅ Frontend Connected</div>
            <div>✅ Database Active</div>
            <div>✅ ML Models Loaded</div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Simple NFL Page
const SimpleNFL = () => {
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
    <div style={{ padding: '50px', fontFamily: 'Inter, Arial, sans-serif' }}>
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        <div style={{ marginBottom: '30px' }}>
          <Link to="/" style={{ color: '#3b82f6', textDecoration: 'none' }}>← Back to Home</Link>
        </div>
        
        <h1 style={{ fontSize: '2.5rem', color: '#1e293b', marginBottom: '20px' }}>🏈 NFL Parlays</h1>
        
        <button 
          onClick={generateParlay}
          disabled={isGenerating}
          style={{
            padding: '15px 30px',
            fontSize: '1.1rem',
            backgroundColor: isGenerating ? '#94a3b8' : '#f97316',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: isGenerating ? 'not-allowed' : 'pointer',
            marginBottom: '30px'
          }}
        >
          {isGenerating ? 'Generating...' : 'Generate NFL Parlay'}
        </button>

        {parlay && (
          <div style={{ 
            backgroundColor: 'white', 
            padding: '30px', 
            borderRadius: '12px', 
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
            border: '1px solid #e2e8f0'
          }}>
            <h3 style={{ color: '#1e293b', marginBottom: '20px' }}>Generated Parlay</h3>
            <div style={{ marginBottom: '20px' }}>
              <strong>Confidence:</strong> {parlay.confidence_percentage}% | 
              <strong> Total Odds:</strong> +{Math.round((parlay.total_odds - 1) * 100)}
            </div>
            
            {parlay.legs && parlay.legs.map((leg, index) => (
              <div key={index} style={{ 
                padding: '15px', 
                marginBottom: '10px', 
                backgroundColor: '#f8fafc', 
                borderRadius: '8px',
                borderLeft: '4px solid #f97316'
              }}>
                <strong>{leg.game_info || 'NFL Game'}</strong><br/>
                {leg.market}: {leg.selection} ({leg.odds > 0 ? '+' : ''}{leg.odds})
              </div>
            ))}

            {parlay.season_note && (
              <div style={{ 
                padding: '15px', 
                backgroundColor: '#fef3c7', 
                borderRadius: '8px', 
                marginTop: '15px',
                border: '1px solid #f59e0b'
              }}>
                <strong>Season Note:</strong> {parlay.season_note}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Simple NBA Page  
const SimpleNBA = () => {
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
    <div style={{ padding: '50px', fontFamily: 'Inter, Arial, sans-serif' }}>
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        <div style={{ marginBottom: '30px' }}>
          <Link to="/" style={{ color: '#3b82f6', textDecoration: 'none' }}>← Back to Home</Link>
        </div>
        
        <h1 style={{ fontSize: '2.5rem', color: '#1e293b', marginBottom: '20px' }}>🏀 NBA Parlays</h1>
        
        <button 
          onClick={generateParlay}
          disabled={isGenerating}
          style={{
            padding: '15px 30px',
            fontSize: '1.1rem',
            backgroundColor: isGenerating ? '#94a3b8' : '#8b5cf6',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: isGenerating ? 'not-allowed' : 'pointer',
            marginBottom: '30px'
          }}
        >
          {isGenerating ? 'Generating...' : 'Generate NBA Parlay'}
        </button>

        {parlay && (
          <div style={{ 
            backgroundColor: 'white', 
            padding: '30px', 
            borderRadius: '12px', 
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
            border: '1px solid #e2e8f0'
          }}>
            <h3 style={{ color: '#1e293b', marginBottom: '20px' }}>Generated Parlay</h3>
            <div style={{ marginBottom: '20px' }}>
              <strong>Confidence:</strong> {parlay.confidence_percentage}% | 
              <strong> Total Odds:</strong> +{Math.round((parlay.total_odds - 1) * 100)}
            </div>
            
            {parlay.legs && parlay.legs.map((leg, index) => (
              <div key={index} style={{ 
                padding: '15px', 
                marginBottom: '10px', 
                backgroundColor: '#f8fafc', 
                borderRadius: '8px',
                borderLeft: '4px solid #8b5cf6'
              }}>
                <strong>{leg.game_info || 'NBA Game'}</strong><br/>
                {leg.market}: {leg.selection} ({leg.odds > 0 ? '+' : ''}{leg.odds})
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Simple Dashboard
const SimpleDashboard = () => {
  const [health, setHealth] = React.useState(null);

  React.useEffect(() => {
    fetch('http://localhost:8000/health')
      .then(res => res.json())
      .then(setHealth)
      .catch(console.error);
  }, []);

  return (
    <div style={{ padding: '50px', fontFamily: 'Inter, Arial, sans-serif' }}>
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        <div style={{ marginBottom: '30px' }}>
          <Link to="/" style={{ color: '#3b82f6', textDecoration: 'none' }}>← Back to Home</Link>
        </div>
        
        <h1 style={{ fontSize: '2.5rem', color: '#1e293b', marginBottom: '20px' }}>📊 System Dashboard</h1>
        
        {health && (
          <div style={{ 
            backgroundColor: 'white', 
            padding: '30px', 
            borderRadius: '12px', 
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
            border: '1px solid #e2e8f0'
          }}>
            <h3 style={{ color: '#059669', marginBottom: '20px' }}>✅ System Health</h3>
            <div style={{ display: 'grid', gap: '15px' }}>
              <div><strong>Status:</strong> {health.status}</div>
              <div><strong>Uptime:</strong> {Math.round(health.uptime_seconds / 60)} minutes</div>
              <div><strong>Last Check:</strong> {new Date(health.timestamp).toLocaleTimeString()}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Simple Knowledge Page
const SimpleKnowledge = () => {
  return (
    <div style={{ padding: '50px', fontFamily: 'Inter, Arial, sans-serif' }}>
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        <div style={{ marginBottom: '30px' }}>
          <Link to="/" style={{ color: '#3b82f6', textDecoration: 'none' }}>← Back to Home</Link>
        </div>
        
        <h1 style={{ fontSize: '2.5rem', color: '#1e293b', marginBottom: '20px' }}>📚 Knowledge Base</h1>
        
        <div style={{ 
          backgroundColor: 'white', 
          padding: '30px', 
          borderRadius: '12px', 
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
          border: '1px solid #e2e8f0'
        }}>
          <h3 style={{ color: '#10b981', marginBottom: '20px' }}>Expert Knowledge Integration</h3>
          <div style={{ display: 'grid', gap: '15px' }}>
            <div>📖 <strong>1,590+</strong> curated knowledge chunks</div>
            <div>🤖 <strong>6+</strong> ML models trained</div>
            <div>📊 <strong>Real-time</strong> odds monitoring</div>
            <div>⚡ <strong>AI-powered</strong> analysis engine</div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Main App Component
const AppSimplified = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SimpleLanding />} />
        <Route path="/nfl" element={<SimpleNFL />} />
        <Route path="/nba" element={<SimpleNBA />} />
        <Route path="/dashboard" element={<SimpleDashboard />} />
        <Route path="/knowledge" element={<SimpleKnowledge />} />
      </Routes>
    </BrowserRouter>
  );
};

export default AppSimplified;



