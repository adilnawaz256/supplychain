import React, { useState, useEffect } from 'react';
import {
  Bell,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ExternalLink,
  MessageSquare,
  Sparkles,
  Bot,
  Send,
  Sliders,
  Check,
  Inbox,
  ShieldCheck
} from 'lucide-react';
import { API_BASE_URL } from '../config/api';

export default function AlertsView() {
  const [teamWorkspace, setTeamWorkspace] = useState('Global Supply Chain Enterprise');
  const [teamChannel, setTeamChannel] = useState('alerts-and-insights');
  const [isTeamsConnected, setIsTeamsConnected] = useState(() => {
    return localStorage.getItem('wisualyst_teams_connected') === 'true';
  });
  const [connectedAccount, setConnectedAccount] = useState(() => {
    return localStorage.getItem('wisualyst_teams_account') || 'fabric@wisualyst.com';
  });

  const [pipelineFailures, setPipelineFailures] = useState(true);
  const [dataQualityIssues, setDataQualityIssues] = useState(true);
  const [schemaChanges, setSchemaChanges] = useState(true);
  const [aiRecommendations, setAiRecommendations] = useState(true);
  const [testSent, setTestSent] = useState(false);
  const [isSending, setIsSending] = useState(false);

  const [riskAlerts, setRiskAlerts] = useState([]);
  const [recommendations, setRecommendations] = useState([]);

  const handleDisconnect = () => {
    setIsTeamsConnected(false);
    setConnectedAccount('');
    localStorage.removeItem('wisualyst_teams_connected');
    localStorage.removeItem('wisualyst_teams_account');
    if (window.history.pushState) {
      window.history.pushState('', document.title, window.location.pathname + '#alerts');
    }
  };

  useEffect(() => {
    // 1. Check URL query params (both search and hash)
    const searchParams = new URLSearchParams(window.location.search);
    const hashString = window.location.hash.includes('?') ? window.location.hash.split('?')[1] : '';
    const hashParams = new URLSearchParams(hashString);
    
    const isConnectedParam = searchParams.get('teams_connected') === 'true' || hashParams.get('teams_connected') === 'true';
    const accountParam = searchParams.get('account') || hashParams.get('account');

    if (isConnectedParam && accountParam) {
      setIsTeamsConnected(true);
      setConnectedAccount(accountParam);
      localStorage.setItem('wisualyst_teams_connected', 'true');
      localStorage.setItem('wisualyst_teams_account', accountParam);
    } else {
      // 2. Fetch connection status directly from API
      fetch(`${API_BASE_URL}/api/auth/microsoft/status`)
        .then(res => res.json())
        .then(data => {
          if (data && data.connected && data.account) {
            setIsTeamsConnected(true);
            setConnectedAccount(data.account);
            localStorage.setItem('wisualyst_teams_connected', 'true');
            localStorage.setItem('wisualyst_teams_account', data.account);
          }
        })
        .catch(err => console.log('OAuth status check note:', err));
    }

    async function loadAlerts() {
      try {
        const [riskRes, recRes] = await Promise.all([
          fetch(`${API_BASE_URL}/api/inventory-risk`),
          fetch(`${API_BASE_URL}/api/recommendations`)
        ]);
        if (riskRes.ok) setRiskAlerts(await riskRes.json());
        if (recRes.ok) setRecommendations(await recRes.json());
      } catch (err) {
        console.error('Error fetching alerts:', err);
      }
    }
    loadAlerts();
  }, []);

  const handleMicrosoftLogin = () => {
    // Direct 1-Click login to Microsoft 365 OAuth
    window.location.href = `${API_BASE_URL}/api/auth/microsoft/login`;
  };

  const handleSendTestMessage = async () => {
    setIsSending(true);
    try {
      await fetch(`${API_BASE_URL}/api/teams/webhook/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          webhook_url: webhookUrl,
          channel: teamChannel,
          type: 'STOCKOUT_ALERT',
          data: topCriticalRisk || { sku: 'SKU-ELEC-101', name: 'Smart IoT Sensor Node v2', risk: 'CRITICAL' }
        })
      });
      setTestSent(true);
      setTimeout(() => setTestSent(false), 4000);
    } catch (err) {
      console.error('Error broadcasting alert:', err);
    } finally {
      setIsSending(false);
    }
  };

  const topCriticalRisk = riskAlerts.find(r => r.stockout_risk_level === 'CRITICAL');
  const topRec = recommendations[0];

  return (
    <div style={{ padding: '0 32px 32px 32px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* 2-Column Grid: Left Settings & Right Teams Preview */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1.35fr',
        gap: '24px'
      }}>
        {/* LEFT COLUMN: Configuration Card */}
        <div className="ui-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '22px' }}>
          
          {/* Teams Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '44px', height: '44px', borderRadius: '12px',
              backgroundColor: '#5b5fc7', color: '#ffffff',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontWeight: 800, fontSize: '1.25rem', boxShadow: '0 4px 10px rgba(91, 95, 199, 0.3)'
            }}>
              T
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '1.05rem', fontWeight: 800, color: '#0f172a' }}>Microsoft Teams</span>
                <span style={{
                  fontSize: '0.72rem', fontWeight: 700,
                  color: isTeamsConnected ? '#059669' : '#d97706',
                  backgroundColor: isTeamsConnected ? '#ecfdf5' : '#fffbe8',
                  padding: '3px 10px', borderRadius: '999px',
                  display: 'flex', alignItems: 'center', gap: '5px'
                }}>
                  <span style={{
                    width: '6px', height: '6px', borderRadius: '50%',
                    backgroundColor: isTeamsConnected ? '#10b981' : '#f59e0b'
                  }} />
                  {isTeamsConnected ? `Connected (${connectedAccount})` : 'Not Connected'}
                </span>
              </div>
              <div style={{ fontSize: '0.76rem', color: '#64748b', marginTop: '2px' }}>
                Authorized Enterprise App via Azure Entra ID
              </div>
            </div>
          </div>

          {/* 1-Click Microsoft OAuth Action Card */}
          <div style={{
            padding: '16px', borderRadius: '12px',
            backgroundColor: isTeamsConnected ? '#f0fdf4' : '#f8fafc',
            border: isTeamsConnected ? '1px solid #bbf7d0' : '1px solid #e2e8f0',
            display: 'flex', flexDirection: 'column', gap: '12px'
          }}>
            {!isTeamsConnected ? (
              <>
                <div style={{ fontSize: '0.82rem', color: '#475569', lineHeight: 1.4 }}>
                  Connect your Microsoft 365 organization account with 1-click. No webhook setup needed!
                </div>
                <button
                  onClick={handleMicrosoftLogin}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px',
                    width: '100%', padding: '12px 18px', borderRadius: '10px',
                    backgroundColor: '#5b5fc7', color: '#ffffff',
                    fontWeight: 700, fontSize: '0.88rem', border: 'none', cursor: 'pointer',
                    boxShadow: '0 4px 12px rgba(91, 95, 199, 0.3)', transition: 'all 0.2s ease'
                  }}
                >
                  <svg width="18" height="18" viewBox="0 0 23 23">
                    <path fill="#f35325" d="M1 1h10v10H1z"/>
                    <path fill="#81bc06" d="M12 1h10v10H12z"/>
                    <path fill="#05a6f0" d="M1 12h10v10H1z"/>
                    <path fill="#ffba08" d="M12 12h10v10H12z"/>
                  </svg>
                  <span>Sign in with Microsoft (1-Click Connect)</span>
                </button>
              </>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <ShieldCheck size={20} color="#059669" />
                  <div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#065f46' }}>
                      Connected as {connectedAccount}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: '#047857' }}>
                      Azure Entra App ID: 52889720-e817-40ce-be25-ca732a9d1a5c
                    </div>
                  </div>
                </div>
                <button
                  onClick={handleDisconnect}
                  style={{
                    fontSize: '0.72rem', color: '#ef4444', background: 'none', border: 'none',
                    fontWeight: 600, cursor: 'pointer', textDecoration: 'underline'
                  }}
                >
                  Disconnect
                </button>
              </div>
            )}
          </div>

          {/* Form Fields */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#475569', marginBottom: '6px' }}>
                Teams Workspace
              </label>
              <select
                value={teamWorkspace}
                onChange={(e) => setTeamWorkspace(e.target.value)}
                className="ui-select"
              >
                <option value="Global Supply Chain Enterprise">Global Supply Chain Enterprise</option>
                <option value="Wisualyst Decision Tower">Wisualyst Decision Tower</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#475569', marginBottom: '6px' }}>
                Post to Channel
              </label>
              <select
                value={teamChannel}
                onChange={(e) => setTeamChannel(e.target.value)}
                className="ui-select"
              >
                <option value="alerts-and-insights"># alerts-and-insights</option>
                <option value="supply-chain-ops"># supply-chain-ops</option>
                <option value="executive-briefing"># executive-briefing</option>
              </select>
            </div>
          </div>

          {/* Alert Type Toggles */}
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#0f172a', marginBottom: '12px' }}>
              Select Alert Types to Broadcast
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#0f172a' }}>Pipeline Failures</div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Notify when ETL / Data Ingestion sync fails</div>
                </div>
                <label className="toggle-switch">
                  <input type="checkbox" checked={pipelineFailures} onChange={(e) => setPipelineFailures(e.target.checked)} />
                  <span className="toggle-slider" />
                </label>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#0f172a' }}>Data Quality Anomalies</div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Notify on schema anomalies & null rates &gt; 5%</div>
                </div>
                <label className="toggle-switch">
                  <input type="checkbox" checked={dataQualityIssues} onChange={(e) => setDataQualityIssues(e.target.checked)} />
                  <span className="toggle-slider" />
                </label>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#0f172a' }}>Critical Stockout Risks</div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Notify when SKU stock drops below safety buffer</div>
                </div>
                <label className="toggle-switch">
                  <input type="checkbox" checked={schemaChanges} onChange={(e) => setSchemaChanges(e.target.checked)} />
                  <span className="toggle-slider" />
                </label>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#0f172a' }}>AI Recommendations</div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Deliver high-impact prescriptive actions to team</div>
                </div>
                <label className="toggle-switch">
                  <input type="checkbox" checked={aiRecommendations} onChange={(e) => setAiRecommendations(e.target.checked)} />
                  <span className="toggle-slider" />
                </label>
              </div>
            </div>
          </div>

          {/* Broadcast Action Button */}
          <div style={{ marginTop: '8px' }}>
            <button
              onClick={handleSendTestMessage}
              disabled={isSending}
              style={{
                width: '100%', padding: '12px 18px', borderRadius: '10px',
                backgroundColor: '#5b5fc7', color: '#ffffff',
                fontWeight: 700, fontSize: '0.9rem', border: 'none', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                boxShadow: '0 4px 12px rgba(91, 95, 199, 0.25)'
              }}
            >
              <Send size={16} />
              <span>{isSending ? 'Dispatching to Teams...' : testSent ? '✓ Adaptive Card Sent to Teams!' : 'Broadcast Alert Card to Microsoft Teams'}</span>
            </button>
          </div>

        </div>

        {/* RIGHT COLUMN: Realistic Microsoft Teams Channel Preview */}
        <div style={{
          backgroundColor: '#ebebf5',
          borderRadius: '16px',
          border: '1px solid #d1d5db',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: 'var(--shadow-md)'
        }}>
          {/* Teams Header Bar */}
          <div style={{
            backgroundColor: '#464775',
            color: '#ffffff',
            padding: '12px 18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '24px', height: '24px', borderRadius: '4px', backgroundColor: '#5b5fc7', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 800 }}>
                T
              </div>
              <span style={{ fontSize: '0.88rem', fontWeight: 700 }}>
                {teamWorkspace} &gt; #{teamChannel}
              </span>
            </div>

            <span style={{ fontSize: '0.72rem', opacity: 0.8 }}>Live Teams Feed</span>
          </div>

          {/* Chat Messages Body */}
          <div style={{
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
            flex: 1,
            maxHeight: '620px',
            overflowY: 'auto'
          }}>
            
            {/* Card 1: Critical Stockout Alert */}
            <div style={{
              backgroundColor: '#ffffff',
              borderRadius: '10px',
              borderLeft: '4px solid #ef4444',
              padding: '16px',
              boxShadow: '0 2px 6px rgba(0,0,0,0.06)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <AlertTriangle size={16} color="#ef4444" />
                  <span style={{ fontSize: '0.82rem', fontWeight: 800, color: '#ef4444' }}>
                    🚨 CRITICAL STOCKOUT ALERT
                  </span>
                </div>
                <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Just now</span>
              </div>

              <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#0f172a' }}>
                {topCriticalRisk ? topCriticalRisk.product_name : 'Smart IoT Sensor Node v2'} ({topCriticalRisk ? topCriticalRisk.sku : 'SKU-ELEC-101'})
              </div>
              <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '2px' }}>
                Location: {topCriticalRisk ? topCriticalRisk.warehouse_name : 'Bangalore Distribution Hub'}
              </div>

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '8px',
                margin: '12px 0',
                padding: '10px',
                backgroundColor: '#f8fafc',
                borderRadius: '8px',
                fontSize: '0.75rem'
              }}>
                <div>
                  <span style={{ color: '#64748b', display: 'block' }}>Current Stock</span>
                  <strong style={{ color: '#ef4444', fontSize: '0.85rem' }}>{topCriticalRisk ? topCriticalRisk.current_stock : 12} units</strong>
                </div>
                <div>
                  <span style={{ color: '#64748b', display: 'block' }}>Safety Buffer</span>
                  <strong style={{ color: '#0f172a', fontSize: '0.85rem' }}>{topCriticalRisk ? topCriticalRisk.safety_stock : 40} units</strong>
                </div>
                <div>
                  <span style={{ color: '#64748b', display: 'block' }}>Days of Inv (DOI)</span>
                  <strong style={{ color: '#ef4444', fontSize: '0.85rem' }}>{topCriticalRisk ? topCriticalRisk.doi : 1.8} days</strong>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '10px' }}>
                <button style={{
                  padding: '6px 12px', borderRadius: '6px', backgroundColor: '#5b5fc7', color: '#ffffff',
                  border: 'none', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer'
                }}>
                  Approve Emergency PO (500 units)
                </button>
                <button style={{
                  padding: '6px 12px', borderRadius: '6px', backgroundColor: '#f1f5f9', color: '#475569',
                  border: '1px solid #cbd5e1', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer'
                }}>
                  View in Wisualyst
                </button>
              </div>
            </div>

            {/* Card 2: AI Prescriptive Action */}
            <div style={{
              backgroundColor: '#ffffff',
              borderRadius: '10px',
              borderLeft: '4px solid #2563eb',
              padding: '16px',
              boxShadow: '0 2px 6px rgba(0,0,0,0.06)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Sparkles size={16} color="#2563eb" />
                  <span style={{ fontSize: '0.82rem', fontWeight: 800, color: '#2563eb' }}>
                    🤖 AI PRESCRIPTIVE RECOMMENDATION
                  </span>
                </div>
                <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>10 mins ago</span>
              </div>

              <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#0f172a' }}>
                {topRec ? topRec.title : 'Transfer 200 units from WH-BOM-01 to WH-BLR-01'}
              </div>
              <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '4px', lineHeight: 1.4 }}>
                {topRec ? topRec.reasoning : 'Prevents AED 45,000 stockout loss. Supplier lead time is 14 days, but inter-warehouse transfer takes only 2 days.'}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '12px' }}>
                <button style={{
                  padding: '6px 12px', borderRadius: '6px', backgroundColor: '#2563eb', color: '#ffffff',
                  border: 'none', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer'
                }}>
                  Execute Inter-Warehouse Transfer
                </button>
              </div>
            </div>

          </div>
        </div>
      </div>

    </div>
  );
}
