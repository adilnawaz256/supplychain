import React, { useState, useRef, useEffect } from 'react';
import { X, Send, Bot, User, Cpu, Sparkles, AlertCircle } from 'lucide-react';

export default function AIAssistantDrawer({ isOpen, onClose }) {
  const [messages, setMessages] = useState([
    {
      sender: 'bot',
      text: "Hello! I am your Supply Chain AI Assistant powered by Claude and MCP Tools.\n\nYou can ask me questions like:\n• *'Which products are at risk of stockout in the next 7 days?'*\n• *'Why is SKU-ELEC-101 at risk?'*\n• *'What should we reorder for Bangalore warehouse?'*",
      tools_used: [],
      reasoning: "System initialized with read-only database MCP tools."
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (!isOpen) return null;

  const handleSend = async (textToSend) => {
    const query = textToSend || input;
    if (!query.trim() || loading) return;

    const userMsg = { sender: 'user', text: query };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: query })
      });

      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, {
          sender: 'bot',
          text: data.response,
          tools_used: data.tools_used || [],
          reasoning: data.reasoning_summary
        }]);
      } else {
        setMessages(prev => [...prev, {
          sender: 'bot',
          text: "I encountered an issue connecting to the AI Agent service. Please ensure the backend server is running."
        }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        sender: 'bot',
        text: "Error communicating with AI service."
      }]);
    } finally {
      setLoading(false);
    }
  };

  const samplePrompts = [
    "Which products are at risk of stockout in the next 7 days?",
    "Why is SKU-ELEC-101 at risk?",
    "What should we reorder for Bangalore warehouse?"
  ];

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      right: 0,
      width: '440px',
      height: '100vh',
      background: 'rgba(14, 21, 38, 0.95)',
      backdropFilter: 'blur(20px)',
      borderLeft: '1px solid var(--border-glass-accent)',
      zIndex: 1000,
      display: 'flex',
      flexDirection: 'column',
      boxShadow: '-10px 0 30px rgba(0,0,0,0.5)'
    }}>
      {/* Drawer Header */}
      <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border-glass)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <Bot size={22} color="var(--primary-cyan)" />
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>AI Decision Assistant</h3>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>ReAct Agent + MCP Read-Only Tools</span>
          </div>
        </div>
        <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
          <X size={20} />
        </button>
      </div>

      {/* Messages List */}
      <div style={{ flex: 1, padding: '1.25rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {messages.map((m, idx) => (
          <div key={idx} style={{ display: 'flex', gap: '0.75rem', flexDirection: m.sender === 'user' ? 'row-reverse' : 'row' }}>
            <div style={{
              width: '32px', height: '32px', borderRadius: '50%',
              background: m.sender === 'user' ? 'var(--primary-indigo)' : 'var(--primary-cyan)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
            }}>
              {m.sender === 'user' ? <User size={16} color="#fff" /> : <Bot size={16} color="#fff" />}
            </div>

            <div style={{ maxWidth: '85%' }}>
              <div style={{
                background: m.sender === 'user' ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                border: '1px solid var(--border-glass)',
                padding: '0.85rem 1rem',
                borderRadius: '12px',
                fontSize: '0.85rem',
                lineHeight: '1.5',
                whiteSpace: 'pre-wrap'
              }}>
                {m.text}
              </div>

              {m.tools_used && m.tools_used.length > 0 && (
                <div style={{ fontSize: '0.7rem', color: 'var(--primary-cyan)', marginTop: '0.4rem', fontFamily: 'var(--font-mono)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <Cpu size={12} /> Tools: {m.tools_used.join(', ')}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
            <Sparkles size={16} className="spin" color="var(--primary-indigo)" />
            ReAct Agent reasoning & querying MCP tools...
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Suggested Prompts */}
      <div style={{ padding: '0.75rem 1.25rem', background: 'rgba(0,0,0,0.2)', borderTop: '1px solid var(--border-glass)' }}>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginBottom: '0.4rem' }}>SUGGESTED PROMPTS:</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          {samplePrompts.map((p, i) => (
            <button 
              key={i} 
              onClick={() => handleSend(p)}
              style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
                color: 'var(--text-muted)',
                padding: '0.35rem 0.6rem',
                borderRadius: '6px',
                textAlign: 'left',
                fontSize: '0.75rem',
                cursor: 'pointer'
              }}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Input */}
      <div style={{ padding: '1rem 1.25rem', borderTop: '1px solid var(--border-glass)', display: 'flex', gap: '0.5rem' }}>
        <input 
          type="text" 
          placeholder="Ask AI about stock risks, forecasts..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          className="input-dark"
          style={{ flex: 1 }}
        />
        <button onClick={() => handleSend()} className="btn-primary" disabled={loading} style={{ padding: '0.65rem' }}>
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
