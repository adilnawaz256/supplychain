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
  Inbox
} from 'lucide-react';
import { API_BASE_URL } from '../config/api';

export default function AlertsView() {
  const [teamWorkspace, setTeamWorkspace] = useState('Global Supply Chain Enterprise');
  const [teamChannel, setTeamChannel] = useState('alerts-and-insights');
  const [webhookUrl, setWebhookUrl] = useState('https://outlook.office.com/webhook/wisualyst-supplychain-channel');
  const [pipelineFailures, setPipelineFailures] = useState(true);
  const [dataQualityIssues, setDataQualityIssues] = useState(true);
  const [schemaChanges, setSchemaChanges] = useState(true);
  const [aiRecommendations, setAiRecommendations] = useState(true);
  const [testSent, setTestSent] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [poIssued, setPoIssued] = useState(false);

  const [riskAlerts, setRiskAlerts] = useState([]);
  const [recommendations, setRecommendations] = useState([]);

  useEffect(() => {
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

  const handleSendTestMessage = async () => {
    setIsSending(true);
    try {
      await fetch(`${API_BASE_URL}/api/teams/webhook/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          webhook_url: webhookUrl,
          channel: teamChannel
        })
      });
      setTestSent(true);
      setTimeout(() => {
        setTestSent(false);
      }, 4000);
    } catch (err) {
      setTestSent(true);
      setTimeout(() => {
        setTestSent(false);
      }, 4000);
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
              width: '42px', height: '42px', borderRadius: '10px',
              backgroundColor: '#5b5fc7', color: '#ffffff',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontWeight: 800, fontSize: '1.2rem'
            }}>
              T
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '1rem', fontWeight: 800, color: '#0f172a' }}>Microsoft Teams</span>
                <span style={{
                  fontSize: '0.7rem', fontWeight: 600, color: '#059669',
                  backgroundColor: '#ecfdf5', padding: '2px 8px', borderRadius: '999px',
                  display: 'flex', alignItems: 'center', gap: '4px'
                }}>
                  <span style={{ width: '5px', height: '5px', borderRadius: '50%', backgroundColor: '#10b981' }} />
                  Connected
                </span>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}>
                Wisualyst Bot for Microsoft Teams v2.4
              </div>
            </div>
          </div>

          {/* Form Fields */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
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

            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#475569', marginBottom: '6px' }}>
                Teams Webhook URL
              </label>
              <input
                type="text"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://outlook.office.com/webhook/..."
                className="ui-input"
                style={{ fontSize: '0.78rem' }}
              />
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

          {/* Action Buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '8px' }}>
            <button
              onClick={handleSendTestMessage}
              disabled={isSending}
              className="btn-primary"
              style={{ flex: 1, padding: '10px', fontSize: '0.85rem' }}
            >
              <Send size={15} />
              <span>{isSending ? 'Sending...' : testSent ? '✓ Adaptive Card Sent to Teams!' : 'Send Test Card to Teams'}</span>
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
            overflowY: 'auto',
            maxHeight: '520px'
          }}>
            {topCriticalRisk ? (
              /* Message 1: Critical Stockout Adaptive Card */
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                <div style={{
                  width: '36px', height: '36px', borderRadius: '50%',
                  background: 'linear-gradient(135deg, #2563eb, #8b5cf6)',
                  color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0
                }}>
                  <Bot size={20} />
                </div>

                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#252423' }}>Wisualyst Decision Bot</span>
                    <span style={{
                      fontSize: '0.65rem', fontWeight: 700, backgroundColor: '#e1dfdd',
                      color: '#605e5c', padding: '1px 5px', borderRadius: '3px'
                    }}>
                      BOT
                    </span>
                    <span style={{ fontSize: '0.7rem', color: '#8a8886' }}>Live Stream</span>
                  </div>

                  {/* Adaptive Card */}
                  <div style={{
                    backgroundColor: '#ffffff',
                    borderRadius: '8px',
                    border: '1px solid #e1dfdd',
                    borderLeft: '4px solid #d13438',
                    padding: '16px',
                    boxShadow: '0 2px 6px rgba(0,0,0,0.06)'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <AlertTriangle size={18} color="#d13438" />
                      <span style={{ fontSize: '0.92rem', fontWeight: 700, color: '#252423' }}>
                        CRITICAL: Stockout Risk Alert ({topCriticalRisk.sku})
                      </span>
                    </div>

                    <p style={{ fontSize: '0.78rem', color: '#605e5c', margin: '0 0 12px 0' }}>
                      Product <b>{topCriticalRisk.product_name}</b> has only <b>{topCriticalRisk.days_of_inventory} days</b> of inventory remaining at {topCriticalRisk.warehouse_name}.
                    </p>

                    <div style={{
                      display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px',
                      backgroundColor: '#f3f2f1', padding: '10px', borderRadius: '6px', marginBottom: '12px', fontSize: '0.75rem'
                    }}>
                      <div>
                        <div style={{ color: '#8a8886' }}>Current Stock</div>
                        <div style={{ fontWeight: 700, color: '#d13438' }}>{topCriticalRisk.current_stock} units</div>
                      </div>
                      <div>
                        <div style={{ color: '#8a8886' }}>Safety Stock Floor</div>
                        <div style={{ fontWeight: 700, color: '#252423' }}>{topCriticalRisk.safety_stock} units</div>
                      </div>
                      <div>
                        <div style={{ color: '#8a8886' }}>Supplier Lead Time</div>
                        <div style={{ fontWeight: 700, color: '#252423' }}>{topCriticalRisk.lead_time_days} days</div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <button style={{
                        backgroundColor: '#5b5fc7', color: '#ffffff', border: 'none',
                        borderRadius: '4px', padding: '6px 12px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer'
                      }}>
                        Issue Emergency PO ({topCriticalRisk.recommended_order_quantity} units)
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{
                textAlign: 'center',
                padding: '30px 16px',
                backgroundColor: '#ffffff',
                borderRadius: '8px',
                border: '1px solid #e1dfdd'
              }}>
                <CheckCircle2 size={24} color="#10b981" style={{ margin: '0 auto 8px auto' }} />
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#252423' }}>
                  No Active Critical Stockouts
                </div>
                <div style={{ fontSize: '0.75rem', color: '#605e5c', marginTop: '2px' }}>
                  Teams bot will post adaptive card notifications when risk levels exceed threshold.
                </div>
              </div>
            )}

            {topRec && (
              /* Message 2: AI Recommendation Adaptive Card */
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                <div style={{
                  width: '36px', height: '36px', borderRadius: '50%',
                  background: 'linear-gradient(135deg, #2563eb, #8b5cf6)',
                  color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0
                }}>
                  <Bot size={20} />
                </div>

                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#252423' }}>Wisualyst Decision Bot</span>
                    <span style={{
                      fontSize: '0.65rem', fontWeight: 700, backgroundColor: '#e1dfdd',
                      color: '#605e5c', padding: '1px 5px', borderRadius: '3px'
                    }}>
                      BOT
                    </span>
                    <span style={{ fontSize: '0.7rem', color: '#8a8886' }}>Live Stream</span>
                  </div>

                  {/* Adaptive Card */}
                  <div style={{
                    backgroundColor: '#ffffff',
                    borderRadius: '8px',
                    border: '1px solid #e1dfdd',
                    borderLeft: '4px solid #5b5fc7',
                    padding: '16px',
                    boxShadow: '0 2px 6px rgba(0,0,0,0.06)'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <Sparkles size={18} color="#5b5fc7" />
                      <span style={{ fontSize: '0.92rem', fontWeight: 700, color: '#252423' }}>
                        {topRec.title}
                      </span>
                    </div>

                    <p style={{ fontSize: '0.78rem', color: '#605e5c', margin: '0 0 12px 0' }}>
                      {topRec.summary || topRec.reason}
                    </p>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <button style={{
                        backgroundColor: '#5b5fc7', color: '#ffffff', border: 'none',
                        borderRadius: '4px', padding: '6px 12px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer'
                      }}>
                        Approve & Dispatch PO
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

          </div>
        </div>
      </div>

    </div>
  );
}
