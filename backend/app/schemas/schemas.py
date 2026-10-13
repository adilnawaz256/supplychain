from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    sku: str
    name: str
    category_id: int
    unit: str = "Units"
    unit_cost: float
    selling_price: float
    lead_time_days: int = 7
    safety_stock_min: int = 10
    reorder_point: int = 20

class ProductResponse(ProductBase):
    id: int
    category_name: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class WarehouseBase(BaseModel):
    code: str
    name: str
    location: str
    capacity: int = 10000

class WarehouseResponse(WarehouseBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class InventoryResponse(BaseModel):
    id: int
    product_id: int
    sku: str
    product_name: str
    warehouse_id: int
    warehouse_name: str
    current_stock: int
    allocated_stock: int
    available_stock: int
    safety_stock: int
    unit_cost: float
    total_value: float
    last_updated: datetime
    class Config:
        from_attributes = True

class SalesHistoryResponse(BaseModel):
    id: int
    product_id: int
    sku: str
    warehouse_id: int
    date: datetime
    quantity_sold: int
    revenue: float
    class Config:
        from_attributes = True

class SupplierResponse(BaseModel):
    id: int
    code: str
    name: str
    contact_email: Optional[str] = None
    rating: float
    lead_time_avg_days: int
    class Config:
        from_attributes = True

class ForecastPoint(BaseModel):
    date: str
    forecasted_demand: float
    lower_bound: float
    upper_bound: float

class ForecastResponse(BaseModel):
    product_id: int
    sku: Optional[str] = None
    product_name: Optional[str] = None
    warehouse_id: int
    warehouse_name: Optional[str] = None
    horizon_days: int
    total_forecasted_demand: Optional[float] = None
    confidence_interval_pct: float = 95.0
    mae: Optional[float] = None
    rmse: Optional[float] = None
    forecast_data: List[ForecastPoint]
    historical_points: Optional[List[Dict[str, Any]]] = None
    model_name: Optional[str] = None
    accuracy_pct: Optional[float] = None
    database_info: Optional[Dict[str, Any]] = None
    calculation_trace: Optional[Dict[str, Any]] = None


class RiskAssessment(BaseModel):
    product_id: int
    sku: str
    product_name: str
    warehouse_id: int
    warehouse_name: str
    current_stock: int
    allocated_stock: int
    available_stock: int
    avg_daily_demand: float
    forecast_7d_demand: float
    lead_time_days: int
    safety_stock: int
    reorder_point: int
    days_of_inventory: float
    stockout_risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    reasoning: str
    recommended_order_quantity: int
    supplier_name: Optional[str] = None

class ControlTowerSummary(BaseModel):
    total_products: int
    total_warehouses: int
    total_inventory_items: int
    total_inventory_value: float
    stockout_critical_count: int
    stockout_high_count: int
    excess_inventory_count: int
    open_purchase_orders: int
    recent_sales_30d_revenue: float
    top_risk_products: List[RiskAssessment]

class AIChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class AIChatResponse(BaseModel):
    response: str
    tools_used: List[str] = []
    reasoning_summary: Optional[str] = None

class IngestionLogResponse(BaseModel):
    status: str
    processed_count: int
    errors: List[str]
    timestamp: str
