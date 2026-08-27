import React, { useState } from 'react';
import {
  Home,
  LayoutGrid,
  Database,
  Cpu,
  FileText,
  Bell,
  LayoutDashboard,
  ChevronDown,
  ShieldCheck,
  LogOut,
  User,
  Settings,
  Sparkles,
  Layers
} from 'lucide-react';

export default function Sidebar({ activeTab, onTabChange, user, onSignOut, onOpenAuth }) {
  const [workspaceMenuOpen, setWorkspaceMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [currentWorkspace, setCurrentWorkspace] = useState('Global Supply Chain');

  const navItems = [
    { id: 'overview', label: 'Overview', icon: Home },
    { id: 'workspaces', label: 'Workspaces', icon: LayoutGrid },
    { id: 'datasources', label: 'Data Sources', icon: Database },
    { id: 'intelligence', label: 'Intelligence Engines', icon: Cpu },
    { id: 'recommendations', label: 'Recommendations', icon: FileText },
    { id: 'alerts', label: 'Alerts', icon: Bell },
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  ];

  const userInitials = user?.user_metadata?.full_name
    ? user.user_metadata.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
    : 'AV';
  const userName = user?.user_metadata?.full_name || 'Avery Johnson';
  const userRole = user?.user_metadata?.company_name ? 'Owner' : 'Admin';

  const workspacesList = [
    'Global Supply Chain',
    'North America Logistics',
    'EMEA Distribution Hub',
    'APAC Supply Network'
  ];

  return (
    <aside style={{
      width: '260px',
      backgroundColor: '#ffffff',
      borderRight: '1px solid #e2e8f0',
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      position: 'sticky',
      top: 0,
      zIndex: 40,
      flexShrink: 0,
      userSelect: 'none'
    }}>
      {/* Brand Header */}
      <div style={{
        padding: '24px 20px 20px 20px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px'
      }}>
        {/* Stylized Gradient 'W' Logo */}
        <div style={{
          width: '38px',
          height: '38px',
          borderRadius: '10px',
          background: 'linear-gradient(135deg, #2563eb, #8b5cf6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 4px 12px rgba(37, 99, 235, 0.25)'
        }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path d="M4 6L8.5 18L12 9.5L15.5 18L20 6" stroke="#ffffff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>

        <div>
          <span style={{
            fontSize: '1.35rem',
            fontWeight: 800,
            letterSpacing: '-0.5px',
            color: '#0f172a',
            fontFamily: 'var(--font-main)'
          }}>
            Wisualyst
          </span>
        </div>
      </div>

      {/* Main Nav Items */}
      <nav style={{
        flex: 1,
        padding: '12px 14px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        overflowY: 'auto'
      }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '14px',
                padding: '11px 14px',
                borderRadius: '10px',
                width: '100%',
                backgroundColor: isActive ? '#eff6ff' : 'transparent',
                color: isActive ? '#2563eb' : '#475569',
                border: 'none',
                cursor: 'pointer',
                fontWeight: isActive ? 600 : 500,
                fontSize: '0.9rem',
                textAlign: 'left',
                transition: 'all 0.15s ease',
                fontFamily: 'var(--font-main)'
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = '#f8fafc';
                  e.currentTarget.style.color = '#0f172a';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = '#475569';
                }
              }}
            >
              <Icon
                size={19}
                color={isActive ? '#2563eb' : '#64748b'}
                strokeWidth={isActive ? 2.3 : 1.8}
              />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Access Control shortcut */}
      <div style={{ padding: '0 14px 10px 14px' }}>
        <button
          onClick={() => onTabChange('access-control')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            padding: '9px 12px',
            borderRadius: '8px',
            width: '100%',
            backgroundColor: activeTab === 'access-control' ? '#f3e8ff' : '#f8fafc',
            color: activeTab === 'access-control' ? '#7e22ce' : '#64748b',
            border: '1px solid #e2e8f0',
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer',
            fontFamily: 'var(--font-main)',
            transition: 'all 0.15s ease'
          }}
        >
          <ShieldCheck size={16} color={activeTab === 'access-control' ? '#7e22ce' : '#64748b'} />
          <span>Access Control</span>
        </button>
      </div>

      {/* Bottom Section: Workspace Selector & User Profile */}
      <div style={{
        padding: '16px 14px 20px 14px',
        borderTop: '1px solid #e2e8f0',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      }}>
        {/* Workspace Dropdown */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setWorkspaceMenuOpen(!workspaceMenuOpen)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '10px 14px',
              borderRadius: '12px',
              backgroundColor: '#ffffff',
              border: '1px solid #e2e8f0',
              cursor: 'pointer',
              textAlign: 'left'
            }}
          >
            <div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: 500 }}>Workspace</div>
              <div style={{ fontSize: '0.85rem', color: '#0f172a', fontWeight: 600 }}>{currentWorkspace}</div>
            </div>
            <ChevronDown size={16} color="#94a3b8" />
          </button>

          {workspaceMenuOpen && (
            <div style={{
              position: 'absolute',
              bottom: '100%',
              left: 0,
              right: 0,
              marginBottom: '6px',
              backgroundColor: '#ffffff',
              border: '1px solid #e2e8f0',
              borderRadius: '12px',
              boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1)',
              padding: '6px',
              zIndex: 50
            }}>
              {workspacesList.map(ws => (
                <div
                  key={ws}
                  onClick={() => {
                    setCurrentWorkspace(ws);
                    setWorkspaceMenuOpen(false);
                  }}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '8px',
                    fontSize: '0.82rem',
                    color: currentWorkspace === ws ? '#2563eb' : '#334155',
                    fontWeight: currentWorkspace === ws ? 600 : 500,
                    backgroundColor: currentWorkspace === ws ? '#eff6ff' : 'transparent',
                    cursor: 'pointer'
                  }}
                  onMouseEnter={(e) => {
                    if (currentWorkspace !== ws) e.currentTarget.style.backgroundColor = '#f8fafc';
                  }}
                  onMouseLeave={(e) => {
                    if (currentWorkspace !== ws) e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                >
                  {ws}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* User Profile Bar */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '6px 4px',
              borderRadius: '10px',
              backgroundColor: 'transparent',
              border: 'none',
              cursor: 'pointer',
              textAlign: 'left'
            }}
          >
            {/* AV Avatar Circle */}
            <div style={{
              width: '38px',
              height: '38px',
              borderRadius: '50%',
              backgroundColor: '#1e293b',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: '0.88rem',
              flexShrink: 0
            }}>
              {userInitials}
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: '0.875rem',
                fontWeight: 600,
                color: '#0f172a',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {userName}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                {userRole}
              </div>
            </div>

            <ChevronDown size={16} color="#94a3b8" />
          </button>

          {userMenuOpen && (
            <div style={{
              position: 'absolute',
              bottom: '100%',
              left: 0,
              right: 0,
              marginBottom: '6px',
              backgroundColor: '#ffffff',
              border: '1px solid #e2e8f0',
              borderRadius: '12px',
              boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1)',
              padding: '6px',
              zIndex: 50
            }}>
              <div
                onClick={() => {
                  onTabChange('access-control');
                  setUserMenuOpen(false);
                }}
                style={{
                  display: 'flex', alignItems: 'center', gap: '10px',
                  padding: '9px 12px', borderRadius: '8px', fontSize: '0.82rem',
                  color: '#334155', cursor: 'pointer'
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f8fafc'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
              >
                <User size={15} color="#64748b" />
                <span>Account & Roles</span>
              </div>

              <div
                onClick={() => {
                  onOpenAuth();
                  setUserMenuOpen(false);
                }}
                style={{
                  display: 'flex', alignItems: 'center', gap: '10px',
                  padding: '9px 12px', borderRadius: '8px', fontSize: '0.82rem',
                  color: '#334155', cursor: 'pointer'
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f8fafc'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
              >
                <Sparkles size={15} color="#8b5cf6" />
                <span>Switch / Sign In</span>
              </div>

              <div style={{ height: '1px', backgroundColor: '#e2e8f0', margin: '4px 0' }} />

              <div
                onClick={() => {
                  onSignOut();
                  setUserMenuOpen(false);
                }}
                style={{
                  display: 'flex', alignItems: 'center', gap: '10px',
                  padding: '9px 12px', borderRadius: '8px', fontSize: '0.82rem',
                  color: '#ef4444', cursor: 'pointer'
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#fef2f2'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
              >
                <LogOut size={15} color="#ef4444" />
                <span>Sign Out</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
