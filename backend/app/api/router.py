from fastapi import APIRouter, Depends, HTTPException, Body, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from backend.app.core.database import get_db, SessionLocal, engine, Base
from backend.app.schemas.schemas import (
    ProductResponse, WarehouseResponse, InventoryResponse, SupplierResponse,
    ForecastResponse, ControlTowerSummary, AIChatRequest, AIChatResponse, IngestionLogResponse
)
from backend.app.services.services import SupplyChainService
from backend.app.services.bi_adapter import LocalBIAdapter
from ai.forecasting.engine import StatisticalForecastEngine
from ai.risk.engine import InventoryRiskEngine
from agents.react_agent import ReActAgent
from connectors.csv_connector import CSVIngestionConnector
from connectors.mock_erp_connector import MockERPConnector
from connectors.mock_wms_connector import MockWMSConnector
from database.seeds.seed_db import seed_database

router = APIRouter()

# --- Seed Endpoint ---
@router.post("/api/seed-database", tags=["Admin"])
def run_seed_db(db: Session = Depends(get_db)):
    seed_database(db)
    return {"status": "SUCCESS", "message": "Database successfully seeded with realistic supply chain data!"}

# --- Core Entities ---
@router.get("/api/products", tags=["Catalog"])
def get_products(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    prods = service.product_repo.get_all()
    return [{
        "id": p.id,
        "sku": p.sku,
        "name": p.name,
        "category_id": p.category_id,
        "category_name": p.category.name if p.category else "Uncategorized",
        "unit": p.unit,
        "unit_cost": p.unit_cost,
        "selling_price": p.selling_price,
        "lead_time_days": p.lead_time_days,
        "safety_stock_min": p.safety_stock_min,
        "reorder_point": p.reorder_point,
        "created_at": p.created_at.isoformat() if p.created_at else None
    } for p in prods]

@router.get("/api/warehouses", tags=["Catalog"])
def get_warehouses(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    whs = service.warehouse_repo.get_all()
    return [{
        "id": w.id, "code": w.code, "name": w.name, "location": w.location, "capacity": w.capacity,
        "created_at": w.created_at.isoformat() if w.created_at else None
    } for w in whs]

@router.get("/api/inventory", tags=["Inventory"])
def get_inventory(warehouse_id: Optional[int] = None, db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    items = service.inventory_repo.get_all(warehouse_id)
    return [{
        "id": i.id,
        "product_id": i.product_id,
        "sku": i.product.sku if i.product else "",
        "product_name": i.product.name if i.product else "",
        "warehouse_id": i.warehouse_id,
        "warehouse_name": i.warehouse.name if i.warehouse else "",
        "current_stock": i.current_stock,
        "allocated_stock": i.allocated_stock,
        "available_stock": i.available_stock,
        "safety_stock": i.safety_stock,
        "unit_cost": i.product.unit_cost if i.product else 0.0,
        "total_value": round(i.current_stock * (i.product.unit_cost if i.product else 0.0), 2),
        "last_updated": i.last_updated.isoformat() if i.last_updated else None
    } for i in items]

@router.get("/api/suppliers", tags=["Suppliers"])
def get_suppliers(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    sups = service.supplier_repo.get_all()
    return [{
        "id": s.id, "code": s.code, "name": s.name, "contact_email": s.contact_email,
        "rating": s.rating, "lead_time_avg_days": s.lead_time_avg_days
    } for s in sups]

# --- AI & Analytics ---
@router.get("/api/forecast/{product_id}", response_model=ForecastResponse, tags=["AI/ML Forecast"])
def get_product_forecast(product_id: int, warehouse_id: Optional[int] = None, horizon_days: int = 30, db: Session = Depends(get_db)):
    engine = StatisticalForecastEngine(db)
    try:
        return engine.generate_forecast(product_id, warehouse_id, horizon_days)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/api/inventory-risk", tags=["AI/ML Risk Engine"])
def get_inventory_risk(warehouse_id: Optional[int] = None, risk_level: Optional[str] = None, db: Session = Depends(get_db)):
    risk_engine = InventoryRiskEngine(db)
    return risk_engine.get_all_inventory_risks(warehouse_id, risk_level)

@router.get("/api/inventory-recommendations", tags=["AI/ML Optimization"])
def get_inventory_recommendations(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    return service.get_inventory_recommendations()

@router.get("/api/control-tower", tags=["Control Tower"])
@router.get("/api/control-tower/summary", tags=["Control Tower"])
def get_control_tower_summary(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    return service.get_control_tower_summary()

# --- Wisualyst 4 Module Endpoints ---
@router.get("/api/modules/inventory", tags=["Wisualyst Modules"])
def get_module_inventory(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    return {
        "module": "Inventory AI",
        "summary": service.get_control_tower_summary(),
        "risks": service.risk_engine.get_all_inventory_risks()
    }

@router.get("/api/modules/demand", tags=["Wisualyst Modules"])
def get_module_demand(product_id: int = 1, db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    return service.forecast_engine.generate_forecast(product_id=product_id, horizon_days=30)

@router.get("/api/modules/procurement", tags=["Wisualyst Modules"])
def get_module_procurement(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    return service.procurement_engine.generate_procurement_intelligence()

@router.get("/api/modules/assortment", tags=["Wisualyst Modules"])
def get_module_assortment(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    return service.assortment_engine.generate_assortment_intelligence()

@router.get("/api/recommendations", tags=["Wisualyst Modules"])
def get_unified_recommendations(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    return service.recommendation_engine.get_unified_recommendations()

# --- Wisualyst Onboarding & Data Connection Routes ---
@router.post("/api/workspace/create", tags=["Wisualyst Onboarding"])
def create_workspace(payload: Dict[str, Any] = Body(...)):
    return {
        "status": "SUCCESS",
        "workspace_id": "ws_dubai_retail_01",
        "name": payload.get("name", "Wisualyst Enterprise Workspace"),
        "industry": payload.get("industry", "Retail & Consumer Goods"),
        "region": payload.get("region", "Global / Middle East"),
        "selected_modules": payload.get("modules", ["inventory", "demand", "procurement", "assortment"])
    }

@router.post("/api/connectors/test", tags=["Wisualyst Onboarding"])
def test_connector(payload: Dict[str, Any] = Body(...)):
    c_type = payload.get("type", "DIRECT_DB").upper()
    if c_type == "DIRECT_DB":
        from connectors.direct_db_connector import DirectDBConnector
        connector = DirectDBConnector(
            host=payload.get("host", ""),
            port=payload.get("port", 5432),
            database=payload.get("database", ""),
            username=payload.get("username", ""),
            password=payload.get("password", ""),
            ssl_mode=payload.get("ssl_mode", "disable")
        )
        return connector.test_connection()
    elif c_type == "ZOHO":
        from connectors.zoho_connector import ZohoConnector
        connector = ZohoConnector(
            client_id=payload.get("client_id", ""),
            client_secret=payload.get("client_secret", ""),
            organization_id=payload.get("organization_id", ""),
            region_domain=payload.get("region_domain", "accounts.zoho.com")
        )
        return connector.authenticate(auth_code=payload.get("auth_code", ""))
    elif c_type == "SFTP":
        from connectors.sftp_connector import SFTPConnector
        connector = SFTPConnector(
            host=payload.get("host", ""),
            port=payload.get("port", 22),
            username=payload.get("username", ""),
            password=payload.get("password", ""),
            remote_path=payload.get("remote_path", "/exports/daily_feeds")
        )
        return connector.test_connection()
    return {"status": "SUCCESS", "message": f"Connection to {c_type} validated successfully!"}

@router.post("/api/connectors/discover", tags=["Wisualyst Onboarding"])
def discover_tables(payload: Dict[str, Any] = Body(...)):
    c_type = payload.get("type", "DIRECT_DB").upper()
    if c_type == "DIRECT_DB":
        from connectors.direct_db_connector import DirectDBConnector
        connector = DirectDBConnector(
            host=payload.get("host", ""),
            port=payload.get("port", 5432),
            database=payload.get("database", ""),
            username=payload.get("username", ""),
            password=payload.get("password", "")
        )
        return {"tables": connector.discover_tables()}
    elif c_type == "ZOHO":
        from connectors.zoho_connector import ZohoConnector
        return {"tables": ZohoConnector().discover_modules()}
    else:
        from connectors.sftp_connector import SFTPConnector
        return {"tables": SFTPConnector().discover_files()}

@router.post("/api/mapping/suggest", tags=["Wisualyst Onboarding"])
def suggest_mapping(payload: Dict[str, Any] = Body(...)):
    from backend.app.services.mapping_engine import CanonicalMappingEngine
    source_fields = payload.get("source_fields", ["ItemCode", "ItemDescription", "WarehouseCode", "QtyOnHand", "TxnDate", "NetAmount", "SupplierCode"])
    engine = CanonicalMappingEngine()
    return {"mappings": engine.suggest_mappings(source_fields)}

@router.get("/api/validation/check", tags=["Wisualyst Onboarding"])
def check_validation(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    return service.validation_engine.evaluate_readiness()

@router.post("/api/workspace/launch", tags=["Wisualyst Onboarding"])
def launch_workspace():
    return {
        "status": "LAUNCHED",
        "workspace_id": "ws_dubai_retail_01",
        "message": "Workspace successfully configured and launched!"
    }

# --- MCP Server Integration ---
@router.get("/api/mcp/tools", tags=["MCP Server Integration"])
def get_mcp_tools(db: Session = Depends(get_db)):
    import os
    from mcp.tools import MCPToolRegistry
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    server_path = os.path.join(base_dir, "mcp", "server.py")
    registry = MCPToolRegistry(db)
    return {
        "status": "ONLINE",
        "mcp_version": "2024-11-05",
        "transport": "JSON-RPC stdio",
        "server_path": server_path,
        "base_dir": base_dir,
        "tools": registry.get_tool_definitions()
    }

# --- BI Integration Adapters ---
@router.get("/api/bi/export", tags=["BI Integration"])
@router.get("/api/bi/powerbi", tags=["BI Integration"])
def export_powerbi(db: Session = Depends(get_db)):
    adapter = LocalBIAdapter()
    return adapter.export_powerbi(db)

@router.get("/api/bi/qlik", tags=["BI Integration"])
def export_qlik(db: Session = Depends(get_db)):
    adapter = LocalBIAdapter()
    return adapter.export_qlik(db)

@router.get("/api/bi/google-sheets", tags=["BI Integration"])
@router.get("/api/bi/export/csv", tags=["BI Integration"])
def export_bi_csv(db: Session = Depends(get_db)):
    adapter = LocalBIAdapter()
    csv_data = adapter.export_inventory_metrics_csv(db)
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=wisualyst_bi_dataset.csv"})

# --- AI Agent Chat ---
@router.post("/api/ai/chat", response_model=AIChatResponse, tags=["AI Agent"])
def ai_chat(req: AIChatRequest, db: Session = Depends(get_db)):
    agent = ReActAgent(db)
    res = agent.process_query(req.message)
    return AIChatResponse(
        response=res["response"],
        tools_used=res["tools_used"],
        reasoning_summary=res["reasoning_summary"]
    )

# --- Ingestion & Connectors ---
@router.post("/api/ingest/csv", response_model=IngestionLogResponse, tags=["Connectors"])
async def ingest_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    csv_str = contents.decode("utf-8")
    connector = CSVIngestionConnector()
    res = connector.ingest_csv_content(csv_str, db)
    return IngestionLogResponse(
        status=res["status"],
        processed_count=res["processed_count"],
        errors=res["errors"],
        timestamp=res["logs"][-1]["timestamp"] if res["logs"] else ""
    )

@router.post("/api/ingest/erp", tags=["Connectors"])
def ingest_erp(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    connector = MockERPConnector()
    return connector.sync_erp_data(payload, db)

@router.post("/api/ingest/wms", tags=["Connectors"])
def ingest_wms(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    connector = MockWMSConnector()
    return connector.sync_wms_inventory(payload, db)

# --- Mock ERP REST Endpoints ---
@router.get("/mock-erp/products", tags=["Mock ERP External API"])
def mock_erp_products():
    return [
        {"sku": "SKU-ERP-901", "name": "Heavy Duty Solar Inverter 5kW", "unit_cost": 450.0, "selling_price": 780.0, "lead_time_days": 14},
        {"sku": "SKU-ERP-902", "name": "Lithium Storage Cell 3.2V 100Ah", "unit_cost": 35.0, "selling_price": 65.0, "lead_time_days": 10}
    ]

@router.get("/mock-erp/suppliers", tags=["Mock ERP External API"])
def mock_erp_suppliers():
    return [
        {"code": "SUP-ERP-01", "name": "SolarTech Energy Systems", "contact_email": "b2b@solartech.com", "rating": 4.7, "lead_time_days": 12}
    ]

# --- Mock WMS REST Endpoints ---
@router.get("/mock-wms/inventory", tags=["Mock WMS External API"])
def mock_wms_inventory():
    return {
        "warehouse_code": "WH-BLR-01",
        "inventory_levels": [
            {"sku": "SKU-ELEC-101", "current_stock": 12, "allocated_stock": 3},
            {"sku": "SKU-IND-201", "current_stock": 8, "allocated_stock": 2}
        ]
    }

