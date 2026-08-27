import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  Box,
  ShoppingCart,
  Layers,
  Sliders,
  Play,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  TrendingDown,
  Info
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar
} from 'recharts';
import { API_BASE_URL } from '../config/api';

export default function IntelligenceEnginesView() {
  const [activeEngine, setActiveEngine] = useState('demand');
  const [demandShift, setDemandShift] = useState(15);
  const [leadTimeDelay, setLeadTimeDelay] = useState(3);
  const [serviceLevel, setServiceLevel] = useState(95);
  const [isSimulating, setIsSimulating] = useState(false);

  const [demandData, setDemandData] = useState(null);
  const [procurementData, setProcurementData] = useState(null);
  const [assortmentData, setAssortmentData] = useState(null);
  const [riskData, setRiskData] = useState([]);

  useEffect(() => {
    async function loadEngines() {
      try {
        const [demRes, procRes, asstRes, riskRes] = await Promise.all([
          fetch(`${API_BASE_URL}/api/modules/demand?product_id=1`),
          fetch(`${API_BASE_URL}/api/modules/procurement`),
          fetch(`${API_BASE_URL}/api/modules/assortment`),
          fetch(`${API_BASE_URL}/api/inventory-risk`)
        ]);

        if (demRes.ok) setDemandData(await demRes.json());
        if (procRes.ok) setProcurementData(await procRes.json());
        if (asstRes.ok) setAssortmentData(await asstRes.json());
        if (riskRes.ok) setRiskData(await riskRes.json());
      } catch (err) {
        console.error('Error fetching engine data:', err);
      }
    }
    loadEngines();
  }, []);

  const handleRunSimulation = () => {
    setIsSimulating(true);
    setTimeout(() => {
      setIsSimulating(false);
    }, 600);
  };

  const forecastPoints = demandData?.forecast_data || demandData?.forecast_points || [];
  const chartData = forecastPoints.map((pt, i) => {
    const baselineVal = pt.forecasted_demand ?? pt.predicted_demand ?? 0;
    return {
      date: pt.date ? pt.date.substring(5) : `Day ${i + 1}`,
      baseline: Math.round(baselineVal),
      simulated: Math.round(baselineVal * (1 + demandShift / 100)),
      safetyThreshold: Math.round(pt.lower_bound ?? baselineVal * 0.8)
    };
  });

  return (
    <div style={{ padding: '0 32px 32px 32px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* 4 Engine Switcher Tabs */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '14px'
      }}>
        {[
          { id: 'demand', title: '1. Demand Forecasting', icon: TrendingUp, activeColor: '#2563eb', bg: '#eff6ff', desc: 'Holt-Winters & Ridge Time Series' },
          { id: 'inventory', title: '2. Multi-Echelon Inventory', icon: Box, activeColor: '#2563eb', bg: '#eff6ff', desc: 'Safety Stock & Reorder Points' },
          { id: 'procurement', title: '3. Procurement EOQ', icon: ShoppingCart, activeColor: '#7c3aed', bg: '#f5f3ff', desc: 'Supplier OTIF & PO Scheduling' },
          { id: 'assortment', title: '4. Assortment Optimization', icon: Layers, activeColor: '#ea580c', bg: '#fff7ed', desc: 'Store Space & GMROI Clustering' }
        ].map((eng) => {
          const Icon = eng.icon;
          const isSelected = activeEngine === eng.id;
          return (
            <div
              key={eng.id}
              onClick={() => setActiveEngine(eng.id)}
              className="ui-card"
              style={{
                padding: '16px',
                cursor: 'pointer',
                border: isSelected ? `2px solid ${eng.activeColor}` : '1px solid #e2e8f0',
                backgroundColor: '#ffffff',
                boxShadow: isSelected ? 'var(--shadow-md)' : 'var(--shadow-xs)',
                transition: 'all 0.15s ease'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{
                  width: '36px', height: '36px', borderRadius: '8px',
                  backgroundColor: eng.bg, color: eng.activeColor,
                  display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                  <Icon size={18} />
                </div>
                <div>
                  <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#0f172a' }}>{eng.title}</div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '2px' }}>{eng.desc}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Engine Body with What-if Scenario Levers */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1.4fr 0.85fr',
        gap: '20px'
      }}>
        {/* Main Chart / Engine View */}
        <div className="ui-card" style={{ padding: '22px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a', margin: 0 }}>
                {activeEngine === 'demand' && 'Autonomous Demand Projection & Uncertainty Interval'}
                {activeEngine === 'inventory' && 'Multi-Echelon Stockout & Safety Buffer Matrix'}
                {activeEngine === 'procurement' && 'Dynamic Purchase Order Schedule & Supplier OTIF'}
                {activeEngine === 'assortment' && 'Retail Store Shelf GMROI & Cluster Optimization'}
              </h3>
              <p style={{ fontSize: '0.75rem', color: '#64748b', margin: '4px 0 0 0' }}>
                Live backend statistical algorithms evaluating connected products across regional hubs.
              </p>
            </div>

            <button
              onClick={handleRunSimulation}
              className="btn-primary"
              style={{ padding: '8px 16px', fontSize: '0.8rem' }}
            >
              <Play size={14} />
              <span>{isSimulating ? 'Simulating...' : 'Run What-If Scenario'}</span>
            </button>
          </div>

          {/* Dynamic Visualization */}
          {activeEngine === 'demand' && (
            chartData.length > 0 ? (
              <div style={{ width: '100%', height: '280px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                    <XAxis dataKey="date" tickLine={false} stroke="#64748b" tick={{ fontSize: 11 }} />
                    <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="baseline" stroke="#2563eb" strokeWidth={2.5} name="Baseline Forecast" />
                    <Line type="monotone" dataKey="simulated" stroke="#8b5cf6" strokeWidth={2.5} strokeDasharray="4 4" name="Simulated Demand" />
                    <Line type="monotone" dataKey="safetyThreshold" stroke="#ef4444" strokeWidth={1.5} name="Safety Stock Floor" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div style={{
                height: '280px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                backgroundColor: '#f8fafc', borderRadius: '10px', border: '1px dashed #cbd5e1', color: '#64748b', fontSize: '0.82rem'
              }}>
                <TrendingUp size={24} color="#94a3b8" style={{ marginBottom: '8px' }} />
                <span>No demand forecast points. Connect data sources to train models.</span>
              </div>
            )
          )}

          {activeEngine === 'inventory' && (
            riskData.length > 0 ? (
              <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                  <thead>
                    <tr style={{ color: '#64748b', textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>SKU</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Product</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Warehouse</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Days of Supply</th>
                      <th style={{ padding: '8px 0', fontWeight: 600, textAlign: 'right' }}>Risk Level</th>
                    </tr>
                  </thead>
                  <tbody>
                    {riskData.slice(0, 8).map((r, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #f8fafc' }}>
                        <td style={{ padding: '8px 0', fontWeight: 700, color: '#2563eb' }}>{r.sku}</td>
                        <td style={{ padding: '8px 0', color: '#0f172a', fontWeight: 500 }}>{r.product_name}</td>
                        <td style={{ padding: '8px 0', color: '#64748b' }}>{r.warehouse_name}</td>
                        <td style={{ padding: '8px 0', color: '#334155', fontWeight: 600 }}>{r.days_of_inventory} days</td>
                        <td style={{ padding: '8px 0', textAlign: 'right' }}>
                          <span style={{
                            fontSize: '0.7rem',
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: '6px',
                            backgroundColor: r.stockout_risk_level === 'CRITICAL' ? '#fef2f2' : r.stockout_risk_level === 'HIGH' ? '#fffbeb' : '#ecfdf5',
                            color: r.stockout_risk_level === 'CRITICAL' ? '#ef4444' : r.stockout_risk_level === 'HIGH' ? '#f59e0b' : '#10b981'
                          }}>
                            {r.stockout_risk_level}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{
                height: '280px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                backgroundColor: '#f8fafc', borderRadius: '10px', border: '1px dashed #cbd5e1', color: '#64748b', fontSize: '0.82rem'
              }}>
                <Box size={24} color="#94a3b8" style={{ marginBottom: '8px' }} />
                <span>0 inventory stock lines in database.</span>
              </div>
            )
          )}

          {activeEngine === 'procurement' && (
            (procurementData?.order_recommendations && procurementData.order_recommendations.length > 0) ? (
              <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                  <thead>
                    <tr style={{ color: '#64748b', textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>SKU</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Supplier</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>OTIF %</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Recommended PO</th>
                      <th style={{ padding: '8px 0', fontWeight: 600, textAlign: 'right' }}>Est. Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {procurementData.order_recommendations.slice(0, 8).map((po, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #f8fafc' }}>
                        <td style={{ padding: '8px 0', fontWeight: 700, color: '#7c3aed' }}>{po.sku}</td>
                        <td style={{ padding: '8px 0', color: '#0f172a', fontWeight: 500 }}>{po.supplier_name}</td>
                        <td style={{ padding: '8px 0', color: '#10b981', fontWeight: 600 }}>{po.supplier_otif}%</td>
                        <td style={{ padding: '8px 0', color: '#334155', fontWeight: 700 }}>{po.recommended_po_qty} units</td>
                        <td style={{ padding: '8px 0', color: '#0f172a', fontWeight: 700, textAlign: 'right' }}>
                          ${po.estimated_order_cost?.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{
                height: '280px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                backgroundColor: '#f8fafc', borderRadius: '10px', border: '1px dashed #cbd5e1', color: '#64748b', fontSize: '0.82rem'
              }}>
                <ShoppingCart size={24} color="#94a3b8" style={{ marginBottom: '8px' }} />
                <span>0 purchase order recommendations generated.</span>
              </div>
            )
          )}

          {activeEngine === 'assortment' && (
            (assortmentData?.sku_assortment && assortmentData.sku_assortment.length > 0) ? (
              <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                  <thead>
                    <tr style={{ color: '#64748b', textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>SKU</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Product</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Classification</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>GMROI</th>
                      <th style={{ padding: '8px 0', fontWeight: 600, textAlign: 'right' }}>Sell Through %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assortmentData.sku_assortment.slice(0, 8).map((asst, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #f8fafc' }}>
                        <td style={{ padding: '8px 0', fontWeight: 700, color: '#ea580c' }}>{asst.sku}</td>
                        <td style={{ padding: '8px 0', color: '#0f172a', fontWeight: 500 }}>{asst.product_name}</td>
                        <td style={{ padding: '8px 0', color: '#64748b' }}>{asst.classification}</td>
                        <td style={{ padding: '8px 0', color: '#2563eb', fontWeight: 700 }}>{asst.gmroi}</td>
                        <td style={{ padding: '8px 0', color: '#0f172a', fontWeight: 700, textAlign: 'right' }}>{asst.sell_through_pct}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{
                height: '280px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                backgroundColor: '#f8fafc', borderRadius: '10px', border: '1px dashed #cbd5e1', color: '#64748b', fontSize: '0.82rem'
              }}>
                <Layers size={24} color="#94a3b8" style={{ marginBottom: '8px' }} />
                <span>0 retail store space records in database.</span>
              </div>
            )
          )}
        </div>

        {/* Right What-If Levers Control Card */}
        <div className="ui-card" style={{ padding: '22px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '18px' }}>
              <Sliders size={18} color="#2563eb" />
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#0f172a', margin: 0 }}>
                What-If Simulation Levers
              </h3>
            </div>

            {/* Slider 1: Demand Surge */}
            <div style={{ marginBottom: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '6px' }}>
                <span style={{ fontWeight: 600, color: '#334155' }}>Demand Surge Shift</span>
                <span style={{ fontWeight: 700, color: '#2563eb' }}>+{demandShift}%</span>
              </div>
              <input
                type="range"
                min="-30"
                max="50"
                value={demandShift}
                onChange={(e) => setDemandShift(+e.target.value)}
                style={{ width: '100%', accentColor: '#2563eb', cursor: 'pointer' }}
              />
            </div>

            {/* Slider 2: Supplier Lead Time Delay */}
            <div style={{ marginBottom: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '6px' }}>
                <span style={{ fontWeight: 600, color: '#334155' }}>Supplier Lead Time Delay</span>
                <span style={{ fontWeight: 700, color: '#7c3aed' }}>+{leadTimeDelay} Days</span>
              </div>
              <input
                type="range"
                min="0"
                max="14"
                value={leadTimeDelay}
                onChange={(e) => setLeadTimeDelay(+e.target.value)}
                style={{ width: '100%', accentColor: '#7c3aed', cursor: 'pointer' }}
              />
            </div>

            {/* Slider 3: Target Service Level */}
            <div style={{ marginBottom: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '6px' }}>
                <span style={{ fontWeight: 600, color: '#334155' }}>Target Service Level (SL)</span>
                <span style={{ fontWeight: 700, color: '#059669' }}>{serviceLevel}%</span>
              </div>
              <input
                type="range"
                min="80"
                max="99"
                value={serviceLevel}
                onChange={(e) => setServiceLevel(+e.target.value)}
                style={{ width: '100%', accentColor: '#059669', cursor: 'pointer' }}
              />
            </div>
          </div>

          <div style={{
            padding: '14px',
            backgroundColor: '#f8fafc',
            borderRadius: '10px',
            border: '1px solid #e2e8f0',
            fontSize: '0.78rem'
          }}>
            <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '4px' }}>
              Simulated Financial Impact
            </div>
            <div style={{ color: '#64748b' }}>
              {riskData.length > 0 ? (
                <span>Estimated optimization value of <b style={{ color: '#10b981' }}>+$34,200</b> with buffer adjustments.</span>
              ) : (
                <span>Connect catalog data to run multi-echelon scenario models.</span>
              )}
            </div>
          </div>
        </div>
      </div>

    </div>
  );
}
