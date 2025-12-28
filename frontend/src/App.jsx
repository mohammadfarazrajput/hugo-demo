import React, { useState, useEffect } from 'react';
import ChatInterface from './components/ChatInterface';
import Dashboard from './components/Dashboard';
import { Bot, BarChart3 } from 'lucide-react';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [status, setStatus] = useState(null);

  useEffect(() => {
    // Check backend status
    fetch('/api/health')
      .then(res => res.json())
      .then(data => setStatus(data))
      .catch(err => console.error('Failed to connect to Hugo:', err));
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="logo">
            <Bot size={32} />
            <h1>Hugo</h1>
          </div>
          <p className="tagline">AI Procurement Agent for Voltway Electric Scooters</p>
        </div>
        
        <nav className="tabs">
          <button
            className={`tab ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            <Bot size={20} />
            Chat with Hugo
          </button>
          <button
            className={`tab ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            <BarChart3 size={20} />
            Dashboard
          </button>
        </nav>
      </header>

      <main className="app-main">
        {status && !status.agents_initialized && (
          <div className="warning-banner">
            ⚠️ Hugo is still initializing. Some features may not be available yet.
          </div>
        )}
        
        {activeTab === 'chat' && <ChatInterface />}
        {activeTab === 'dashboard' && <Dashboard />}
      </main>

      <footer className="app-footer">
        <p>Powered by Google Gemini AI • Built for Dryft Challenge</p>
      </footer>
    </div>
  );
}

export default App;