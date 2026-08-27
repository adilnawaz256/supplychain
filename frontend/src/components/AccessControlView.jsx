import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Users,
  KeyRound,
  FileText,
  Search,
  SlidersHorizontal,
  Plus,
  Edit2,
  MoreVertical,
  ChevronLeft,
  ChevronRight,
  Shield,
  Lock,
  Network,
  Code,
  BarChart2,
  Briefcase,
  Eye,
  ArrowRight,
  CheckCircle2
} from 'lucide-react';
import { API_BASE_URL } from '../config/api';

export default function AccessControlView({ onOpenNewRoleModal }) {
  const [activeSubTab, setActiveSubTab] = useState('roles');
  const [searchQuery, setSearchQuery] = useState('');
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadRoles() {
      try {
        const res = await fetch(`${API_BASE_URL}/api/access-control/roles`);
        if (res.ok) {
          const data = await res.json();
          setRoles(data);
        }
      } catch (err) {
        console.error('Error fetching roles:', err);
      } finally {
        setLoading(false);
      }
    }
    loadRoles();
  }, []);

  const getRoleIcon = (id) => {
    switch (id) {
      case 'admin': return { icon: ShieldCheck, color: '#7c3aed', bg: '#f5f3ff' };
      case 'de': return { icon: Code, color: '#2563eb', bg: '#eff6ff' };
      case 'da': return { icon: BarChart2, color: '#059669', bg: '#ecfdf5' };
      case 'om': return { icon: Briefcase, color: '#d97706', bg: '#fffbeb' };
      default: return { icon: Eye, color: '#475569', bg: '#f1f5f9' };
    }
  };

  const filteredRoles = roles.filter(r =>
    r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (r.desc && r.desc.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div style={{ padding: '0 32px 32px 32px', display: 'flex', flexDirection: 'column', gap: '24px' }}>

      {/* Sub Tabs: Roles, Users, Permissions, Audit Logs */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '24px',
        borderBottom: '1px solid #e2e8f0',
        paddingBottom: '4px'
      }}>
        <button
          onClick={() => setActiveSubTab('roles')}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '10px 4px', background: 'none', border: 'none',
            borderBottom: activeSubTab === 'roles' ? '2.5px solid #2563eb' : '2.5px solid transparent',
            color: activeSubTab === 'roles' ? '#2563eb' : '#64748b',
            fontWeight: activeSubTab === 'roles' ? 700 : 500,
            fontSize: '0.9rem', cursor: 'pointer'
          }}
        >
          <ShieldCheck size={17} />
          <span>Roles</span>
        </button>

        <button
          onClick={() => setActiveSubTab('users')}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '10px 4px', background: 'none', border: 'none',
            borderBottom: activeSubTab === 'users' ? '2.5px solid #2563eb' : '2.5px solid transparent',
            color: activeSubTab === 'users' ? '#2563eb' : '#64748b',
            fontWeight: activeSubTab === 'users' ? 700 : 500,
            fontSize: '0.9rem', cursor: 'pointer'
          }}
        >
          <Users size={17} />
          <span>Users</span>
        </button>

        <button
          onClick={() => setActiveSubTab('permissions')}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '10px 4px', background: 'none', border: 'none',
            borderBottom: activeSubTab === 'permissions' ? '2.5px solid #2563eb' : '2.5px solid transparent',
            color: activeSubTab === 'permissions' ? '#2563eb' : '#64748b',
            fontWeight: activeSubTab === 'permissions' ? 700 : 500,
            fontSize: '0.9rem', cursor: 'pointer'
          }}
        >
          <KeyRound size={17} />
          <span>Permissions</span>
        </button>

        <button
          onClick={() => setActiveSubTab('audit')}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '10px 4px', background: 'none', border: 'none',
            borderBottom: activeSubTab === 'audit' ? '2.5px solid #2563eb' : '2.5px solid transparent',
            color: activeSubTab === 'audit' ? '#2563eb' : '#64748b',
            fontWeight: activeSubTab === 'audit' ? 700 : 500,
            fontSize: '0.9rem', cursor: 'pointer'
          }}
        >
          <FileText size={17} />
          <span>Audit Logs</span>
        </button>
      </div>

      {/* Main Roles Table Card */}
      <div className="ui-card" style={{ padding: '24px' }}>
        
        {/* Header with Search and Actions */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '20px',
          gap: '16px',
          flexWrap: 'wrap'
        }}>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#0f172a', margin: 0 }}>
              Roles
            </h3>
            <p style={{ fontSize: '0.78rem', color: '#64748b', margin: '4px 0 0 0' }}>
              Define user roles and control access to data, tools, and workspace resources.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {/* Search Input */}
            <div style={{ position: 'relative', width: '240px' }}>
              <Search size={16} color="#94a3b8" style={{ position: 'absolute', left: '12px', top: '11px' }} />
              <input
                type="text"
                placeholder="Search roles..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="ui-input"
                style={{ paddingLeft: '36px', paddingRight: '12px', fontSize: '0.82rem' }}
              />
            </div>

            {/* Filters Button */}
            <button className="btn-secondary" style={{ padding: '8px 14px', fontSize: '0.82rem' }}>
              <SlidersHorizontal size={14} />
              <span>Filters</span>
            </button>

            {/* + New Role Button */}
            <button
              onClick={onOpenNewRoleModal}
              className="btn-primary"
              style={{ padding: '8px 16px', fontSize: '0.82rem' }}
            >
              <Plus size={15} />
              <span>New Role</span>
            </button>
          </div>
        </div>

        {/* Roles Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{
                color: '#64748b',
                textAlign: 'left',
                borderBottom: '1px solid #e2e8f0',
                fontSize: '0.78rem'
              }}>
                <th style={{ padding: '12px 14px', fontWeight: 600 }}>Role Name</th>
                <th style={{ padding: '12px 14px', fontWeight: 600 }}>Description</th>
                <th style={{ padding: '12px 14px', fontWeight: 600 }}>Users</th>
                <th style={{ padding: '12px 14px', fontWeight: 600 }}>Permission Scope</th>
                <th style={{ padding: '12px 14px', fontWeight: 600 }}>Last Modified</th>
                <th style={{ padding: '12px 14px', fontWeight: 600, textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredRoles.map((role) => {
                const iconInfo = getRoleIcon(role.id);
                const Icon = iconInfo.icon;
                return (
                  <tr
                    key={role.id}
                    style={{
                      borderBottom: '1px solid #f1f5f9',
                      transition: 'background-color 0.15s ease'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f8fafc'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    {/* Role Name */}
                    <td style={{ padding: '14px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{
                          width: '34px', height: '34px', borderRadius: '8px',
                          backgroundColor: iconInfo.bg, color: iconInfo.color,
                          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
                        }}>
                          <Icon size={18} />
                        </div>
                        <span style={{ fontWeight: 700, color: '#0f172a' }}>{role.name}</span>
                      </div>
                    </td>

                    {/* Description */}
                    <td style={{ padding: '14px', color: '#475569', fontSize: '0.82rem', maxWidth: '300px' }}>
                      {role.desc}
                    </td>

                    {/* Users count */}
                    <td style={{ padding: '14px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#475569', fontWeight: 600 }}>
                        <Users size={15} color="#94a3b8" />
                        <span>{role.usersCount}</span>
                      </div>
                    </td>

                    {/* Permission Scope Badge */}
                    <td style={{ padding: '14px' }}>
                      <span style={{
                        fontSize: '0.74rem',
                        fontWeight: 600,
                        color: role.scopeColor || '#2563eb',
                        backgroundColor: role.scopeBg || '#eff6ff',
                        padding: '3px 10px',
                        borderRadius: '6px',
                        display: 'inline-block'
                      }}>
                        {role.scope}
                      </span>
                    </td>

                    {/* Last Modified */}
                    <td style={{ padding: '14px', fontSize: '0.78rem' }}>
                      <div style={{ color: '#0f172a', fontWeight: 500 }}>{role.lastModified}</div>
                      <div style={{ color: '#64748b', fontSize: '0.72rem' }}>by {role.author}</div>
                    </td>

                    {/* Actions */}
                    <td style={{ padding: '14px', textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                        <button
                          style={{
                            background: 'none', border: 'none', cursor: 'pointer',
                            color: '#64748b', padding: '4px', borderRadius: '6px'
                          }}
                          title="Edit Role"
                        >
                          <Edit2 size={15} />
                        </button>
                        <button
                          style={{
                            background: 'none', border: 'none', cursor: 'pointer',
                            color: '#64748b', padding: '4px', borderRadius: '6px'
                          }}
                          title="More options"
                        >
                          <MoreVertical size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginTop: '18px',
          paddingTop: '14px',
          borderTop: '1px solid #f1f5f9',
          fontSize: '0.78rem',
          color: '#64748b'
        }}>
          <div>
            Showing 1 to {filteredRoles.length} of {roles.length} roles
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button style={{
              width: '28px', height: '28px', borderRadius: '6px',
              border: '1px solid #e2e8f0', background: '#ffffff',
              display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: '#94a3b8'
            }}>
              <ChevronLeft size={15} />
            </button>
            <button style={{
              width: '28px', height: '28px', borderRadius: '6px',
              border: '1px solid #2563eb', background: '#eff6ff', color: '#2563eb',
              fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer'
            }}>
              1
            </button>
            <button style={{
              width: '28px', height: '28px', borderRadius: '6px',
              border: '1px solid #e2e8f0', background: '#ffffff',
              display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: '#94a3b8'
            }}>
              <ChevronRight size={15} />
            </button>
          </div>
        </div>
      </div>

      {/* BOTTOM SECTION: Access Governance (5 Cards) */}
      <div>
        <div style={{ marginBottom: '14px' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a', margin: 0 }}>
            Access Governance
          </h3>
          <p style={{ fontSize: '0.78rem', color: '#64748b', margin: '4px 0 0 0' }}>
            Enterprise-grade security and governance to protect your data and control access.
          </p>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(5, 1fr)',
          gap: '14px'
        }}>
          {/* Card 1: Granular Permissions */}
          <div className="ui-card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div style={{
                width: '36px', height: '36px', borderRadius: '10px',
                backgroundColor: '#f5f3ff', color: '#7c3aed',
                display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '12px'
              }}>
                <Shield size={18} />
              </div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#0f172a' }}>Granular Permissions</div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '4px', lineHeight: 1.4 }}>
                Assign fine-grained permissions at the feature, workspace, and data level.
              </div>
            </div>
            <button style={{
              background: 'none', border: 'none', color: '#2563eb',
              fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '4px', marginTop: '14px', padding: 0
            }}>
              <span>Manage permissions</span>
              <ArrowRight size={13} />
            </button>
          </div>

          {/* Card 2: Audit Logs */}
          <div className="ui-card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div style={{
                width: '36px', height: '36px', borderRadius: '10px',
                backgroundColor: '#eff6ff', color: '#2563eb',
                display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '12px'
              }}>
                <FileText size={18} />
              </div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#0f172a' }}>Audit Logs</div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '4px', lineHeight: 1.4 }}>
                Track user activities, role changes, and permission updates in real time.
              </div>
            </div>
            <button style={{
              background: 'none', border: 'none', color: '#2563eb',
              fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '4px', marginTop: '14px', padding: 0
            }}>
              <span>View audit logs</span>
              <ArrowRight size={13} />
            </button>
          </div>

          {/* Card 3: Data Encryption */}
          <div className="ui-card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div style={{
                width: '36px', height: '36px', borderRadius: '10px',
                backgroundColor: '#ecfdf5', color: '#059669',
                display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '12px'
              }}>
                <Lock size={18} />
              </div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#0f172a' }}>Data Encryption</div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '4px', lineHeight: 1.4 }}>
                All data is encrypted in transit and at rest using enterprise-grade standards.
              </div>
            </div>
            <button style={{
              background: 'none', border: 'none', color: '#2563eb',
              fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '4px', marginTop: '14px', padding: 0
            }}>
              <span>Encryption settings</span>
              <ArrowRight size={13} />
            </button>
          </div>

          {/* Card 4: Connection Controls */}
          <div className="ui-card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div style={{
                width: '36px', height: '36px', borderRadius: '10px',
                backgroundColor: '#fffbeb', color: '#d97706',
                display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '12px'
              }}>
                <Network size={18} />
              </div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#0f172a' }}>Connection Controls</div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '4px', lineHeight: 1.4 }}>
                Restrict data source access by role, IP allowlist, or private network rules.
              </div>
            </div>
            <button style={{
              background: 'none', border: 'none', color: '#2563eb',
              fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '4px', marginTop: '14px', padding: 0
            }}>
              <span>Manage connections</span>
              <ArrowRight size={13} />
            </button>
          </div>

          {/* Card 5: Secure by Design Highlight */}
          <div style={{
            padding: '18px',
            borderRadius: '16px',
            backgroundColor: '#eff6ff',
            border: '1px solid #bfdbfe',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between'
          }}>
            <div>
              <div style={{
                width: '36px', height: '36px', borderRadius: '10px',
                backgroundColor: '#dbeafe', color: '#2563eb',
                display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '12px'
              }}>
                <ShieldCheck size={20} />
              </div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#1e3a8a' }}>Secure by Design</div>
              <div style={{ fontSize: '0.72rem', color: '#3b82f6', marginTop: '4px', lineHeight: 1.4 }}>
                Wisualyst follows industry best practices for access control, data protection, and compliance.
              </div>
            </div>
            <button style={{
              background: 'none', border: 'none', color: '#1d4ed8',
              fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '4px', marginTop: '14px', padding: 0
            }}>
              <span>View security overview</span>
              <ArrowRight size={13} />
            </button>
          </div>
        </div>
      </div>

    </div>
  );
}
