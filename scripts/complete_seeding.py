
#!/usr/bin/env python3
import sys
import random
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.core.database import SessionLocal
from backend.app.models.models import (
    Product, Warehouse, RetailSpace, Customer, Order,
    WorkspaceMember, PermissionSetting, AuditLog
)

def complete_seeding():
    db = SessionLocal()
    try:
        wh_default = db.query(Warehouse).first()
        products = db.query(Product).all()
        customers = db.query(Customer).all()
        
        # 1. Retail Space: ensure all 3081 products have store space
        existing_space_prod_ids = set(r[0] for r in db.query(RetailSpace.product_id).all())
        new_spaces = []
        for prod in products:
            if prod.id not in existing_space_prod_ids:
                new_spaces.append({
                    "store_id": "STORE-001",
                    "product_id": prod.id,
                    "category": "General Merchandise",
                    "allocated_space_sqm": round(random.uniform(0.5, 3.5), 1),
                    "display_units": random.randint(15, 80),
                    "shelf_capacity": random.randint(50, 150)
                })
        if new_spaces:
            for i in range(0, len(new_spaces), 1000):
                db.bulk_insert_mappings(RetailSpace, new_spaces[i:i + 1000])
                db.commit()
            print(f"✓ Added {len(new_spaces)} RetailSpace entries (total: {db.query(RetailSpace).count()})")
        else:
            print(f"✓ RetailSpace already has {len(existing_space_prod_ids)} entries")

        # 2. Orders
        ord_count = db.query(Order).count()
        if ord_count == 0 and customers:
            print(f"Seeding Orders using {len(customers)} existing customers...")
            orders = []
            for idx in range(120):
                cust = customers[idx % len(customers)]
                order_date = datetime.utcnow() - timedelta(days=random.randint(1, 45))
                orders.append(Order(
                    order_number=f"ORD-2026-{10000 + idx}",
                    customer_id=cust.id,
                    warehouse_id=wh_default.id if wh_default else 1,
                    order_date=order_date,
                    status=random.choice(["DELIVERED", "SHIPPED", "PROCESSING"]),
                    total_amount=round(random.uniform(45.0, 850.0), 2)
                ))
            db.add_all(orders)
            db.commit()
            print(f"✓ Created {len(orders)} Orders.")
        else:
            print(f"Found {ord_count} existing Orders.")

        # 3. Workspace Members
        mem_count = db.query(WorkspaceMember).count()
        if mem_count == 0:
            print("Seeding Workspace Members...")
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
            print("✓ Seeded Workspace Members.")
        else:
            print(f"Found {mem_count} existing Workspace Members.")

        # 4. Permission Settings
        perm_count = db.query(PermissionSetting).count()
        if perm_count == 0:
            print("Seeding Permission Settings...")
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
            print("✓ Seeded Permission Settings.")
        else:
            print(f"Found {perm_count} existing Permission Settings.")

        # 5. Audit Logs
        log_count = db.query(AuditLog).count()
        if log_count == 0:
            print("Seeding Audit Logs...")
            logs_seed = [
                ("System Administrator", "Database Connected", "Data Source", "Seeded real database directly from Data.xlsx", "127.0.0.1"),
                ("System Administrator", "User Login", "Authentication", "User signed into Supply Chain Control Tower", "127.0.0.1"),
                ("Operations Manager", "PO Approved", "Procurement", "Dispatched Purchase Order PO-2026-8001 for SKU-10002", "127.0.0.1"),
                ("Lead Data Engineer", "Canonical Field Mapped", "Schema", "Mapped source field StockCode -> canonical field sku", "127.0.0.1"),
                ("System Auto-Engine", "100/100 Readiness Calculated", "Data Quality", "Automated pipeline validated 100/100 coverage index", "127.0.0.1")
            ]
            for l_user, l_act, l_cat, l_det, l_ip in logs_seed:
                db.add(AuditLog(user=l_user, action=l_act, type=l_cat, details=l_det, ip_address=l_ip))
            db.commit()
            print("✓ Seeded Audit Logs.")
        else:
            print(f"Found {log_count} existing Audit Logs.")

        print("All auxiliary tables successfully verified and seeded!")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    complete_seeding()
