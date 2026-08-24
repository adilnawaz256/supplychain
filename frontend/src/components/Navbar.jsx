import React from 'react';
import { Activity, ShieldAlert, Cpu, Bot, RefreshCw, Database } from 'lucide-react';

export default function Navbar({ onOpenChat, onSeedDatabase, isSeeding }) {
  return (
    <header className="glass-panel" style={{ borderRadius: '0 0 16px 16px', padding: '1rem 2rem', marginBottom: '2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ 
            width: '42px', height: '42px', borderRadius: '12px', 
            background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 20px rgba(99, 102, 241, 0.4)'
          }}>
            <Cpu size={24} color="#ffffff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.02em', background: 'linear-gradient(90deg, #ffffff, #9ca3af)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Supply Chain AI Control Tower
            </h1>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '2px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', display: 'inline-block', boxShadow: '0 0 8px #10b981' }}></span>
              Real-time Decision Intelligence POC | Engine Online
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button 
            onClick={onSeedDatabase} 
            disabled={isSeeding}
            className="input-dark" 
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.8rem' }}
            title="Reseed PostgreSQL / SQLite database with sample supply chain data"
          >
            {isSeeding ? <RefreshCw size={14} className="spin" /> : <Database size={14} />}
            {isSeeding ? 'Seeding...' : 'Reseed Data'}
          </button>

          <button onClick={onOpenChat} className="btn-primary">
            <Bot size={18} />
            Ask AI Assistant
          </button>
        </div>
      </div>
    </header>
  );
}
