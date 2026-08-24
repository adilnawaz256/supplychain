import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import KPICards from './components/KPICards';
import RiskMatrixTable from './components/RiskMatrixTable';
import ForecastChart from './components/ForecastChart';
import RecommendationsPanel from './components/RecommendationsPanel';
import AIAssistantDrawer from './components/AIAssistantDrawer';

export default function App() {
  const [summary, setSummary] = useState(null);
  const [risks, setRisks] = useState([]);
  const [products, setProducts] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [selectedProductId, setSelectedProductId] = useState(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = async () => {
    try {
      const [sumRes, riskRes, prodRes, whRes, recRes] = await Promise.all([
        fetch('/api/control-tower'),
        fetch('/api/inventory-risk'),
        fetch('/api/products'),
        fetch('/api/warehouses'),
        fetch('/api/inventory-recommendations')
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

  const handleSeedDatabase = async () => {
    setIsSeeding(true);
    try {
      const res = await fetch('/api/seed-database', { method: 'POST' });
      if (res.ok) {
        await fetchDashboardData();
        alert("Database reseeded successfully with fresh supply chain data!");
      }
    } catch (err) {
      alert("Error seeding database.");
    } finally {
      setIsSeeding(false);
    }
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '0 1.5rem 3rem 1.5rem' }}>
      <Navbar 
        onOpenChat={() => setIsChatOpen(true)} 
        onSeedDatabase={handleSeedDatabase}
        isSeeding={isSeeding}
      />

      {loading ? (
        <div style={{ textAlign: 'center', padding: '5rem', color: 'var(--text-muted)' }}>
          Loading Control Tower Intelligence...
        </div>
      ) : (
        <main>
          <KPICards summary={summary} />

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

          <RecommendationsPanel 
            recommendations={recommendations} 
          />
        </main>
      )}

      <AIAssistantDrawer 
        isOpen={isChatOpen} 
        onClose={() => setIsChatOpen(false)} 
      />
    </div>
  );
}
