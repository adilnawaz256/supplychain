import React, { useState, useEffect, useCallback } from 'react';
import {
  Database,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
  Table,
  Layers,
  Server,
  Check,
  Upload,
  Zap,
  Trash2,
  Lock,
  Building,
  Globe,
  Settings,
  ShieldCheck,
  Plus,
  Save,
  RotateCcw,
  SlidersHorizontal,
  FileSpreadsheet,
  Unplug
} from 'lucide-react';
import { API_BASE_URL } from '../config/api';

const TARGET_TABLE_CANONICAL = {
  products: [
    { key: 'sku', label: 'Product SKU (sku)', required: true },
    { key: 'name', label: 'Product Name (name)', required: true },
    { key: 'category', label: 'Category (category)', required: false },
    { key: 'unit_cost', label: 'Unit Cost (unit_cost)', required: false },
    { key: 'selling_price', label: 'Selling Price (selling_price)', required: false },
    { key: 'lead_time_days', label: 'Lead Time Days (lead_time_days)', required: false },
    { key: 'safety_stock_min', label: 'Safety Stock Min (safety_stock_min)', required: false },
    { key: 'reorder_point', label: 'Reorder Point (reorder_point)', required: false },
    { key: 'warehouse_code', label: 'Warehouse Code (inventory)', required: false },
    { key: 'current_stock', label: 'Stock On Hand (inventory)', required: false },
    { key: 'supplier_code', label: 'Supplier Code (suppliers)', required: false },
    { key: 'supplier_name', label: 'Supplier Name (suppliers)', required: false }
  ],
  orders: [
    { key: 'order_number', label: 'Order Number (order_number)', required: true },
    { key: 'customer_id', label: 'Customer ID (customer_id)', required: false },
    { key: 'order_date', label: 'Order Date (order_date)', required: true },
    { key: 'status', label: 'Status (status)', required: false },
    { key: 'total_amount', label: 'Total Amount (total_amount)', required: false },
    { key: 'shipping_address', label: 'Shipping Address (shipping_address)', required: false },
    { key: 'product_sku', label: 'Product SKU (feeds sales history)', required: false },
    { key: 'quantity_sold', label: 'Quantity Sold (feeds sales history)', required: false },
    { key: 'sales_revenue', label: 'Line Revenue (feeds sales history)', required: false },
    { key: 'warehouse_code', label: 'Warehouse Code', required: false }
  ],
  inventory: [
    { key: 'product_id', label: 'Product SKU / ID (product_id)', required: true },
    { key: 'warehouse_id', label: 'Warehouse Code / ID (warehouse_id)', required: false },
    { key: 'current_stock', label: 'Current Stock (current_stock)', required: true },
    { key: 'reserved_stock', label: 'Reserved Stock (reserved_stock)', required: false },
    { key: 'reorder_quantity', label: 'Reorder Quantity (reorder_quantity)', required: false }
  ],
  shipments: [
    { key: 'tracking_number', label: 'Tracking Number (tracking_number)', required: true },
    { key: 'order_id', label: 'Order ID (order_id)', required: false },
    { key: 'carrier', label: 'Carrier (carrier)', required: false },
    { key: 'status', label: 'Status (status)', required: false },
    { key: 'shipped_date', label: 'Shipped Date (shipped_date)', required: false }
  ],
  customers: [
    { key: 'customer_code', label: 'Customer Code (customer_code)', required: true },
    { key: 'name', label: 'Customer Name (name)', required: true },
    { key: 'email', label: 'Email (email)', required: false },
    { key: 'tier', label: 'Tier (tier)', required: false }
  ]
};

const autoMapColumn = (colName, tableName) => {
  if (!colName) return '';
  const clean = colName.toLowerCase().replace(/[\s_-]/g, '');
  const canonicalList = TARGET_TABLE_CANONICAL[tableName] || [];
  for (const c of canonicalList) {
    const keyClean = c.key.toLowerCase().replace(/[\s_-]/g, '');
    if (clean === keyClean || clean.includes(keyClean) || keyClean.includes(clean)) {
      return c.key;
    }
  }
  return '';
};

