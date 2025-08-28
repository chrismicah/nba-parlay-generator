const TestApp = () => {
  return (
    <div style={{ padding: '50px', fontFamily: 'Arial, sans-serif' }}>
      <h1 style={{ color: 'green', fontSize: '2rem' }}>✅ React is Working!</h1>
      <p>This is a minimal React app without any external dependencies.</p>
      <button 
        style={{ 
          padding: '10px 20px', 
          backgroundColor: '#007bff', 
          color: 'white', 
          border: 'none', 
          borderRadius: '5px',
          cursor: 'pointer',
          fontSize: '1rem'
        }}
        onClick={() => alert('Button clicked!')}
      >
        Test Button
      </button>
      <div style={{ marginTop: '20px', padding: '10px', backgroundColor: '#f8f9fa', borderRadius: '5px' }}>
        <strong>Debug Info:</strong>
        <ul>
          <li>✅ React mounted successfully</li>
          <li>✅ JavaScript executing</li>
          <li>✅ Styles applying</li>
        </ul>
      </div>
    </div>
  );
};

export default TestApp;



