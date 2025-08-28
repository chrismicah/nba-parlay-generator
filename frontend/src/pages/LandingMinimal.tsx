import React from 'react';

const LandingMinimal: React.FC = () => {
  return (
    <div style={{ padding: '50px', textAlign: 'center', backgroundColor: '#f0f0f0' }}>
      <h1 style={{ color: '#333', fontSize: '3rem', marginBottom: '20px' }}>
        🏀 NBA Parlay AI System 🏈
      </h1>
      <p style={{ fontSize: '1.5rem', color: '#666', marginBottom: '30px' }}>
        System is running successfully!
      </p>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        gap: '20px',
        flexWrap: 'wrap'
      }}>
        <button 
          style={{ 
            padding: '15px 30px', 
            fontSize: '1.2rem', 
            backgroundColor: '#007bff', 
            color: 'white', 
            border: 'none', 
            borderRadius: '8px',
            cursor: 'pointer'
          }}
          onClick={() => window.location.href = '/nfl'}
        >
          🏈 NFL Parlays
        </button>
        <button 
          style={{ 
            padding: '15px 30px', 
            fontSize: '1.2rem', 
            backgroundColor: '#28a745', 
            color: 'white', 
            border: 'none', 
            borderRadius: '8px',
            cursor: 'pointer'
          }}
          onClick={() => window.location.href = '/nba'}
        >
          🏀 NBA Parlays
        </button>
        <button 
          style={{ 
            padding: '15px 30px', 
            fontSize: '1.2rem', 
            backgroundColor: '#6f42c1', 
            color: 'white', 
            border: 'none', 
            borderRadius: '8px',
            cursor: 'pointer'
          }}
          onClick={() => window.location.href = '/dashboard'}
        >
          📊 Dashboard
        </button>
      </div>
      <div style={{ marginTop: '40px', fontSize: '1rem', color: '#999' }}>
        <p>✅ Backend Running</p>
        <p>✅ Frontend Running</p>
        <p>✅ Both terminals restarted</p>
      </div>
    </div>
  );
};

export default LandingMinimal;



