import random
import sys
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.app.core.database import engine, Base, SessionLocal
from backend.app.models.models import (
    ProductCategory, Product, Warehouse, Inventory, SalesHistory,
    Supplier, SupplierProduct, Customer, Order, OrderItem, PurchaseOrder,
    PurchaseOrderItem, Shipment
)

def seed_database(db: Session):
    print("Initializing Database Tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")

    # 1. Product Categories
    categories_data = [
        ("Electronics & Gadgets", "Consumer electronics, chips, smart devices"),
        ("Industrial Machinery & Parts", "Pumps, valves, gears, bearings"),
        ("Fast Moving Consumer Goods", "Packaged goods, beverages, home care"),
        ("Apparel & Footwear", "Clothing, shoes, protective gear"),
        ("Pharmaceuticals & Health", "Medical supplies, OTC medicine, wellness"),
    ]
    category_objs = []
    for name, desc in categories_data:
        cat = ProductCategory(name=name, description=desc)
        db.add(cat)
        category_objs.append(cat)
    db.commit()

    # 2. Warehouses
    warehouses_data = [
        ("WH-BLR-01", "Bangalore Distribution Hub", "Bangalore, Karnataka", 25000),
        ("WH-BOM-01", "Mumbai Mega Logistics Park", "Bhiwandi, Maharashtra", 40000),
        ("WH-DEL-01", "Delhi NCR Fulfillment Center", "Gurugram, Haryana", 30000),
    ]
    warehouse_objs = []
    for code, name, loc, cap in warehouses_data:
        wh = Warehouse(code=code, name=name, location=loc, capacity=cap)
        db.add(wh)
        warehouse_objs.append(wh)
    db.commit()

    # 3. Suppliers
    suppliers_data = [
        ("SUP-001", "Apex Electronics Ltd", "orders@apexelectronics.com", 4.8, 5),
        ("SUP-002", "Bharat Heavy Components", "supply@bharatcomponents.in", 4.2, 14),
        ("SUP-003", "Global FMCG Suppliers", "contact@globalfmcg.com", 4.6, 3),
        ("SUP-004", "Vanguard Pharma Corp", "logistics@vanguardpharma.com", 4.9, 7),
        ("SUP-005", "TexStyle Industries", "sales@texstyle.com", 3.9, 10),
    ]
    supplier_objs = []
    for code, name, email, rating, lead_time in suppliers_data:
        sup = Supplier(code=code, name=name, contact_email=email, rating=rating, lead_time_avg_days=lead_time)
        db.add(sup)
        supplier_objs.append(sup)
    db.commit()

    # 4. 50+ Products
    product_templates = [
        # Electronics (Category 1)
        ("SKU-ELEC-101", "Smart IoT Sensor Node v2", 1, 45.0, 85.0, 7, 20, 50),
        ("SKU-ELEC-102", "Industrial Microcontroller Chipset", 1, 12.0, 28.0, 14, 100, 250),
        ("SKU-ELEC-103", "LiFePO4 Power Storage Module 12V", 1, 120.0, 220.0, 10, 15, 35),
        ("SKU-ELEC-104", "High-Gain Wi-Fi Antenna Array", 1, 18.0, 39.0, 5, 40, 90),
        ("SKU-ELEC-105", "Embedded Edge AI Accelerator Card", 1, 210.0, 380.0, 12, 10, 25),
        ("SKU-ELEC-106", "Optical Pulse Scanner Lens", 1, 35.0, 70.0, 8, 30, 75),
        ("SKU-ELEC-107", "Rugged Tablet 10-inch Display", 1, 280.0, 490.0, 15, 8, 20),
        ("SKU-ELEC-108", "Wireless Telemetry Gateway", 1, 95.0, 175.0, 7, 15, 40),
        ("SKU-ELEC-109", "Thermal Camera Inspection Module", 1, 340.0, 620.0, 20, 5, 12),
        ("SKU-ELEC-110", "Digital Multimeter Calibration Kit", 1, 65.0, 125.0, 6, 25, 60),

        # Industrial (Category 2)
        ("SKU-IND-201", "High-Pressure Hydraulic Valve 3/4in", 2, 85.0, 160.0, 14, 25, 60),
        ("SKU-IND-202", "Stainless Steel Ball Bearing 6204", 2, 5.5, 14.0, 7, 200, 500),
        ("SKU-IND-203", "Heavy Duty Centrifugal Water Pump", 2, 450.0, 890.0, 21, 5, 15),
        ("SKU-IND-204", "Pneumatic Cylinder 50mm Stroke", 2, 60.0, 115.0, 10, 15, 40),
        ("SKU-IND-205", "Precision Servo Motor 750W", 2, 220.0, 410.0, 18, 10, 25),
        ("SKU-IND-206", "Industrial Timing Belt HTD 8M", 2, 14.0, 32.0, 5, 80, 180),
        ("SKU-IND-207", "Pressure Relief Valve 100 PSI", 2, 42.0, 88.0, 8, 30, 70),
        ("SKU-IND-208", "Cast Iron Pipe Flange 4in", 2, 28.0, 58.0, 12, 50, 120),
        ("SKU-IND-209", "Linear Motion Guide Rail 1000mm", 2, 110.0, 210.0, 15, 12, 30),
        ("SKU-IND-210", "Synthetic Gear Lubricant 20L", 2, 75.0, 140.0, 4, 20, 45),

        # FMCG (Category 3)
        ("SKU-FMCG-301", "Organic Green Tea Pack 250g", 3, 3.2, 7.5, 3, 300, 700),
        ("SKU-FMCG-302", "Disinfectant Surface Cleaner 5L", 3, 8.5, 18.0, 4, 150, 400),
        ("SKU-FMCG-303", "Whole Wheat Flour 10kg Bag", 3, 6.0, 11.5, 2, 400, 1000),
        ("SKU-FMCG-304", "Extra Virgin Olive Oil 1L", 3, 9.0, 19.5, 5, 120, 300),
        ("SKU-FMCG-305", "Roasted Almonds Snack 500g", 3, 5.5, 12.0, 4, 200, 500),
        ("SKU-FMCG-306", "Biodegradable Paper Towels 12pk", 3, 7.0, 14.5, 3, 250, 600),
        ("SKU-FMCG-307", "Natural Mineral Water Case 24x500ml", 3, 4.0, 9.0, 2, 500, 1200),
        ("SKU-FMCG-308", "Dark Chocolate Bars 70% 100g", 3, 2.1, 4.8, 4, 350, 800),
        ("SKU-FMCG-309", "Instant Arabica Coffee Powder 200g", 3, 4.8, 10.5, 3, 220, 550),
        ("SKU-FMCG-310", "Eco Dishwashing Liquid 1L", 3, 3.5, 7.8, 3, 180, 450),

        # Apparel (Category 4)
        ("SKU-APP-401", "High-Visibility Safety Vest XL", 4, 6.5, 15.0, 6, 100, 250),
        ("SKU-APP-402", "Steel-Toe Industrial Work Boots", 4, 38.0, 85.0, 10, 30, 80),
        ("SKU-APP-403", "Breathable Cotton Polo Shirt (Navy)", 4, 9.0, 22.0, 8, 80, 200),
        ("SKU-APP-404", "Heavy Denim Overalls (Large)", 4, 24.0, 54.0, 12, 25, 60),
        ("SKU-APP-405", "Thermal Insulated Work Gloves (Pair)", 4, 4.2, 10.5, 4, 150, 400),
        ("SKU-APP-406", "Waterproof Rain Jacket (Medium)", 4, 28.0, 65.0, 9, 35, 90),
        ("SKU-APP-407", "Ergonomic Back Support Belt", 4, 16.0, 38.0, 7, 40, 100),
        ("SKU-APP-408", "Anti-Static Cleanroom Coverall", 4, 32.0, 72.0, 14, 20, 50),
        ("SKU-APP-409", "UV Protective Sun Hat", 4, 5.0, 12.0, 5, 60, 150),
        ("SKU-APP-410", "Compression Support Socks (L)", 4, 7.5, 18.0, 6, 90, 220),

        # Pharma & Health (Category 5)
        ("SKU-PHA-501", "Paracetamol 500mg Tablets (100s)", 5, 2.5, 6.0, 3, 500, 1500),
        ("SKU-PHA-502", "N95 Respirator Masks Box of 50", 5, 12.0, 28.0, 5, 200, 600),
        ("SKU-PHA-503", "Digital Infrared Forehead Thermometer", 5, 18.0, 42.0, 7, 50, 130),
        ("SKU-PHA-504", "Hand Sanitizer Gel 500ml", 5, 2.8, 6.5, 3, 400, 1000),
        ("SKU-PHA-505", "Vitamin C 1000mg Effervescent (20s)", 5, 3.8, 8.9, 4, 300, 800),
        ("SKU-PHA-506", "Automated Blood Pressure Monitor", 5, 28.0, 64.0, 8, 30, 75),
        ("SKU-PHA-507", "Sterile Surgical Gauze Roll 10cm", 5, 1.8, 4.2, 4, 350, 900),
        ("SKU-PHA-508", "Medical Nitrile Gloves Box of 100", 5, 7.2, 16.5, 5, 250, 700),
        ("SKU-PHA-509", "Pulse Oximeter Fingertip Monitor", 5, 15.0, 34.0, 6, 60, 150),
        ("SKU-PHA-510", "First Aid Emergency Kit Premium", 5, 22.0, 49.0, 7, 40, 110),
    ]

    product_objs = []
    for sku, name, cat_id, cost, price, lead_time, ss, rop in product_templates:
        prod = Product(
            sku=sku, name=name, category_id=cat_id,
            unit_cost=cost, selling_price=price,
            lead_time_days=lead_time, safety_stock_min=ss, reorder_point=rop
        )
        db.add(prod)
        product_objs.append(prod)
    db.commit()

    # 5. Supplier Product Mappings
    for i, prod in enumerate(product_objs):
        # Map each product to at least one primary supplier
        sup = supplier_objs[i % len(supplier_objs)]
        sp = SupplierProduct(
            supplier_id=sup.id,
            product_id=prod.id,
            supplier_sku=f"SUP-SKU-{prod.sku}",
            contracted_price=prod.unit_cost * 0.95,
            lead_time_days=prod.lead_time_days
        )
        db.add(sp)
    db.commit()

    # 6. Inventory Records with Intended Risk Scenarios across Warehouses
    print("Generating Inventory Levels across Warehouses...")
    for prod in product_objs:
        for wh in warehouse_objs:
            # Intentionally create diverse scenarios:
            # 1. Critical Stockout Risk: High demand fast movers in BLR with stock < 2 days
            if prod.sku in ["SKU-ELEC-101", "SKU-IND-201", "SKU-PHA-501"] and wh.code == "WH-BLR-01":
                curr = random.randint(5, 18)  # Critical low stock vs reorder point (50+)
                alloc = random.randint(2, 5)
            # 2. High Risk: Stock near reorder point
            elif prod.sku in ["SKU-ELEC-102", "SKU-FMCG-301", "SKU-APP-402"] and wh.code == "WH-BOM-01":
                curr = prod.reorder_point + random.randint(-5, 5)
                alloc = random.randint(5, 10)
            # 3. Overstock / Low Risk: Stock > 5x Max Capacity/Reorder Point
            elif prod.sku in ["SKU-FMCG-303", "SKU-IND-202", "SKU-APP-405"] and wh.code == "WH-DEL-01":
                curr = prod.reorder_point * 10
                alloc = 15
            # 4. Normal / Medium Risk
            else:
                curr = prod.reorder_point * random.randint(2, 5)
                alloc = random.randint(5, 20)

            avail = max(0, curr - alloc)
            inv = Inventory(
                product_id=prod.id,
                warehouse_id=wh.id,
                current_stock=curr,
                allocated_stock=alloc,
                available_stock=avail,
                safety_stock=prod.safety_stock_min,
                max_stock_capacity=prod.reorder_point * 12
            )
            db.add(inv)
    db.commit()

    # 7. 180 Days of Daily Sales History
    print("Generating 180 days of daily sales history...")
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=180)

    sales_records = []
    for prod in product_objs:
        # Base daily demand varies by category
        base_demand = random.randint(5, 30) if prod.category_id in [3, 5] else random.randint(2, 10)
        
        for wh in warehouse_objs:
            curr_date = start_date
            while curr_date <= end_date:
                # Add weekly seasonality (higher on weekends/mid-week) and trend
                day_of_week = curr_date.weekday()
                day_multiplier = 1.3 if day_of_week in [4, 5] else 0.9
                trend_multiplier = 1.0 + ((curr_date - start_date).days / 180.0) * 0.2
                noise = random.uniform(0.7, 1.4)
                
                qty = int(base_demand * day_multiplier * trend_multiplier * noise)
                qty = max(0, qty)
                revenue = round(qty * prod.selling_price, 2)
                
                sales_records.append(SalesHistory(
                    product_id=prod.id,
                    warehouse_id=wh.id,
                    date=curr_date,
                    quantity_sold=qty,
                    revenue=revenue
                ))
                curr_date += timedelta(days=1)
                
    db.bulk_save_objects(sales_records)
    db.commit()

    # 8. Customers & Orders
    print("Generating Customers, Customer Orders & Purchase Orders...")
    customers_data = [
        ("Acme Retail Corp", "procurement@acme.com", "South"),
        ("Metro Logistics & Distribution", "orders@metrologistics.in", "West"),
        ("Apex Supply Partners", "info@apexsupply.com", "North"),
        ("Sunrise Health Systems", "buying@sunrisehealth.org", "South"),
        ("Industrial Tech Enterprises", "supply@indtech.com", "West"),
    ]
    cust_objs = []
    for name, email, region in customers_data:
        c = Customer(name=name, email=email, region=region)
        db.add(c)
        cust_objs.append(c)
    db.commit()

    # Orders
    statuses = ["DELIVERED", "DELIVERED", "SHIPPED", "PROCESSING", "PENDING"]
    for i in range(1, 25):
        cust = cust_objs[i % len(cust_objs)]
        wh = warehouse_objs[i % len(warehouse_objs)]
        status = statuses[i % len(statuses)]
        order_date = datetime.utcnow() - timedelta(days=random.randint(1, 30))
        
        ord_obj = Order(
            order_number=f"ORD-2026-{1000+i}",
            customer_id=cust.id,
            warehouse_id=wh.id,
            order_date=order_date,
            status=status,
            total_amount=0.0
        )
        db.add(ord_obj)
        db.commit()

        # Add items
        total_amt = 0.0
        selected_prods = random.sample(product_objs, random.randint(2, 5))
        for p in selected_prods:
            qty = random.randint(5, 50)
            item_amt = qty * p.selling_price
            total_amt += item_amt
            oi = OrderItem(
                order_id=ord_obj.id,
                product_id=p.id,
                quantity=qty,
                unit_price=p.selling_price
            )
            db.add(oi)
        
        ord_obj.total_amount = round(total_amt, 2)
        db.commit()

        # Shipment if shipped/delivered
        if status in ["SHIPPED", "DELIVERED"]:
            ship = Shipment(
                tracking_number=f"TRK-EXPRESS-{5000+i}",
                order_id=ord_obj.id,
                warehouse_id=wh.id,
                carrier="Express Freight India",
                status="DELIVERED" if status == "DELIVERED" else "IN_TRANSIT",
                shipped_date=order_date + timedelta(days=1),
                estimated_delivery=order_date + timedelta(days=3)
            )
            db.add(ship)
            db.commit()

    # Purchase Orders (Open / Pending Replenishments)
    for i in range(1, 10):
        sup = supplier_objs[i % len(supplier_objs)]
        wh = warehouse_objs[i % len(warehouse_objs)]
        po = PurchaseOrder(
            po_number=f"PO-2026-{8000+i}",
            supplier_id=sup.id,
            warehouse_id=wh.id,
            status="ISSUED" if i % 2 == 0 else "PENDING",
            expected_delivery_date=datetime.utcnow() + timedelta(days=random.randint(3, 10)),
            total_cost=0.0
        )
        db.add(po)
        db.commit()

        total_po_cost = 0.0
        p_items = random.sample(product_objs, 2)
        for p in p_items:
            qty = random.randint(100, 500)
            c = qty * p.unit_cost
            total_po_cost += c
            poi = PurchaseOrderItem(
                purchase_order_id=po.id,
                product_id=p.id,
                quantity=qty,
                unit_cost=p.unit_cost
            )
            db.add(poi)
        po.total_cost = round(total_po_cost, 2)
        db.commit()

    # 10. Retail Space Facing for Assortment AI
    from backend.app.models.models import RetailSpace
    for idx, p in enumerate(product_objs):
        rs = RetailSpace(
            store_id=f"STORE-DXB-{(idx % 5) + 1:02d}",
            product_id=p.id,
            category=p.category.name if p.category else "Retail",
            allocated_space_sqm=round(random.uniform(0.5, 3.5), 1),
            display_units=random.randint(10, 50),
            shelf_capacity=random.randint(40, 100)
        )
        db.add(rs)
    db.commit()

    print("Database seeding completed successfully!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