export default function DataSourcesView({ onNavigate }) {
  const [activeStep, setActiveStep] = useState(1);

  // --- Step 1: Workspace Form ---
  const [workspaceName, setWorkspaceName] = useState('Global Supply Chain');
  const [workspaceRegion, setWorkspaceRegion] = useState('UAE / GCC Hub');
  const [selectedIndustry, setSelectedIndustry] = useState('Retail & Distribution');

  // --- Step 2: Database / Connector Form ---
  const [connectorType, setConnectorType] = useState('DIRECT_DB');
  const [dbForm, setDbForm] = useState(() => {
    try {
      const saved = localStorage.getItem('wisualyst_connected_db_config');
      if (saved) return JSON.parse(saved);
    } catch (e) {}
    return { host: '', port: '5432', database: '', username: '', password: '', ssl_mode: 'require' };
  });

  const [isConnecting, setIsConnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(() => {
    try {
      return localStorage.getItem('wisualyst_db_connected') === 'true';
    } catch (e) {
      return false;
    }
  });
  const [connectSuccessMsg, setConnectSuccessMsg] = useState(null);
  const [connectErrorMsg, setConnectErrorMsg] = useState(null);

  // --- Step 3: Discovered Schema & Column Mapping ---
  const [selectedExternalTable, setSelectedExternalTable] = useState('');
  const [targetTable, setTargetTable] = useState('products');
  const [discoveredTables, setDiscoveredTables] = useState(() => {
    try {
      const saved = localStorage.getItem('wisualyst_discovered_tables');
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      return [];
    }
  });

  const [externalColumns, setExternalColumns] = useState([]);
  const [fieldMappings, setFieldMappings] = useState({});

  // --- Step 4: Data Dump & Ingestion Execution ---
  const [isDumping, setIsDumping] = useState(false);
  const [dumpResult, setDumpResult] = useState(null);
  const [importHistory, setImportHistory] = useState([]);
  const [importJob, setImportJob] = useState(null);

  // --- Persistent Multi-Device Synchronization ---
  // Fetches live status from PostgreSQL backend so all laptops/browsers show connected
  const syncFromBackend = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/connectors/status`);
      if (!res.ok) return;
      const data = await res.json();

      setIsConnected(!!data.is_connected);
      try {
        if (data.is_connected) localStorage.setItem('wisualyst_db_connected', 'true');
        else localStorage.removeItem('wisualyst_db_connected');
      } catch (e) {}

      if (data.workspace) {
        if (data.workspace.name) setWorkspaceName(data.workspace.name);
        if (data.workspace.region) setWorkspaceRegion(data.workspace.region);
        if (data.workspace.industry) setSelectedIndustry(data.workspace.industry);
      }

      if (data.connector) {
        setDbForm(prev => ({
          ...prev,
          host: data.connector.host || prev.host,
          port: data.connector.port || prev.port,
          database: data.connector.database || prev.database,
          username: data.connector.username || prev.username,
          ssl_mode: data.connector.ssl_mode || prev.ssl_mode
        }));
      }

      if (data.discovered_tables && data.discovered_tables.length > 0) {
        setDiscoveredTables(data.discovered_tables);
        try {
          localStorage.setItem('wisualyst_discovered_tables', JSON.stringify(data.discovered_tables));
        } catch (e) {}
        if (!selectedExternalTable) {
          setSelectedExternalTable(data.selected_external_table || data.discovered_tables[0].table_name);
        }
      }

      if (data.target_table) {
        setTargetTable(data.target_table);
      }

      if (data.field_mappings && Object.keys(data.field_mappings).length > 0) {
        setFieldMappings(prev => ({ ...prev, ...data.field_mappings }));
      }

      setImportHistory(data.ingestion_history || []);
      if (data.ingestion_status === 'SUCCESS') {
        setDumpResult(prev => prev?.details ? prev : {
          status: 'SUCCESS',
          message: `Last import: ${data.rows_ingested} rows from '${data.selected_external_table}' into '${data.target_table}'.`,
          rowsIngested: data.rows_ingested
        });
      }
    } catch (err) {
      console.warn('Backend pipeline sync note:', err);
    }
  }, [selectedExternalTable]);

  useEffect(() => {
    syncFromBackend();
    const handleFocus = () => syncFromBackend();
    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [syncFromBackend]);

  // Initialize default selected external table if discovered
  useEffect(() => {
    if (!selectedExternalTable && discoveredTables.length > 0) {
      setSelectedExternalTable(discoveredTables[0].table_name);
    }
  }, [discoveredTables, selectedExternalTable]);

  // Dynamic Column Prepopulation on Table Switch or Discovery
  useEffect(() => {
    let cols = [];
    if (selectedExternalTable) {
      const matchingTableObj = discoveredTables.find(t => t.table_name === selectedExternalTable);
      if (matchingTableObj && matchingTableObj.columns && matchingTableObj.columns.length > 0) {
        cols = matchingTableObj.columns;
      }
    }

    setExternalColumns(cols);

    setFieldMappings(prev => {
      const initialMap = { ...prev };
      cols.forEach(col => {
        if (!initialMap[col]) {
          initialMap[col] = autoMapColumn(col, targetTable);
        }
      });
      return initialMap;
    });
  }, [selectedExternalTable, targetTable, discoveredTables]);

  // Save Step 1 (Workspace details) to backend database
  const handleSaveStep1 = async () => {
    try {
      await fetch(`${API_BASE_URL}/api/connectors/save-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace_name: workspaceName,
          workspace_region: workspaceRegion,
          industry_vertical: selectedIndustry,
          active_step: 2
        })
      });
    } catch (e) {
      console.warn('Step 1 persist error:', e);
    }
    setActiveStep(2);
  };

  // Handle Database Connection & Table/Column Discovery
  const handleConnectDatabase = async (e) => {
    if (e) e.preventDefault();
    setIsConnecting(true);
    setConnectSuccessMsg(null);
    setConnectErrorMsg(null);

    try {
      const res = await fetch(`${API_BASE_URL}/api/connectors/discover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: connectorType,
          workspace_name: workspaceName,
          workspace_region: workspaceRegion,
          industry_vertical: selectedIndustry,
          ...dbForm
        })
      });

      const data = await res.json();
      if (!res.ok) {
        setConnectErrorMsg(data.detail || 'Could not connect to the database. Check host, port, username and password.');
        return;
      }
      if (data.tables && data.tables.length > 0) {
        setIsConnected(true);
        setDiscoveredTables(data.tables);
        setSelectedExternalTable(data.tables[0].table_name);
        setConnectSuccessMsg(`Connected & Synced across all devices! Discovered ${data.tables.length} tables in PostgreSQL database.`);
        try {
          localStorage.setItem('wisualyst_db_connected', 'true');
          localStorage.setItem('wisualyst_connected_db_config', JSON.stringify(dbForm));
          localStorage.setItem('wisualyst_discovered_tables', JSON.stringify(data.tables));
        } catch (e) {}
        setTimeout(() => setActiveStep(3), 600);
      } else {
        setIsConnected(true);
        setDiscoveredTables([]);
        setConnectSuccessMsg('Connected, but this database has no tables we can read.');
      }
    } catch (err) {
      setConnectErrorMsg(`Could not reach the backend: ${err.message}`);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      await fetch(`${API_BASE_URL}/api/connectors/disconnect`, { method: 'POST' });
    } catch (e) {}
    setIsConnected(false);
    setConnectSuccessMsg(null);
    try {
      localStorage.removeItem('wisualyst_db_connected');
    } catch (e) {}
    setActiveStep(1);
  };

  const handleMappingChange = (extCol, canonicalCol) => {
    setFieldMappings(prev => {
      const updated = {
        ...prev,
        [extCol]: canonicalCol
      };
      // Persist mapping to backend asynchronously so other devices see the saved mapping
      fetch(`${API_BASE_URL}/api/connectors/save-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          field_mappings: updated,
          target_table: targetTable,
          selected_external_table: selectedExternalTable
        })
      }).catch(() => {});
      return updated;
    });
  };

  const handleExecuteDataDump = async () => {
    setIsDumping(true);
    setDumpResult(null);

    try {
      const res = await fetch(`${API_BASE_URL}/api/connectors/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: connectorType,
          source_table: selectedExternalTable,
          target_table: targetTable,
          mappings: Object.entries(fieldMappings).filter(([src, tgt]) => tgt && externalColumns.includes(src)).map(([src, tgt]) => ({
            source_field: src,
            target_canonical_field: tgt
          })),
          ...dbForm
        })
      });

      const job = await res.json();
      if (!res.ok) {
        setDumpResult({ status: 'ERROR', message: job.detail || 'Import failed.' });
        return;
      }
      // The import runs in the background in batches; follow its progress until it finishes.
      let current = job;
      setImportJob(current);
      while (current.status === 'QUEUED' || current.status === 'RUNNING') {
        await new Promise(r => setTimeout(r, 1500));
        const poll = await fetch(`${API_BASE_URL}/api/jobs/${job.id}`);
        current = await poll.json();
        setImportJob(current);
      }
      const data = current.result || {};
      if (current.status !== 'SUCCESS') {
        setDumpResult({ status: 'ERROR', message: current.message || 'Import failed.' });
        return;
      }
      setDumpResult({
        status: 'SUCCESS',
        message: data.message,
        rowsIngested: data.rows_processed,
        details: data
      });
      setActiveStep(4);
      syncFromBackend();
    } catch (err) {
      setDumpResult({ status: 'ERROR', message: `Could not reach the backend: ${err.message}` });
    } finally {
      setIsDumping(false);
      setImportJob(null);
    }
  };

  return (
    <div style={{ padding: '28px 36px', maxWidth: '1400px', margin: '0 auto' }}>
      
      {/* Header */}
      <div style={{ marginBottom: '28px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '1.85rem', fontWeight: 800, color: '#0f172a', margin: '0 0 6px 0', letterSpacing: '-0.5px' }}>
            Workspace & Data Source Pipeline
          </h1>
          <p style={{ fontSize: '0.92rem', color: '#64748b', margin: 0 }}>
            Unified pipeline: Setup workspace, connect database, auto-discover schema, map columns, and dump into Supabase DB.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {isConnected ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{
                fontSize: '0.78rem',
                background: '#ecfdf5',
                color: '#047857',
                border: '1px solid #a7f3d0',
                padding: '5px 12px',
                borderRadius: '8px',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
              }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981', display: 'inline-block' }} />
                <CheckCircle2 size={14} /> Database Connected
              </span>
              <button
                onClick={handleDisconnect}
                title="Disconnect database connection across all devices"
                style={{
                  background: '#ffffff',
                  border: '1px solid #e2e8f0',
                  color: '#64748b',
                  fontSize: '0.75rem',
                  padding: '5px 10px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = '#ef4444'; e.currentTarget.style.borderColor = '#fca5a5'; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = '#64748b'; e.currentTarget.style.borderColor = '#e2e8f0'; }}
              >
                <Unplug size={12} /> Disconnect
              </button>
            </div>
          ) : (
            <span style={{ fontSize: '0.78rem', background: '#f8fafc', color: '#64748b', border: '1px solid #e2e8f0', padding: '5px 12px', borderRadius: '8px', fontWeight: 600 }}>
              Database Disconnected
            </span>
          )}
          <span style={{ fontSize: '0.78rem', background: '#eff6ff', color: '#2563eb', padding: '5px 12px', borderRadius: '8px', fontWeight: 700 }}>
            Step {activeStep} of 4
          </span>
        </div>
      </div>

      {/* Stepper Tabs */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '32px',
        backgroundColor: '#ffffff', padding: '16px', borderRadius: '16px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.03)'
      }}>
        <div onClick={() => setActiveStep(1)} style={{ padding: '12px 16px', borderRadius: '12px', backgroundColor: activeStep === 1 ? '#eff6ff' : '#f8fafc', border: activeStep === 1 ? '1.5px solid #2563eb' : '1px solid #e2e8f0', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '28px', height: '28px', borderRadius: '50%', backgroundColor: activeStep === 1 ? '#2563eb' : '#cbd5e1', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.82rem' }}>1</div>
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: activeStep === 1 ? '#1e40af' : '#334155' }}>Workspace Setup</div>
            <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Details & Region</div>
          </div>
        </div>

        <div onClick={() => setActiveStep(2)} style={{ padding: '12px 16px', borderRadius: '12px', backgroundColor: activeStep === 2 ? '#eff6ff' : '#f8fafc', border: activeStep === 2 ? '1.5px solid #2563eb' : '1px solid #e2e8f0', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '28px', height: '28px', borderRadius: '50%', backgroundColor: activeStep === 2 ? '#2563eb' : '#cbd5e1', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.82rem' }}>2</div>
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: activeStep === 2 ? '#1e40af' : '#334155' }}>Database Credentials</div>
            <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Postgres / Supabase</div>
          </div>
        </div>

        <div onClick={() => setActiveStep(3)} style={{ padding: '12px 16px', borderRadius: '12px', backgroundColor: activeStep === 3 ? '#eff6ff' : '#f8fafc', border: activeStep === 3 ? '1.5px solid #2563eb' : '1px solid #e2e8f0', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '28px', height: '28px', borderRadius: '50%', backgroundColor: activeStep === 3 ? '#2563eb' : '#cbd5e1', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.82rem' }}>3</div>
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: activeStep === 3 ? '#1e40af' : '#334155' }}>Column Schema Mapping</div>
            <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Discovered &rarr; Supabase</div>
          </div>
        </div>

        <div onClick={() => setActiveStep(4)} style={{ padding: '12px 16px', borderRadius: '12px', backgroundColor: activeStep === 4 ? '#ecfdf5' : '#f8fafc', border: activeStep === 4 ? '1.5px solid #10b981' : '1px solid #e2e8f0', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '28px', height: '28px', borderRadius: '50%', backgroundColor: activeStep === 4 ? '#10b981' : '#cbd5e1', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.82rem' }}>4</div>
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: activeStep === 4 ? '#047857' : '#334155' }}>Data Ingestion</div>
            <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Dump to Supabase DB</div>
          </div>
        </div>
      </div>

      {/* STEP 1: WORKSPACE SETUP */}
      {activeStep === 1 && (
        <div style={{ backgroundColor: '#ffffff', borderRadius: '20px', border: '1px solid #e2e8f0', padding: '32px', boxShadow: '0 4px 12px rgba(0,0,0,0.04)' }}>
          
          {isConnected && (
            <div style={{
              padding: '12px 16px',
              borderRadius: '12px',
              backgroundColor: '#ecfdf5',
              border: '1px solid #a7f3d0',
              color: '#047857',
              fontSize: '0.88rem',
              fontWeight: 600,
              marginBottom: '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <CheckCircle2 size={18} color="#10b981" />
                <span>Database is connected and synchronized with Supabase across all laptops & devices.</span>
              </div>
              <button
                onClick={() => setActiveStep(3)}
                style={{
                  background: '#047857',
                  color: '#ffffff',
                  border: 'none',
                  padding: '6px 14px',
                  borderRadius: '8px',
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                Go to Schema Mapping &rarr;
              </button>
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '12px', background: '#eff6ff', color: '#2563eb', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Building size={22} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0f172a', margin: 0 }}>Step 1: Workspace Selection & Setup</h2>
              <p style={{ fontSize: '0.84rem', color: '#64748b', margin: '2px 0 0 0' }}>Configure your enterprise workspace profile and regional data preferences.</p>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px', marginBottom: '28px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.84rem', fontWeight: 600, color: '#334155', marginBottom: '8px' }}>Workspace Name</label>
              <input type="text" value={workspaceName} onChange={(e) => setWorkspaceName(e.target.value)} className="ui-input" placeholder="Global Supply Chain" />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.84rem', fontWeight: 600, color: '#334155', marginBottom: '8px' }}>Data Hosting Region</label>
              <select value={workspaceRegion} onChange={(e) => setWorkspaceRegion(e.target.value)} className="ui-input">
                <option value="UAE / GCC Hub">UAE / GCC Hub (ap-south-1)</option>
                <option value="EU West (Frankfurt)">EU West (Frankfurt)</option>
                <option value="US East (N. Virginia)">US East (N. Virginia)</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.84rem', fontWeight: 600, color: '#334155', marginBottom: '8px' }}>Industry Vertical</label>
              <select value={selectedIndustry} onChange={(e) => setSelectedIndustry(e.target.value)} className="ui-input">
                <option value="Retail & Distribution">Retail & Distribution</option>
                <option value="Manufacturing & Consumer Goods">Manufacturing & Consumer Goods</option>
                <option value="E-Commerce & Omnichannel">E-Commerce & Omnichannel</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button onClick={handleSaveStep1} className="btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 24px' }}>
              <span>Next: Setup Database Credentials</span>
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: DATABASE CREDENTIALS */}
      {activeStep === 2 && (
        <div style={{ backgroundColor: '#ffffff', borderRadius: '20px', border: '1px solid #e2e8f0', padding: '32px', boxShadow: '0 4px 12px rgba(0,0,0,0.04)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '12px', background: '#eff6ff', color: '#2563eb', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Database size={22} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0f172a', margin: 0 }}>Step 2: Connect Database & Discover Schema</h2>
              <p style={{ fontSize: '0.84rem', color: '#64748b', margin: '2px 0 0 0' }}>Input host credentials to connect and auto-discover database tables & columns.</p>
            </div>
          </div>

          {connectSuccessMsg && (
            <div style={{ padding: '12px 16px', borderRadius: '10px', backgroundColor: '#ecfdf5', border: '1px solid #a7f3d0', color: '#047857', fontSize: '0.85rem', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle2 size={18} />
              <span>{connectSuccessMsg}</span>
            </div>
          )}

          {connectErrorMsg && (
            <div style={{ padding: '12px 16px', borderRadius: '10px', backgroundColor: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', fontSize: '0.85rem', marginBottom: '20px', display: 'flex', alignItems: 'flex-start', gap: '8px', wordBreak: 'break-word' }}>
              <AlertTriangle size={18} style={{ flexShrink: 0 }} />
              <span>{connectErrorMsg}</span>
            </div>
          )}

          {isConnected && !connectSuccessMsg && (
            <div style={{ padding: '12px 16px', borderRadius: '10px', backgroundColor: '#eff6ff', border: '1px solid #bfdbfe', color: '#1e40af', fontSize: '0.85rem', marginBottom: '20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={18} color="#2563eb" />
                <span>Connected to PostgreSQL at <strong>{dbForm.host}</strong> ({dbForm.database}). Saved in cloud database.</span>
              </div>
              <button
                type="button"
                onClick={() => setActiveStep(3)}
                style={{
                  background: '#2563eb',
                  color: '#ffffff',
                  border: 'none',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                Proceed to Mapping &rarr;
              </button>
            </div>
          )}

          <form onSubmit={handleConnectDatabase} style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px', marginBottom: '28px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Host / Server Address</label>
              <input type="text" required value={dbForm.host} onChange={(e) => setDbForm({ ...dbForm, host: e.target.value })} className="ui-input" placeholder="db.example.com" />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Port</label>
              <input type="text" required value={dbForm.port} onChange={(e) => setDbForm({ ...dbForm, port: e.target.value })} className="ui-input" placeholder="5432" />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Database Name</label>
              <input type="text" required value={dbForm.database} onChange={(e) => setDbForm({ ...dbForm, database: e.target.value })} className="ui-input" placeholder="postgres" />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Username</label>
              <input type="text" required value={dbForm.username} onChange={(e) => setDbForm({ ...dbForm, username: e.target.value })} className="ui-input" placeholder="database user" />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Password</label>
              <input type="password" value={dbForm.password} onChange={(e) => setDbForm({ ...dbForm, password: e.target.value })} className="ui-input" placeholder="Enter Database Password" />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>SSL Mode</label>
              <select value={dbForm.ssl_mode} onChange={(e) => setDbForm({ ...dbForm, ssl_mode: e.target.value })} className="ui-input">
                <option value="require">Require SSL (Supabase Standard)</option>
                <option value="disable">Disable SSL</option>
              </select>
            </div>

            <div style={{ gridColumn: 'span 2', display: 'flex', justifyContent: 'space-between', marginTop: '12px' }}>
              <button type="button" onClick={() => setActiveStep(1)} className="btn-secondary">Back to Step 1</button>
              <div style={{ display: 'flex', gap: '10px' }}>
                {isConnected && (
                  <button type="button" onClick={() => setActiveStep(3)} className="btn-secondary" style={{ color: '#2563eb', borderColor: '#bfdbfe' }}>
                    Skip to Mappings &rarr;
                  </button>
                )}
                <button type="submit" disabled={isConnecting} className="btn-primary">
                  {isConnecting ? 'Discovering Schema...' : 'Connect & Fetch Schema Columns →'}
                </button>
              </div>
            </div>
          </form>
        </div>
      )}

      {/* STEP 3: SELECT TABLE & MAP COLUMNS */}
      {activeStep === 3 && (
        <div style={{ backgroundColor: '#ffffff', borderRadius: '20px', border: '1px solid #e2e8f0', padding: '32px', boxShadow: '0 4px 12px rgba(0,0,0,0.04)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: '12px', background: '#eff6ff', color: '#2563eb', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Table size={22} />
              </div>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0f172a', margin: 0 }}>Step 3: Column Schema Mapping</h2>
                <p style={{ fontSize: '0.84rem', color: '#64748b', margin: '2px 0 0 0' }}>Connected database columns prepopulated. Map discovered columns to target Supabase tables.</p>
              </div>
            </div>

            <span style={{ fontSize: '0.78rem', background: '#f1f5f9', color: '#475569', padding: '4px 10px', borderRadius: '6px', fontWeight: 600 }}>
              {externalColumns.length} Discovered Columns
            </span>
          </div>

          {/* 1. Select External Source PostgreSQL Table */}
          <div style={{ marginBottom: '20px', background: '#f8fafc', padding: '16px 20px', borderRadius: '14px', border: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <span style={{ fontSize: '0.88rem', fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Database size={16} color="#2563eb" /> 1. Select External PostgreSQL Source Table:
              </span>
              <span style={{ fontSize: '0.78rem', color: '#64748b', fontWeight: 600 }}>
                {discoveredTables.length} Tables Discovered in Connected DB
              </span>
            </div>

            {discoveredTables.length === 0 && (
              <div style={{ fontSize: '0.84rem', color: '#92400e', background: '#fffbeb', border: '1px solid #fde68a', padding: '10px 14px', borderRadius: '10px' }}>
                No tables discovered yet. Go back to Step 2, enter your database password and click "Connect & Fetch Schema Columns".
              </div>
            )}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {discoveredTables.map((t) => {
                const isSelected = selectedExternalTable === t.table_name;
                return (
                  <button
                    key={t.table_name}
                    onClick={() => {
                      setSelectedExternalTable(t.table_name);
                      // Auto suggest target Supabase table based on name
                      const lower = t.table_name.toLowerCase();
                      let nextTarget = 'products';
                      if (lower.includes('order') || lower.includes('sale')) nextTarget = 'orders';
                      else if (lower.includes('stock') || lower.includes('inventory') || lower.includes('warehouse')) nextTarget = 'inventory';
                      else if (lower.includes('ship') || lower.includes('carrier') || lower.includes('logistics')) nextTarget = 'shipments';
                      else if (lower.includes('cust') || lower.includes('client') || lower.includes('user')) nextTarget = 'customers';
                      setTargetTable(nextTarget);
                      
                      // Save active selection to backend
                      fetch(`${API_BASE_URL}/api/connectors/save-config`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          selected_external_table: t.table_name,
                          target_table: nextTarget
                        })
                      }).catch(() => {});
                    }}
                    style={{
                      padding: '8px 14px', borderRadius: '8px', fontSize: '0.82rem', fontWeight: 700,
                      backgroundColor: isSelected ? '#1e40af' : '#ffffff',
                      color: isSelected ? '#ffffff' : '#334155',
                      border: isSelected ? '1.5px solid #1e40af' : '1px solid #cbd5e1',
                      cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px'
                    }}
                  >
                    <Table size={14} />
                    <span>{t.table_name}</span>
                    <span style={{ fontSize: '0.72rem', opacity: 0.85, background: isSelected ? 'rgba(255,255,255,0.2)' : '#f1f5f9', padding: '1px 6px', borderRadius: '4px' }}>
                      {t.record_count ?? 0} rows
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 2. Select Target Supabase DB Canonical Table */}
          <div style={{ marginBottom: '24px', background: '#eff6ff', padding: '16px 20px', borderRadius: '14px', border: '1px solid #bfdbfe' }}>
            <span style={{ fontSize: '0.88rem', fontWeight: 700, color: '#1e3a8a', display: 'block', marginBottom: '10px' }}>
              2. Select Target Supabase DB Table:
            </span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {[
                { id: 'products', label: 'products (Product Catalog & SKUs)' },
                { id: 'orders', label: 'orders (Sales Orders & POs)' },
                { id: 'inventory', label: 'inventory (Stock on Hand & Transits)' },
                { id: 'shipments', label: 'shipments (Fulfillment & Tracking)' },
                { id: 'customers', label: 'customers (Clients & Demand Tiers)' }
              ].map((table) => {
                const isSelected = targetTable === table.id;
                return (
                  <button
                    key={table.id}
                    onClick={() => {
                      setTargetTable(table.id);
                      fetch(`${API_BASE_URL}/api/connectors/save-config`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ target_table: table.id })
                      }).catch(() => {});
                    }}
                    style={{
                      padding: '8px 14px', borderRadius: '8px', fontSize: '0.82rem', fontWeight: 700,
                      backgroundColor: isSelected ? '#2563eb' : '#ffffff',
                      color: isSelected ? '#ffffff' : '#334155',
                      border: isSelected ? '1.5px solid #2563eb' : '1px solid #cbd5e1',
                      cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px'
                    }}
                  >
                    <Layers size={14} />
                    <span>{table.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 3. Column Mapping Table */}
          <div style={{ border: '1px solid #e2e8f0', borderRadius: '12px', overflow: 'hidden', marginBottom: '28px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569', fontWeight: 700 }}>
                  <th style={{ padding: '12px 16px', textAlign: 'left' }}>External Column (Source)</th>
                  <th style={{ padding: '12px 16px', textAlign: 'center', width: '50px' }}>&rarr;</th>
                  <th style={{ padding: '12px 16px', textAlign: 'left' }}>Target Supabase Column ({targetTable})</th>
                </tr>
              </thead>
              <tbody>
                {externalColumns.map((col, idx) => (
                  <tr key={col} style={{ borderBottom: idx === externalColumns.length - 1 ? 'none' : '1px solid #f1f5f9' }}>
                    <td style={{ padding: '12px 16px', fontWeight: 600, color: '#0f172a' }}>
                      <code>{col}</code>
                    </td>
                    <td style={{ padding: '12px 16px', textAlign: 'center', color: '#94a3b8' }}>
                      <ArrowRight size={16} />
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <select
                        value={fieldMappings[col] || ''}
                        onChange={(e) => handleMappingChange(col, e.target.value)}
                        className="ui-input"
                        style={{ padding: '6px 10px', fontSize: '0.82rem', borderColor: fieldMappings[col] ? '#10b981' : '#cbd5e1' }}
                      >
                        <option value="">-- Ignore Column --</option>
                        {(TARGET_TABLE_CANONICAL[targetTable] || []).map(item => (
                          <option key={item.key} value={item.key}>
                            {item.label} {item.required ? '*' : ''}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {importJob && (
            <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 10, padding: '12px 16px', marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, fontSize: '0.84rem', color: '#1e40af', fontWeight: 600, flexWrap: 'wrap' }}>
                <span>{importJob.message}</span>
                {importJob.progress_pct != null && <span>{importJob.progress_pct}%</span>}
              </div>
              <div style={{ marginTop: 8, height: 8, background: '#dbeafe', borderRadius: 999, overflow: 'hidden' }}>
                <div style={{ width: `${importJob.progress_pct ?? 3}%`, height: '100%', background: '#2563eb', transition: 'width 0.4s ease' }} />
              </div>
              <div style={{ marginTop: 6, fontSize: '0.74rem', color: '#475569' }}>
                Rows are copied in batches of 5,000. You can leave this page; the import keeps running on the server.
              </div>
            </div>
          )}

          {dumpResult?.status === 'ERROR' && (
            <div style={{ padding: '12px 16px', borderRadius: '10px', backgroundColor: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', fontSize: '0.85rem', marginBottom: '20px', display: 'flex', alignItems: 'flex-start', gap: '8px', wordBreak: 'break-word' }}>
              <AlertTriangle size={18} style={{ flexShrink: 0 }} />
              <span>{dumpResult.message}</span>
            </div>
          )}

          {!dbForm.password && (
            <div style={{ fontSize: '0.8rem', color: '#92400e', marginBottom: '14px' }}>
              The database password is not stored. If the import fails with an authentication error, re-enter it in Step 2.
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <button onClick={() => setActiveStep(2)} className="btn-secondary">Back to Step 2</button>
            <button onClick={handleExecuteDataDump} disabled={isDumping || !selectedExternalTable} className="btn-primary" style={{ padding: '12px 28px' }}>
              {isDumping ? `Copying rows from ${selectedExternalTable}...` : `Import '${selectedExternalTable || '—'}' into ${targetTable} →`}
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: DATA DUMP & INGESTION EXECUTION */}
      {activeStep === 4 && (
        <div style={{ backgroundColor: '#ffffff', borderRadius: '20px', border: '1px solid #e2e8f0', padding: '36px', textAlign: 'center', boxShadow: '0 4px 12px rgba(0,0,0,0.04)' }}>
          <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: '#ecfdf5', color: '#10b981', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px auto' }}>
            <CheckCircle2 size={36} />
          </div>

          <h2 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#0f172a', margin: '0 0 8px 0' }}>
            Data imported
          </h2>

          <p style={{ fontSize: '0.95rem', color: '#475569', maxWidth: '600px', margin: '0 auto 24px auto', lineHeight: 1.5 }}>
            {dumpResult?.message || 'No import has run yet. Pick a table in Step 3 and import it.'}
          </p>

          {dumpResult?.details && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '12px', maxWidth: '760px', margin: '0 auto 24px auto', textAlign: 'left' }}>
              {[
                ['Rows read', dumpResult.details.rows_fetched],
                ['Rows imported', dumpResult.details.rows_processed],
                ['Rows skipped', dumpResult.details.rows_skipped],
                ['Products', dumpResult.details.products_upserted],
                ['Stock lines', dumpResult.details.inventory_upserted],
                ['New sales rows', dumpResult.details.sales_created],
                ['Sales already present', dumpResult.details.sales_already_present],
                ['Suppliers', dumpResult.details.suppliers_upserted],
                ['Customers', dumpResult.details.customers_upserted],
                ['Orders', dumpResult.details.orders_upserted],
                ['Order lines', dumpResult.details.order_lines_created],
                ['Shipments', dumpResult.details.shipments_upserted]
              ].filter(([, v]) => v).map(([label, v]) => (
                <div key={label} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '10px 14px' }}>
                  <div style={{ fontSize: '0.72rem', color: '#64748b' }}>{label}</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#0f172a' }}>{Number(v).toLocaleString()}</div>
                </div>
              ))}
            </div>
          )}

          {dumpResult?.details?.skip_reasons && Object.keys(dumpResult.details.skip_reasons).length > 0 && (
            <p style={{ fontSize: '0.82rem', color: '#b45309', margin: '0 auto 20px auto', maxWidth: '600px' }}>
              Skipped: {Object.entries(dumpResult.details.skip_reasons).map(([r, n]) => `${n} rows (${r})`).join(', ')}
            </p>
          )}

          {importHistory.length > 0 && (
            <div style={{ maxWidth: '760px', margin: '0 auto 28px auto', textAlign: 'left', border: '1px solid #e2e8f0', borderRadius: '12px', overflow: 'hidden' }}>
              <div style={{ padding: '10px 14px', background: '#f8fafc', fontSize: '0.8rem', fontWeight: 700, color: '#334155' }}>
                Tables imported so far
              </div>
              {importHistory.map((h) => (
                <div key={h.source_table} style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap', padding: '10px 14px', borderTop: '1px solid #f1f5f9', fontSize: '0.82rem' }}>
                  <span><code>{h.source_table}</code> &rarr; <strong>{h.target_table}</strong></span>
                  <span style={{ color: h.status === 'SUCCESS' ? '#047857' : '#b91c1c', fontWeight: 600 }}>
                    {h.status === 'SUCCESS' ? `${h.rows_processed} rows` : 'failed'} · {new Date(h.at + 'Z').toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}

          <p style={{ fontSize: '0.85rem', color: '#475569', maxWidth: '620px', margin: '0 auto 24px auto', lineHeight: 1.5 }}>
            The ML engines are now recalculating with this data in the background. The Home dashboard shows their progress
            and updates by itself when they finish. Import more tables (sales, stock, customers, orders) to switch on more engines.
          </p>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '16px' }}>
            <button onClick={() => setActiveStep(3)} className="btn-secondary">Import another table</button>
            <button onClick={() => onNavigate && onNavigate('overview')} className="btn-primary">See what the ML engines found →</button>
          </div>
        </div>
      )}

    </div>
  );
}
