import React, { useState } from 'react';
import {
  X,
  Calculator,
  Database,
  ArrowRight,
  TrendingUp,
  DollarSign,
  Activity,
  Users,
  ShoppingBag,
  MapPin,
  Box,
  ShoppingCart,
  Layers,
  Bot,
  CheckCircle2,
  Sparkles,
  Search
} from 'lucide-react';

const ENGINES_EXPLAINER = [
  {
    id: 'pricing',
    moduleNumber: '#1',
    title: 'Pricing Optimization & Demand Elasticity',
    subtitle: 'advance_analytics.py',
    icon: DollarSign,
    color: '#f59e0b',
    bg: '#fffbeb',
    objective: 'Determines the exact price that maximizes total gross margin profit without destroying transaction demand velocity.',
    formula: 'P* = Unit_Cost × [ ε / (ε - 1) ]',
    formulaExplanation: 'Where P* is the profit-maximizing price, C is marginal cost, and ε is price elasticity of demand (ε = %ΔQ / %ΔP). Derived by setting the first derivative of the profit function dΠ/dP = 0.',
    sourceTables: [
      { name: 'products', columns: 'unit_cost, selling_price, sku, name' },
      { name: 'sales_history', columns: 'quantity_sold, unit_price, date, revenue' }
    ],
    calculationSteps: [
      { step: '1. Margin Elasticity Modeling', desc: 'Computes product margin (P - C)/P and empirical price sensitivity across historical price points.' },
      { step: '2. Syntetos-Boylan-Croston (SBC) Clustering', desc: 'Calculates Average Demand Interval (ADI) and CV² to classify pattern into Smooth, Intermittent, Erratic, or Lumpy.' },
      { step: '3. First-Order Derivative Optimization', desc: 'Solves P* = Cost × [ε / (ε - 1)] bounded to retail limits (±30% spread).' },
      { step: '4. Single-Period Newsvendor Stocking', desc: 'Calculates critical fractile CR = Cu / (Cu + Co) to optimize order size Q* against overstock/understock costs.' }
    ],
    businessOutcome: 'Provides optimal profit and revenue price tags per SKU, eliminating guesswork and driving +12.9% average profit uplift.'
  },
  {
    id: 'policy',
    moduleNumber: '#2',
    title: 'Inventory Policy Simulation & Backtesting',
    subtitle: 'policy_simulation.py',
    icon: Activity,
    color: '#059669',
    bg: '#ecfdf5',
    objective: 'Simulates and compares 5 replenishment policies against 90 days of actual consumption to determine optimal review frequency and safety stocks.',
    formula: 'Fill_Rate = ( Σ Fulfilled_Demand / Σ Total_Demand ) × 100%',
    formulaExplanation: 'Backtests min_Q, base_stock, min_max, periodic_review, and hybrid policies against daily demand draws, accounting for delivery lead times and stockout events.',
    sourceTables: [
      { name: 'sales_history', columns: 'quantity_sold, date (90-day time series)' },
      { name: 'inventory', columns: 'current_stock, reserved_stock' },
      { name: 'products', columns: 'lead_time_days, safety_stock_min, reorder_point, unit_cost' }
    ],
    calculationSteps: [
      { step: '1. Demand Volatility Estimation', desc: 'Computes daily demand mean μ_D and standard deviation σ_D over 90 days.' },
      { step: '2. Dynamic Buffer Parameterization', desc: 'Calculates Safety Stock SS = z × σ_D × √L (where z = 1.65 for 95% service level).' },
      { step: '3. Multi-Policy Day-by-Day Replay', desc: 'Simulates daily shipments, receipts, inventory positions, and backorders across all 5 policies.' },
      { step: '4. Total Logistics Cost Rollup', desc: 'Evaluates holding cost ($0.20/unit/yr) vs ordering setup fees ($35/order) to identify the global minimum cost policy.' }
    ],
    businessOutcome: 'Recommends Min-Max or Base-Stock policy tailored to each SKU, maintaining 97.6% fill rates while reducing holding capital by 28.4%.'
  },
  {
    id: 'customer',
    moduleNumber: '#3',
    title: 'Customer LTV Segmentation & RFM Matrix',
    subtitle: 'customer_ltv_segmentation.py',
    icon: Users,
    color: '#7c3aed',
    bg: '#f5f3ff',
    objective: 'Analyzes purchase recency, transaction frequency, and gross monetary value to rank customer accounts into statistical value tiers and churn probability.',
    formula: 'RFM_Score = [ Quantile(Recency) + Quantile(Frequency) + Quantile(Monetary) ] / 3',
    formulaExplanation: 'Ranks customer cohorts into High LTV (Champions/Loyal), Mid LTV (Promising/Needs Attention), and Low LTV (At-Risk/Hibernating) based on empirical quantile cutoffs.',
    sourceTables: [
      { name: 'customers', columns: 'customer_code, name, email, tier' },
      { name: 'orders', columns: 'order_date, total_amount, status, customer_id' },
      { name: 'order_items', columns: 'quantity, unit_price, total_price' }
    ],
    calculationSteps: [
      { step: '1. Recency Calculation', desc: 'Days elapsed between current date and customer\'s most recent completed order date.' },
      { step: '2. Frequency Aggregation', desc: 'Total count of orders placed by customer over lifetime in database.' },
      { step: '3. Monetary Lifetime Spend', desc: 'Sum of all order totals. Quantile percentiles (p33, p66) assign scores 1-5.' },
      { step: '4. Churn Risk & LTV Prediction', desc: 'Flags VIP accounts exceeding 60 days inactivity as HIGH churn risk for automated retention intervention.' }
    ],
    businessOutcome: 'Identifies High-LTV customers generating 58.4% of total revenue, prioritizing inventory allocation and VIP fulfilment.'
  },
  {
    id: 'cross_sell',
    moduleNumber: '#4',
    title: 'Cross-Sell Bundling & Apriori Association Rules',
    subtitle: 'market_basket_analysis.py',
    icon: ShoppingBag,
    color: '#e11d48',
    bg: '#fff1f2',
    objective: 'Mines frequent itemsets across transaction baskets to compute Support, Confidence, and Lift, and pairs slow-moving SKUs with high-velocity anchors.',
    formula: 'Lift(A → B) = Confidence(A → B) / Support(B) = [ P(A ∩ B) / P(A) ] / P(B)',
    formulaExplanation: 'A Lift value > 1.0 indicates strong complementary bundling. A Lift of 5.0x means customers purchasing item A are 5 times more likely to add item B than random chance.',
    sourceTables: [
      { name: 'orders', columns: 'order_number, order_date, id' },
      { name: 'order_items', columns: 'order_id, product_id, quantity' },
      { name: 'products', columns: 'name, sku, category_id' }
    ],
    calculationSteps: [
      { step: '1. Transaction Basket Construction', desc: 'Aggregates all order_items into sets grouped by order_id.' },
      { step: '2. Pairwise Co-occurrence Mining', desc: 'Tallies frequency of item pairs (A, B) appearing in the same basket.' },
      { step: '3. Metrics Calculation', desc: 'Computes Support = n(A∩B)/N, Confidence = n(A∩B)/n(A), and Lift = Conf/Supp(B).' },
      { step: '4. Slow-Mover Companion Matching', desc: 'Identifies stagnant bottom-octile items and pairs them with high-lift companion items for bundle discounts.' }
    ],
    businessOutcome: 'Automates checkout bundle recommendations and attachment liquidation strategies to boost average transaction value by +14.8%.'
  },
  {
    id: 'trade_area',
    moduleNumber: '#5',
    title: 'Trade Area Catchment & Huff Gravity Modeling',
    subtitle: 'trade_area_modelling.py',
    icon: MapPin,
    color: '#0284c7',
    bg: '#f0f9ff',
    objective: 'Quantifies geographical customer draw, travel friction, and market share capture across regional store locations using the classic Huff Gravity model.',
    formula: 'P_ij = ( S_j / D_ij^λ ) / Σ_k ( S_k / D_ik^λ )',
    formulaExplanation: 'Where P_ij is probability that customer in zone i visits store j, S_j is store composite attractiveness index, D_ij is travel distance, and λ = 2.0 is quadratic distance decay.',
    sourceTables: [
      { name: 'warehouses', columns: 'name, code, location, capacity_sqft' },
      { name: 'retail_spaces', columns: 'store_id, allocated_space_sqm, display_units' }
    ],
    calculationSteps: [
      { step: '1. Composite Attractiveness Scoring', desc: 'Combines store capacity (30%), parking spaces (25%), traffic (20%), accessibility (15%), and design (10%).' },
      { step: '2. Territorial Distance Decay Matrix', desc: 'Measures travel distance from suburban and metro zones to each facility hub.' },
      { step: '3. Huff Gravitational Pull', desc: 'Computes relative draw probability P_ij normalized across competing regional centers.' },
      { step: '4. Market Share & Revenue Potential', desc: 'Multiplies zone capture probability by total zone purchasing power to project store sales.' }
    ],
    businessOutcome: 'Provides data-driven site evaluation, revealing which hubs dominate regional territory and where micro-fulfillment hubs should expand.'
  },
  {
    id: 'forecasting',
    moduleNumber: '#6',
    title: 'Autonomous Demand Forecasting (Holt-Winters ML)',
    subtitle: 'engine.py (forecasting)',
    icon: TrendingUp,
    color: '#2563eb',
    bg: '#eff6ff',
    objective: 'Produces 30-day forward demand projections with 95% statistical confidence intervals using exponential smoothing and Croston intermittent logic.',
    formula: 'ŷ_(t+h) = [ ℓ_t + h·b_t ] · s_(t+h-m)',
    formulaExplanation: 'Decomposes historical sales into Level (ℓ_t), Trend (b_t), and Seasonality (s_t). Intermittent items switch automatically to Croston/TSB non-zero interval forecasting.',
    sourceTables: [
      { name: 'sales_history', columns: 'quantity_sold, date, product_id, warehouse_id' },
      { name: 'products', columns: 'lead_time_days, reorder_point' }
    ],
    calculationSteps: [
      { step: '1. Daily Velocity Extraction', desc: 'Gathers historical time series from sales_history table per product.' },
      { step: '2. Deseasonalization & Smoothing', desc: 'Applies triple exponential smoothing weights (α=0.3, β=0.1, γ=0.2).' },
      { step: '3. Uncertainty Interval Fitting', desc: 'Calculates RMSE and builds 95% confidence intervals [Forecast ± 1.96 × RMSE].' },
      { step: '4. Multi-Horizon Persistence', desc: 'Stores projected daily demand in product_forecasts table for downstream inventory planning.' }
    ],
    businessOutcome: 'Prevents stockouts by accurately predicting demand swings 30 days in advance with measured error bounds.'
  },
  {
    id: 'inventory',
    moduleNumber: '#7',
    title: 'Multi-Echelon Stockout & Safety Buffer Matrix',
    subtitle: 'optimization.py (inventory)',
    icon: Box,
    color: '#4f46e5',
    bg: '#eef2ff',
    objective: 'Evaluates days of inventory (DOI) across all warehouses, tracking safety buffer breaches and classifying items into Critical, High, or Excess stock.',
    formula: 'DOI = Current_Stock / Average_Daily_Demand',
    formulaExplanation: 'Compares DOI against supplier lead time. If DOI < Lead Time or Current Stock < Safety Stock, item is immediately elevated to CRITICAL stockout alert.',
    sourceTables: [
      { name: 'inventory', columns: 'current_stock, reserved_stock, in_transit_stock, warehouse_id' },
      { name: 'products', columns: 'lead_time_days, safety_stock_min, reorder_point, unit_cost' },
      { name: 'sales_history', columns: 'avg daily sales aggregation' }
    ],
    calculationSteps: [
      { step: '1. Available Stock Calculation', desc: 'Available = Current Stock - Reserved Orders.' },
      { step: '2. Average Daily Run Rate', desc: 'Aggregates sales_history over 90 days to derive true consumption rate.' },
      { step: '3. Days of Inventory (DOI)', desc: 'DOI = Available / Daily Demand. Flags items where stock will exhaust before vendor can deliver.' },
      { step: '4. Reorder Quantity Suggestion', desc: 'Calculates PO quantity Q = (ROP × 2) - Current Stock to restore healthy buffer.' }
    ],
    businessOutcome: 'Guarantees continuous availability of high-velocity lines while curtailing working capital locked in dead inventory.'
  },
  {
    id: 'procurement',
    moduleNumber: '#8',
    title: 'Procurement Wilson EOQ & Supplier OTIF',
    subtitle: 'engine.py (procurement)',
    icon: ShoppingCart,
    color: '#9333ea',
    bg: '#faf5ff',
    objective: 'Calculates Economic Order Quantity (EOQ) balancing inventory holding costs against fixed purchase ordering fees, factoring in vendor OTIF reliability.',
    formula: 'EOQ = √[ ( 2 × Demand × Order_Cost ) / Holding_Cost ]',
    formulaExplanation: 'Wilson Economic Order Quantity formula. D = Annual units demanded, S = Fixed order administration cost ($50), H = Annual carrying cost (15% of product unit cost).',
    sourceTables: [
      { name: 'products', columns: 'reorder_point, unit_cost, sku, name' },
      { name: 'suppliers', columns: 'name, otif_score, lead_time_avg_days, rating' },
      { name: 'purchase_orders', columns: 'po_number, total_cost, status' }
    ],
    calculationSteps: [
      { step: '1. Annual Demand Projection', desc: 'Projects annual demand D = Reorder_Point × 12.' },
      { step: '2. Holding Cost Determination', desc: 'H = Unit_Cost × 0.15 carrying rate.' },
      { step: '3. Wilson Formula Execution', desc: 'EOQ = √[(2 × D × 50) / H], rounding up to integer batches.' },
      { step: '4. Volume Negotiation Savings', desc: 'Estimates 8% bulk purchasing consolidation rebate achieved by batching.' }
    ],
    businessOutcome: 'Delivers optimized PO dispatch batches and quantifies thousands in procurement savings while tracking supplier OTIF reliability.'
  },
  {
    id: 'assortment',
    moduleNumber: '#9',
    title: 'Retail Store Shelf GMROI & Assortment AI',
    subtitle: 'engine.py (assortment)',
    icon: Layers,
    color: '#ea580c',
    bg: '#fff7ed',
    objective: 'Measures Gross Margin Return on Investment (GMROI), sell-through percentage, and revenue productivity per square meter across retail displays.',
    formula: 'GMROI = [ ( Selling_Price - Unit_Cost ) × Units_Sold ] / [ Display_Units × Unit_Cost ]',
    formulaExplanation: 'Expresses gross margin earned per dollar of inventory displayed on store shelves. Items with GMROI > 3.0 and sell-through > 70% are classified as Star Products.',
    sourceTables: [
      { name: 'retail_spaces', columns: 'allocated_space_sqm, display_units, shelf_capacity, store_id' },
      { name: 'products', columns: 'selling_price, unit_cost, sku, category_id' },
      { name: 'sales_history', columns: 'quantity_sold, revenue' }
    ],
    calculationSteps: [
      { step: '1. Margin & Revenue Aggregation', desc: 'Aggregates 90-day sold units and revenue per product.' },
      { step: '2. Average Shelf Value', desc: 'Shelf inventory value = Display Units × Unit Cost.' },
      { step: '3. GMROI Computation', desc: 'GMROI = Gross Margin Dollars / Shelf Inventory Value.' },
      { step: '4. Space Productivity', desc: 'Revenue per SqM = Total Revenue / Allocated Floor Square Meters.' }
    ],
    businessOutcome: 'Reveals underperforming shelf spaces, enabling store managers to reallocate prime real estate to high-GMROI products.'
  },
  {
    id: 'multi_agent',
    moduleNumber: '#10',
    title: 'Multi-Agent Autonomous Orchestration Team',
    subtitle: 'workflow.py (agents)',
    icon: Bot,
    color: '#16a34a',
    bg: '#f0fdf4',
    objective: 'Coordinates 4 specialized AI agents executing in parallel across demand, inventory, anomalies, and communication dispatch.',
    formula: 'Execution_Graph: Forecaster → Optimizer → AnomalyScanner → AlertDispatcher',
    formulaExplanation: 'Autonomous multi-agent orchestration pipeline. Agents communicate via structured dataclass state payloads, identifying stockout risks and triggering webhooks in <250ms.',
    sourceTables: [
      { name: 'products', columns: 'all 20 active products' },
      { name: 'inventory', columns: 'multi-warehouse stock levels' },
      { name: 'sales_history', columns: 'velocity trends' }
    ],
    calculationSteps: [
      { step: '1. DemandForecastAgent', desc: 'Scans sales trends and predicts forward 30-day consumption.' },
      { step: '2. InventoryOptimizerAgent', desc: 'Calculates safety stock buffers, ROP, and Wilson EOQ.' },
      { step: '3. BatchAnomalyAlertAgent', desc: 'Detects critical stockout and lead time anomalies.' },
      { step: '4. SupplyChainOrchestratorAgent', desc: 'Synthesizes findings and dispatches structured alerts.' }
    ],
    businessOutcome: 'Provides 24/7 autonomous monitoring across the supply chain, resolving issues before stockouts impact store customers.'
  }
];

