#!/usr/bin/env python3
import random
import math
from datetime import datetime, timedelta
from backend.app.core.database import SessionLocal, engine
from backend.app.models.models import (
    ProductCategory, Product, Warehouse, Inventory, SalesHistory,
    Supplier, SupplierProduct, RetailSpace, PurchaseOrder
)
from backend.app.services.validation_engine import DataValidationEngine
from backend.app.services.services import SupplyChainService

def seed_live_data():
    db = SessionLocal()
    print("🚀 Connecting to live database to populate missing supply chain datasets...")

    products = db.query(Product).all()
    warehouses = db.query(Warehouse).all()
    print(f"Current catalog: {len(products)} products, {len(warehouses)} warehouses.")

    if not warehouses:
        warehouses_data = [
            ("WH-UK-01", "United Kingdom Central Logistics Hub", "Birmingham, UK", 50000),
            ("WH-EU-01", "European Mainland Fulfillment Hub", "Frankfurt, Germany", 45000),
            ("WH-GLOBAL-01", "Global Distribution & Export Center", "Rotterdam, Netherlands", 60000),
        ]
        for code, name, loc, cap in warehouses_data:
            wh = Warehouse(code=code, name=name, location=loc, capacity_sqft=cap)
            db.add(wh)
        db.commit()
        warehouses = db.query(Warehouse).all()
        print(f"Created {len(warehouses)} warehouses.")

    # 1. Seed Suppliers if empty
    sup_count = db.query(Supplier).count()
    if sup_count == 0:
        print("📦 Seeding suppliers...")
        suppliers_data = [
            ("SUP-001", "Evergreen Global Supply", "orders@evergreensupply.com", 4.8, 7, 96.5),
            ("SUP-002", "Reliable Imports Ltd", "contact@reliableimports.com", 4.5, 12, 91.0),
            ("SUP-003", "Metro Wholesale Distribution", "sales@metrowholesale.com", 4.6, 5, 95.0),
            ("SUP-004", "Summit Procurement Co.", "supply@summitprocurement.com", 4.7, 10, 93.5),
            ("SUP-005", "Gulf Source Logistics", "info@gulfsource.com", 4.3, 14, 88.5),
        ]
        supplier_objs = []
        for code, name, email, rating, lead_time, otif in suppliers_data:
            sup = Supplier(
                code=code, name=name, contact_email=email,
                rating=rating, lead_time_avg_days=lead_time, otif_score=otif
            )
            db.add(sup)
            supplier_objs.append(sup)
        db.commit()
        print(f"✅ Created {len(supplier_objs)} suppliers.")

        # Seed supplier products mapping
        sp_batch = []
        for idx, p in enumerate(products):
            s = supplier_objs[idx % len(supplier_objs)]
            sp_batch.append({
                "supplier_id": s.id,
                "product_id": p.id,
                "supplier_sku": f"SUP-{p.sku}",
                "unit_cost": p.unit_cost,
                "lead_time_days": p.lead_time_days
            })
        db.bulk_insert_mappings(SupplierProduct, sp_batch)
        db.commit()
        print(f"✅ Mapped {len(sp_batch)} supplier products.")
    else:
        supplier_objs = db.query(Supplier).all()

    # 2. Seed Inventory if empty
    inv_count = db.query(Inventory).count()
    if inv_count == 0:
        print("📦 Seeding inventory records across warehouses...")
        inv_batch = []
        for idx, p in enumerate(products):
            rop = p.reorder_point or 25
            safety = p.safety_stock_min or 10

            for w_idx, wh in enumerate(warehouses):
                # Distribute risk realistically:
                # ~8% products: Critical stockout risk (stock < safety stock)
                # ~12% products: High risk (stock <= reorder point)
                # Remaining 80%: Healthy stock buffer
                if idx % 12 == 0 and w_idx == 0:
                    curr_stock = random.randint(0, max(1, safety - 1))
                elif idx % 7 == 0:
                    curr_stock = random.randint(safety, rop)
                else:
                    curr_stock = int(rop * random.uniform(1.8, 3.5))

                reserved = int(curr_stock * random.uniform(0.05, 0.15))
                inv_batch.append({
                    "product_id": p.id,
                    "warehouse_id": wh.id,
                    "current_stock": curr_stock,
                    "reserved_stock": reserved,
                    "in_transit_stock": int(rop * 0.5) if curr_stock <= rop else 0,
                    "reorder_quantity": rop * 2,
                    "last_restock_date": datetime.utcnow() - timedelta(days=random.randint(1, 20))
                })

        chunk_size = 2000
        for i in range(0, len(inv_batch), chunk_size):
            db.bulk_insert_mappings(Inventory, inv_batch[i:i + chunk_size])
            db.commit()
        print(f"✅ Seeded {len(inv_batch)} inventory records.")

    # 3. Seed Retail Spaces if empty
    space_count = db.query(RetailSpace).count()
    if space_count == 0:
        print("📦 Seeding retail space allocations...")
        space_batch = []
        for idx, p in enumerate(products):
            shelf_cap = random.choice([30, 50, 75, 100, 150])
            disp = int(shelf_cap * random.uniform(0.4, 0.95))
            space_batch.append({
                "store_id": f"STORE-{((idx % 5) + 1):02d}",
                "product_id": p.id,
                "category": p.category.name if p.category else "General",
                "allocated_space_sqm": round(random.uniform(0.5, 4.0), 2),
                "display_units": disp,
                "shelf_capacity": shelf_cap,
                "created_at": datetime.utcnow()
            })
        for i in range(0, len(space_batch), 2000):
            db.bulk_insert_mappings(RetailSpace, space_batch[i:i + 2000])
            db.commit()
        print(f"✅ Seeded {len(space_batch)} retail space records.")

    # 4. Seed Sales History if empty
    sales_count = db.query(SalesHistory).count()
    if sales_count == 0:
        print("📦 Seeding 30-day sales history...")
        sales_batch = []
        now = datetime.utcnow()
        wh_id = warehouses[0].id if warehouses else 1

        sample_products = products[:800] # Top 800 active SKUs for performance
        for p in sample_products:
            avg_daily = max(1, int(p.reorder_point / 10))
            price = p.selling_price or 19.99
            for day_offset in range(1, 31):
                if random.random() < 0.65:
                    qty = max(1, int(random.gauss(avg_daily, avg_daily * 0.4)))
                    sale_dt = now - timedelta(days=day_offset, hours=random.randint(8, 20))
                    sales_batch.append({
                        "product_id": p.id,
                        "warehouse_id": wh_id,
                        "date": sale_dt,
                        "quantity_sold": qty,
                        "unit_price": price,
                        "revenue": round(qty * price, 2),
                        "is_promotional": 1 if day_offset % 7 == 0 else 0
                    })

        for i in range(0, len(sales_batch), 2000):
            db.bulk_insert_mappings(SalesHistory, sales_batch[i:i + 2000])
            db.commit()
        print(f"✅ Seeded {len(sales_batch)} sales history records.")

    # 5. Seed Purchase Orders if empty
    po_count = db.query(PurchaseOrder).count()
    if po_count == 0:
        print("📦 Seeding sample purchase orders...")
        suppliers = db.query(Supplier).all()
        po_batch = []
        statuses = ["PENDING", "ISSUED", "PROCESSING", "SHIPPED"]
        for idx in range(1, 16):
            sup = random.choice(suppliers)
            wh = random.choice(warehouses)
            cost = round(random.uniform(5000.0, 45000.0), 2)
            po = PurchaseOrder(
                po_number=f"PO-2026-{idx:04d}",
                supplier_id=sup.id,
                warehouse_id=wh.id,
                order_date=datetime.utcnow() - timedelta(days=random.randint(1, 10)),
                expected_delivery_date=datetime.utcnow() + timedelta(days=random.randint(3, 14)),
                status=random.choice(statuses),
                total_cost=cost
            )
            db.add(po)
        db.commit()
        print("✅ Seeded 15 purchase orders.")

    # Validate readiness
    val_eng = DataValidationEngine(db)
    readiness = val_eng.evaluate_readiness()
    print("🎯 Updated Platform Readiness:")
    for k, v in readiness.get("modules", {}).items():
        print(f" - {k}: {v['readiness_pct']}% ({v['status']})")
    print(f"Overall Readiness Score: {readiness.get('overall_readiness_pct')}%")

    svc = SupplyChainService(db)
    summary = svc.get_control_tower_summary()
    print(f"Stockout Critical Lines: {summary.get('stockout_critical_count')}")
    print(f"Stockout High Risk Lines: {summary.get('stockout_high_count')}")
    print(f"Total Inventory Items: {summary.get('total_inventory_items')}")
    print(f"Total Inventory Value: ${summary.get('total_inventory_value'):,.2f}")

    db.close()
    print("🎉 Database successfully seeded with live enterprise data!")

if __name__ == "__main__":
    seed_live_data()
