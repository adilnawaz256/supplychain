import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.models import (
    Product,
    ProductCategory,
    Warehouse,
    Inventory,
    SalesHistory,
    Supplier,
    SupplierProduct,
    Customer,
    Order,
    RetailSpace
)

def _parse_datetime(val: Any) -> datetime.datetime:
    if isinstance(val, datetime.datetime):
        return val
    if isinstance(val, datetime.date):
        return datetime.datetime.combine(val, datetime.time.min)
    if isinstance(val, str) and val.strip():
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.datetime.strptime(val.split(".")[0].strip(), fmt)
            except Exception:
                continue
    return datetime.datetime.utcnow()

class IngestionService:
    """
    Ingests remote records transformed via canonical mapping into internal PostgreSQL database.
    Optimized with in-memory lookup caching for ultra-fast bulk execution.
    """
    def __init__(self, db: Session):
        self.db = db

    def ingest_records(
        self,
        table_name: str,
        records: List[Dict[str, Any]],
        mappings: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        if not records:
            return {
                "status": "SUCCESS",
                "message": f"Table '{table_name}' had 0 records to ingest.",
                "rows_processed": 0,
                "dataset_summary": self.get_summary()
            }

        # Build mapping lookup: source_field -> target_canonical_field
        field_map = {}
        for m in mappings:
            src = m.get("source_field")
            tgt = m.get("target_canonical_field")
            if src and tgt and tgt != "ignore":
                field_map[src] = tgt

        # Pre-cache existing lookups in memory to avoid per-row network roundtrips
        existing_categories = {c.name.lower(): c for c in self.db.query(ProductCategory).all()}
        existing_warehouses = {w.code.lower(): w for w in self.db.query(Warehouse).all()}
        existing_suppliers = {s.code.lower(): s for s in self.db.query(Supplier).all()}
        
        # Pre-load SKUs present in this batch
        candidate_skus = []
        for r in records:
            sku_val = None
            for src_col, tgt_field in field_map.items():
                if tgt_field == "product_sku" and src_col in r:
                    sku_val = r[src_col]
                    break
            if sku_val is None:
                sku_val = r.get("sku") or r.get("item_code") or r.get("itemcode")
            if sku_val is not None:
                candidate_skus.append(str(sku_val).strip())

        existing_products = {}
        if candidate_skus:
            # Query existing in chunks of 500
            for i in range(0, len(candidate_skus), 500):
                chunk = candidate_skus[i:i+500]
                for p in self.db.query(Product).filter(Product.sku.in_(chunk)).all():
                    existing_products[p.sku] = p

        processed_count = 0
        products_upserted = 0
        inventory_upserted = 0
        sales_created = 0
        suppliers_upserted = 0

        # Ensure at least one default warehouse and category exist
        default_wh = existing_warehouses.get("wh-01")
        if not default_wh:
            default_wh = Warehouse(code="WH-01", name="Central Distribution Hub", location="Main Logistic Center")
            self.db.add(default_wh)
            self.db.flush()
            existing_warehouses["wh-01"] = default_wh

        default_cat = existing_categories.get("general")
        if not default_cat:
            default_cat = ProductCategory(name="General", description="General Category")
            self.db.add(default_cat)
            self.db.flush()
            existing_categories["general"] = default_cat

        for row in records:
            mapped_row = {}
            for col, val in row.items():
                if col in field_map:
                    mapped_row[field_map[col]] = val
                else:
                    mapped_row[col] = val

            prod = None
            wh = default_wh

            # 1. Product Master mapping
            sku_val = mapped_row.get("product_sku") or row.get("sku") or row.get("item_code") or row.get("itemcode")
            if sku_val is not None:
                sku = str(sku_val).strip()
                name = str(mapped_row.get("product_name") or row.get("name") or row.get("itemdescription") or f"Product {sku}")
                unit_cost = float(mapped_row.get("unit_cost") or row.get("unit_cost") or 0.0)
                selling_price = float(mapped_row.get("selling_price") or row.get("selling_price") or round(unit_cost * 1.5, 2) or 10.0)
                lead_time = int(mapped_row.get("lead_time_days") or row.get("lead_time_days") or 7)
                safety_stock = int(mapped_row.get("safety_stock_min") or row.get("safety_stock_min") or 10)
                reorder_pt = int(mapped_row.get("reorder_point") or row.get("reorder_point") or 20)
                cat_name = str(mapped_row.get("category_name") or row.get("category") or "General").strip()

                cat = existing_categories.get(cat_name.lower())
                if not cat:
                    cat = ProductCategory(name=cat_name)
                    self.db.add(cat)
                    self.db.flush()
                    existing_categories[cat_name.lower()] = cat

                prod = existing_products.get(sku)
                if not prod:
                    prod = Product(
                        sku=sku,
                        name=name,
                        category_id=cat.id,
                        unit_cost=unit_cost,
                        selling_price=selling_price,
                        lead_time_days=lead_time,
                        safety_stock_min=safety_stock,
                        reorder_point=reorder_pt
                    )
                    self.db.add(prod)
                    self.db.flush()
                    existing_products[sku] = prod
                    products_upserted += 1
                else:
                    if "product_name" in mapped_row or "name" in row:
                        prod.name = name
                    if "unit_cost" in mapped_row or "unit_cost" in row:
                        prod.unit_cost = unit_cost
                    if "selling_price" in mapped_row or "selling_price" in row:
                        prod.selling_price = selling_price
                    products_upserted += 1

            # 2. Warehouse & Inventory mapping
            wh_code_val = mapped_row.get("warehouse_code") or row.get("warehouse_code") or row.get("warehousecode")
            stock_val = mapped_row.get("current_stock") or row.get("current_stock") or row.get("qtyonhand")
            if wh_code_val is not None:
                wh_code = str(wh_code_val).strip()
                wh = existing_warehouses.get(wh_code.lower())
                if not wh:
                    wh = Warehouse(code=wh_code, name=f"Warehouse {wh_code}", location="Regional Distribution Hub")
                    self.db.add(wh)
                    self.db.flush()
                    existing_warehouses[wh_code.lower()] = wh

            if stock_val is not None and prod:
                stock_qty = int(stock_val or 0)
                reserved_qty = int(mapped_row.get("reserved_stock") or row.get("reserved_stock") or 0)
                in_transit_qty = int(mapped_row.get("in_transit_stock") or row.get("in_transit_stock") or 0)

                inv = self.db.query(Inventory).filter(
                    Inventory.product_id == prod.id,
                    Inventory.warehouse_id == wh.id
                ).first()
                if not inv:
                    inv = Inventory(
                        product_id=prod.id,
                        warehouse_id=wh.id,
                        current_stock=stock_qty,
                        reserved_stock=reserved_qty,
                        in_transit_stock=in_transit_qty
                    )
                    self.db.add(inv)
                else:
                    inv.current_stock = stock_qty
                    inv.reserved_stock = reserved_qty
                    inv.in_transit_stock = in_transit_qty
                inventory_upserted += 1

            # 3. Sales History mapping
            txn_date_val = mapped_row.get("transaction_date") or row.get("date") or row.get("txndate")
            qty_sold_val = mapped_row.get("quantity_sold") or row.get("quantity_sold")
            revenue_val = mapped_row.get("sales_revenue") or row.get("revenue") or row.get("netamount")
            if (qty_sold_val is not None or revenue_val is not None) and prod:
                qty_sold = int(qty_sold_val or 1)
                revenue = float(revenue_val or (qty_sold * prod.selling_price))
                unit_price = round(revenue / qty_sold, 2) if qty_sold > 0 else 15.0
                txn_date = _parse_datetime(txn_date_val)

                sh = SalesHistory(
                    product_id=prod.id,
                    warehouse_id=wh.id,
                    date=txn_date,
                    quantity_sold=qty_sold,
                    unit_price=unit_price,
                    revenue=revenue
                )
                self.db.add(sh)
                sales_created += 1

            # 4. Supplier mapping
            sup_code_val = mapped_row.get("supplier_code") or row.get("supplier_code") or row.get("suppliercode")
            sup_name_val = mapped_row.get("supplier_name") or row.get("supplier_name")
            if sup_code_val is not None or sup_name_val is not None:
                sup_code = str(sup_code_val or "SUP-01").strip()
                sup = existing_suppliers.get(sup_code.lower())
                if not sup:
                    sup = Supplier(code=sup_code, name=str(sup_name_val or f"Supplier {sup_code}"))
                    self.db.add(sup)
                    self.db.flush()
                    existing_suppliers[sup_code.lower()] = sup
                    suppliers_upserted += 1

                if prod:
                    sp = self.db.query(SupplierProduct).filter(
                        SupplierProduct.supplier_id == sup.id,
                        SupplierProduct.product_id == prod.id
                    ).first()
                    if not sp:
                        sp = SupplierProduct(supplier_id=sup.id, product_id=prod.id, unit_cost=prod.unit_cost)
                        self.db.add(sp)

            processed_count += 1
            if processed_count % 100 == 0:
                self.db.commit()

        self.db.commit()

        return {
            "status": "SUCCESS",
            "message": f"Successfully dumped {processed_count} records from '{table_name}' into internal PostgreSQL database!",
            "rows_processed": processed_count,
            "products_upserted": products_upserted,
            "inventory_upserted": inventory_upserted,
            "sales_created": sales_created,
            "suppliers_upserted": suppliers_upserted,
            "dataset_summary": self.get_summary()
        }

    def get_summary(self) -> Dict[str, Any]:
        """Fetch current counts from internal database"""
        try:
            p_count = self.db.query(Product).count()
            i_count = self.db.query(Inventory).count()
            s_count = self.db.query(SalesHistory).count()
            sup_count = self.db.query(Supplier).count()
            r_count = self.db.query(RetailSpace).count()
            return {
                "products_mapped": p_count,
                "inventory_items_mapped": i_count,
                "sales_history_records": s_count,
                "suppliers_connected": sup_count,
                "retail_store_spaces": r_count
            }
        except Exception:
            return {
                "products_mapped": 0,
                "inventory_items_mapped": 0,
                "sales_history_records": 0,
                "suppliers_connected": 0,
                "retail_store_spaces": 0
            }
