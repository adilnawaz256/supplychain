from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from backend.app.core.database import get_db
from backend.app.schemas.schemas import ForecastResponse, AIChatRequest, AIChatResponse
from backend.app.services.services import SupplyChainService
from backend.app.models.models import Product
from backend.ml.forecasting.engine import StatisticalForecastEngine
from backend.ml.risk.engine import InventoryRiskEngine
from backend.ml.agents.react_agent import ReActAgent

router = APIRouter()

# --- Demand Forecasting ---
@router.get("/api/forecast/{product_id}", response_model=ForecastResponse, tags=["AI/ML Forecast"])
def get_product_forecast(product_id: int, warehouse_id: Optional[int] = None, horizon_days: int = 30, db: Session = Depends(get_db)):
    engine = StatisticalForecastEngine(db)
    try:
        return engine.generate_forecast(product_id, warehouse_id, horizon_days)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

# --- Inventory Risk ---
@router.get("/api/inventory-risk", tags=["AI/ML Risk Engine"])
def get_inventory_risk(warehouse_id: Optional[int] = None, risk_level: Optional[str] = None, db: Session = Depends(get_db)):
    risk_engine = InventoryRiskEngine(db)
    return risk_engine.get_all_inventory_risks(warehouse_id, risk_level)

# --- Inventory Optimization Recommendations ---
@router.get("/api/inventory-recommendations", tags=["AI/ML Optimization"])
def get_inventory_recommendations(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    return service.get_inventory_recommendations()

# --- Wisualyst Core Modules ---
@router.get("/api/modules/inventory", tags=["Wisualyst Modules"])
def get_module_inventory(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    return {
        "module": "Inventory AI",
        "summary": service.get_control_tower_summary(),
        "risks": service.risk_engine.get_all_inventory_risks()
    }

@router.get("/api/modules/demand", tags=["Wisualyst Modules"])
def get_module_demand(product_id: Optional[int] = None, db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    if not product_id:
        first_prod = db.query(Product).first()
        product_id = first_prod.id if first_prod else 1
    return service.forecast_engine.generate_forecast(product_id=product_id, horizon_days=30)

@router.get("/api/modules/procurement", tags=["Wisualyst Modules"])
def get_module_procurement(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    return service.procurement_engine.generate_procurement_intelligence()

@router.get("/api/modules/assortment", tags=["Wisualyst Modules"])
def get_module_assortment(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    return service.assortment_engine.generate_assortment_intelligence()

# --- Advanced Analytics & Optimization Engines (5 Modules) ---
@router.get("/api/modules/pricing-optimization", tags=["Wisualyst Modules"])
@router.get("/api/modules/advance-analytics", tags=["Wisualyst Modules"])
def get_module_pricing_optimization(db: Session = Depends(get_db)):
    """Module 1: Advance Analytics (Pricing Optimization, Elasticity, Demand Pattern, Newsvendor)."""
    service = SupplyChainService(db)
    return service.get_pricing_optimization()

@router.get("/api/modules/policy-simulation", tags=["Wisualyst Modules"])
@router.get("/api/modules/inventory-policies", tags=["Wisualyst Modules"])
def get_module_policy_simulation(db: Session = Depends(get_db)):
    """Module 2: Inventory Optimization (Policy Backtesting & Simulation: min_Q, base_stock, min_max, periodic, hybrid)."""
    service = SupplyChainService(db)
    return service.get_policy_simulation()

@router.get("/api/modules/customer-ltv", tags=["Wisualyst Modules"])
@router.get("/api/modules/customer-segmentation", tags=["Wisualyst Modules"])
def get_module_customer_ltv(db: Session = Depends(get_db)):
    """Module 3: Customer Segmentation and LTV (RFM scoring, KMeans clustering, ML classification)."""
    service = SupplyChainService(db)
    return service.get_customer_ltv()

@router.get("/api/modules/market-basket", tags=["Wisualyst Modules"])
@router.get("/api/modules/cross-sell", tags=["Wisualyst Modules"])
def get_module_market_basket(db: Session = Depends(get_db)):
    """Module 4: Recommendation Algorithm (Cross-sell, Apriori Association Rules, Slow-mover bundling)."""
    service = SupplyChainService(db)
    return service.get_market_basket()

@router.get("/api/modules/trade-area", tags=["Wisualyst Modules"])
@router.get("/api/modules/store-analysis", tags=["Wisualyst Modules"])
def get_module_trade_area(db: Session = Depends(get_db)):
    """Module 5: Trade Area Modelling (Store Huff gravity analysis, catchment potential, distance decay)."""
    service = SupplyChainService(db)
    return service.get_trade_area()

# --- AI Agents & Workflow ---
@router.post("/api/agents/multi-agent-workflow/run", tags=["Multi-Agent AI Engine"])
def run_multi_agent_workflow(auto_dispatch_teams: bool = True, db: Session = Depends(get_db)):
    try:
        from backend.ml.agents.workflow import MultiAgentSupplyChainWorkflow
        workflow = MultiAgentSupplyChainWorkflow(db)
        res = workflow.execute_workflow(auto_dispatch_teams=auto_dispatch_teams)
        return {
            "status": "SUCCESS",
            "timestamp": res.timestamp,
            "total_execution_ms": res.total_execution_ms,
            "products_scanned": res.products_scanned,
            "anomalies_detected": res.anomalies_detected,
            "critical_alerts_triggered": res.critical_alerts_triggered,
            "agent_logs": [
                {
                    "agent_name": log.agent_name,
                    "action": log.action,
                    "status": log.status,
                    "execution_ms": log.execution_ms,
                    "details": log.details
                } for log in res.agent_logs
            ],
            "forecast_insights": res.forecast_insights,
            "inventory_optimizations": res.inventory_optimizations,
            "anomalies": res.anomalies,
            "summary_message": res.summary_message
        }
    except Exception as e:
        return {"status": "ERROR", "message": f"Multi-agent execution note: {e}"}

@router.post("/api/ai/chat", response_model=AIChatResponse, tags=["AI Agent"])
def ai_chat(req: AIChatRequest, db: Session = Depends(get_db)):
    agent = ReActAgent(db)
    res = agent.process_query(req.message)
    return AIChatResponse(
        response=res["response"],
        tools_used=res["tools_used"],
        reasoning_summary=res["reasoning_summary"]
    )
