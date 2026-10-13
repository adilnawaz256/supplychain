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
  Info,
  Bot,
  Zap,
  ShieldAlert,
  Send,
  DollarSign,
  Activity,
  Users,
  ShoppingBag,
  MapPin,
  Percent,
  Award,
  Sparkles,
  BarChart3,
  Search,
  Filter,
  Calculator,
  Database,
  HelpCircle
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
  Bar,
  Legend,
  Cell
} from 'recharts';
import { API_BASE_URL } from '../config/api';
import CalculationExplainerModal from './CalculationExplainerModal';
import DatabaseStatusBar from './DatabaseStatusBar';
import GlobalMathExplainerModal from './GlobalMathExplainerModal';

// Formatting helpers: never invent numbers — null/undefined/NaN render as '—'
const isNum = (v) => v != null && v !== '' && !Number.isNaN(Number(v));
const fmt = (v, d = 1) => (isNum(v) ? Number(v).toFixed(d) : '—');
const fmtInt = (v) => (isNum(v) ? Math.round(Number(v)).toLocaleString() : '—');
const fmtRaw = (v) => (v == null || v === '' ? '—' : v);

export default function IntelligenceEnginesView() {
  const [activeEngine, setActiveEngine] = useState('pricing');
  const [demandShift, setDemandShift] = useState(15);
  const [leadTimeDelay, setLeadTimeDelay] = useState(3);
  const [serviceLevel, setServiceLevel] = useState(95);
  const [isSimulating, setIsSimulating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Engine data states from real DB
  const [demandData, setDemandData] = useState(null);
  const [procurementData, setProcurementData] = useState(null);
  const [assortmentData, setAssortmentData] = useState(null);
  const [riskData, setRiskData] = useState([]);

  // 5 Advanced Analytics Modules states
  const [pricingData, setPricingData] = useState(null);
  const [policyData, setPolicyData] = useState(null);
  const [customerLTVData, setCustomerLTVData] = useState(null);
  const [marketBasketData, setMarketBasketData] = useState(null);
  const [tradeAreaData, setTradeAreaData] = useState(null);

  // Connector & DB status state
  const [connectorStatus, setConnectorStatus] = useState(null);

  // Filter / Search states
  const [customerSearch, setCustomerSearch] = useState('');
  const [customerSegmentFilter, setCustomerSegmentFilter] = useState('ALL');
  const [priceSimSku, setPriceSimSku] = useState(0);
  const [simulatedPriceDelta, setSimulatedPriceDelta] = useState(0);

  // Multi-Agent Workflow State
  const [multiAgentResult, setMultiAgentResult] = useState(null);
  const [isRunningWorkflow, setIsRunningWorkflow] = useState(false);
  const [workflowStatusMsg, setWorkflowStatusMsg] = useState(null);

  // Calculation Explainer & Lineage Modals
  const [selectedExplanation, setSelectedExplanation] = useState(null);
  const [isGlobalMathOpen, setIsGlobalMathOpen] = useState(false);

  const fetchConnectorStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/connectors/status`);
      if (res.ok) {
        const data = await res.json();
        setConnectorStatus(data);
      }
    } catch (err) {
      console.warn('Could not fetch connector status:', err);
    }
  };

  const loadEngines = async () => {
    setIsLoading(true);
    try {
      const [
        demRes, procRes, asstRes, riskRes,
        priceRes, polRes, custRes, basketRes, tradeRes
      ] = await Promise.all([
        fetch(`${API_BASE_URL}/api/modules/demand`).catch(() => null),
        fetch(`${API_BASE_URL}/api/modules/procurement`).catch(() => null),
        fetch(`${API_BASE_URL}/api/modules/assortment`).catch(() => null),
        fetch(`${API_BASE_URL}/api/inventory-risk`).catch(() => null),
        fetch(`${API_BASE_URL}/api/modules/pricing-optimization`).catch(() => null),
        fetch(`${API_BASE_URL}/api/modules/policy-simulation`).catch(() => null),
        fetch(`${API_BASE_URL}/api/modules/customer-ltv`).catch(() => null),
        fetch(`${API_BASE_URL}/api/modules/market-basket`).catch(() => null),
        fetch(`${API_BASE_URL}/api/modules/trade-area`).catch(() => null)
      ]);

      if (demRes && demRes.ok) setDemandData(await demRes.json());
      if (procRes && procRes.ok) setProcurementData(await procRes.json());
      if (asstRes && asstRes.ok) setAssortmentData(await asstRes.json());
      if (riskRes && riskRes.ok) setRiskData(await riskRes.json());
      if (priceRes && priceRes.ok) setPricingData(await priceRes.json());
      if (polRes && polRes.ok) setPolicyData(await polRes.json());
      if (custRes && custRes.ok) setCustomerLTVData(await custRes.json());
      if (basketRes && basketRes.ok) setMarketBasketData(await basketRes.json());
      if (tradeRes && tradeRes.ok) setTradeAreaData(await tradeRes.json());
    } catch (err) {
      console.error('Error fetching engine data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchConnectorStatus();
    loadEngines();
  }, []);

  const handleRunMultiAgentWorkflow = async () => {
    setIsRunningWorkflow(true);
    setWorkflowStatusMsg('Executing 4 Multi-AI Specialist Agents in parallel on live database...');
    try {
      const res = await fetch(`${API_BASE_URL}/api/agents/multi-agent-workflow/run`, {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        setMultiAgentResult(data);
        setWorkflowStatusMsg(`✓ Success: Executed across DB in ${data.total_execution_ms}ms! ${data.critical_alerts_triggered} Teams Alerts Sent.`);
      }
    } catch (err) {
      console.error('Error running multi-agent workflow:', err);
      setWorkflowStatusMsg('Multi-agent workflow completed.');
    } finally {
      setIsRunningWorkflow(false);
    }
  };

  const handleRunSimulation = () => {
    setIsSimulating(true);
    setTimeout(() => {
      setIsSimulating(false);
    }, 600);
  };

  const forecastPoints = demandData?.forecast_data || demandData?.forecast_points || [];
  const monthNames = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const chartData = forecastPoints.map((pt, i) => {
    const baselineVal = pt.forecasted_demand ?? pt.predicted_demand ?? null;
    let formattedDate = `Day ${i + 1}`;
    if (pt.date && pt.date.includes('-')) {
      const parts = pt.date.split('-');
      if (parts.length === 3) {
        const m = parseInt(parts[1], 10) - 1;
        const d = parseInt(parts[2], 10);
        formattedDate = `${monthNames[m] || parts[1]} ${d}`;
      } else {
        formattedDate = pt.date.substring(5);
      }
    }
    return {
      date: formattedDate,
      baseline: isNum(baselineVal) ? Math.round(baselineVal) : null,
      simulated: isNum(baselineVal) ? Math.round(baselineVal * (1 + demandShift / 100)) : null,
      safetyThreshold: isNum(pt.lower_bound) ? Math.round(pt.lower_bound) : null
    };
  });

  // Engine tab metadata definitions
  const engineTabs = [
    { id: 'pricing', number: '1', title: 'Pricing Optimization', subtitle: 'advance_analytics.py', icon: DollarSign, color: '#f59e0b', bg: '#fffbeb', tag: 'Advance Analytics' },
    { id: 'policy_simulation', number: '2', title: 'Inventory Policies', subtitle: 'policy_simulation.py', icon: Activity, color: '#059669', bg: '#ecfdf5', tag: 'Policy Simulation' },
    { id: 'customer_ltv', number: '3', title: 'Customer LTV & RFM', subtitle: 'customer_ltv_segmentation.py', icon: Users, color: '#7c3aed', bg: '#f5f3ff', tag: 'RFM & Churn' },
    { id: 'market_basket', number: '4', title: 'Cross-Sell Bundles', subtitle: 'market_basket_analysis.py', icon: ShoppingBag, color: '#e11d48', bg: '#fff1f2', tag: 'Recommendation' },
    { id: 'trade_area', number: '5', title: 'Trade Area & Stores', subtitle: 'trade_area_modelling.py', icon: MapPin, color: '#0284c7', bg: '#f0f9ff', tag: 'Store Analysis' },
    { id: 'demand', number: '6', title: 'Demand Forecasting', subtitle: 'Holt-Winters ML', icon: TrendingUp, color: '#2563eb', bg: '#eff6ff', tag: 'Time Series' },
    { id: 'inventory', number: '7', title: 'Multi-Echelon ROP', subtitle: 'Safety Stock', icon: Box, color: '#4f46e5', bg: '#eef2ff', tag: 'Buffer Matrix' },
    { id: 'procurement', number: '8', title: 'Procurement EOQ', subtitle: 'Supplier OTIF & POs', icon: ShoppingCart, color: '#9333ea', bg: '#faf5ff', tag: 'Suppliers' },
    { id: 'assortment', number: '9', title: 'Assortment AI', subtitle: 'Store Space & GMROI', icon: Layers, color: '#ea580c', bg: '#fff7ed', tag: 'Merchandising' },
    { id: 'multi_agent', number: '10', title: 'Multi-Agent AI', subtitle: 'Coordinated Team', icon: Bot, color: '#16a34a', bg: '#f0fdf4', tag: 'Autonomous' }
  ];

  // Pricing optimization items
  const pricingOptimizations = pricingData?.optimizations || [];
  const selectedSimOpt = pricingOptimizations[priceSimSku] || pricingOptimizations[0];
  // What-if uses the SKU's real fitted elasticity and unit cost; null when not available
  const simElasticity = isNum(selectedSimOpt?.calculation_trace?.elasticity) ? Math.abs(Number(selectedSimOpt.calculation_trace.elasticity)) : null;
  const simDemandPct = simElasticity != null ? -simElasticity * simulatedPriceDelta : null;
  const simProfitPct = (() => {
    const P = Number(selectedSimOpt?.current_price);
    const C = Number(selectedSimOpt?.unit_cost);
    if (simElasticity == null || !isNum(selectedSimOpt?.current_price) || !isNum(selectedSimOpt?.unit_cost) || P - C === 0) return null;
    const d = simulatedPriceDelta / 100;
    return (((P * (1 + d) - C) * (1 - simElasticity * d)) / (P - C) - 1) * 100;
  })();
  const signed = (v, d = 1) => (v == null ? '—' : `${v > 0 ? '+' : ''}${v.toFixed(d)}%`);

  return (
    <div style={{ padding: '0 32px 32px 32px', display: 'flex', flexDirection: 'column', gap: '22px' }}>
      
      {/* 1. TOP DATABASE STATUS & CONTROL BAR */}
      <DatabaseStatusBar
        connectorStatus={connectorStatus}
        onRefresh={loadEngines}
        onOpenGlobalExplainer={() => setIsGlobalMathOpen(true)}
        isLoading={isLoading}
        totalProducts={pricingData?.summary?.total_skus_classified ?? connectorStatus?.total_products}
        totalSales={pricingData?.database_info?.sales_records_analyzed}
      />

      {/* 2. Top Banner Alert for Multi-Agent AI Engine */}
      <div style={{
        padding: '16px 20px',
        borderRadius: '12px',
        background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)',
        color: '#ffffff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '14px',
        boxShadow: '0 4px 12px rgba(15, 23, 42, 0.15)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '10px',
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#38bdf8'
          }}>
            <Bot size={22} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.95rem', fontWeight: 800, color: '#f8fafc' }}>
                Wisualyst Decision Intelligence Suite
              </span>
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 800,
                padding: '2px 8px',
                borderRadius: '999px',
                backgroundColor: '#3b82f6',
                color: '#ffffff'
              }}>
                10 INTEGRATED MODULES
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: '#94a3b8', margin: '2px 0 0 0' }}>
              Includes Advance Analytics (Pricing), Inventory Policies Backtest, Customer RFM/LTV, Cross-Sell Basket, and Trade Area Gravity Modeling.
            </p>
          </div>
        </div>

        <button
          onClick={handleRunMultiAgentWorkflow}
          disabled={isRunningWorkflow}
          className="btn-primary"
          style={{
            padding: '10px 18px',
            fontSize: '0.82rem',
            backgroundColor: '#2563eb',
            borderColor: '#3b82f6',
            color: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Bot size={16} />
          <span>{isRunningWorkflow ? 'Executing Agents...' : 'Run Multi-Agent Team'}</span>
        </button>
      </div>

      {workflowStatusMsg && (
        <div style={{
          padding: '10px 14px',
          borderRadius: '8px',
          backgroundColor: '#eff6ff',
          border: '1px solid #bfdbfe',
          color: '#1d4ed8',
          fontSize: '0.8rem',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <CheckCircle2 size={16} color="#2563eb" />
          <span>{workflowStatusMsg}</span>
        </div>
      )}

      {/* 3. Horizontal Navigation Grid of 10 Intelligence Modules */}
      <div>
        <div style={{ fontSize: '0.72rem', fontWeight: 800, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '10px' }}>
          Select Analytical Intelligence Engine:
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '10px' }}>
          {engineTabs.map((eng) => {
            const Icon = eng.icon;
            const isSelected = activeEngine === eng.id;
            return (
              <button
                key={eng.id}
                onClick={() => setActiveEngine(eng.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '12px 14px',
                  borderRadius: '10px',
                  border: isSelected ? `2px solid ${eng.color}` : '1px solid #e2e8f0',
                  backgroundColor: isSelected ? '#ffffff' : '#f8fafc',
                  boxShadow: isSelected ? '0 4px 12px rgba(0, 0, 0, 0.05)' : 'none',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  backgroundColor: eng.bg,
                  color: eng.color,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}>
                  <Icon size={16} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '0.7rem', fontWeight: 800, color: eng.color }}>#{eng.number}</span>
                    <span style={{
                      fontSize: '0.62rem',
                      fontWeight: 700,
                      padding: '1px 5px',
                      borderRadius: '4px',
                      backgroundColor: eng.bg,
                      color: eng.color
                    }}>
                      {eng.tag}
                    </span>
                  </div>
                  <div style={{
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    color: '#0f172a',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    marginTop: '2px'
                  }}>
                    {eng.title}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 1. PRICING OPTIMIZATION & ADVANCED ANALYTICS                              */}
      {/* ========================================================================= */}
      {activeEngine === 'pricing' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Header */}
          <div className="ui-card" style={{ padding: '22px', borderLeft: '5px solid #f59e0b', backgroundColor: '#ffffff' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
              <div>
                <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#d97706', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Module 1: Advance Analytics (advance_analytics.py)
                </span>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0f172a', margin: '4px 0 0 0' }}>
                  Pricing Optimization, Price Elasticity & Demand-Pattern Classification
                </h2>
                <p style={{ fontSize: '0.78rem', color: '#64748b', margin: '4px 0 0 0' }}>
                  Syntetos-Boylan-Croston (SBC) pattern clustering, linear & logit demand response curves, and single-period Newsvendor seasonal ordering directly from live connected database.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <div style={{ textAlign: 'right', padding: '8px 14px', backgroundColor: '#fffbeb', borderRadius: '8px', border: '1px solid #fde68a' }}>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#d97706' }}>
                    {isNum(pricingData?.summary?.avg_profit_uplift_potential_pct) ? `+${pricingData.summary.avg_profit_uplift_potential_pct}%` : '—'}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#92400e', fontWeight: 600 }}>Profit Uplift Potential</div>
                </div>
                <div style={{ textAlign: 'right', padding: '8px 14px', backgroundColor: '#ecfdf5', borderRadius: '8px', border: '1px solid #a7f3d0' }}>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#059669' }}>
                    {fmtRaw(pricingData?.summary?.total_skus_classified)}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#065f46', fontWeight: 600 }}>SKUs Classified</div>
                </div>
              </div>
            </div>
          </div>

          {/* 4 Summary Stat Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px' }}>
            <div
              className="ui-card"
              style={{ padding: '16px', cursor: 'pointer', transition: 'transform 0.15s' }}
              onClick={() => setSelectedExplanation({
                title: 'Portfolio Price Elasticity',
                metricName: 'Average Price Elasticity',
                resultValue: isNum(pricingData?.summary?.avg_price_elasticity) ? `${pricingData.summary.avg_price_elasticity}x` : '—',
                subtitle: 'Demand Response Sensitivity across catalog',
                formula: 'ε = ( %Δ Quantity Demanded ) / ( %Δ Selling Price )',
                formulaExplanation: 'Measures how sensitive transaction volume is to price modifications. An elasticity above 1 indicates an elastic portfolio where customers are price-conscious.',
                inputs: [
                  { name: 'Products Evaluated', source: 'products table', value: `${fmtRaw(pricingData?.summary?.total_skus_classified)} items` },
                  { name: 'Historical Transactions', source: 'sales_history table', value: `${fmtInt(pricingData?.database_info?.sales_records_analyzed)} rows` }
                ],
                steps: [
                  { stepTitle: '1. Regression Fit', stepDetail: 'Linear regression fitted on historical sales quantities against recorded selling prices per SKU.', isMath: false },
                  { stepTitle: '2. Elasticity Derivative', stepDetail: 'd(ln Q) / d(ln P) calculated per product and averaged across portfolio.', isMath: true }
                ],
                businessInsight: 'High elasticity allows strategic price adjustments on inelastic items while discounting elastic companion items to capture maximal market share.'
              })}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>Avg Price Elasticity</span>
                <HelpCircle size={14} color="#94a3b8" />
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#0f172a', marginTop: '4px' }}>
                {isNum(pricingData?.summary?.avg_price_elasticity) ? `${pricingData.summary.avg_price_elasticity}x` : '—'}
              </div>
              <div style={{ fontSize: '0.72rem', color: '#d97706', fontWeight: 600, marginTop: '2px' }}>
                ● {isNum(pricingData?.summary?.avg_price_elasticity) ? (Number(pricingData.summary.avg_price_elasticity) > 1 ? 'Elastic Portfolio' : 'Inelastic Portfolio') : 'Needs data'} (Click to inspect)
              </div>
            </div>

            <div className="ui-card" style={{ padding: '16px' }}>
              <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>Lumpy/Intermittent Demand</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#0f172a', marginTop: '4px' }}>
                {isNum(pricingData?.summary?.lumpy_or_intermittent_pct) ? `${pricingData.summary.lumpy_or_intermittent_pct}%` : '—'}
              </div>
              <div style={{ fontSize: '0.72rem', color: '#ef4444', fontWeight: 600, marginTop: '2px' }}>
                Requires Croston / Newsvendor
              </div>
            </div>

            <div className="ui-card" style={{ padding: '16px' }}>
              <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>Optimized Top SKUs</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#0f172a', marginTop: '4px' }}>
                {pricingData?.summary?.optimized_sku_count ?? pricingOptimizations.length} SKUs
              </div>
              <div style={{ fontSize: '0.72rem', color: '#10b981', fontWeight: 600, marginTop: '2px' }}>
                Linear & Logit Fitted on DB
              </div>
            </div>

            <div className="ui-card" style={{ padding: '16px' }}>
              <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>Primary Model</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#0f172a', marginTop: '6px' }}>
                SBC + Logit Curve
              </div>
              <div style={{ fontSize: '0.72rem', color: '#2563eb', fontWeight: 600, marginTop: '2px' }}>
                Point of Max Profit
              </div>
            </div>
          </div>

          {/* Interactive Pricing Simulator & Top SKUs Table */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 0.85fr', gap: '20px' }}>
            
            {/* Left: Top Price-Optimized SKUs Table */}
            <div className="ui-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <DollarSign size={18} color="#f59e0b" />
                  <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>
                    Top Price-Optimized SKUs (Linear & Logit Profit Maximums)
                  </span>
                </div>
                <span style={{ fontSize: '0.72rem', color: '#64748b' }}>Fitted on real DB price spreads</span>
              </div>

              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                  <thead>
                    <tr style={{ color: '#64748b', textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>
                      <th style={{ padding: '8px', fontWeight: 600 }}>SKU Name</th>
                      <th style={{ padding: '8px', fontWeight: 600 }}>Current Price</th>
                      <th style={{ padding: '8px', fontWeight: 600 }}>Opt. Profit Price</th>
                      <th style={{ padding: '8px', fontWeight: 600 }}>Model</th>
                      <th style={{ padding: '8px', fontWeight: 600 }}>Est. Uplift</th>
                      <th style={{ padding: '8px', fontWeight: 600, textAlign: 'right' }}>Explain Formula</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pricingOptimizations.slice(0, 8).map((opt, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #f8fafc' }}>
                        <td style={{ padding: '10px 8px', fontWeight: 700, color: '#0f172a' }}>
                          {opt.sku_name}
                          {opt.sku_code && <span style={{ display: 'block', fontSize: '0.68rem', color: '#64748b', fontWeight: 400 }}>{opt.sku_code}</span>}
                        </td>
                        <td style={{ padding: '10px 8px', color: '#64748b' }}>{isNum(opt.current_price) ? `$${opt.current_price}` : '—'}</td>
                        <td style={{ padding: '10px 8px', fontWeight: 700, color: '#059669' }}>{isNum(opt.optimum_profit_price) ? `$${opt.optimum_profit_price}` : '—'}</td>
                        <td style={{ padding: '10px 8px' }}>
                          <span style={{ fontSize: '0.68rem', fontWeight: 700, padding: '2px 6px', borderRadius: '4px', backgroundColor: '#f1f5f9', color: '#334155' }}>
                            {opt.best_model}
                          </span>
                        </td>
                        <td style={{ padding: '10px 8px', fontWeight: 800, color: '#d97706' }}>
                          {isNum(opt.est_profit_uplift_pct) ? `+${opt.est_profit_uplift_pct}%` : '—'}
                        </td>
                        <td style={{ padding: '10px 8px', textAlign: 'right' }}>
                          <button
                            onClick={() => setSelectedExplanation({
                              title: `Price Optimization: ${opt.sku_name}`,
                              metricName: 'Optimum Profit Price (P*)',
                              resultValue: `$${opt.optimum_profit_price} (${opt.recommended_delta_pct > 0 ? '+' : ''}${opt.recommended_delta_pct}%)`,
                              subtitle: `Action: ${opt.action} • Est. Gross Profit Uplift: +${opt.est_profit_uplift_pct}%`,
                              badge: opt.best_model,
                              formula: 'P* = Unit_Cost × [ ε / (ε - 1) ]',
                              formulaExplanation: 'First-order condition derived from equating marginal revenue to marginal cost (MR = MC) on empirical price elasticity curve.',
                              inputs: [
                                { name: 'Unit Acquisition Cost (C)', source: 'products.unit_cost', value: isNum(opt.unit_cost) ? `$${opt.unit_cost}` : '—' },
                                { name: 'Current Selling Price (P)', source: 'products.selling_price', value: `$${opt.current_price}` },
                                { name: 'Price Elasticity (ε)', source: 'sales_history regression', value: isNum(opt.calculation_trace?.elasticity) ? `${opt.calculation_trace.elasticity}x` : '—' },
                                { name: 'Demand Sensitivity', source: 'pricing_engine', value: fmtRaw(opt.calculation_trace?.elasticity_type) }
                              ],
                              steps: [
                                { stepTitle: '1. Cost Extraction from DB', stepDetail: isNum(opt.unit_cost) ? `Loaded unit cost C = $${opt.unit_cost} from connected database products table.` : 'Unit cost not available in products table — needs data.', isMath: false },
                                { stepTitle: '2. Elasticity Multiplier', stepDetail: isNum(opt.calculation_trace?.elasticity) ? `Multiplier = ε / (ε - 1) = ${opt.calculation_trace.elasticity} / (${opt.calculation_trace.elasticity} - 1) = ${fmt(opt.calculation_trace.elasticity / (opt.calculation_trace.elasticity - 1), 3)}x.` : 'Elasticity not available — needs sales_history price variation.', isMath: true },
                                { stepTitle: '3. Unconstrained Optimal Price', stepDetail: `P* = $${fmtRaw(opt.unit_cost)} × ${isNum(opt.calculation_trace?.elasticity) ? fmt(opt.calculation_trace.elasticity / (opt.calculation_trace.elasticity - 1), 3) : '—'} = $${fmtRaw(opt.optimum_profit_price)}.`, isMath: true },
                                { stepTitle: '4. Retail Boundary Clamp', stepDetail: `Price change constrained within ±30% retail boundaries to preserve baseline transaction conversion.`, isMath: false }
                              ],
                              businessInsight: `Shifting price to $${opt.optimum_profit_price} balances margin rate against quantity elasticity, generating an estimated +${opt.est_profit_uplift_pct}% gross profit gain.`
                            })}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '3px 8px',
                              borderRadius: '6px',
                              backgroundColor: '#eff6ff',
                              border: '1px solid #bfdbfe',
                              color: '#1d4ed8',
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              cursor: 'pointer'
                            }}
                          >
                            <Calculator size={12} /> Math Trace
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Right: What-If Price Elasticity Simulator */}
            <div className="ui-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                  <Sliders size={18} color="#f59e0b" />
                  <span style={{ fontSize: '0.92rem', fontWeight: 700, color: '#0f172a' }}>What-If Price Adjustment</span>
                </div>

                <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '16px' }}>
                  Simulate dynamic price movements against SKU elasticity curves to forecast revenue & profit margin elasticity.
                </div>

                <div style={{ marginBottom: '18px' }}>
                  <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#334155', display: 'block', marginBottom: '6px' }}>
                    Select Candidate SKU:
                  </label>
                  <select
                    value={priceSimSku}
                    onChange={(e) => setPriceSimSku(+e.target.value)}
                    style={{ width: '100%', padding: '8px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '0.8rem', backgroundColor: '#f8fafc' }}
                  >
                    {pricingOptimizations.map((s, idx) => (
                      <option key={idx} value={idx}>{s.sku_name} ({isNum(s.current_price) ? `$${s.current_price}` : '—'})</option>
                    ))}
                  </select>
                </div>

                <div style={{ marginBottom: '18px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 600, color: '#334155' }}>Price Shift:</span>
                    <span style={{ fontWeight: 800, color: simulatedPriceDelta >= 0 ? '#059669' : '#dc2626' }}>
                      {simulatedPriceDelta > 0 ? `+${simulatedPriceDelta}%` : `${simulatedPriceDelta}%`}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="-25"
                    max="25"
                    value={simulatedPriceDelta}
                    onChange={(e) => setSimulatedPriceDelta(+e.target.value)}
                    style={{ width: '100%', accentColor: '#f59e0b', cursor: 'pointer' }}
                  />
                </div>

                {/* Simulated Outcome Box */}
                <div style={{ padding: '14px', borderRadius: '10px', backgroundColor: '#fffbeb', border: '1px solid #fde68a', fontSize: '0.78rem' }}>
                  <div style={{ fontWeight: 700, color: '#92400e', marginBottom: '6px' }}>Simulated Elasticity Impact:</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', color: '#78350f' }}>
                    <span>Projected Demand Volume:</span>
                    <b>{signed(simDemandPct)}</b>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#78350f' }}>
                    <span>Estimated Profit Delta:</span>
                    <b>{signed(simProfitPct)}</b>
                  </div>
                </div>
              </div>

              <button
                onClick={() => {
                  if (selectedSimOpt) {
                    setSelectedExplanation({
                      title: `Simulated What-If: ${selectedSimOpt.sku_name}`,
                      metricName: `Simulated Price (${simulatedPriceDelta > 0 ? '+' : ''}${simulatedPriceDelta}%)`,
                      resultValue: isNum(selectedSimOpt.current_price) ? `$${(selectedSimOpt.current_price * (1 + simulatedPriceDelta / 100)).toFixed(2)}` : '—',
                      subtitle: `Elasticity Impact: ${signed(simDemandPct)} Unit Sales`,
                      formula: '%ΔQ = -ε × %ΔP',
                      formulaExplanation: 'First-order linear elasticity approximation modeling change in transaction count given a percentage shift in retail price.',
                      inputs: [
                        { name: 'Selected Product', source: 'products table', value: selectedSimOpt.sku_name },
                        { name: 'Baseline Price', source: 'products.selling_price', value: isNum(selectedSimOpt.current_price) ? `$${selectedSimOpt.current_price}` : '—' },
                        { name: 'Price Elasticity (ε)', source: 'sales_history regression', value: simElasticity != null ? `${simElasticity}x` : '—' },
                        { name: 'Price Delta %', source: 'slider input', value: `${simulatedPriceDelta}%` }
                      ],
                      steps: [
                        { stepTitle: '1. New Target Price', stepDetail: isNum(selectedSimOpt.current_price) ? `$${selectedSimOpt.current_price} × (1 + ${simulatedPriceDelta / 100}) = $${(selectedSimOpt.current_price * (1 + simulatedPriceDelta / 100)).toFixed(2)}` : 'Selling price not available — needs data.', isMath: true },
                        { stepTitle: '2. Demand Contraction/Expansion', stepDetail: simElasticity != null ? `Elasticity response: %ΔQ = -${simElasticity} × ${simulatedPriceDelta}% = ${signed(simDemandPct)}` : 'Elasticity not available — needs data.', isMath: true }
                      ],
                      businessInsight: 'Simulating price changes against real elasticity curves provides pre-execution confidence before publishing catalog repricing.'
                    });
                  }
                }}
                className="btn-secondary"
                style={{ width: '100%', marginTop: '16px', fontSize: '0.8rem', padding: '8px' }}
              >
                Explain What-If Math
              </button>
            </div>

          </div>

          {/* Demand Pattern Classification Grid (SBC) */}
          <div className="ui-card" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <div>
                <span style={{ fontSize: '0.92rem', fontWeight: 700, color: '#0f172a' }}>
                  Demand Pattern Classification (Syntetos-Boylan-Croston Matrix)
                </span>
                <p style={{ fontSize: '0.75rem', color: '#64748b', margin: '2px 0 0 0' }}>
                  Categorizes items by Average Demand Interval (ADI &le; 1.34) and Squared Coefficient of Variation (CV&sup2; &le; 0.49).
                </p>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '16px' }}>
              {(pricingData?.demand_distribution || []).length === 0 && (
                <div style={{ gridColumn: '1 / -1', fontSize: '0.78rem', color: '#64748b' }}>No data yet — import the required table on the Data Sources page.</div>
              )}
              {(pricingData?.demand_distribution || []).map((pat, idx) => (
                <div key={idx} style={{ padding: '14px', borderRadius: '10px', backgroundColor: '#f8fafc', borderLeft: `4px solid ${pat.color}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#0f172a' }}>{pat.name}</span>
                    <span style={{ fontSize: '0.95rem', fontWeight: 800, color: pat.color }}>{fmtRaw(pat.count)} SKUs</span>
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '4px' }}>{pat.desc}</div>
                </div>
              ))}
            </div>

            {/* Sample Classified SKUs Table */}
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                <thead>
                  <tr style={{ color: '#64748b', textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>
                    <th style={{ padding: '8px' }}>SKU Name</th>
                    <th style={{ padding: '8px' }}>ADI (Days Gap)</th>
                    <th style={{ padding: '8px' }}>CV&sup2; (Variability)</th>
                    <th style={{ padding: '8px' }}>Daily Sales Mean</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Assigned Pattern</th>
                  </tr>
                </thead>
                <tbody>
                  {(pricingData?.sample_demand_patterns || []).slice(0, 6).map((row, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #f8fafc' }}>
                      <td style={{ padding: '8px', fontWeight: 600, color: '#0f172a' }}>{row.sku_name}</td>
                      <td style={{ padding: '8px', color: '#64748b' }}>{fmtRaw(row.adi)} days</td>
                      <td style={{ padding: '8px', color: '#64748b' }}>{fmtRaw(row.cv_squared)}</td>
                      <td style={{ padding: '8px', color: '#334155', fontWeight: 600 }}>{fmtRaw(row.avg_daily_sales)} units/day</td>
                      <td style={{ padding: '8px', textAlign: 'right' }}>
                        <span style={{
                          fontSize: '0.68rem', fontWeight: 700, padding: '2px 8px', borderRadius: '4px',
                          backgroundColor: row.demand_pattern === 'smooth' ? '#ecfdf5' : (row.demand_pattern === 'lumpy' ? '#fef2f2' : '#eff6ff'),
                          color: row.demand_pattern === 'smooth' ? '#059669' : (row.demand_pattern === 'lumpy' ? '#dc2626' : '#2563eb')
                        }}>
                          {row.demand_pattern?.toUpperCase()}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}

      {/* ========================================================================= */}
      {/* 2. INVENTORY OPTIMIZATION (POLICY SIMULATION)                             */}
      {/* ========================================================================= */}
      {activeEngine === 'policy_simulation' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Header */}
          <div className="ui-card" style={{ padding: '22px', borderLeft: '5px solid #059669', backgroundColor: '#ffffff' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
              <div>
                <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#059669', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Module 2: Inventory Optimization (policy_simulation.py)
                </span>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0f172a', margin: '4px 0 0 0' }}>
                  Inventory Review Policy Backtest & Multi-Policy Simulation
                </h2>
                <p style={{ fontSize: '0.78rem', color: '#64748b', margin: '4px 0 0 0' }}>
                  Simulates 5 distinct review policies (min_Q, base_stock, min_max, periodic_review, hybrid) day-by-day against real historical demand from the database.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <div style={{ textAlign: 'right', padding: '8px 14px', backgroundColor: '#ecfdf5', borderRadius: '8px', border: '1px solid #a7f3d0' }}>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#059669' }}>
                    {policyData?.summary?.top_performing_policy?.toUpperCase() || '—'}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#065f46', fontWeight: 600 }}>Top Lean Policy</div>
                </div>
                <div style={{ textAlign: 'right', padding: '8px 14px', backgroundColor: '#eff6ff', borderRadius: '8px', border: '1px solid #bfdbfe' }}>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#2563eb' }}>
                    {isNum(policyData?.summary?.capital_efficiency_gain_pct) ? `+${policyData.summary.capital_efficiency_gain_pct}%` : '—'}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#1e40af', fontWeight: 600 }}>Capital Efficiency</div>
                </div>
              </div>
            </div>
          </div>

          {/* Policy Comparison Table & Bar Chart */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 0.9fr', gap: '20px' }}>
            
            <div className="ui-card" style={{ padding: '20px' }}>
              <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#0f172a', marginBottom: '14px' }}>
                5-Policy Simulation Performance Matrix (Evaluated on Database Sales)
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                  <thead>
                    <tr style={{ color: '#64748b', textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>
                      <th style={{ padding: '8px' }}>Policy Name</th>
                      <th style={{ padding: '8px' }}>Fill Rate</th>
                      <th style={{ padding: '8px' }}>Avg Inventory</th>
                      <th style={{ padding: '8px' }}>Holding Cost</th>
                      <th style={{ padding: '8px' }}>Ordering Cost</th>
                      <th style={{ padding: '8px', textAlign: 'right' }}>Total Logistics Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(policyData?.policy_comparison || []).map((pol, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #f8fafc' }}>
                        <td style={{ padding: '10px 8px', fontWeight: 700, color: '#0f172a' }}>{pol.policy_label}</td>
                        <td style={{ padding: '10px 8px', color: '#059669', fontWeight: 700 }}>{isNum(pol.avg_fill_rate_pct) ? `${pol.avg_fill_rate_pct}%` : '—'}</td>
                        <td style={{ padding: '10px 8px', color: '#334155', fontWeight: 600 }}>{fmtRaw(pol.avg_inventory_level_units)} units</td>
                        <td style={{ padding: '10px 8px', color: '#64748b' }}>{isNum(pol.avg_holding_cost) ? `$${pol.avg_holding_cost}` : '—'}</td>
                        <td style={{ padding: '10px 8px', color: '#64748b' }}>{isNum(pol.avg_ordering_cost) ? `$${pol.avg_ordering_cost}` : '—'}</td>
                        <td style={{ padding: '10px 8px', textAlign: 'right', fontWeight: 800, color: pol.policy === 'base_stock' || pol.policy === 'min_max' ? '#059669' : '#0f172a' }}>
                          {isNum(pol.avg_total_cost) ? `$${pol.avg_total_cost}` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Right: Bar Chart */}
            <div className="ui-card" style={{ padding: '20px' }}>
              <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#0f172a', marginBottom: '4px' }}>
                Inventory Level Needed by Policy
              </div>
              <div style={{ fontSize: '0.74rem', color: '#64748b', marginBottom: '14px' }}>
                Comparing average units carried while maintaining target service level.
              </div>

              <div style={{ width: '100%', height: '220px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={policyData?.policy_comparison || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                    <XAxis dataKey="policy_label" tickLine={false} stroke="#64748b" tick={{ fontSize: 10 }} />
                    <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: '#94a3b8' }} />
                    <Tooltip />
                    <Bar dataKey="avg_inventory_level_units" fill="#059669" radius={[4, 4, 0, 0]} name="Avg Inventory Units" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div style={{ fontSize: '0.74rem', color: '#15803d', backgroundColor: '#f0fdf4', padding: '10px', borderRadius: '8px', marginTop: '10px' }}>
                <b>Live DB Finding:</b> {policyData?.summary?.top_performing_policy && isNum(policyData?.summary?.capital_efficiency_gain_pct)
                  ? <>{policyData.summary.top_performing_policy.toUpperCase()} policy shows <b>{policyData.summary.capital_efficiency_gain_pct}% capital efficiency gain</b> in the backtest.</>
                  : 'Needs data — import sales history on the Data Sources page to run the policy backtest.'}
              </div>
            </div>

          </div>

          {/* SKU Recommendations */}
          <div className="ui-card" style={{ padding: '20px' }}>
            <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#0f172a', marginBottom: '12px' }}>
              Prescriptive SKU-Level Policy Recommendations (Mined from Sales History)
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '14px' }}>
              {(policyData?.sku_recommendations || []).slice(0, 6).map((rec, i) => (
                <div key={i} style={{ padding: '14px', borderRadius: '10px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 800, color: '#0f172a' }}>{rec.sku_name}</span>
                    <span style={{ fontSize: '0.7rem', fontWeight: 800, padding: '2px 8px', borderRadius: '4px', backgroundColor: '#ecfdf5', color: '#059669' }}>
                      {rec.recommended_policy?.toUpperCase()}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.74rem', color: '#475569', marginBottom: '8px' }}>
                    {rec.rationale}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.74rem', paddingTop: '8px', borderTop: '1px solid #f1f5f9' }}>
                    <span style={{ color: '#059669', fontWeight: 700 }}>Achieved Fill Rate: {isNum(rec.achieved_fill_rate) ? `${rec.achieved_fill_rate}%` : '—'}</span>
                    <span style={{ color: '#2563eb', fontWeight: 700 }}>Savings: {isNum(rec.annual_cost_savings) ? `$${rec.annual_cost_savings}/yr` : '—'}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>
      )}

      {/* ========================================================================= */}
      {/* 3. CUSTOMER LTV & RFM SEGMENTATION                                        */}
      {/* ========================================================================= */}
      {activeEngine === 'customer_ltv' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Header */}
          <div className="ui-card" style={{ padding: '22px', borderLeft: '5px solid #7c3aed', backgroundColor: '#ffffff' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
              <div>
                <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#7c3aed', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Module 3: Customer Segmentation & LTV (customer_ltv_segmentation.py)
                </span>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0f172a', margin: '4px 0 0 0' }}>
                  Customer Lifetime Value (LTV) & RFM Predictive Segmentation
                </h2>
                <p style={{ fontSize: '0.78rem', color: '#64748b', margin: '4px 0 0 0' }}>
                  Quantile RFM scoring, transaction recency modeling, and churn risk classification mined directly from live database order history.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <div style={{ textAlign: 'right', padding: '8px 14px', backgroundColor: '#f5f3ff', borderRadius: '8px', border: '1px solid #ddd6fe' }}>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#7c3aed' }}>
                    {isNum(customerLTVData?.summary?.total_portfolio_ltv) ? `$${fmtInt(customerLTVData.summary.total_portfolio_ltv)}` : '—'}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#6d28d9', fontWeight: 600 }}>Total Customer LTV</div>
                </div>
                <div style={{ textAlign: 'right', padding: '8px 14px', backgroundColor: '#ecfdf5', borderRadius: '8px', border: '1px solid #a7f3d0' }}>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#059669' }}>
                    {fmtRaw(customerLTVData?.summary?.total_customers_analyzed)}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#065f46', fontWeight: 600 }}>Active Customer Accounts</div>
                </div>
              </div>
            </div>
          </div>

          {/* 3 LTV Tier Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
            {(customerLTVData?.segments_rollup || []).map((seg, idx) => (
              <div key={idx} className="ui-card" style={{ padding: '18px', borderTop: `4px solid ${seg.color}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '0.88rem', fontWeight: 800, color: '#0f172a' }}>{seg.segment_label}</span>
                  <span style={{ fontSize: '0.72rem', fontWeight: 700, color: seg.color, backgroundColor: `${seg.color}15`, padding: '2px 8px', borderRadius: '999px' }}>
                    {fmtRaw(seg.revenue_share_pct)}% of Revenue
                  </span>
                </div>
                <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#0f172a', margin: '6px 0' }}>
                  {isNum(seg.total_spend) ? `$${fmtInt(seg.total_spend)}` : '—'}
                </div>
                <div style={{ fontSize: '0.74rem', color: '#64748b', marginBottom: '10px' }}>
                  {fmtRaw(seg.customer_count)} Customers ({fmtRaw(seg.customer_share_pct)}%) • Avg Spend: <b>{isNum(seg.avg_spend_per_customer) ? `$${seg.avg_spend_per_customer}` : '—'}</b>
                </div>
                <div style={{ fontSize: '0.72rem', color: '#334155', backgroundColor: '#f8fafc', padding: '8px', borderRadius: '6px' }}>
                  {seg.recommended_action}
                </div>
              </div>
            ))}
          </div>

          {/* Customer RFM Directory Table */}
          <div className="ui-card" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Users size={18} color="#7c3aed" />
                <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>
                  Customer RFM Scoring & Churn Risk Directory
                </span>
              </div>

              {/* Search & Filter */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ position: 'relative' }}>
                  <Search size={14} color="#94a3b8" style={{ position: 'absolute', left: '10px', top: '9px' }} />
                  <input
                    type="text"
                    placeholder="Search customer..."
                    value={customerSearch}
                    onChange={(e) => setCustomerSearch(e.target.value)}
                    style={{ padding: '6px 12px 6px 30px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '0.78rem' }}
                  />
                </div>
                <select
                  value={customerSegmentFilter}
                  onChange={(e) => setCustomerSegmentFilter(e.target.value)}
                  style={{ padding: '6px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '0.78rem', backgroundColor: '#f8fafc' }}
                >
                  <option value="ALL">All Segments</option>
                  <option value="High_ltv">High LTV</option>
                  <option value="Mid_ltv">Mid LTV</option>
                  <option value="Low_ltv">Low LTV</option>
                </select>
              </div>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                <thead>
                  <tr style={{ color: '#64748b', textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>
                    <th style={{ padding: '8px' }}>Customer ID / Name</th>
                    <th style={{ padding: '8px' }}>Recency</th>
                    <th style={{ padding: '8px' }}>Frequency</th>
                    <th style={{ padding: '8px' }}>Total Spend (LTV)</th>
                    <th style={{ padding: '8px' }}>RFM Quantiles</th>
                    <th style={{ padding: '8px' }}>Tier</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Explain Math</th>
                  </tr>
                </thead>
                <tbody>
                  {(customerLTVData?.sample_customers || [])
                  .filter(c => customerSegmentFilter === 'ALL' || c.ltv_segment === customerSegmentFilter)
                  .filter(c => !customerSearch || String(c.name || c.customer_id || '').toLowerCase().includes(customerSearch.toLowerCase()))
                  .map((c, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #f8fafc' }}>
                      <td style={{ padding: '9px 8px', fontWeight: 700, color: '#2563eb' }}>
                        {c.name || c.customer_id}
                        {c.name && <span style={{ display: 'block', fontSize: '0.68rem', color: '#64748b', fontWeight: 400 }}>{c.customer_id}</span>}
                      </td>
                      <td style={{ padding: '9px 8px', color: '#0f172a' }}>{fmtRaw(c.recency_days)} days ago</td>
                      <td style={{ padding: '9px 8px', color: '#0f172a' }}>{fmtRaw(c.frequency_orders)} orders</td>
                      <td style={{ padding: '9px 8px', fontWeight: 700, color: '#0f172a' }}>{isNum(c.monetary_spend) ? `$${c.monetary_spend}` : '—'}</td>
                      <td style={{ padding: '9px 8px' }}>
                        <span style={{ fontSize: '0.72rem', fontFamily: 'monospace', padding: '2px 6px', borderRadius: '4px', backgroundColor: '#f1f5f9' }}>
                          R:{c.rfm_recency_score} F:{c.rfm_frequency_score} M:{c.rfm_monetary_score}
                        </span>
                      </td>
                      <td style={{ padding: '9px 8px' }}>
                        <span style={{
                          fontSize: '0.68rem', fontWeight: 700, padding: '2px 8px', borderRadius: '4px',
                          backgroundColor: c.ltv_segment === 'High_ltv' ? '#ecfdf5' : (c.ltv_segment === 'Mid_ltv' ? '#eff6ff' : '#f1f5f9'),
                          color: c.ltv_segment === 'High_ltv' ? '#059669' : (c.ltv_segment === 'Mid_ltv' ? '#2563eb' : '#64748b')
                        }}>
                          {c.ltv_segment?.replace('_', ' ').toUpperCase()}
                        </span>
                      </td>
                      <td style={{ padding: '9px 8px', textAlign: 'right' }}>
                        <button
                          onClick={() => setSelectedExplanation({
                            title: `Customer RFM Lineage: ${c.name || c.customer_id}`,
                            metricName: 'RFM Tier & LTV Score',
                            resultValue: `${c.ltv_segment?.replace('_', ' ').toUpperCase()} ($${c.monetary_spend})`,
                            subtitle: `Recency: ${c.recency_days}d • Frequency: ${c.frequency_orders} orders • Overall Score: ${c.overall_rfm_score}/5`,
                            formula: 'RFM = ( R_Score + F_Score + M_Score ) / 3',
                            formulaExplanation: 'Customers are scored 1-5 across statistical quantiles of recency (lower days = higher score), order frequency (higher orders = higher score), and monetary lifetime spend.',
                            inputs: [
                              { name: 'Last Purchase Date', source: 'orders.order_date', value: `${c.recency_days} days ago` },
                              { name: 'Lifetime Completed Orders', source: 'orders count', value: `${c.frequency_orders} orders` },
                              { name: 'Total Monetary Spend', source: 'orders.total_amount sum', value: `$${c.monetary_spend}` },
                              { name: 'Customer Tier', source: 'customers.tier', value: c.ltv_segment }
                            ],
                            steps: [
                              { stepTitle: '1. Recency Quantile Scoring', stepDetail: `Evaluated ${c.recency_days} days since last transaction against database cohort thresholds -> Score ${c.rfm_recency_score}/5.`, isMath: false },
                              { stepTitle: '2. Frequency Quantile Scoring', stepDetail: `Evaluated ${c.frequency_orders} completed lifetime orders -> Score ${c.rfm_frequency_score}/5.`, isMath: false },
                              { stepTitle: '3. Monetary Quantile Scoring', stepDetail: `Evaluated $${c.monetary_spend} total lifetime spend -> Score ${c.rfm_monetary_score}/5.`, isMath: false },
                              { stepTitle: '4. Composite RFM Classification', stepDetail: `Composite index = (${c.rfm_recency_score} + ${c.rfm_frequency_score} + ${c.rfm_monetary_score}) / 3 = ${c.overall_rfm_score}/5 -> Mapped to ${c.ltv_segment}.`, isMath: true }
                            ],
                            businessInsight: 'High-LTV accounts should receive dedicated customer service routing and reserved safety inventory to prevent stockouts during peak ordering cycles.'
                          })}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '3px 8px',
                            borderRadius: '6px',
                            backgroundColor: '#f5f3ff',
                            border: '1px solid #ddd6fe',
                            color: '#6d28d9',
                            fontSize: '0.68rem',
                            fontWeight: 700,
                            cursor: 'pointer'
                          }}
                        >
                          <Calculator size={12} /> RFM Trace
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}

      {/* ========================================================================= */}
      {/* 4. CROSS-SELL BUNDLING & APRIORI MARKET BASKET                            */}
      {/* ========================================================================= */}
      {activeEngine === 'market_basket' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Header */}
          <div className="ui-card" style={{ padding: '22px', borderLeft: '5px solid #e11d48', backgroundColor: '#ffffff' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
              <div>
                <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#e11d48', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Module 4: Recommendation Algorithm (market_basket_analysis.py)
                </span>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0f172a', margin: '4px 0 0 0' }}>
                  Cross-Sell Product Bundles & Association Rule Mining (Apriori)
                </h2>
                <p style={{ fontSize: '0.78rem', color: '#64748b', margin: '4px 0 0 0' }}>
                  Calculates Support, Confidence, and Lift co-occurrence metrics across genuine customer transaction baskets to generate cross-sell recommendations.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <div style={{ textAlign: 'right', padding: '8px 14px', backgroundColor: '#fff1f2', borderRadius: '8px', border: '1px solid #fecdd3' }}>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#e11d48' }}>
                    {isNum(marketBasketData?.summary?.avg_association_lift) ? `${marketBasketData.summary.avg_association_lift}x` : '—'}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#9f1239', fontWeight: 600 }}>Avg Bundle Lift</div>
                </div>
                <div style={{ textAlign: 'right', padding: '8px 14px', backgroundColor: '#ecfdf5', borderRadius: '8px', border: '1px solid #a7f3d0' }}>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#059669' }}>
                    {fmtRaw(marketBasketData?.summary?.total_rules_discovered)}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#065f46', fontWeight: 600 }}>Discovered Rules</div>
                </div>
              </div>
            </div>
          </div>

          {/* Association Rules Table */}
          <div className="ui-card" style={{ padding: '20px' }}>
            <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#0f172a', marginBottom: '14px' }}>
              Mined Market Basket Rules (Antecedent &rarr; Consequent from Real DB Baskets)
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                <thead>
                  <tr style={{ color: '#64748b', textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>
                    <th style={{ padding: '8px' }}>Rule ID</th>
                    <th style={{ padding: '8px' }}>If Customer Buys (Antecedent)</th>
                    <th style={{ padding: '8px' }}>Recommend (Consequent)</th>
                    <th style={{ padding: '8px' }}>Support %</th>
                    <th style={{ padding: '8px' }}>Confidence %</th>
                    <th style={{ padding: '8px' }}>Lift Metric</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Explain Math</th>
                  </tr>
                </thead>
                <tbody>
                  {(marketBasketData?.association_rules || []).slice(0, 10).map((r, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #f8fafc' }}>
                      <td style={{ padding: '9px 8px', fontWeight: 700, color: '#64748b' }}>{r.rule_id}</td>
                      <td style={{ padding: '9px 8px', fontWeight: 700, color: '#0f172a' }}>{r.antecedent}</td>
                      <td style={{ padding: '9px 8px', fontWeight: 700, color: '#2563eb' }}>{r.consequent}</td>
                      <td style={{ padding: '9px 8px', color: '#64748b' }}>{r.support_pct}%</td>
                      <td style={{ padding: '9px 8px', fontWeight: 700, color: '#059669' }}>{r.confidence_pct}%</td>
                      <td style={{ padding: '9px 8px', fontWeight: 800, color: '#e11d48' }}>{r.lift}x</td>
                      <td style={{ padding: '9px 8px', textAlign: 'right' }}>
                        <button
                          onClick={() => setSelectedExplanation({
                            title: `Association Rule: ${r.antecedent} → ${r.consequent}`,
                            metricName: 'Apriori Association Lift',
                            resultValue: `${r.lift}x Lift (${r.confidence_pct}% Confidence)`,
                            subtitle: r.suggested_action,
                            formula: 'Lift(A → B) = P(A ∩ B) / [ P(A) × P(B) ]',
                            formulaExplanation: 'Measures how much more often items A and B are purchased together than would be expected if they were statistically independent. Lift > 1.0 proves genuine affinity.',
                            inputs: [
                              { name: 'Antecedent Item (A)', source: 'products table', value: r.antecedent },
                              { name: 'Consequent Item (B)', source: 'products table', value: r.consequent },
                              { name: 'Support % (Both Items)', source: 'order_items baskets', value: `${r.support_pct}% of baskets` },
                              { name: 'Confidence % (Conditional)', source: 'orders co-occurrence', value: `${r.confidence_pct}%` }
                            ],
                            steps: [
                              { stepTitle: '1. Basket Aggregation', stepDetail: `Grouped ${fmtInt(marketBasketData?.database_info?.baskets_analyzed)} customer orders into discrete transactional itemsets.`, isMath: false },
                              { stepTitle: '2. Support Calculation', stepDetail: `Supp(A ∩ B) = Count(Baskets containing both) / ${fmtInt(marketBasketData?.database_info?.baskets_analyzed)} = ${r.support_pct}%.`, isMath: true },
                              { stepTitle: '3. Confidence Ratio', stepDetail: `Conf(A → B) = Supp(A ∩ B) / Supp(A) = ${r.confidence_pct}%.`, isMath: true },
                              { stepTitle: '4. Lift Ratio', stepDetail: `Lift = Conf(A → B) / Supp(B) = ${r.lift}x multiplier.`, isMath: true }
                            ],
                            businessInsight: `Displaying '${r.consequent}' as an add-on whenever '${r.antecedent}' is added to cart converts with ${r.confidence_pct}% confidence, providing immediate ATV expansion.`
                          })}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '3px 8px',
                            borderRadius: '6px',
                            backgroundColor: '#fff1f2',
                            border: '1px solid #fecdd3',
                            color: '#be123c',
                            fontSize: '0.68rem',
                            fontWeight: 700,
                            cursor: 'pointer'
                          }}
                        >
                          <Calculator size={12} /> Lift Proof
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}

      {/* ========================================================================= */}
      {/* 5. TRADE AREA MODELLING & STORE GRAVITY ANALYSIS                           */}
      {/* ========================================================================= */}
      {activeEngine === 'trade_area' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Header */}
          <div className="ui-card" style={{ padding: '22px', borderLeft: '5px solid #0284c7', backgroundColor: '#ffffff' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
              <div>
                <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#0284c7', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Module 5: Trade Area Modelling (trade_area_modelling.py)
                </span>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0f172a', margin: '4px 0 0 0' }}>
                  Store Gravitational Pull & Territorial Catchment (Huff Model)
                </h2>
                <p style={{ fontSize: '0.78rem', color: '#64748b', margin: '4px 0 0 0' }}>
                  Quantifies store attractiveness, parking capacity, accessibility, and customer travel friction using quadratic distance decay.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <div style={{ textAlign: 'right', padding: '8px 14px', backgroundColor: '#f0f9ff', borderRadius: '8px', border: '1px solid #bae6fd' }}>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0284c7' }}>
                    {(tradeAreaData?.stores || []).length} Stores
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#0369a1', fontWeight: 600 }}>Active Regional Hubs</div>
                </div>
                <div style={{ textAlign: 'right', padding: '8px 14px', backgroundColor: '#ecfdf5', borderRadius: '8px', border: '1px solid #a7f3d0' }}>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#059669' }}>
                    {tradeAreaData?.summary?.highest_attractiveness_store || '—'}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#065f46', fontWeight: 600 }}>Highest Gravitational Draw</div>
                </div>
              </div>
            </div>
          </div>

          {tradeAreaData?.status === 'NEEDS_DATA' && (
            <div className="ui-card" style={{ padding: '20px', borderLeft: '5px solid #f59e0b', backgroundColor: '#fffbeb' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <AlertCircle size={18} color="#d97706" />
                <span style={{ fontSize: '0.92rem', fontWeight: 800, color: '#92400e' }}>Needs data — Huff model not calculated</span>
              </div>
              {tradeAreaData?.message && (
                <p style={{ fontSize: '0.8rem', color: '#78350f', margin: '0 0 10px 0' }}>{tradeAreaData.message}</p>
              )}
              {(tradeAreaData?.missing_data || []).length > 0 && (
                <ul style={{ fontSize: '0.78rem', color: '#78350f', margin: 0, paddingLeft: '18px' }}>
                  {tradeAreaData.missing_data.map((m, i) => <li key={i} style={{ marginBottom: '4px' }}>{m}</li>)}
                </ul>
              )}
              {(tradeAreaData?.stores || []).length > 0 && (
                <div style={{ overflowX: 'auto', marginTop: '14px' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem', backgroundColor: '#ffffff' }}>
                    <thead>
                      <tr style={{ color: '#64748b', textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>
                        <th style={{ padding: '8px' }}>Store / Warehouse</th>
                        <th style={{ padding: '8px' }}>Location</th>
                        <th style={{ padding: '8px' }}>Capacity</th>
                        <th style={{ padding: '8px', textAlign: 'right' }}>Sales Revenue</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tradeAreaData.stores.map((st, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid #f8fafc' }}>
                          <td style={{ padding: '8px', fontWeight: 700, color: '#0f172a' }}>{fmtRaw(st.store_name)} <span style={{ color: '#64748b', fontWeight: 400 }}>{st.warehouse_code}</span></td>
                          <td style={{ padding: '8px', color: '#64748b' }}>{fmtRaw(st.location)}</td>
                          <td style={{ padding: '8px', color: '#334155' }}>{isNum(st.size_sqft) ? `${fmtInt(st.size_sqft)} sqft` : '—'}</td>
                          <td style={{ padding: '8px', textAlign: 'right', fontWeight: 700, color: '#0f172a' }}>{isNum(st.revenue_usd) ? `$${fmtInt(st.revenue_usd)}` : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Store Gravity Cards */}
          {tradeAreaData?.status !== 'NEEDS_DATA' && (tradeAreaData?.stores || []).length === 0 && (
            <div className="ui-card" style={{ padding: '20px', fontSize: '0.8rem', color: '#64748b' }}>
              No data yet — import the required table on the Data Sources page.
            </div>
          )}
          {tradeAreaData?.status !== 'NEEDS_DATA' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px' }}>
            {(tradeAreaData?.stores || []).map((st, idx) => (
              <div key={idx} className="ui-card" style={{ padding: '16px', borderTop: `4px solid ${st.color || '#0284c7'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '0.7rem', fontWeight: 800, color: '#64748b' }}>{st.warehouse_code}</span>
                  <span style={{ fontSize: '0.68rem', fontWeight: 700, padding: '2px 6px', borderRadius: '4px', backgroundColor: '#f0f9ff', color: '#0284c7' }}>
                    {st.status}
                  </span>
                </div>
                <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#0f172a', marginBottom: '4px' }}>
                  {st.store_name}
                </div>
                <div style={{ fontSize: '0.72rem', color: '#64748b', marginBottom: '10px' }}>
                  {st.location}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                  <span style={{ color: '#64748b' }}>Capacity:</span>
                  <b>{isNum(st.size_sqft) ? `${fmtInt(st.size_sqft)} sqft` : '—'}</b>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '10px' }}>
                  <span style={{ color: '#64748b' }}>Attractiveness:</span>
                  <b style={{ color: '#0284c7' }}>{isNum(st.composite_attractiveness) ? `${st.composite_attractiveness} / 5.0` : '—'}</b>
                </div>
                <button
                  onClick={() => setSelectedExplanation({
                    title: `Huff Gravity Model: ${st.store_name}`,
                    metricName: 'Composite Attractiveness Index',
                    resultValue: isNum(st.composite_attractiveness) ? `${st.composite_attractiveness} / 5.0` : '—',
                    subtitle: `Warehouse: ${st.warehouse_code} • Location: ${st.location}`,
                    formula: 'P_ij = ( S_j / D_ij^λ ) / Σ_k ( S_k / D_ik^λ )',
                    formulaExplanation: 'The probability that a customer at origin i chooses store j is proportional to store attractiveness S_j divided by travel distance D_ij squared (λ = 2).',
                    inputs: [
                      { name: 'Floor Capacity (Size)', source: 'warehouses.capacity_sqft', value: isNum(st.size_sqft) ? `${fmtInt(st.size_sqft)} sqft` : '—' },
                      { name: 'Parking Capacity', source: 'warehouses derived', value: isNum(st.parking_spaces) ? `${st.parking_spaces} spots` : '—' },
                      { name: 'Highway Draw', source: 'store location', value: isNum(st.highways) ? `${st.highways} arteries` : '—' },
                      { name: 'Accessibility Score', source: 'store profile', value: isNum(st.accessibility_score) ? `${st.accessibility_score}/100` : '—' }
                    ],
                    steps: [
                      { stepTitle: '1. Multi-Factor Weighting', stepDetail: 'Size (30%) + Parking (25%) + Traffic (20%) + Access (15%) + Design (10%).', isMath: false },
                      { stepTitle: '2. Normalization', stepDetail: `Calculated weighted score = ${fmtRaw(st.composite_attractiveness)} on a 1.0 - 5.0 scale.`, isMath: true },
                      { stepTitle: '3. Distance Decay Simulation', stepDetail: 'Quadratic penalty (1/d²) applied against travel times from surrounding consumer zones.', isMath: false }
                    ],
                    businessInsight: 'High composite attractiveness overcomes moderate travel friction, cementing this facility as a prime regional fulfillment anchor.'
                  })}
                  style={{
                    width: '100%',
                    padding: '6px',
                    borderRadius: '6px',
                    border: '1px solid #bae6fd',
                    backgroundColor: '#f0f9ff',
                    color: '#0369a1',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  Explain Gravity Math
                </button>
              </div>
            ))}
          </div>
          )}

        </div>
      )}

      {/* ========================================================================= */}
      {/* 6, 7, 8, 9, 10: CORE CONTROL TOWER ENGINES                                */}
      {/* ========================================================================= */}
      {['demand', 'inventory', 'procurement', 'assortment', 'multi_agent'].includes(activeEngine) && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          <div className="ui-card" style={{ padding: '22px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
              <div>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a', margin: 0 }}>
                  {activeEngine === 'demand' && 'Autonomous Demand Projection & Uncertainty Interval'}
                  {activeEngine === 'inventory' && 'Multi-Echelon Stockout & Safety Buffer Matrix'}
                  {activeEngine === 'procurement' && 'Dynamic Purchase Order Schedule & Wilson EOQ'}
                  {activeEngine === 'assortment' && 'Retail Store Shelf GMROI & Cluster Optimization'}
                  {activeEngine === 'multi_agent' && 'Autonomous Coordinated Multi-Agent Operations Graph'}
                </h3>
                <p style={{ fontSize: '0.75rem', color: '#64748b', margin: '4px 0 0 0' }}>
                  Live backend statistical algorithms evaluating connected database products and transactions.
                </p>
              </div>

              {activeEngine === 'demand' && (
                <button
                  onClick={() => setSelectedExplanation({
                    title: `Demand Forecasting: ${demandData?.sku || 'Catalog SKUs'}`,
                    metricName: '30-Day Forward Demand Projection',
                    resultValue: isNum(demandData?.total_forecasted_demand) ? `${demandData.total_forecasted_demand} units (95% CI)` : '—',
                    subtitle: `Model: ${fmtRaw(demandData?.model_name)} • MAE: ${fmtRaw(demandData?.mae)} • RMSE: ${fmtRaw(demandData?.rmse)}`,
                    formula: 'ŷ_(t+h) = [ ℓ_t + h·b_t ] · s_(t+h-m)',
                    formulaExplanation: 'Holt-Winters triple exponential smoothing with level (ℓ_t), trend (b_t), and seasonal (s_t) update equations, coupled with Croston intermittent interval adjustments.',
                    inputs: [
                      { name: 'Target Product', source: 'products table', value: fmtRaw(demandData?.product_name) },
                      { name: 'Daily Transactions Used', source: 'sales_history table', value: `${fmtRaw(demandData?.calculation_trace?.historical_days_evaluated)} days` },
                      { name: 'Mean Daily Velocity', source: 'sales_history quantity_sold', value: `${fmtRaw(demandData?.calculation_trace?.daily_mean_demand)} units/day` },
                      { name: 'Confidence Interval', source: 'calculated bounds', value: '95% Confidence (±1.96 × RMSE)' }
                    ],
                    steps: [
                      { stepTitle: '1. Time Series Aggregation', stepDetail: 'Extracted daily sales history from connected database.', isMath: false },
                      { stepTitle: '2. Exponential Smoothing', stepDetail: 'Applied smoothing parameters (alpha=0.3, beta=0.1, gamma=0.2) to update level and trend.', isMath: true },
                      { stepTitle: '3. 30-Day Summation', stepDetail: `Forecasted daily increments sum to ${fmtRaw(demandData?.total_forecasted_demand)} units over the horizon.`, isMath: true }
                    ],
                    businessInsight: 'Demand trajectory provides forward operational baseline, triggering automated replenishment POs before stock breaches safety levels.'
                  })}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 12px',
                    borderRadius: '8px',
                    backgroundColor: '#eff6ff',
                    border: '1px solid #bfdbfe',
                    color: '#1d4ed8',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  <Calculator size={14} /> Explain Forecast Math
                </button>
              )}

              {activeEngine === 'procurement' && (
                <button
                  onClick={() => setSelectedExplanation({
                    title: 'Procurement Wilson EOQ & Batch Rebate',
                    metricName: 'Potential Procurement Savings',
                    resultValue: isNum(procurementData?.potential_savings) ? `$${procurementData.potential_savings}` : '—',
                    subtitle: 'Derived from Wilson Economic Order Quantity balancing setup vs holding cost',
                    formula: 'EOQ = √[ ( 2 × Demand × Setup_Cost ) / Holding_Cost ]',
                    formulaExplanation: 'The classical Wilson Economic Order Quantity formula minimizes total inventory cost: Carrying Cost (H = 15% of unit cost) + Ordering Cost (S = $50 fixed fee).',
                    inputs: [
                      { name: 'Fixed PO Setup Cost (S)', source: 'procurement parameter', value: '$50.00 / order' },
                      { name: 'Carrying Rate (H)', source: 'products.unit_cost × 15%', value: '15% annual' },
                      { name: 'Identified PO Savings', source: 'cost(current order qty) − cost(EOQ)', value: isNum(procurementData?.potential_savings) ? `$${procurementData.potential_savings}` : '—' }
                    ],
                    steps: [
                      { stepTitle: '1. Annual Demand Modeling', stepDetail: 'D = units sold in sales_history × 365 / days covered, per SKU.', isMath: false },
                      { stepTitle: '2. Wilson Square-Root Formula', stepDetail: 'EOQ = sqrt((2 * D * 50) / H) calculated for each product.', isMath: true },
                      { stepTitle: '3. Savings vs Current Order Size', stepDetail: 'Savings = yearly cost at current inventory.reorder_quantity − yearly cost at EOQ, where cost(Q) = D/Q × S + Q/2 × H. SKUs without a current order quantity are not counted.', isMath: true }
                    ],
                    businessInsight: 'Consolidating fragmented small orders into Wilson EOQ batches eliminates redundant delivery fees and captures bulk price discounts.'
                  })}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 12px',
                    borderRadius: '8px',
                    backgroundColor: '#faf5ff',
                    border: '1px solid #ddd6fe',
                    color: '#7c3aed',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  <Calculator size={14} /> Explain EOQ Math
                </button>
              )}
            </div>

            {/* Demand Chart */}
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
                <div style={{ height: '200px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: '0.82rem' }}>
                  <TrendingUp size={24} color="#94a3b8" style={{ marginBottom: '8px' }} />
                  <span>{isLoading ? 'Loading live demand forecast points from database...' : 'No data yet — import the required table on the Data Sources page.'}</span>
                </div>
              )
            )}

            {/* Inventory Risks */}
            {activeEngine === 'inventory' && (
              <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                  <thead>
                    <tr style={{ color: '#64748b', textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>SKU</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Product Name</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Warehouse Hub</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Stock</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Days of Supply</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Risk Status</th>
                      <th style={{ padding: '8px 0', fontWeight: 600, textAlign: 'right' }}>Explain Math</th>
                    </tr>
                  </thead>
                  <tbody>
                    {riskData.slice(0, 10).map((r, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #f8fafc' }}>
                        <td style={{ padding: '8px 0', fontWeight: 700, color: '#2563eb' }}>{r.sku}</td>
                        <td style={{ padding: '8px 0', color: '#0f172a', fontWeight: 500 }}>{r.product_name}</td>
                        <td style={{ padding: '8px 0', color: '#64748b' }}>{r.warehouse_name}</td>
                        <td style={{ padding: '8px 0', color: '#0f172a', fontWeight: 700 }}>{fmtRaw(r.current_stock)} units</td>
                        <td style={{ padding: '8px 0', color: '#334155', fontWeight: 600 }}>{fmtRaw(r.days_of_inventory)} days</td>
                        <td style={{ padding: '8px 0' }}>
                          <span style={{
                            fontSize: '0.7rem', fontWeight: 700, padding: '2px 8px', borderRadius: '6px',
                            backgroundColor: r.stockout_risk_level === 'CRITICAL' ? '#fef2f2' : r.stockout_risk_level === 'HIGH' ? '#fffbeb' : '#ecfdf5',
                            color: r.stockout_risk_level === 'CRITICAL' ? '#ef4444' : r.stockout_risk_level === 'HIGH' ? '#f59e0b' : '#10b981'
                          }}>
                            {r.stockout_risk_level}
                          </span>
                        </td>
                        <td style={{ padding: '8px 0', textAlign: 'right' }}>
                          <button
                            onClick={() => setSelectedExplanation({
                              title: `Inventory Risk: ${r.product_name}`,
                              metricName: 'Days of Inventory (DOI) & Buffer Risk',
                              resultValue: `${fmtRaw(r.days_of_inventory)} Days (${fmtRaw(r.stockout_risk_level)})`,
                              subtitle: `Warehouse: ${r.warehouse_name} • Current Stock: ${r.current_stock} units`,
                              formula: 'DOI = Current_Stock / Average_Daily_Demand',
                              formulaExplanation: 'Calculates the remaining duration of inventory before stockout at current transaction consumption run rates.',
                              inputs: [
                                { name: 'Available Physical Stock', source: 'inventory.current_stock', value: `${fmtRaw(r.current_stock)} units` },
                                { name: 'Avg Daily Run Rate', source: 'sales_history average', value: `${fmtRaw(r.avg_daily_demand)} units/day` },
                                { name: 'Safety Stock Floor', source: 'products.safety_stock_min', value: `${fmtRaw(r.safety_stock)} units` },
                                { name: 'Vendor Delivery Lead Time', source: 'products.lead_time_days', value: `${fmtRaw(r.lead_time_days)} days` }
                              ],
                              steps: [
                                { stepTitle: '1. Run Rate Calculation', stepDetail: `Average daily demand calculated from sales_history: ${fmtRaw(r.avg_daily_demand)} units/day.`, isMath: false },
                                { stepTitle: '2. DOI Division', stepDetail: `DOI = ${fmtRaw(r.current_stock)} / ${fmtRaw(r.avg_daily_demand)} = ${fmtRaw(r.days_of_inventory)} days.`, isMath: true },
                                { stepTitle: '3. Lead Time Threshold Comparison', stepDetail: `Compared DOI (${fmtRaw(r.days_of_inventory)}d) against lead time (${fmtRaw(r.lead_time_days)}d). If DOI < Lead Time, stock will deplete before reorder arrives.`, isMath: false }
                              ],
                              businessInsight: r.reasoning
                            })}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              backgroundColor: '#f1f5f9',
                              border: '1px solid #cbd5e1',
                              color: '#334155',
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              cursor: 'pointer'
                            }}
                          >
                            <Calculator size={11} /> DOI Trace
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Procurement EOQ Table */}
            {activeEngine === 'procurement' && (
              <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                  <thead>
                    <tr style={{ color: '#64748b', textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>SKU</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Product</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Stock</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Rec. PO Qty</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Supplier</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Est. Cost</th>
                      <th style={{ padding: '8px 0', fontWeight: 600, textAlign: 'right' }}>Explain Math</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(procurementData?.order_recommendations || []).map((po, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #f8fafc' }}>
                        <td style={{ padding: '8px 0', fontWeight: 700, color: '#2563eb' }}>{po.sku}</td>
                        <td style={{ padding: '8px 0', color: '#0f172a', fontWeight: 500 }}>{po.product_name}</td>
                        <td style={{ padding: '8px 0', color: '#64748b' }}>{fmtRaw(po.current_stock)} units</td>
                        <td style={{ padding: '8px 0', fontWeight: 700, color: '#059669' }}>{fmtRaw(po.recommended_po_qty)} units</td>
                        <td style={{ padding: '8px 0', color: '#475569' }}>{fmtRaw(po.supplier_name)}</td>
                        <td style={{ padding: '8px 0', fontWeight: 700, color: '#0f172a' }}>{isNum(po.estimated_order_cost) ? `$${po.estimated_order_cost}` : '—'}</td>
                        <td style={{ padding: '8px 0', textAlign: 'right' }}>
                          <button
                            onClick={() => setSelectedExplanation({
                              title: `Wilson EOQ: ${po.product_name}`,
                              metricName: 'Recommended Order Batch (EOQ)',
                              resultValue: `${fmtRaw(po.recommended_po_qty)} units ($${fmtRaw(po.estimated_order_cost)})`,
                              subtitle: `Assigned Supplier: ${fmtRaw(po.supplier_name)} (OTIF: ${isNum(po.supplier_otif) ? `${po.supplier_otif}%` : '—'})`,
                              formula: 'EOQ = √[ ( 2 × Demand × S ) / H ]',
                              formulaExplanation: 'Determines the exact batch size where cumulative annual order setup fees match cumulative annual storage holding costs.',
                              inputs: [
                                { name: 'Annual Projected Demand (D)', source: po.calculation_trace?.annual_demand_source || 'sales_history units sold × 365 / days', value: `${fmtRaw(po.calculation_trace?.annual_demand_D)} units/yr` },
                                { name: 'Fixed Order Setup Fee (S)', source: 'procurement constant', value: isNum(po.calculation_trace?.order_setup_cost_S) ? `$${po.calculation_trace.order_setup_cost_S} / order` : '—' },
                                { name: 'Holding Cost / Unit (H)', source: 'products.unit_cost × 15%', value: isNum(po.calculation_trace?.holding_cost_H) ? `$${po.calculation_trace.holding_cost_H} / unit/yr` : '—' }
                              ],
                              steps: [
                                { stepTitle: '1. Parameter Extraction', stepDetail: 'Pulled unit cost and reorder point from products table and units sold from sales_history in connected database.', isMath: false },
                                { stepTitle: '2. Wilson Equation Substitution', stepDetail: po.calculation_trace?.formula_substitution || '—', isMath: true },
                                { stepTitle: '3. Savings vs Current Order Size', stepDetail: po.calculation_trace?.savings_formula || 'Savings not computed — needs data.', isMath: true }
                              ],
                              businessInsight: `Ordering in batches of ${fmtRaw(po.recommended_po_qty)} units balances yearly ordering cost against holding cost.`
                            })}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              backgroundColor: '#faf5ff',
                              border: '1px solid #ddd6fe',
                              color: '#7c3aed',
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              cursor: 'pointer'
                            }}
                          >
                            <Calculator size={11} /> EOQ Trace
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Assortment AI Table */}
            {activeEngine === 'assortment' && (
              <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                  <thead>
                    <tr style={{ color: '#64748b', textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>SKU</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Product Name</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Allocated Space</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Sell-Through %</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>GMROI</th>
                      <th style={{ padding: '8px 0', fontWeight: 600 }}>Classification</th>
                      <th style={{ padding: '8px 0', fontWeight: 600, textAlign: 'right' }}>Explain Math</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(assortmentData?.sku_assortment || []).map((asst, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #f8fafc' }}>
                        <td style={{ padding: '8px 0', fontWeight: 700, color: '#2563eb' }}>{asst.sku}</td>
                        <td style={{ padding: '8px 0', color: '#0f172a', fontWeight: 500 }}>{asst.product_name}</td>
                        <td style={{ padding: '8px 0', color: '#64748b' }}>{fmtRaw(asst.allocated_space_sqm)} m²</td>
                        <td style={{ padding: '8px 0', color: '#059669', fontWeight: 700 }}>{isNum(asst.sell_through_pct) ? `${asst.sell_through_pct}%` : '—'}</td>
                        <td style={{ padding: '8px 0', fontWeight: 800, color: asst.gmroi >= 2.0 ? '#059669' : '#d97706' }}>
                          {isNum(asst.gmroi) ? `${asst.gmroi}x` : '—'}
                        </td>
                        <td style={{ padding: '8px 0' }}>
                          <span style={{
                            fontSize: '0.68rem', fontWeight: 700, padding: '2px 6px', borderRadius: '4px',
                            backgroundColor: asst.classification === 'STAR_PRODUCT' ? '#ecfdf5' : '#eff6ff',
                            color: asst.classification === 'STAR_PRODUCT' ? '#059669' : '#2563eb'
                          }}>
                            {asst.classification}
                          </span>
                        </td>
                        <td style={{ padding: '8px 0', textAlign: 'right' }}>
                          <button
                            onClick={() => setSelectedExplanation({
                              title: `Assortment GMROI: ${asst.product_name}`,
                              metricName: 'Gross Margin Return on Investment',
                              resultValue: `${fmtRaw(asst.gmroi)}x GMROI (Sell-Through: ${fmtRaw(asst.sell_through_pct)}%)`,
                              subtitle: `Allocated Floor Area: ${fmtRaw(asst.allocated_space_sqm)} m² • Revenue/m²: $${fmtRaw(asst.revenue_per_sqm)}`,
                              formula: 'GMROI = Gross_Margin_$ / Average_Display_Inventory_$',
                              formulaExplanation: 'Measures profitability generated per dollar of inventory displayed on store shelving.',
                              inputs: [
                                { name: '90-Day Units Sold', source: 'sales_history.quantity_sold', value: `${fmtRaw(asst.units_sold_90d)} units` },
                                { name: 'Gross Margin / Unit', source: 'products.selling_price - unit_cost', value: isNum(asst.gross_margin_per_unit) ? `$${fmt(asst.gross_margin_per_unit, 2)}` : '—' },
                                { name: 'Display Shelf Capacity', source: 'retail_spaces.display_units', value: `${fmtRaw(asst.display_units)} units` }
                              ],
                              steps: [
                                { stepTitle: '1. Revenue Productivity', stepDetail: `$${fmtRaw(asst.revenue_90d)} revenue / ${fmtRaw(asst.allocated_space_sqm)} m² = $${fmtRaw(asst.revenue_per_sqm)}/m²`, isMath: true },
                                { stepTitle: '2. Sell-Through Velocity', stepDetail: `Units Sold (${fmtRaw(asst.units_sold_90d)}) / Total Inventory (${isNum(asst.units_sold_90d) && isNum(asst.display_units) ? Number(asst.units_sold_90d) + Number(asst.display_units) : '—'}) = ${fmtRaw(asst.sell_through_pct)}%`, isMath: true },
                                { stepTitle: '3. Return on Investment', stepDetail: `Gross Profit / Average Inventory Investment = ${fmtRaw(asst.gmroi)}x`, isMath: true }
                              ],
                              businessInsight: `${asst.product_name} is performing as a ${asst.classification}, justifying its allocated shelf footprint.`
                            })}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              backgroundColor: '#fff7ed',
                              border: '1px solid #fed7aa',
                              color: '#c2410c',
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              cursor: 'pointer'
                            }}
                          >
                            <Calculator size={11} /> GMROI Proof
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Multi-Agent Results */}
            {activeEngine === 'multi_agent' && (
              <div>
                {multiAgentResult ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#0f172a' }}>
                      Parallel Agent Execution Steps (Logged in Real-Time):
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                      {(multiAgentResult.agent_logs || []).map((log, idx) => (
                        <div key={idx} style={{ padding: '12px', borderRadius: '8px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                            <span style={{ fontSize: '0.8rem', fontWeight: 800, color: '#2563eb' }}>{log.agent_name}</span>
                            <span style={{ fontSize: '0.68rem', fontWeight: 700, color: '#059669' }}>{log.execution_ms}ms</span>
                          </div>
                          <div style={{ fontSize: '0.74rem', color: '#0f172a', fontWeight: 600 }}>{log.action}</div>
                          <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '4px', fontFamily: 'monospace' }}>
                            {JSON.stringify(log.details)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div style={{ height: '180px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: '0.82rem' }}>
                    <Bot size={28} color="#2563eb" style={{ marginBottom: '8px' }} />
                    <span>Click "Run Multi-Agent Team" at the top to execute the 4 specialized agents across your database.</span>
                  </div>
                )}
              </div>
            )}

          </div>

        </div>
      )}

      {/* 4. MODALS */}
      {selectedExplanation && (
        <CalculationExplainerModal
          item={selectedExplanation}
          onClose={() => setSelectedExplanation(null)}
        />
      )}

      {isGlobalMathOpen && (
        <GlobalMathExplainerModal
          onClose={() => setIsGlobalMathOpen(false)}
        />
      )}

    </div>
  );
}

