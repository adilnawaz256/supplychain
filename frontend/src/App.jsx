import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import KPICards from './components/KPICards';
import RiskMatrixTable from './components/RiskMatrixTable';
import ForecastChart from './components/ForecastChart';
import RecommendationsPanel from './components/RecommendationsPanel';
import ProcurementModule from './components/ProcurementModule';
import AssortmentModule from './components/AssortmentModule';
import BIIntegrationsPanel from './components/BIIntegrationsPanel';
import AIAssistantDrawer from './components/AIAssistantDrawer';
import OnboardingWizard from './components/OnboardingWizard';
import { API_BASE_URL } from './config/api';
import { 
  LayoutDashboard, Box, TrendingUp, ShoppingCart, ShoppingBag, 
  Lightbulb, Database, Plug, Settings, Sparkles, ChevronRight, Layers
} from 'lucide-react';

export default function App() {
  const [isOnboarding, setIsOnboarding] = useState(false);
  const [activeTab, setActiveTab] = useState('control-tower'); // control-tower, inventory, demand, procurement, assortment, recommendations, integrations, onboarding
  const [summary, setSummary] = useState(null);
  const [risks, setRisks] = useState([]);
  const [products, setProducts] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [selectedProductId, setSelectedProductId] = useState(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = async () => {
    try {
      const [sumRes, riskRes, prodRes, whRes, recRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/control-tower/summary`),
        fetch(`${API_BASE_URL}/api/inventory-risk`),
        fetch(`${API_BASE_URL}/api/products`),
        fetch(`${API_BASE_URL}/api/warehouses`),
        fetch(`${API_BASE_URL}/api/recommendations`)
      ]);

      if (sumRes.ok) setSummary(await sumRes.json());
      if (riskRes.ok) setRisks(await riskRes.json());
      if (prodRes.ok) {
        const prods = await prodRes.json();
        setProducts(prods);
        if (prods.length > 0 && !selectedProductId) {
          setSelectedProductId(prods[0].id);
        }
      }
      if (whRes.ok) setWarehouses(await whRes.json());
      if (recRes.ok) setRecommendations(await recRes.json());
    } catch (err) {
      console.error("Error fetching dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleStartOnboarding = () => {
    setActiveTab('onboarding');
    setIsOnboarding(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const navItems = [
    { id: 'control-tower', label: 'Control Tower', icon: LayoutDashboard },
    { id: 'inventory', label: 'Inventory AI', icon: Box },
    { id: 'demand', label: 'Demand AI', icon: TrendingUp },
    { id: 'procurement', label: 'Procurement AI', icon: ShoppingCart },
    { id: 'assortment', label: 'Assortment AI', icon: ShoppingBag },
    { id: 'recommendations', label: 'Recommendations', icon: Lightbulb },
    { id: 'integrations', label: 'BI Integrations', icon: Plug },
    { id: 'onboarding', label: 'Data & Onboarding', icon: Database }
  ];

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    if (tabId === 'onboarding') {
      setIsOnboarding(true);
    } else {
      setIsOnboarding(false);
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar 
        onOpenChat={() => setIsChatOpen(true)} 
        onRelaunchOnboarding={handleStartOnboarding}
        activeTab={activeTab}
      />

      <div style={{ flex: 1, display: 'flex', maxWidth: '1440px', width: '100%', margin: '0 auto', padding: '24px 20px' }}>
        
        {/* Left Sidebar Navigation */}
        <aside style={{ width: '240px', flexShrink: 0, paddingRight: '24px' }}>
          <div className="glass-panel" style={{ padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ fontSize: '0.7rem', color: '#64748b', fontWeight: 700, padding: '8px 12px', textTransform: 'uppercase', letterSpacing: '1px' }}>
              Intelligence Modules
            </div>
            {navItems.map(item => {
              const IconComp = item.icon;
              const isActive = (activeTab === item.id) || (item.id === 'onboarding' && isOnboarding);
              return (
                <button
                  key={item.id}
                  onClick={() => handleTabChange(item.id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '12px',
                    padding: '12px 14px', borderRadius: '10px', width: '100%',
                    background: isActive ? 'linear-gradient(135deg, rgba(99,102,241,0.25), rgba(139,92,246,0.25))' : 'transparent',
                    border: isActive ? '1px solid rgba(99,102,241,0.4)' : '1px solid transparent',
                    color: isActive ? '#f8fafc' : '#94a3b8',
                    fontWeight: isActive ? 600 : 500, fontSize: '0.88rem',
                    cursor: 'pointer', textAlign: 'left', transition: 'all 0.15s ease'
                  }}
                >
                  <IconComp size={18} color={isActive ? '#818cf8' : '#64748b'} />
                  <span style={{ flex: 1 }}>{item.label}</span>
                  {isActive && <ChevronRight size={14} color="#818cf8" />}
                </button>
              );
            })}
          </div>
        </aside>

        {/* Main Content Area */}
        <main style={{ flex: 1, minWidth: 0 }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '80px', color: '#94a3b8' }}>
              Loading Wisualyst Decision Intelligence...
            </div>
          ) : (
            <>
              {/* Show empty state banner only when NOT in onboarding tab */}
              {products.length === 0 && activeTab !== 'onboarding' && !isOnboarding && (
                <div style={{
                  padding: '24px 32px', borderRadius: '16px', marginBottom: '24px',
                  background: 'rgba(99, 102, 241, 0.12)', border: '1px solid rgba(99, 102, 241, 0.3)',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                }}>
                  <div>
                    <h3 style={{ fontSize: '1.1rem', color: '#f8fafc', margin: '0 0 6px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Database size={20} color="#818cf8" /> No Connected Data Source
                    </h3>
                    <p style={{ color: '#94a3b8', margin: 0, fontSize: '0.85rem' }}>
                      Your database is clean. Launch the Onboarding Wizard to connect your PostgreSQL, Zoho, or SFTP feeds.
                    </p>
                  </div>
                  <button onClick={handleStartOnboarding} className="glow-btn-primary" style={{ padding: '10px 20px', whiteSpace: 'nowrap' }}>
                    Connect Data Source
                  </button>
                </div>
              )}

              {activeTab === 'control-tower' && !isOnboarding && (
                <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  <KPICards summaryData={summary} />
                  <RiskMatrixTable 
                    risks={risks} 
                    warehouses={warehouses} 
                    onSelectProduct={(id) => setSelectedProductId(id)}
                  />
                  <ForecastChart 
                    products={products} 
                    selectedProductId={selectedProductId}
                    onSelectProduct={(id) => setSelectedProductId(id)}
                  />
                  <RecommendationsPanel recommendations={recommendations} />
                </div>
              )}

              {activeTab === 'inventory' && !isOnboarding && (
                <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  <KPICards summaryData={summary} />
                  <RiskMatrixTable 
                    risks={risks} 
                    warehouses={warehouses} 
                    onSelectProduct={(id) => setSelectedProductId(id)}
                  />
                </div>
              )}

              {activeTab === 'demand' && !isOnboarding && (
                <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  <ForecastChart 
                    products={products} 
                    selectedProductId={selectedProductId}
                    onSelectProduct={(id) => setSelectedProductId(id)}
                  />
                </div>
              )}

              {activeTab === 'procurement' && !isOnboarding && <ProcurementModule />}

              {activeTab === 'assortment' && !isOnboarding && <AssortmentModule />}

              {activeTab === 'recommendations' && !isOnboarding && (
                <div className="animate-fade-in">
                  <RecommendationsPanel recommendations={recommendations} />
                </div>
              )}

              {activeTab === 'integrations' && !isOnboarding && <BIIntegrationsPanel />}

              {(activeTab === 'onboarding' || isOnboarding) && (
                <div className="animate-fade-in" style={{ marginTop: 0 }}>
                  <OnboardingWizard onComplete={() => { setIsOnboarding(false); setActiveTab('control-tower'); fetchDashboardData(); }} />
                </div>
              )}
            </>
          )}
        </main>
      </div>

      <AIAssistantDrawer 
        isOpen={isChatOpen} 
        onClose={() => setIsChatOpen(false)} 
      />
    </div>
  );
}
