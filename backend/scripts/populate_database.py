#!/usr/bin/env python3
"""Industrial database population script for Wisualyst Platform.

Populates PostgreSQL with real products from data/Data.xlsx, full multi-echelon
inventory stock levels across 3 regional warehouses, historical sales records,
retail store shelf facing, open purchase orders, customers, roles, and audit logs.
"""

import sys
import os
import math
import random
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Ensure project root is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.core.database import SessionLocal, engine, Base
from backend.app.models.models import (
    ProductCategory, Product, Warehouse, Inventory, SalesHistory,
    Supplier, SupplierProduct, Customer, Order, OrderItem, PurchaseOrder,
    PurchaseOrderItem, RetailSpace, Role, WorkspaceMember, PermissionSetting, AuditLog
)

def populate_database():
    print("=======================================================")
    print("🚀 Initializing Live Database Population for PostgreSQL")
    print(f"📡 Database URL: {engine.url.render_as_string(hide_password=True)}")
    print("=======================================================")

    db = SessionLocal()
    try:
        # Step 1: Ensure all tables exist in PostgreSQL
        print("1. Creating tables if not exist...")
        Base.metadata.create_all(bind=engine)

        # Step 2: Warehouses
        wh_count = db.query(Warehouse).count()
        if wh_count == 0:
            print("2. Creating 3 Regional Logistics Warehouses...")
            wh1 = Warehouse(code="WH-UK-01", name="United Kingdom Central Logistics Hub", location="Birmingham, UK", capacity_sqft=50000)
            wh2 = Warehouse(code="WH-EU-01", name="European Mainland Fulfillment Hub", location="Frankfurt, Germany", capacity_sqft=45000)
            wh3 = Warehouse(code="WH-GLOBAL-01", name="Global Distribution & Export Center", location="Rotterdam, Netherlands", capacity_sqft=60000)
            db.add_all([wh1, wh2, wh3])
            db.commit()
            print("✓ Created 3 Warehouses.")
        else:
            print(f"2. Found {wh_count} existing Warehouses.")

        warehouses = db.query(Warehouse).all()
        wh_default = warehouses[0]

        # Step 3: Categories
        cat_count = db.query(ProductCategory).count()
        category_map = {}
        if cat_count == 0:
            print("3. Creating Product Categories...")
            categories_dict = {
                "Home Decor": "Candles, frames, wall hangings, and decorative home ornaments",
                "Storage & Organization": "Baskets, boxes, drawers, and organizational accessories",
                "Gifts & Novelties": "Occasion gifts, cards, trinkets, and novelties",
                "Kitchen & Tableware": "Mugs, teapots, cutlery, baking moulds, and tableware",
                "General Merchandise": "General retail goods, bags, toys, and apparel accessories"
            }
            for cat_name, cat_desc in categories_dict.items():
                cat = ProductCategory(name=cat_name, description=cat_desc)
                db.add(cat)
                db.commit()
                category_map[cat_name] = cat.id
            print(f"✓ Created {len(category_map)} Categories.")
        else:
            for cat in db.query(ProductCategory).all():
                category_map[cat.name] = cat.id
            print(f"3. Found {cat_count} existing Categories.")

        def categorize_product(desc: str) -> int:
            d_lower = desc.lower()
            if any(w in d_lower for w in ["frame", "heart", "candle", "holder", "light", "clock", "mirror", "sign", "wood"]):
                return category_map.get("Home Decor", 1)
            elif any(w in d_lower for w in ["box", "bag", "basket", "storage", "case", "tin", "bin", "cabinet"]):
                return category_map.get("Storage & Organization", 2)
            elif any(w in d_lower for w in ["cup", "mug", "teapot", "plate", "bowl", "cutlery", "spoon", "mould", "baking"]):
                return category_map.get("Kitchen & Tableware", 4)
            elif any(w in d_lower for w in ["card", "wrap", "ribbon", "gift", "christmas", "party", "toy"]):
                return category_map.get("Gifts & Novelties", 3)
            return category_map.get("General Merchandise", 5)

        # Step 4: Load Data.xlsx
        data_path = Path("data/Data.xlsx")
        print(f"4. Reading data from {data_path}...")
        df_raw = pd.read_excel(data_path)
        df = df_raw.copy()
        df["StockCode"] = df["StockCode"].astype(str).str.strip()
        df["Description"] = df["Description"].astype(str).str.strip()
        df = df[
            (df["Quantity"] > 0) & 
            (df["Price"] > 0) & 
            (~df["Invoice"].astype(str).str.startswith("C", na=False)) &
            (df["StockCode"] != "nan") &
            (df["Description"] != "nan") &
            (df["Description"] != "")
        ].copy()
        df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
        df["revenue"] = df["Quantity"] * df["Price"]
        print(f"✓ Processed {len(df)} cleaned transactions.")

        # Step 5: Products
        prod_count = db.query(Product).count()
        if prod_count == 0:
            print("5. Extracting and inserting products from Data.xlsx...")
            prod_stats = df.groupby("StockCode").agg(
                Description=("Description", lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0]),
                AvgPrice=("Price", "mean"),
                TotalQty=("Quantity", "sum"),
                SalesDays=("InvoiceDate", lambda x: x.dt.date.nunique()),
                LeadTime=("lead_time_days", "first") if "lead_time_days" in df.columns else ("Quantity", lambda x: 14),
                Cost=("Cost", "first") if "Cost" in df.columns else ("Price", lambda x: x.mean() * 0.6)
            ).reset_index()

            prod_batch = []
            for _, row in prod_stats.iterrows():
                sku = str(row["StockCode"])
                name = str(row["Description"])[:200]
                cat_id = categorize_product(name)
                price = round(float(row["AvgPrice"]), 2)
                cost = round(float(row["Cost"]) if pd.notna(row["Cost"]) and row["Cost"] > 0 else price * 0.6, 2)
                lead_time = int(row["LeadTime"]) if pd.notna(row["LeadTime"]) and row["LeadTime"] > 0 else 14
                
                daily_demand = max(0.5, row["TotalQty"] / max(1, row["SalesDays"]))
                std_dev = daily_demand * 0.4
                safety_stock = int(math.ceil(1.65 * std_dev * math.sqrt(lead_time)))
                reorder_point = int(math.ceil(daily_demand * lead_time + safety_stock))

                prod_batch.append({
                    "sku": sku,
                    "name": name,
                    "category_id": cat_id,
                    "unit_cost": cost,
                    "selling_price": price,
                    "lead_time_days": lead_time,
                    "safety_stock_min": max(5, safety_stock),
                    "reorder_point": max(15, reorder_point),
                    "unit": "Units"
                })

            for i in range(0, len(prod_batch), 1000):
                db.bulk_insert_mappings(Product, prod_batch[i:i + 1000])
                db.commit()
            print(f"✓ Inserted {len(prod_batch)} Products.")
        else:
            print(f"5. Found {prod_count} existing Products.")

        products = db.query(Product).all()
        product_id_map = {p.sku: p.id for p in products}

        # Step 6: Suppliers
        sup_count = db.query(Supplier).count()
        if sup_count == 0:
            print("6. Creating Suppliers...")
            suppliers_data = [
                ("SUP-001", "Evergreen Global Supply", "orders@evergreensupply.com", 4.8, 7),
                ("SUP-002", "Reliable Imports Ltd", "contact@reliableimports.com", 4.5, 12),
                ("SUP-003", "Metro Wholesale Distribution", "sales@metrowholesale.com", 4.6, 5),
                ("SUP-004", "Summit Procurement Co.", "supply@summitprocurement.com", 4.7, 10),
                ("SUP-005", "Gulf Source Logistics", "info@gulfsource.com", 4.3, 14),
            ]
            supplier_objs = []
            for code, name, email, rating, lead_time in suppliers_data:
                sup = Supplier(code=code, name=name, contact_email=email, rating=rating, lead_time_avg_days=lead_time)
                db.add(sup)
                supplier_objs.append(sup)
            db.commit()
            print(f"✓ Created {len(supplier_objs)} Suppliers.")

            # Supplier Products
            sp_batch = []
            for idx, prod in enumerate(products):
                sup = supplier_objs[idx % len(supplier_objs)]
                sp_batch.append({
                    "supplier_id": sup.id,
                    "product_id": prod.id,
                    "supplier_sku": f"SUP-{prod.sku}",
                    "unit_cost": prod.unit_cost,
                    "lead_time_days": prod.lead_time_days
                })
            for i in range(0, len(sp_batch), 1000):
                db.bulk_insert_mappings(SupplierProduct, sp_batch[i:i + 1000])
                db.commit()
            print(f"✓ Created {len(sp_batch)} SupplierProduct mappings.")
        else:
            print(f"6. Found {sup_count} existing Suppliers.")

        # Step 7: Inventory (CRITICAL TO FIX THE 0 INVENTORY ISSUE)
        inv_count = db.query(Inventory).count()
        if inv_count == 0:
            print("7. Seeding Inventory across all 3 Regional Warehouses...")
            random.seed(42)
            inv_batch = []

            for idx, prod in enumerate(products):
                for w_idx, wh in enumerate(warehouses):
                    # Realistic Operational Risk Distribution:
                    # ~8% Critical Stockout, ~12% High Risk, ~65% Healthy, ~15% Excess
                    dice = (idx * 3 + w_idx) % 100
                    if dice < 8:
                        # CRITICAL STOCKOUT
                        multiplier = random.uniform(0.1, 0.45)
                    elif dice < 20:
                        # HIGH RISK
                        multiplier = random.uniform(0.5, 0.95)
                    elif dice < 85:
                        # HEALTHY BUFFER
                        multiplier = random.uniform(1.2, 2.2)
                    else:
                        # EXCESS INVENTORY
                        multiplier = random.uniform(2.8, 4.5)

                    stock_level = max(2, int(prod.reorder_point * multiplier))
                    reserved = int(stock_level * 0.08)
                    in_transit = int(prod.reorder_point * 0.5) if multiplier < 1.0 else 0

                    inv_batch.append({
                        "product_id": prod.id,
                        "warehouse_id": wh.id,
                        "current_stock": stock_level,
                        "reserved_stock": reserved,
                        "in_transit_stock": in_transit,
                        "reorder_quantity": max(20, prod.reorder_point * 2),
                        "last_restock_date": datetime.utcnow() - timedelta(days=random.randint(1, 20))
                    })

            for i in range(0, len(inv_batch), 1000):
                db.bulk_insert_mappings(Inventory, inv_batch[i:i + 1000])
                db.commit()
            print(f"✓ Successfully seeded {len(inv_batch)} Inventory records!")
        else:
            print(f"7. Found {inv_count} existing Inventory records.")

        # Step 8: Sales History (In safe 1,000-record chunks)
        sales_count = db.query(SalesHistory).count()
        if sales_count == 0:
            print("8. Seeding SalesHistory records in 1,000-row chunks...")
            # Take recent 20,000 transactions across products
            df_sample = df.sort_values("InvoiceDate", ascending=False).head(20000)
            sales_batch = []
            for _, row in df_sample.iterrows():
                sku = str(row["StockCode"])
                p_id = product_id_map.get(sku)
                if not p_id:
                    continue
                sales_batch.append({
                    "product_id": p_id,
                    "warehouse_id": wh_default.id,
                    "date": row["InvoiceDate"].to_pydatetime(),
                    "quantity_sold": int(row["Quantity"]),
                    "unit_price": round(float(row["Price"]), 2),
                    "revenue": round(float(row["revenue"]), 2),
                    "is_promotional": 0
                })

            for i in range(0, len(sales_batch), 1000):
                db.bulk_insert_mappings(SalesHistory, sales_batch[i:i + 1000])
                db.commit()
            print(f"✓ Successfully seeded {len(sales_batch)} SalesHistory records!")
        else:
            print(f"8. Found {sales_count} existing SalesHistory records.")

        # Step 9: Retail Space (Assortment AI Module)
        space_count = db.query(RetailSpace).count()
        if space_count == 0:
            print("9. Seeding Retail Space allocations...")
            space_batch = []
            for prod in products[:600]:
                space_batch.append({
                    "store_id": "STORE-001",
                    "product_id": prod.id,
                    "category": "General Merchandise",
                    "allocated_space_sqm": round(random.uniform(0.5, 3.5), 1),
                    "display_units": random.randint(15, 80),
                    "shelf_capacity": random.randint(50, 150)
                })
            for i in range(0, len(space_batch), 1000):
                db.bulk_insert_mappings(RetailSpace, space_batch[i:i + 1000])
                db.commit()
            print(f"✓ Successfully seeded {len(space_batch)} RetailSpace records!")
        else:
            print(f"9. Found {space_count} existing RetailSpace records.")

        # Step 10: Purchase Orders
        po_count = db.query(PurchaseOrder).count()
        if po_count == 0:
            print("10. Seeding Purchase Orders...")
            pos_data = [
                ("PO-2026-8001", 1, 1, "PENDING", 4500.0, 5),
                ("PO-2026-8002", 2, 1, "ISSUED", 8200.0, 7),
                ("PO-2026-8003", 3, 2, "PENDING", 3400.0, 3),
                ("PO-2026-8004", 4, 3, "ISSUED", 12500.0, 10),
                ("PO-2026-8005", 5, 1, "PENDING", 6700.0, 6),
                ("PO-2026-8006", 1, 2, "ISSUED", 5100.0, 8),
                ("PO-2026-8007", 2, 3, "PENDING", 9300.0, 12),
                ("PO-2026-8008", 3, 1, "ISSUED", 2800.0, 4),
                ("PO-2026-8009", 4, 2, "PENDING", 7600.0, 9),
                ("PO-2026-8010", 5, 3, "ISSUED", 11200.0, 14),
            ]
            for po_num, sup_id, wh_id, status, cost, days in pos_data:
                po = PurchaseOrder(
                    po_number=po_num,
                    supplier_id=sup_id,
                    warehouse_id=wh_id,
                    status=status,
                    order_date=datetime.utcnow() - timedelta(days=random.randint(1, 8)),
                    expected_delivery_date=datetime.utcnow() + timedelta(days=days),
                    total_cost=cost
                )
                db.add(po)
            db.commit()
            print("✓ Created 10 active Purchase Orders.")
        else:
            print(f"10. Found {po_count} existing Purchase Orders.")

        # Step 11: Customers & Orders
        cust_count = db.query(Customer).count()
        if cust_count == 0:
            print("11. Seeding Customers and Customer Orders...")
            df_cust = df.dropna(subset=["Customer ID"]).copy()
            unique_cust_ids = df_cust["Customer ID"].unique()
            cust_id_map = {}
            for c_raw_id in unique_cust_ids[:200]:
                c_code = f"CUST-{int(c_raw_id)}"
                c = Customer(
                    customer_code=c_code,
                    name=f"Customer {int(c_raw_id)}",
                    email=f"customer{int(c_raw_id)}@retailer.com",
                    tier="PREMIUM" if int(c_raw_id) % 2 == 0 else "STANDARD"
                )
                db.add(c)
                db.flush()
                cust_id_map[c_raw_id] = c.id
            db.commit()

            # Orders
            invoice_groups = df_cust.groupby("Invoice")
            ord_count = 0
            for inv_code, grp in invoice_groups:
                if ord_count >= 80:
                    break
                c_raw = grp["Customer ID"].iloc[0]
                c_db_id = cust_id_map.get(c_raw)
                if not c_db_id:
                    continue
                inv_date = grp["InvoiceDate"].iloc[0].to_pydatetime()
                total_amt = float(grp["revenue"].sum())

                ord_obj = Order(
                    order_number=f"ORD-{inv_code}",
                    customer_id=c_db_id,
                    warehouse_id=wh_default.id,
                    order_date=inv_date,
                    status="DELIVERED",
                    total_amount=round(total_amt, 2)
                )
                db.add(ord_obj)
                ord_count += 1
            db.commit()
            print(f"✓ Seeded Customers and {ord_count} Orders.")
        else:
            print(f"11. Found {cust_count} existing Customers.")

        # Step 12: Roles, Workspace Members, Permissions & Audit Logs
        role_count = db.query(Role).count()
        if role_count == 0:
            print("12. Seeding Roles, Workspace Members, Permissions, and Audit Logs...")
            roles_seed = [
                ("admin", "Admin", "Full access to all features, settings, data pipelines, and user management.", "Full Access", "#7c3aed", "#f5f3ff"),
                ("de", "Data Engineer", "Manage data sources, database connectors, canonical mappings, and ETL discovery.", "Data & Engine Access", "#2563eb", "#eff6ff"),
                ("da", "Data Analyst", "Analyze inventory metrics, demand forecasts, create custom BI reports, and view insights.", "Read & Analyze", "#059669", "#ecfdf5"),
                ("om", "Operations Manager", "Monitor stockout KPIs, manage alerts, approve PO recommendations, and execute orders.", "Limited Access", "#d97706", "#fffbeb"),
                ("viewer", "Viewer", "View dashboards, alerts, and executive reports with read-only permissions.", "Read Only", "#475569", "#f1f5f9")
            ]
            for r_key, r_name, r_desc, r_scope, r_color, r_bg in roles_seed:
                db.add(Role(role_key=r_key, name=r_name, description=r_desc, scope=r_scope, scope_color=r_color, scope_bg=r_bg, author="System"))

            members_seed = [
                ("System Administrator", "admin@supplychain.internal", "Admin", "Active", "SA", "#7c3aed", "#f5f3ff"),
                ("Lead Data Engineer", "de@supplychain.internal", "Data Engineer", "Active", "DE", "#2563eb", "#eff6ff"),
                ("Senior Data Analyst", "da@supplychain.internal", "Data Analyst", "Active", "DA", "#059669", "#ecfdf5"),
                ("Operations Manager", "om@supplychain.internal", "Operations Manager", "Active", "OM", "#d97706", "#fffbeb"),
                ("System Viewer", "viewer@supplychain.internal", "Viewer", "Inactive", "SV", "#64748b", "#f1f5f9")
            ]
            for m_name, m_email, m_role, m_status, m_init, m_color, m_bg in members_seed:
                db.add(WorkspaceMember(name=m_name, email=m_email, role=m_role, status=m_status, initials=m_init, color=m_color, bg=m_bg))

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

            logs_seed = [
                ("System Administrator", "Database Connected", "Data Source", f"Seeded real database directly from Data.xlsx", "127.0.0.1"),
                ("System Administrator", "User Login", "Authentication", "User signed into Supply Chain Control Tower", "127.0.0.1"),
                ("Operations Manager", "PO Approved", "Procurement", "Dispatched Purchase Order PO-2026-8001 for SKU-10002", "127.0.0.1"),
                ("Lead Data Engineer", "Canonical Field Mapped", "Schema", "Mapped source field StockCode -> canonical field sku", "127.0.0.1"),
                ("System Auto-Engine", "100/100 Readiness Calculated", "Data Quality", "Automated pipeline validated 100/100 coverage index", "127.0.0.1")
            ]
            for l_user, l_act, l_cat, l_det, l_ip in logs_seed:
                db.add(AuditLog(user=l_user, action=l_act, type=l_cat, details=l_det, ip_address=l_ip))

            db.commit()
            print("✓ Seeded Roles, Members, Permissions, and Audit Logs.")
        else:
            print(f"12. Found {role_count} existing Roles.")

        print("=======================================================")
        print("🎉 Live Database Successfully Populated with Real Data!")
        print("=======================================================")

    except Exception as e:
        print(f"❌ Error during database population: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    populate_database()
