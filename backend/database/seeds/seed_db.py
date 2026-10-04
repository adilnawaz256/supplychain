import os
import sys

_file_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(os.path.dirname(_file_dir))
_root_dir = os.path.dirname(_backend_dir)
for _p in [_root_dir, _backend_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import hashlib
import secrets
import random
import math
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.app.core.database import engine, Base, SessionLocal
from backend.app.models.models import (
    User, Role, WorkspaceMember, PermissionSetting, AuditLog,
    WorkspacePipelineConfig, ProductCategory, Product, Warehouse, Inventory,
    Supplier, SupplierProduct, SalesHistory, RetailSpace, Customer, Order,
    OrderItem, PurchaseOrder, PurchaseOrderItem
)

def hash_password(password: str, salt: str = None) -> str:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"{salt}${hashed}"

def seed_database(db: Session):
    print("Initializing Clean Auth, Governance & Enterprise Supply Chain Database Tables...")
    target_engine = db.bind if (db is not None and db.bind is not None) else engine
    try:
        with target_engine.connect() as conn:
            with conn.begin():
                Base.metadata.create_all(bind=conn)
    except Exception as e:
        print(f"Table creation note: {e}")

    # Wipe operational tables cleanly before re-seeding to prevent duplicates
    try:
        db.query(OrderItem).delete()
        db.query(Order).delete()
        db.query(PurchaseOrderItem).delete()
        db.query(PurchaseOrder).delete()
        db.query(RetailSpace).delete()
        db.query(SalesHistory).delete()
        db.query(Inventory).delete()
        db.query(SupplierProduct).delete()
        db.query(Supplier).delete()
        db.query(Customer).delete()
        db.query(Product).delete()
        db.query(ProductCategory).delete()
        db.query(Warehouse).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Table cleanup note: {e}")

    # 1. Seed Roles & Users if empty
    if db.query(Role).count() == 0:
        roles_seed = [
            ("admin", "Admin", "Full access to all features, settings, data pipelines, and user management.", "Full Access", "#7c3aed", "#f5f3ff"),
            ("de", "Data Engineer", "Manage data sources, database connectors, canonical mappings, and ETL discovery.", "Data & Engine Access", "#2563eb", "#eff6ff"),
            ("da", "Data Analyst", "Analyze inventory metrics, demand forecasts, create custom BI reports, and view insights.", "Read & Analyze", "#059669", "#ecfdf5"),
            ("om", "Operations Manager", "Monitor stockout KPIs, manage alerts, approve PO recommendations, and execute orders.", "Limited Access", "#d97706", "#fffbeb"),
            ("viewer", "Viewer", "View dashboards, alerts, and executive reports with read-only permissions.", "Read Only", "#475569", "#f1f5f9")
        ]
        for r_key, r_name, r_desc, r_scope, r_color, r_bg in roles_seed:
            db.add(Role(role_key=r_key, name=r_name, description=r_desc, scope=r_scope, scope_color=r_color, scope_bg=r_bg, author="System"))
        db.commit()

    if db.query(User).count() == 0:
        admin_user = User(
            email="admin@supplychain.internal",
            password_hash=hash_password("admin123"),
            full_name="System Administrator",
            company_name="Global Supply Chain Co.",
            role="Admin"
        )
        db.add(admin_user)
        db.commit()

    if db.query(WorkspaceMember).count() == 0:
        members_seed = [
            ("System Administrator", "admin@supplychain.internal", "Admin", "Active", "SA", "#7c3aed", "#f5f3ff"),
            ("Lead Data Engineer", "de@supplychain.internal", "Data Engineer", "Active", "DE", "#2563eb", "#eff6ff"),
            ("Senior Data Analyst", "da@supplychain.internal", "Data Analyst", "Active", "DA", "#059669", "#ecfdf5"),
            ("Operations Manager", "om@supplychain.internal", "Operations Manager", "Active", "OM", "#d97706", "#fffbeb"),
            ("System Viewer", "viewer@supplychain.internal", "Viewer", "Inactive", "SV", "#64748b", "#f1f5f9")
        ]
        for m_name, m_email, m_role, m_status, m_init, m_color, m_bg in members_seed:
            db.add(WorkspaceMember(name=m_name, email=m_email, role=m_role, status=m_status, initials=m_init, color=m_color, bg=m_bg))
        db.commit()

    if db.query(PermissionSetting).count() == 0:
        perms_seed = [
            ("overview", "Overview & Executive Control Tower", 1, 1, 1, 1, 1),
            ("workspaces", "Workspaces & Multi-Tenant Setup", 1, 1, 0, 0, 0),
            ("datasources", "Data Sources & Pipeline", 1, 1, 0, 0, 0),
            ("intelligence", "Intelligence & Forecasting Engines", 1, 1, 1, 1, 1),
            ("recommendations", "Prescriptive Recommendations & PO Dispatch", 1, 0, 1, 1, 0),
            ("access_control", "Access Control & Security Governance", 1, 0, 0, 0, 0)
        ]
        for p_key, p_name, p_admin, p_de, p_da, p_om, p_view in perms_seed:
            db.add(PermissionSetting(module_key=p_key, module_name=p_name, admin_access=p_admin, de_access=p_de, da_access=p_da, om_access=p_om, viewer_access=p_view))
        db.commit()

    # 2. Seed Categories
    print("Seeding Product Categories...")
    cat_names = [
        "Home & Kitchen Essentials",
        "Electronics & Mobile Accessories",
        "Apparel & Bags",
        "Health & Wellness",
        "Office & Workspace Supplies"
    ]
    categories = []
    for c_name in cat_names:
        cat = ProductCategory(name=c_name, description=f"Catalog category for {c_name}")
        db.add(cat)
        categories.append(cat)
    db.commit()
    for cat in categories:
        db.refresh(cat)

    # 3. Seed Warehouses / Retail Hubs
    print("Seeding Warehouses & Stores...")
    wh_defs = [
        ("WH-DXB-01", "Dubai Central Logistics Superhub", "Dubai Logistics City, DWC Zone", 75000),
        ("WH-AUH-02", "Abu Dhabi Coastal Fulfillment Terminal", "Mussafah Industrial Port Zone", 52000),
        ("WH-RUH-03", "Riyadh Gateway Cross-Dock Facility", "Sulay Logistic Corridor, Riyadh", 64000),
        ("WH-SHJ-04", "Sharjah Regional Distribution Center", "SAIF Industrial Zone, Sharjah", 38000)
    ]
    warehouses = []
    for code, name, loc, cap in wh_defs:
        wh = Warehouse(code=code, name=name, location=loc, capacity_sqft=cap, is_active=1)
        db.add(wh)
        warehouses.append(wh)
    db.commit()
    for wh in warehouses:
        db.refresh(wh)

    # 4. Seed Suppliers
    print("Seeding Suppliers...")
    sup_defs = [
        ("SUP-APEX", "Apex Global Manufacturing", "procurement@apex-mfg.com", "+971-4-8891000", 6, 4.8, 96.8),
        ("SUP-EMIR", "Emirates Logistics & Cargo FZE", "orders@emirateslogistics.ae", "+971-2-5542100", 8, 4.6, 94.2),
        ("SUP-PRIME", "Prime Fasteners & Components Ltd", "supply@prime-intl.com", "+971-4-3215500", 12, 4.2, 88.5),
        ("SUP-ORIENT", "Orient Pack & Container Works", "sales@orientpack.co", "+971-6-5268800", 5, 4.7, 95.1),
        ("SUP-HORIZON", "Horizon Trade Network", "contact@horizontrade.ae", "+971-4-9988112", 14, 3.9, 81.4)
    ]
    suppliers = []
    for code, name, email, phone, lead_t, rating, otif in sup_defs:
        sup = Supplier(code=code, name=name, contact_email=email, contact_phone=phone, lead_time_avg_days=lead_t, rating=rating, otif_score=otif)
        db.add(sup)
        suppliers.append(sup)
    db.commit()
    for sup in suppliers:
        db.refresh(sup)

    # 5. Seed Enterprise Products Catalog (20 items across categories)
    print("Seeding Enterprise Product Catalog...")
    product_defs = [
        # Cat 0: Home & Kitchen
        ("SKU-HK-001", "Eco-Friendly Bamboo Cutlery Set", 0, 4.50, 12.99, 7, 25, 60),
        ("SKU-HK-002", "Insulated Stainless Steel Flask 750ml", 0, 8.20, 24.50, 10, 30, 80),
        ("SKU-HK-003", "Modular Glass Food Storage Containers (Set of 4)", 0, 11.40, 29.99, 12, 20, 50),
        ("SKU-HK-004", "Silicone Oven Baking Mat Duo", 0, 3.10, 9.99, 5, 40, 100),
        # Cat 1: Electronics
        ("SKU-EL-101", "Fast Charge USB-C Braided Cable 2M", 1, 2.20, 8.99, 5, 50, 150),
        ("SKU-EL-102", "Wireless Qi Charging Pad 15W", 1, 7.80, 22.50, 8, 30, 75),
        ("SKU-EL-103", "Noise Cancelling Ergonomic Earbuds Pro", 1, 28.50, 69.99, 14, 15, 45),
        ("SKU-EL-104", "Multi-Port Travel Adapter 65W GaN", 1, 14.60, 36.00, 10, 25, 70),
        # Cat 2: Apparel & Bags
        ("SKU-AP-201", "Water-Resistant Commuter Backpack 25L", 2, 16.80, 48.00, 14, 20, 60),
        ("SKU-AP-202", "Lightweight Canvas Tote Bag", 2, 2.80, 8.50, 6, 60, 180),
        ("SKU-AP-203", "Compact Travel Packing Cubes (6-Pack)", 2, 6.40, 19.99, 8, 35, 90),
        ("SKU-AP-204", "Thermal Merino Blend Socks (3-Pack)", 2, 4.90, 14.50, 7, 30, 85),
        # Cat 3: Health & Wellness
        ("SKU-HW-301", "Natural Botanical Hydrating Mist 150ml", 3, 5.20, 16.00, 9, 25, 65),
        ("SKU-HW-302", "Organic Cold-Pressed Argan Hair Serum", 3, 9.10, 26.50, 11, 20, 55),
        ("SKU-HW-303", "Aromatherapy Ultrasonic Diffuser", 3, 13.50, 38.00, 12, 15, 40),
        ("SKU-HW-304", "Natural Lavender Sleep Pillow Spray", 3, 4.10, 12.50, 6, 30, 80),
        # Cat 4: Office Supplies
        ("SKU-OF-401", "Hardcover Bullet Grid Journal A5", 4, 3.80, 11.99, 7, 40, 110),
        ("SKU-OF-402", "Aluminum Laptop Cooling Riser Stand", 4, 12.00, 32.50, 10, 20, 50),
        ("SKU-OF-403", "Gel Roller Ink Pens 0.5mm (Box of 12)", 4, 2.50, 7.99, 5, 60, 160),
        ("SKU-OF-404", "Desk Organizer Vegan Leather Mat 80x40cm", 4, 8.90, 24.00, 8, 25, 70)
    ]

    products = []
    for sku, name, cat_idx, cost, price, lead_d, ss, rop in product_defs:
        c_id = categories[cat_idx].id if cat_idx < len(categories) else None
        p = Product(
            sku=sku,
            name=name,
            category_id=c_id,
            unit="Units",
            unit_cost=cost,
            selling_price=price,
            lead_time_days=lead_d,
            safety_stock_min=ss,
            reorder_point=rop
        )
        db.add(p)
        products.append(p)
    db.commit()
    for p in products:
        db.refresh(p)

    # 6. Seed Supplier-Product Associations
    print("Linking Products to Suppliers...")
    for idx, p in enumerate(products):
        primary_sup = suppliers[idx % len(suppliers)]
        sp = SupplierProduct(
            supplier_id=primary_sup.id,
            product_id=p.id,
            supplier_sku=f"VEND-{p.sku}",
            moq=max(10, p.reorder_point // 2),
            unit_cost=p.unit_cost,
            lead_time_days=primary_sup.lead_time_avg_days
        )
        db.add(sp)
    db.commit()

    # 7. Seed Multi-Warehouse Inventory (Varied stock levels: Critical, Optimal, Excess)
    print("Seeding Multi-Warehouse Inventory Records...")
    for p_idx, p in enumerate(products):
        for wh_idx, wh in enumerate(warehouses):
            # Introduce controlled variability for stockout risk testing
            if p_idx % 6 == 0 and wh_idx == 0:
                # Stockout risk (Current stock below safety stock)
                current_stk = max(2, int(p.safety_stock_min * 0.4))
                reserved = max(1, int(current_stk * 0.5))
            elif p_idx % 5 == 1 and wh_idx == 1:
                # Excess inventory (high stock)
                current_stk = int(p.reorder_point * 3.5)
                reserved = 10
            else:
                # Healthy operational stock
                current_stk = int(p.reorder_point * (1.2 + 0.3 * (wh_idx % 3)))
                reserved = int(current_stk * 0.15)

            inv = Inventory(
                product_id=p.id,
                warehouse_id=wh.id,
                current_stock=current_stk,
                reserved_stock=reserved,
                in_transit_stock=int(p.reorder_point * 0.5) if (p_idx + wh_idx) % 2 == 0 else 0,
                reorder_quantity=p.reorder_point * 2,
                last_restock_date=datetime.utcnow() - timedelta(days=wh_idx * 4 + 2)
            )
            db.add(inv)
    db.commit()

    # 8. Seed Retail Spaces (for GMROI, Assortment AI & Space Productivity)
    print("Seeding Retail Shelf Spaces...")
    cat_map = {c.id: c.name for c in categories}
    for idx, p in enumerate(products):
        store_id = warehouses[idx % len(warehouses)].code
        cat_name = cat_map.get(p.category_id, "General")
        sqm = round(1.2 + (idx % 4) * 0.6, 2)
        disp_units = int(15 + (idx * 7) % 45)
        shelf_c = disp_units + 20
        rs = RetailSpace(
            store_id=store_id,
            product_id=p.id,
            category=cat_name,
            allocated_space_sqm=sqm,
            display_units=disp_units,
            shelf_capacity=shelf_c
        )
        db.add(rs)
    db.commit()

    # 9. Seed Customers (16 diverse customers across enterprise, wholesale, retail tiers)
    print("Seeding Customer Base...")
    customer_defs = [
        ("CUST-ENT-001", "Al Futtaim Retail Group", "procurement@alfuttaim-sample.ae", "ENTERPRISE"),
        ("CUST-ENT-002", "Sharaf DG Commercial Supplies", "b2b@sharafdg-sample.ae", "ENTERPRISE"),
        ("CUST-WHOLE-003", "Gulf Star Hospitality Distribution", "purchasing@gulfstar-sample.com", "WHOLESALE"),
        ("CUST-WHOLE-004", "Emirates Corporate Gifting Ltd", "orders@ecg-sample.ae", "WHOLESALE"),
        ("CUST-VIP-005", "Khalid Al Mansoori Trading", "km@mansoori-sample.ae", "VIP"),
        ("CUST-VIP-006", "Fatima Al Zahra Concept Store", "fz@zahra-sample.com", "VIP"),
        ("CUST-VIP-007", "Apex Tech Solutions Dubai", "inventory@apextech-sample.ae", "VIP"),
        ("CUST-STD-008", "Yas Island Boutique Resort", "supplies@yasboutique-sample.ae", "STANDARD"),
        ("CUST-STD-009", "Downtown Fitness & Wellness Center", "frontdesk@dtfit-sample.com", "STANDARD"),
        ("CUST-STD-010", "Deira Waterfront Market Co.", "supply@deirawm-sample.ae", "STANDARD"),
        ("CUST-STD-011", "Jumeirah Café & Roastery", "beans@jumeirahcafe-sample.ae", "STANDARD"),
        ("CUST-STD-012", "Sharjah University Bookstore", "bookstore@shjuniv-sample.edu", "STANDARD"),
        ("CUST-STD-013", "Marina Bay Coworking Spaces", "ops@marinabay-sample.io", "STANDARD"),
        ("CUST-STD-014", "Palm Leisure Club & Spa", "spa@palmleisure-sample.com", "STANDARD"),
        ("CUST-STD-015", "Oasis Green Grocery & Health", "purchasing@oasisgreen-sample.ae", "STANDARD"),
        ("CUST-STD-016", "Barsha Business Centers FZ", "admin@barshabiz-sample.ae", "STANDARD")
    ]
    customers = []
    for c_code, c_name, c_email, c_tier in customer_defs:
        cust = Customer(customer_code=c_code, name=c_name, email=c_email, tier=c_tier)
        db.add(cust)
        customers.append(cust)
    db.commit()
    for cust in customers:
        db.refresh(cust)

    # 10. Seed Realistic 90-Day Daily Sales History
    # Produces authentic SBC demand pattern clustering: Smooth, Intermittent, Erratic, and Lumpy
    print("Generating 90-Day Daily Sales Transactions...")
    now = datetime.utcnow()
    sales_batch = []

    for p_idx, p in enumerate(products):
        # Assign pattern type based on product index
        # 0..7: Smooth (daily regular demand)
        # 8..12: Intermittent (orders every few days, steady quantities)
        # 13..16: Erratic (frequent orders, highly variable sizes)
        # 17..19: Lumpy (infrequent, spiky orders)
        if p_idx < 8:
            pattern = "smooth"
        elif p_idx < 13:
            pattern = "intermittent"
        elif p_idx < 17:
            pattern = "erratic"
        else:
            pattern = "lumpy"

        base_qty = max(2, int(p.reorder_point // max(1, p.lead_time_days)))

        for d in range(90, 0, -1):
            sale_date = now - timedelta(days=d)
            wh = warehouses[(p_idx + d) % len(warehouses)]

            # Decide if sale occurs on this day
            if pattern == "smooth":
                has_sale = (d % 1 == 0) # Everyday
                qty = max(1, int(random.gauss(base_qty, max(0.5, base_qty * 0.15))))
            elif pattern == "intermittent":
                has_sale = (d % 3 == 0) # Every 3 days
                qty = max(2, int(random.gauss(base_qty * 2.5, max(0.5, base_qty * 0.2))))
            elif pattern == "erratic":
                has_sale = (d % 2 == 0) # Frequent
                qty = max(1, int(random.expovariate(1.0 / (base_qty * 2.0))))
            else: # lumpy
                has_sale = (d % 7 == 0) # Rare
                qty = max(3, int(random.expovariate(1.0 / (base_qty * 3.5))))

            if has_sale:
                price = p.selling_price
                rev = round(qty * price, 2)
                sales_batch.append(SalesHistory(
                    product_id=p.id,
                    warehouse_id=wh.id,
                    date=sale_date,
                    quantity_sold=qty,
                    unit_price=price,
                    revenue=rev,
                    is_promotional=1 if (d % 15 == 0) else 0
                ))

    # Bulk insert sales in chunks of 500
    for chunk_start in range(0, len(sales_batch), 500):
        db.bulk_save_objects(sales_batch[chunk_start:chunk_start + 500])
        db.commit()

    # 11. Seed Orders & Multi-Item Order Baskets (For Cross-Sell Apriori Association Rules)
    print("Seeding Multi-Item Customer Orders & Baskets...")
    # Curated companion pairs that naturally bundle together:
    # Cutlery (0) & Flask (1)
    # Cable (4) & Wireless Charger (5) & Earbuds (6)
    # Backpack (8) & Packing Cubes (10)
    # Botanical Mist (12) & Argan Serum (13) & Pillow Spray (15)
    # Bullet Journal (16) & Gel Pens (18) & Laptop Stand (17)
    natural_pairs = [
        (0, 1), (4, 5), (5, 6), (8, 10), (12, 13), (12, 15), (16, 18), (17, 19), (0, 3)
    ]

    orders_count = 60
    for o_idx in range(orders_count):
        cust = customers[o_idx % len(customers)]
        wh = warehouses[o_idx % len(warehouses)]
        o_date = now - timedelta(days=int((orders_count - o_idx) * 1.4))

        ord_obj = Order(
            order_number=f"ORD-2026-{1000 + o_idx}",
            customer_id=cust.id,
            warehouse_id=wh.id,
            order_date=o_date,
            status="DELIVERED" if o_idx < 50 else "PROCESSING",
            total_amount=0.0,
            shipping_address=f"Commercial District Gate {o_idx % 8 + 1}, {wh.location}"
        )
        db.add(ord_obj)
        db.flush()

        # Build basket items
        basket_pids = set()
        # Include a natural co-occurrence pair
        pair = natural_pairs[o_idx % len(natural_pairs)]
        basket_pids.add(products[pair[0]].id)
        basket_pids.add(products[pair[1]].id)

        # Maybe add a third companion item
        if o_idx % 2 == 0:
            extra_pid = products[(pair[0] + 2) % len(products)].id
            basket_pids.add(extra_pid)

        order_total = 0.0
        for pid in basket_pids:
            prod_ref = next(p for p in products if p.id == pid)
            item_qty = random.randint(1, 4) if cust.tier in ["VIP", "WHOLESALE", "ENTERPRISE"] else random.randint(1, 2)
            item_total = round(item_qty * prod_ref.selling_price, 2)
            order_total += item_total

            item = OrderItem(
                order_id=ord_obj.id,
                product_id=prod_ref.id,
                quantity=item_qty,
                unit_price=prod_ref.selling_price,
                total_price=item_total
            )
            db.add(item)

        ord_obj.total_amount = round(order_total, 2)

    db.commit()

    # 12. Seed Purchase Orders (For Procurement EOQ & PO Dispatch Tracking)
    print("Seeding Purchase Orders...")
    for po_idx in range(6):
        sup = suppliers[po_idx % len(suppliers)]
        wh = warehouses[po_idx % len(warehouses)]
        po = PurchaseOrder(
            po_number=f"PO-SUP-2026-{500 + po_idx}",
            supplier_id=sup.id,
            warehouse_id=wh.id,
            order_date=now - timedelta(days=po_idx * 3 + 1),
            status="PENDING" if po_idx < 3 else "ISSUED",
            expected_delivery_date=now + timedelta(days=sup.lead_time_avg_days - po_idx),
            total_cost=0.0
        )
        db.add(po)
        db.flush()

        po_tot = 0.0
        for item_idx in range(2):
            prod = products[(po_idx * 2 + item_idx) % len(products)]
            qty = prod.reorder_point * 2
            cost = round(qty * prod.unit_cost, 2)
            po_tot += cost
            po_item = PurchaseOrderItem(
                purchase_order_id=po.id,
                product_id=prod.id,
                quantity=qty,
                unit_cost=prod.unit_cost
            )
            db.add(po_item)
        po.total_cost = round(po_tot, 2)
    db.commit()

    # 13. Update Workspace Pipeline Config to Live Synced State
    cfg = db.query(WorkspacePipelineConfig).filter(WorkspacePipelineConfig.workspace_key == "default").first()
    if not cfg:
        cfg = WorkspacePipelineConfig(workspace_key="default")
        db.add(cfg)
    
    cfg.is_connected = 1
    cfg.connector_type = "DIRECT_DB"
    cfg.active_step = 4
    cfg.rows_ingested = len(products)
    cfg.ingestion_status = "LIVE_SYNCED"
    cfg.last_connected_at = datetime.utcnow()
    cfg.last_ingested_at = datetime.utcnow()
    db.commit()

    print(f"✅ Enterprise supply chain dataset seeded successfully: {len(products)} products, {len(sales_batch)} sales transactions, {orders_count} orders, {len(warehouses)} warehouses, {len(suppliers)} suppliers!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