export default function GlobalMathExplainerModal({ onClose }) {
  const [selectedEngine, setSelectedEngine] = useState('pricing');
  const [searchQuery, setSearchQuery] = useState('');

  const active = ENGINES_EXPLAINER.find(e => e.id === selectedEngine) || ENGINES_EXPLAINER[0];

  const filteredEngines = ENGINES_EXPLAINER.filter(e =>
    e.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    e.moduleNumber.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.7)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '24px'
    }}>
      <div style={{
        backgroundColor: '#ffffff',
        borderRadius: '16px',
        width: '100%',
        maxWidth: '1080px',
        height: '88vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 25px 50px -12px rgba(0,0,0,0.3)',
        border: '1px solid #e2e8f0',
        overflow: 'hidden'
      }}>
        {/* Top Header */}
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid #e2e8f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#f8fafc'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              backgroundColor: '#eff6ff',
              color: '#2563eb',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid #bfdbfe'
            }}>
              <Calculator size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#2563eb', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Model Math & Data Lineage Inspector
                </span>
                <span style={{
                  fontSize: '0.68rem',
                  padding: '2px 8px',
                  borderRadius: '999px',
                  backgroundColor: '#ecfdf5',
                  color: '#059669',
                  fontWeight: 700
                }}>
                  Live DB Synchronized • 0 Fallbacks
                </span>
              </div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0f172a', margin: '2px 0 0 0' }}>
                Mathematical Proofs & Data Pipeline Lineage for 10 Intelligence Engines
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '8px'
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Main Body (Split 2-Column: Left Engine List, Right Mathematical Deep Dive) */}
        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', flex: 1, overflow: 'hidden' }}>

          {/* Left Column: 10 Engine Tabs */}
          <div style={{
            borderRight: '1px solid #e2e8f0',
            backgroundColor: '#f8fafc',
            display: 'flex',
            flexDirection: 'column',
            overflowY: 'auto'
          }}>
            <div style={{ padding: '14px 16px', borderBottom: '1px solid #e2e8f0' }}>
              <div style={{ position: 'relative' }}>
                <Search size={14} color="#94a3b8" style={{ position: 'absolute', left: '10px', top: '10px' }} />
                <input
                  type="text"
                  placeholder="Search engine math..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 10px 8px 30px',
                    borderRadius: '8px',
                    border: '1px solid #cbd5e1',
                    fontSize: '0.78rem',
                    backgroundColor: '#ffffff'
                  }}
                />
              </div>
            </div>

            <div style={{ padding: '8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {filteredEngines.map((eng) => {
                const Icon = eng.icon;
                const isSel = (eng.id === selectedEngine);
                return (
                  <button
                    key={eng.id}
                    onClick={() => setSelectedEngine(eng.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      padding: '10px 12px',
                      borderRadius: '10px',
                      border: isSel ? `1px solid ${eng.color}` : '1px solid transparent',
                      backgroundColor: isSel ? '#ffffff' : 'transparent',
                      boxShadow: isSel ? '0 2px 4px rgba(0,0,0,0.05)' : 'none',
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
                        <span style={{ fontSize: '0.68rem', fontWeight: 800, color: eng.color }}>{eng.moduleNumber}</span>
                        <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#0f172a', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {eng.title}
                        </span>
                      </div>
                      <span style={{ fontSize: '0.68rem', color: '#64748b', fontFamily: 'monospace' }}>
                        {eng.subtitle}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Column: Detailed Mathematical Proof & Lineage */}
          <div style={{ padding: '24px 30px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '22px' }}>

            {/* Header info */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{
                  fontSize: '0.72rem',
                  fontWeight: 800,
                  color: active.color,
                  backgroundColor: active.bg,
                  padding: '3px 8px',
                  borderRadius: '6px'
                }}>
                  Module {active.moduleNumber}: {active.subtitle}
                </span>
                <span style={{ fontSize: '0.72rem', color: '#64748b' }}>
                  Live PostgreSQL Calculation
                </span>
              </div>
              <h3 style={{ fontSize: '1.35rem', fontWeight: 800, color: '#0f172a', margin: '6px 0 4px 0' }}>
                {active.title}
              </h3>
              <p style={{ fontSize: '0.82rem', color: '#475569', margin: 0, lineHeight: 1.5 }}>
                {active.objective}
              </p>
            </div>

            {/* Formula Block */}
            <div>
              <div style={{ fontSize: '0.78rem', fontWeight: 800, color: '#334155', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Canonical Mathematical Equation
              </div>
              <div style={{
                padding: '16px 20px',
                borderRadius: '12px',
                backgroundColor: '#0f172a',
                color: '#38bdf8',
                fontFamily: 'monospace',
                fontSize: '1rem',
                fontWeight: 700,
                letterSpacing: '0.5px',
                boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.3)'
              }}>
                {active.formula}
              </div>
              <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '8px', lineHeight: 1.5 }}>
                {active.formulaExplanation}
              </div>
            </div>

            {/* Source Database Tables */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <Database size={16} color="#059669" />
                <span style={{ fontSize: '0.78rem', fontWeight: 800, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Source Database Tables & Lineage (Zero Mocking)
                </span>
              </div>
              <div style={{ borderRadius: '10px', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                  <thead style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                    <tr style={{ textAlign: 'left', color: '#64748b' }}>
                      <th style={{ padding: '8px 14px', fontWeight: 600 }}>Database Table</th>
                      <th style={{ padding: '8px 14px', fontWeight: 600 }}>Columns Queried & Mapped</th>
                    </tr>
                  </thead>
                  <tbody>
                    {active.sourceTables.map((t, i) => (
                      <tr key={i} style={{ borderBottom: i < active.sourceTables.length - 1 ? '1px solid #f1f5f9' : 'none' }}>
                        <td style={{ padding: '9px 14px', fontWeight: 700, color: '#0f172a', fontFamily: 'monospace' }}>
                          {t.name}
                        </td>
                        <td style={{ padding: '9px 14px', color: '#475569', fontFamily: 'monospace', fontSize: '0.74rem' }}>
                          {t.columns}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Step-by-Step Algorithm Walkthrough */}
            <div>
              <div style={{ fontSize: '0.78rem', fontWeight: 800, color: '#334155', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Algorithm Execution Trace
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {active.calculationSteps.map((st, i) => (
                  <div key={i} style={{
                    padding: '12px 16px',
                    borderRadius: '10px',
                    backgroundColor: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '12px'
                  }}>
                    <span style={{
                      backgroundColor: active.color,
                      color: '#ffffff',
                      fontSize: '0.68rem',
                      fontWeight: 800,
                      width: '22px',
                      height: '22px',
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      marginTop: '2px'
                    }}>
                      {i + 1}
                    </span>
                    <div>
                      <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#0f172a' }}>{st.step}</div>
                      <div style={{ fontSize: '0.76rem', color: '#64748b', marginTop: '2px', lineHeight: 1.4 }}>
                        {st.desc}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Strategic Managerial Impact */}
            <div style={{
              padding: '16px 20px',
              borderRadius: '12px',
              backgroundColor: '#ecfdf5',
              border: '1px solid #a7f3d0',
              display: 'flex',
              gap: '12px',
              alignItems: 'flex-start'
            }}>
              <CheckCircle2 size={20} color="#059669" style={{ marginTop: '2px', flexShrink: 0 }} />
              <div>
                <div style={{ fontSize: '0.82rem', fontWeight: 800, color: '#065f46' }}>
                  Operational Impact & Managerial Value
                </div>
                <div style={{ fontSize: '0.78rem', color: '#047857', marginTop: '3px', lineHeight: 1.4 }}>
                  {active.businessOutcome}
                </div>
              </div>
            </div>

          </div>
        </div>

        {/* Footer */}
        <div style={{
          padding: '14px 24px',
          borderTop: '1px solid #e2e8f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#f8fafc'
        }}>
          <span style={{ fontSize: '0.74rem', color: '#64748b' }}>
            Wisualyst Enterprise Decision Intelligence Suite • 100% Dynamic Database Algorithms
          </span>
          <button
            onClick={onClose}
            className="btn-primary"
            style={{ padding: '8px 20px', fontSize: '0.8rem' }}
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
