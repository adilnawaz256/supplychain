import React, { useState } from 'react';
import { Download, ExternalLink, Database, FileSpreadsheet, CheckCircle2 } from 'lucide-react';
import { API_BASE_URL } from '../config/api';

export default function BIIntegrationsPanel() {
  const [downloaded, setDownloaded] = useState(false);

  const handleDownloadCsv = () => {
    window.open(`${API_BASE_URL}/api/bi/google-sheets`, '_blank');
    setDownloaded(true);
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* BI EXPORT ADAPTERS */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h2 style={{ fontSize: '1.4rem', color: '#f8fafc', marginBottom: '8px' }}>BI & Analytics Export Adapters</h2>
        <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '24px' }}>
          Connect Wisualyst canonical datasets directly to Power BI, Qlik Sense, and Google Sheets for enterprise reporting.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
          {/* Power BI */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <div style={{ padding: '10px', borderRadius: '10px', background: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b' }}>
                <Database size={24} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.05rem', color: '#f8fafc' }}>Power BI Desktop</h3>
                <span className="badge badge-success">DirectQuery Enabled</span>
              </div>
            </div>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '16px' }}>
              REST API dataset stream formatted for Power BI Dataflows & DirectQuery connections.
            </p>
            <a 
              href={`${API_BASE_URL}/api/bi/powerbi`} 
              target="_blank" 
              rel="noreferrer"
              style={{ textDecoration: 'none' }}
              className="glow-btn-primary"
            >
              <ExternalLink size={14} /> Open Power BI JSON Endpoint
            </a>
          </div>

          {/* Qlik Sense */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <div style={{ padding: '10px', borderRadius: '10px', background: 'rgba(6, 182, 212, 0.15)', color: '#06b6d4' }}>
                <Database size={24} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.05rem', color: '#f8fafc' }}>Qlik Sense REST</h3>
                <span className="badge badge-medium">REST Connector</span>
              </div>
            </div>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '16px' }}>
              qTable formatted JSON dataset stream for Qlik Sense Cloud and Qlik Enterprise.
            </p>
            <a 
              href={`${API_BASE_URL}/api/bi/qlik`} 
              target="_blank" 
              rel="noreferrer"
              style={{ textDecoration: 'none' }}
              className="glow-btn-primary"
            >
              <ExternalLink size={14} /> Open Qlik REST Endpoint
            </a>
          </div>

          {/* Google Sheets */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <div style={{ padding: '10px', borderRadius: '10px', background: 'rgba(16, 185, 129, 0.15)', color: '#10b981' }}>
                <FileSpreadsheet size={24} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.05rem', color: '#f8fafc' }}>Google Sheets / CSV</h3>
                <span className="badge badge-success">CSV Stream</span>
              </div>
            </div>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '16px' }}>
              Download flattened CSV dataset or link using Google Sheets IMPORTDATA formula.
            </p>
            <button onClick={handleDownloadCsv} className="glow-btn-primary">
              <Download size={14} /> Download CSV Dataset
            </button>
            {downloaded && (
              <div style={{ marginTop: '8px', fontSize: '0.75rem', color: '#6ee7b7', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <CheckCircle2 size={12} /> Dataset downloaded
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
