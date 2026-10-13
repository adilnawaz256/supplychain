import React, { useState } from 'react';
import {
  X,
  ShieldCheck,
  UserPlus,
  Sliders,
  HelpCircle,
  CheckCircle2,
  DollarSign,
  Box,
  TrendingUp,
  ShoppingCart
} from 'lucide-react';

/* ---------------- 1. NEW ROLE MODAL ---------------- */
export function NewRoleModal({ isOpen, onClose, onSave }) {
  const [roleName, setRoleName] = useState('');
  const [description, setDescription] = useState('');
  const [scope, setScope] = useState('Data & Engine Access');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!roleName) return;
    if (onSave) onSave({ name: roleName, desc: description, scope });
    onClose();
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="ui-card animate-slide-up" onClick={(e) => e.stopPropagation()} style={{
        width: '460px',
        maxWidth: '92vw',
        padding: '24px',
        position: 'relative'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldCheck size={20} color="#2563eb" />
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0f172a', margin: 0 }}>Create New Role</h3>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '6px' }}>
              Role Name
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Supply Chain Planner"
              value={roleName}
              onChange={(e) => setRoleName(e.target.value)}
              className="ui-input"
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '6px' }}>
              Description
            </label>
            <textarea
              rows={3}
              placeholder="Describe access privileges and responsibilities..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="ui-input"
              style={{ resize: 'none' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '6px' }}>
              Permission Scope
            </label>
            <select
              value={scope}
              onChange={(e) => setScope(e.target.value)}
              className="ui-select"
            >
              <option value="Full Access">Full Access (All features & settings)</option>
              <option value="Data & Engine Access">Data & Engine Access</option>
              <option value="Read & Analyze">Read & Analyze (Reports & Insights)</option>
              <option value="Limited Access">Limited Access (View only alerts & recs)</option>
              <option value="Read Only">Read Only</option>
            </select>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
            <button type="button" onClick={onClose} className="btn-secondary" style={{ padding: '8px 16px' }}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" style={{ padding: '8px 20px' }}>
              Save Role
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ---------------- 2. INVITE MEMBER MODAL ---------------- */
export function InviteMemberModal({ isOpen, onClose, onInvite }) {
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState('Editor');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!email) return;
    if (onInvite) onInvite({ email, name, role });
    onClose();
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="ui-card animate-slide-up" onClick={(e) => e.stopPropagation()} style={{
        width: '460px',
        maxWidth: '92vw',
        padding: '24px',
        position: 'relative'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <UserPlus size={20} color="#2563eb" />
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0f172a', margin: 0 }}>Invite Team Member</h3>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '6px' }}>
              Full Name
            </label>
            <input
              type="text"
              placeholder="e.g. John Doe"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="ui-input"
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '6px' }}>
              Work Email
            </label>
            <input
              type="email"
              required
              placeholder="colleague@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="ui-input"
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '6px' }}>
              Assigned Role
            </label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="ui-select"
            >
              <option value="Editor">Editor (Full edit & pipeline access)</option>
              <option value="Viewer">Viewer (Read-only access)</option>
              <option value="Owner">Admin / Co-Owner</option>
            </select>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
            <button type="button" onClick={onClose} className="btn-secondary" style={{ padding: '8px 16px' }}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" style={{ padding: '8px 20px' }}>
              Send Invitation
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ---------------- 3. RECOMMENDATION SIMULATION MODAL ---------------- */
export function RecommendationSimulationModal({ isOpen, onClose, recommendation }) {
  if (!isOpen || !recommendation) return null;

  const impact = recommendation.financial_impact;
  const impactText = typeof impact === 'number' && !Number.isNaN(impact)
    ? `$${impact.toLocaleString()}`
    : (impact == null || impact === '' ? '—' : String(impact));

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="ui-card animate-slide-up" onClick={(e) => e.stopPropagation()} style={{
        width: '540px',
        maxWidth: '92vw',
        padding: '26px',
        position: 'relative'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#2563eb', backgroundColor: '#eff6ff', padding: '2px 8px', borderRadius: '6px' }}>
              {recommendation.tag || recommendation.category || 'AI Recommendation'}
            </span>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#0f172a', margin: '6px 0 0 0' }}>
              {recommendation.title}
            </h3>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}>
            <X size={18} />
          </button>
        </div>

        {/* Real recommendation details from the API (no simulated numbers) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '18px', fontSize: '0.82rem', color: '#334155' }}>
          {recommendation.summary && <div>{recommendation.summary}</div>}
          {recommendation.reason && <div><b>Reason:</b> {recommendation.reason}</div>}
          {recommendation.recommended_action && <div><b>Recommended action:</b> {recommendation.recommended_action}</div>}
          <div><b>Financial impact:</b> {impactText}</div>
        </div>

        <div style={{
          padding: '14px',
          borderRadius: '10px',
          backgroundColor: '#fffbeb',
          border: '1px solid #fde68a',
          fontSize: '0.8rem',
          color: '#78350f',
          marginBottom: '18px',
          lineHeight: 1.45
        }}>
          <b>Needs data: </b>
          What-if scenario simulation (demand / lead-time levers) is not calculated from the database yet, so no simulated impact is shown.
        </div>

        {/* Bottom Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
          <button
            onClick={onClose}
            className="btn-primary"
            style={{ padding: '8px 22px' }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---------------- 4. PLATFORM GUIDE & HELP MODAL ---------------- */
export function HelpModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="ui-card animate-slide-up" onClick={(e) => e.stopPropagation()} style={{
        width: '580px',
        maxWidth: '92vw',
        padding: '28px',
        position: 'relative'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '36px', height: '36px', borderRadius: '10px',
              background: 'linear-gradient(135deg, #2563eb, #8b5cf6)',
              color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              W
            </div>
            <div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#0f172a', margin: 0 }}>Wisualyst Platform Guide</h3>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Decision-Intelligence Control Tower</div>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}>
            <X size={18} />
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '0.85rem', color: '#334155', lineHeight: 1.5 }}>
          <div style={{ padding: '12px', borderRadius: '10px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
            <b style={{ color: '#0f172a' }}>1. Overview:</b> Live KPI telemetry (readiness score, stockout risk, forecast accuracy, savings — computed from your database) + Forecast vs Actual confidence ribbon chart + Top AI Recommendations.
          </div>
          <div style={{ padding: '12px', borderRadius: '10px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
            <b style={{ color: '#0f172a' }}>2. Workspaces:</b> 5-step workspace onboarding wizard with team invites & module activation + BI Export Streams (Power BI, Qlik, Google Sheets, Tableau, Excel).
          </div>
          <div style={{ padding: '12px', borderRadius: '10px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
            <b style={{ color: '#0f172a' }}>3. Data Sources:</b> Connect PostgreSQL, Zoho ERP, SFTP feeds + Schema Discovery + Canonical Field Mapping + Quality & Readiness report.
          </div>
          <div style={{ padding: '12px', borderRadius: '10px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
            <b style={{ color: '#0f172a' }}>4. Alerts & Teams:</b> Real-time webhook notifications for Pipeline failures, Data quality drops, and AI recommendations with interactive Teams preview.
          </div>
          <div style={{ padding: '12px', borderRadius: '10px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
            <b style={{ color: '#0f172a' }}>5. Access Control:</b> Role-based access control (Admin, Data Engineer, Data Analyst, Operations Manager, Viewer) + Enterprise security governance.
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '20px' }}>
          <button onClick={onClose} className="btn-primary" style={{ padding: '8px 20px' }}>
            Got It
          </button>
        </div>
      </div>
    </div>
  );
}
