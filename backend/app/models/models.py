from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, Index, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from backend.app.core.database import Base

class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

# --- 1. Auth & Team Governance Models ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    company_name = Column(String(150), nullable=True)
    role = Column(String(50), default="Admin")
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    role = Column(String(50), default="Viewer")
    status = Column(String(20), default="Active")
    initials = Column(String(10), default="U")
    color = Column(String(20), default="#2563eb")
    bg = Column(String(20), default="#eff6ff")
    created_at = Column(DateTime, default=datetime.utcnow)

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    role_key = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    scope = Column(String(100), default="Full Access")
    scope_color = Column(String(20), default="#7c3aed")
    scope_bg = Column(String(20), default="#f3e8ff")
    author = Column(String(100), default="Admin")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    type = Column(String(50), default="User Action")

class PermissionSetting(Base):
    __tablename__ = "permission_settings"

    id = Column(Integer, primary_key=True, index=True)
    module_key = Column(String(50), nullable=False, unique=True)
    module_name = Column(String(150), nullable=False)
    admin_access = Column(Integer, default=1)
    de_access = Column(Integer, default=1)
    da_access = Column(Integer, default=1)
    om_access = Column(Integer, default=1)
    viewer_access = Column(Integer, default=0)

class WorkspacePipelineConfig(Base):
    __tablename__ = "workspace_pipeline_configs"

    id = Column(Integer, primary_key=True, index=True)
    workspace_key = Column(String(100), default="default", unique=True, index=True)
    workspace_name = Column(String(150), default="Global Supply Chain")
    workspace_region = Column(String(100), default="UAE / GCC Hub")
    industry_vertical = Column(String(100), default="Retail & Distribution")
    connector_type = Column(String(50), default="DIRECT_DB")
    is_connected = Column(Integer, default=0) # 1 = connected, 0 = disconnected
    host = Column(String(255), nullable=True)
    port = Column(Integer, default=5432)
    database_name = Column(String(100), nullable=True)
    username = Column(String(150), nullable=True)
    ssl_mode = Column(String(20), default="require")
    discovered_tables = Column(JSON, nullable=True)
    field_mappings = Column(JSON, nullable=True)
    active_step = Column(Integer, default=1)
    target_table = Column(String(100), default="products")
    selected_external_table = Column(String(100), nullable=True)
    last_connected_at = Column(DateTime, nullable=True)
    last_ingested_at = Column(DateTime, nullable=True)
    ingestion_status = Column(String(50), nullable=True)
    rows_ingested = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# --- 2. Core Supply Chain & Pipeline Sync Models ---
class ProductCategory(Base):
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    category_id = Column(Integer, nullable=True)
    unit = Column(String(20), default="Units")
    unit_cost = Column(Float, nullable=False, default=0.0)
    selling_price = Column(Float, nullable=False, default=0.0)
    lead_time_days = Column(Integer, nullable=False, default=7)
    safety_stock_min = Column(Integer, nullable=False, default=10)
    reorder_point = Column(Integer, nullable=False, default=20)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(150), nullable=False)
    location = Column(String(200), nullable=False)
    capacity_sqft = Column(Integer, default=50000)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False)
    warehouse_id = Column(Integer, nullable=True, default=1)
    current_stock = Column(Integer, nullable=False, default=0)
    reserved_stock = Column(Integer, default=0)
    in_transit_stock = Column(Integer, default=0)
    reorder_quantity = Column(Integer, default=50)
    last_restock_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(150), nullable=False)
    contact_email = Column(String(100), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    lead_time_avg_days = Column(Integer, default=7)
    rating = Column(Float, default=4.5)
    otif_score = Column(Float, default=92.5)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SupplierProduct(Base):
    __tablename__ = "supplier_products"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    supplier_sku = Column(String(100), nullable=True)
    moq = Column(Integer, default=1)
    unit_cost = Column(Float, nullable=False, default=0.0)
    lead_time_days = Column(Integer, default=7)
    created_at = Column(DateTime, default=datetime.utcnow)

class SalesHistory(Base):
    __tablename__ = "sales_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    warehouse_id = Column(Integer, nullable=True, index=True)
    date = Column(DateTime, nullable=False, index=True)
    quantity_sold = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    revenue = Column(Float, nullable=False)
    is_promotional = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class RetailSpace(Base):
    __tablename__ = "retail_spaces"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(50), nullable=False, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    category = Column(String(100), default="General")
    allocated_space_sqm = Column(Float, default=1.0)
    display_units = Column(Integer, default=10)
    shelf_capacity = Column(Integer, default=50)
    created_at = Column(DateTime, default=datetime.utcnow)

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    customer_code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(100), nullable=True)
    tier = Column(String(20), default="STANDARD")
    created_at = Column(DateTime, default=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), nullable=False, unique=True, index=True)
    customer_id = Column(Integer, nullable=True)
    warehouse_id = Column(Integer, nullable=True)
    order_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String(50), default="PENDING")
    total_amount = Column(Float, default=0.0)
    shipping_address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String(50), nullable=False, unique=True, index=True)
    supplier_id = Column(Integer, nullable=False)
    warehouse_id = Column(Integer, nullable=True)
    order_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String(50), default="PENDING")
    expected_delivery_date = Column(DateTime, nullable=True)
    total_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Float, nullable=False)

class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String(100), nullable=False, unique=True, index=True)
    order_id = Column(Integer, nullable=True)
    warehouse_id = Column(Integer, nullable=True)
    carrier = Column(String(100), default="Standard Express")
    status = Column(String(50), default="IN_TRANSIT")
    shipped_date = Column(DateTime, default=datetime.utcnow)
    estimated_delivery = Column(DateTime, nullable=True)

class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False)
    warehouse_id = Column(Integer, nullable=True)
    transaction_type = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False)
    reference_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class MicrosoftOAuthConnection(Base):
    __tablename__ = "microsoft_oauth_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), nullable=False, unique=True, index=True)
    user_id = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    severity = Column(String(20), default="INFO")
    timestamp = Column(DateTime, default=datetime.utcnow)

class ProductForecast(Base):
    __tablename__ = "product_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    warehouse_id = Column(Integer, default=0, index=True)
    horizon_days = Column(Integer, default=30)
    total_forecasted_demand = Column(Float, default=0.0)
    confidence_interval_pct = Column(Float, default=95.0)
    mae = Column(Float, default=0.0)
    rmse = Column(Float, default=0.0)
    forecast_data = Column(JSON, nullable=True)
    historical_points = Column(JSON, nullable=True)
    model_name = Column(String(100), default="Statistical ML / Croston Intermittent Model")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
