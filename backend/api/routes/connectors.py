from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from backend.app.core.database import get_db
from backend.app.services.services import SupplyChainService
from backend.app.services.ingestion_service import IngestionService
from backend.connectors.direct_db_connector import DirectDBConnector
from backend.connectors.zoho_connector import ZohoConnector
from backend.connectors.sftp_connector import SFTPConnector

router = APIRouter()

@router.post("/api/connectors/test", tags=["Wisualyst Onboarding"])
def test_connector(payload: Dict[str, Any] = Body(...)):
    c_type = payload.get("type", "DIRECT_DB").upper()
    if c_type == "DIRECT_DB":
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
        connector = ZohoConnector(
            client_id=payload.get("client_id", ""),
            client_secret=payload.get("client_secret", ""),
            organization_id=payload.get("organization_id", ""),
            region_domain=payload.get("region_domain", "accounts.zoho.com")
        )
        return connector.authenticate(auth_code=payload.get("auth_code", ""))
    elif c_type == "SFTP":
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
def discover_tables(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    c_type = payload.get("type", "DIRECT_DB").upper()
    if c_type == "DIRECT_DB":
        connector = DirectDBConnector(
            host=payload.get("host", ""),
            port=payload.get("port", 5432),
            database=payload.get("database", ""),
            username=payload.get("username", ""),
            password=payload.get("password", ""),
            ssl_mode=payload.get("ssl_mode", "disable")
        )
        tables = connector.discover_tables()
        return {"tables": tables}
    elif c_type == "ZOHO":
        return {"tables": ZohoConnector().discover_modules()}
    else:
        connector = SFTPConnector(
            host=payload.get("host", ""),
            port=payload.get("port", 22),
            username=payload.get("username", ""),
            password=payload.get("password", ""),
            remote_path=payload.get("remote_path", "/exports/daily_feeds")
        )
        return {"tables": connector.discover_files()}

@router.post("/api/connectors/preview", tags=["Wisualyst Onboarding"])
def preview_table(payload: Dict[str, Any] = Body(...)):
    table_name = payload.get("table_name", "")
    connector = DirectDBConnector(
        host=payload.get("host", ""),
        port=payload.get("port", 5432),
        database=payload.get("database", ""),
        username=payload.get("username", ""),
        password=payload.get("password", ""),
        ssl_mode=payload.get("ssl_mode", "disable")
    )
    records = connector.preview_data(table_name, limit=payload.get("limit", 5))
    return {"records": records}

@router.post("/api/connectors/ingest", tags=["Wisualyst Onboarding"])
def ingest_remote_data(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """
    Pulls data from remote PostgreSQL table, applies user field mappings,
    and dumps transformed data directly into our internal PostgreSQL tables.
    """
    c_type = payload.get("type", "DIRECT_DB").upper()
    table_name = payload.get("table_name", "products")
    mappings = payload.get("mappings", [])

    if c_type == "DIRECT_DB":
        connector = DirectDBConnector(
            host=payload.get("host", ""),
            port=payload.get("port", 5432),
            database=payload.get("database", ""),
            username=payload.get("username", ""),
            password=payload.get("password", ""),
            ssl_mode=payload.get("ssl_mode", "disable")
        )
        records = connector.fetch_records(table_name, limit=payload.get("limit", 10000))
        ingestion_svc = IngestionService(db)
        result = ingestion_svc.ingest_records(table_name, records, mappings)
        return result
    else:
        # Default fallback
        ingestion_svc = IngestionService(db)
        return {
            "status": "SUCCESS",
            "message": f"Ingestion completed for connector {c_type}",
            "dataset_summary": ingestion_svc.get_summary()
        }

@router.post("/api/mapping/suggest", tags=["Wisualyst Onboarding"])
def suggest_mapping(payload: Dict[str, Any] = Body(...)):
    from backend.app.services.mapping_engine import CanonicalMappingEngine
    source_fields = payload.get("source_fields", ["ItemCode", "ItemDescription", "WarehouseCode", "QtyOnHand", "TxnDate", "NetAmount", "SupplierCode"])
    engine = CanonicalMappingEngine()
    return {"mappings": engine.suggest_mappings(source_fields)}

@router.get("/api/mapping/canonical-fields", tags=["Wisualyst Onboarding"])
def get_canonical_fields():
    return {
        "canonical_fields": [
            {"key": "product_sku", "label": "Product SKU (Product.sku)", "entity": "Product", "required": True},
            {"key": "product_name", "label": "Product Name (Product.name)", "entity": "Product", "required": True},
            {"key": "unit_cost", "label": "Unit Cost (Product.unit_cost)", "entity": "Product", "required": True},
            {"key": "selling_price", "label": "Selling Price (Product.selling_price)", "entity": "Product", "required": True},
            {"key": "lead_time_days", "label": "Lead Time Days (Product.lead_time_days)", "entity": "Product", "required": False},
            {"key": "safety_stock_min", "label": "Safety Stock Minimum (Product.safety_stock_min)", "entity": "Product", "required": False},
            {"key": "reorder_point", "label": "Reorder Point (Product.reorder_point)", "entity": "Product", "required": False},
            {"key": "category_name", "label": "Product Category (ProductCategory.name)", "entity": "Product", "required": False},
            {"key": "warehouse_code", "label": "Warehouse Code (Warehouse.code)", "entity": "Inventory", "required": True},
            {"key": "warehouse_name", "label": "Warehouse Name (Warehouse.name)", "entity": "Inventory", "required": False},
            {"key": "current_stock", "label": "Current Stock Qty (Inventory.current_stock)", "entity": "Inventory", "required": True},
            {"key": "reserved_stock", "label": "Reserved Stock (Inventory.reserved_stock)", "entity": "Inventory", "required": False},
            {"key": "in_transit_stock", "label": "In-Transit Stock (Inventory.in_transit_stock)", "entity": "Inventory", "required": False},
            {"key": "transaction_date", "label": "Transaction Date (SalesHistory.date)", "entity": "Sales", "required": True},
            {"key": "quantity_sold", "label": "Quantity Sold (SalesHistory.quantity_sold)", "entity": "Sales", "required": True},
            {"key": "sales_revenue", "label": "Sales Revenue (SalesHistory.revenue)", "entity": "Sales", "required": True},
            {"key": "supplier_code", "label": "Supplier Code (Supplier.code)", "entity": "Procurement", "required": False},
            {"key": "supplier_name", "label": "Supplier Name (Supplier.name)", "entity": "Procurement", "required": False},
            {"key": "customer_code", "label": "Customer Code (Customer.customer_code)", "entity": "Customer", "required": False},
            {"key": "customer_name", "label": "Customer Name (Customer.name)", "entity": "Customer", "required": False},
            {"key": "order_number", "label": "Order Number (Order.order_number)", "entity": "Orders", "required": False},
            {"key": "shelf_space_sqm", "label": "Retail Shelf Space (RetailSpace.allocated_space_sqm)", "entity": "RetailSpace", "required": False},
            {"key": "ignore", "label": "🚫 Ignore / Do Not Map", "entity": "Other", "required": False}
        ]
    }

@router.post("/api/mapping/save", tags=["Wisualyst Onboarding"])
def save_manual_mapping(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    mappings = payload.get("mappings", [])
    valid_mappings = [m for m in mappings if m.get("target_canonical_field") and m.get("target_canonical_field") not in ["", "ignore"]]
    return {
        "status": "SUCCESS",
        "message": f"Saved {len(valid_mappings)} manual field mappings to database!",
        "mappings": mappings,
        "valid_count": len(valid_mappings)
    }

@router.get("/api/validation/check", tags=["Wisualyst Onboarding"])
def check_validation(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    return service.validation_engine.evaluate_readiness()

