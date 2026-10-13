import datetime
import hashlib
import json
from typing import List, Dict, Any, Optional, Iterable
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
    OrderItem,
    Shipment,
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
                return datetime.datetime.strptime(val.split(".")[0].split("+")[0].strip(), fmt)
            except Exception:
                continue
    return datetime.datetime.utcnow()

def _to_float(val: Any, default: float = 0.0) -> float:
    try:
        if val is None or (isinstance(val, str) and not val.strip()):
            return default
        return float(str(val).replace(",", ""))
    except (TypeError, ValueError):
        return default

def _to_int(val: Any, default: int = 0) -> int:
    return int(round(_to_float(val, float(default))))

def _present(val: Any) -> bool:
    return val is not None and not (isinstance(val, str) and not val.strip())

# The Data Sources UI maps columns onto short per-table names (e.g. "sku", "name");
# the ingestion logic below works on canonical field names.
TARGET_FIELD_ALIASES = {
    "products": {
        "sku": "product_sku", "name": "product_name", "category": "category_name",
    },
    "inventory": {
        "product_id": "product_sku", "warehouse_id": "warehouse_code",
    },
    "orders": {
        "customer_id": "customer_code", "order_date": "transaction_date",
        "total_amount": "order_total", "status": "order_status",
    },
    "customers": {
        "name": "customer_name", "email": "customer_email", "tier": "customer_tier",
    },
    "shipments": {
        "order_id": "order_number", "status": "shipment_status",
    },
}

# Unmapped source columns are still recognised when their name is an obvious match.
RAW_COLUMN_FALLBACKS = {
    "product_sku": ["sku", "item_code", "itemcode", "stockcode", "product_code"],
    "product_name": ["product_name", "itemdescription", "item_name", "description"],
    "unit_cost": ["unit_cost", "unitcost", "cost"],
    "selling_price": ["selling_price", "sellingprice", "price", "unit_price"],
    "lead_time_days": ["lead_time_days", "leadtimedays", "lead_time"],
    "safety_stock_min": ["safety_stock_min", "safetystock", "safety_stock"],
    "reorder_point": ["reorder_point", "reorderpoint", "rop"],
    "category_name": ["category", "category_name", "categoryname"],
    "warehouse_code": ["warehouse_code", "warehousecode", "warehouse"],
    "current_stock": ["current_stock", "qtyonhand", "qty_on_hand", "stock", "on_hand"],
    "reserved_stock": ["reserved_stock", "reservedqty"],
    "in_transit_stock": ["in_transit_stock", "intransit"],
    "transaction_date": ["date", "txndate", "transaction_date", "order_date", "sale_date"],
    "quantity_sold": ["quantity_sold", "qty_sold", "quantity", "qty"],
    "sales_revenue": ["revenue", "netamount", "sales_revenue", "line_total"],
    "supplier_code": ["supplier_code", "suppliercode", "vendor_code"],
    "supplier_name": ["supplier_name", "vendor_name"],
}

def _canonical_field(target_table: str, field: str) -> str:
    return TARGET_FIELD_ALIASES.get(target_table, {}).get(field, field)


SUMMARY_KEYS = ("products_upserted", "inventory_upserted", "sales_created", "suppliers_upserted",
                "customers_upserted", "orders_upserted", "shipments_upserted", "sales_already_present",
                "order_lines_created")


def _source_key(source_table: str, raw: Dict[str, Any]) -> str:
    """Fingerprint of one source row, so importing the same table again never duplicates sales."""
    blob = json.dumps({"t": source_table, "r": raw}, sort_keys=True, default=str)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


class IngestionRun:
    """
    One import of one source table, fed batch by batch. Lookup tables (products, warehouses,
    customers, ...) are loaded once and kept in memory across batches; sales rows, the largest
    table, are deduplicated per batch by source-row fingerprint and inserted in bulk.
    """
    def __init__(self, db: Session, source_table: str, mappings: List[Dict[str, str]], target_table: str = "products"):
        self.db = db
        self.source_table = source_table
        self.target_table = target_table
        self.field_map: Dict[str, str] = {}
        for m in mappings:
            src = m.get("source_field")
            tgt = m.get("target_canonical_field")
            if src and tgt and tgt != "ignore":
                self.field_map[src] = _canonical_field(target_table, tgt)

        self.categories = {c.name.lower(): c for c in db.query(ProductCategory).all()}
        self.warehouses = {w.code.lower(): w for w in db.query(Warehouse).all()}
        self.suppliers = {s.code.lower(): s for s in db.query(Supplier).all()}
        self.customers = {c.customer_code.lower(): c for c in db.query(Customer).all()}
        self.products = {p.sku: p for p in db.query(Product).all()}
        self.inventory = {(i.product_id, i.warehouse_id): i for i in db.query(Inventory).all()}
        self.supplier_links = {(sp.supplier_id, sp.product_id) for sp in
                               db.query(SupplierProduct.supplier_id, SupplierProduct.product_id).all()}

        self.counts = {k: 0 for k in SUMMARY_KEYS}
        self.rows_seen = 0
        self.processed = 0
        self.skipped = 0
        self.skip_reasons: Dict[str, int] = {}

    # --- helpers -------------------------------------------------------------
    def _build_row(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        mapped = {self.field_map[c]: v for c, v in raw.items() if c in self.field_map}
        lowered = {str(k).lower().replace(" ", "_"): v for k, v in raw.items() if k not in self.field_map}
        for canonical, candidates in RAW_COLUMN_FALLBACKS.items():
            if canonical in mapped:
                continue
            for cand in candidates:
                if _present(lowered.get(cand)):
                    mapped[canonical] = lowered[cand]
                    break
        return mapped

    def _skip(self, reason: str):
        self.skipped += 1
        self.skip_reasons[reason] = self.skip_reasons.get(reason, 0) + 1

    def _warehouse(self, code: Any) -> Warehouse:
        wh_code = str(code).strip() if _present(code) else "WH-01"
        wh = self.warehouses.get(wh_code.lower())
        if not wh:
            wh = Warehouse(code=wh_code, name=f"Warehouse {wh_code}" if wh_code != "WH-01" else "Central Distribution Hub",
                           location="Imported from connected database")
            self.db.add(wh)
            self.db.flush()
            self.warehouses[wh_code.lower()] = wh
        return wh

    def _customer(self, code: Any, name: Any = None) -> Optional[Customer]:
        if not _present(code):
            return None
        key = str(code).strip()
        cust = self.customers.get(key.lower())
        if not cust:
            cust = Customer(customer_code=key, name=str(name).strip() if _present(name) else f"Customer {key}")
            self.db.add(cust)
            self.db.flush()
            self.customers[key.lower()] = cust
            if self.target_table != "customers":
                self.counts["customers_upserted"] += 1
        return cust

    def _product(self, row: Dict[str, Any]) -> (Optional[Product], bool):
        if not _present(row.get("product_sku")):
            return None, False
        sku = str(row["product_sku"]).strip()
        prod = self.products.get(sku)
        creates = self.target_table in ("products", "inventory", "orders") or any(
            _present(row.get(f)) for f in ("product_name", "unit_cost", "selling_price"))
        if not prod and creates:
            unit_cost = _to_float(row.get("unit_cost"))
            cat_name = str(row.get("category_name") or "General").strip() or "General"
            cat = self.categories.get(cat_name.lower())
            if not cat:
                cat = ProductCategory(name=cat_name)
                self.db.add(cat)
                self.db.flush()
                self.categories[cat_name.lower()] = cat
            prod = Product(
                sku=sku,
                name=str(row.get("product_name") or f"Product {sku}")[:200],
                category_id=cat.id,
                unit_cost=unit_cost,
                selling_price=_to_float(row.get("selling_price"), round(unit_cost * 1.5, 2)),
                lead_time_days=_to_int(row.get("lead_time_days"), 7),
                safety_stock_min=_to_int(row.get("safety_stock_min"), 10),
                reorder_point=_to_int(row.get("reorder_point"), 20),
            )
            self.db.add(prod)
            self.db.flush()
            self.products[sku] = prod
            self.counts["products_upserted"] += 1
            return prod, True
        if prod and self.target_table == "products":
            if _present(row.get("product_name")):
                prod.name = str(row["product_name"])[:200]
            if _present(row.get("unit_cost")):
                prod.unit_cost = _to_float(row["unit_cost"])
            if _present(row.get("selling_price")):
                prod.selling_price = _to_float(row["selling_price"])
            if _present(row.get("lead_time_days")):
                prod.lead_time_days = _to_int(row["lead_time_days"], 7)
            if _present(row.get("safety_stock_min")):
                prod.safety_stock_min = _to_int(row["safety_stock_min"], 10)
            if _present(row.get("reorder_point")):
                prod.reorder_point = _to_int(row["reorder_point"], 20)
            self.counts["products_upserted"] += 1
            return prod, True
        return prod, False

    # --- main entry point ----------------------------------------------------
    def ingest_batch(self, records: List[Dict[str, Any]]) -> None:
        rows = [(raw, self._build_row(raw)) for raw in records]
        self.rows_seen += len(rows)

        orders_by_no: Dict[str, Order] = {}
        shipments_by_trk: Dict[str, Shipment] = {}
        if self.target_table in ("orders", "shipments"):
            order_nos = {str(r["order_number"]).strip()[:50] for _, r in rows if _present(r.get("order_number"))}
            for chunk in _chunks(list(order_nos), 500):
                for o in self.db.query(Order).filter(Order.order_number.in_(chunk)).all():
                    orders_by_no[o.order_number] = o
        if self.target_table == "shipments":
            trks = {str(r["tracking_number"]).strip()[:100] for _, r in rows if _present(r.get("tracking_number"))}
            for chunk in _chunks(list(trks), 500):
                for sh in self.db.query(Shipment).filter(Shipment.tracking_number.in_(chunk)).all():
                    shipments_by_trk[sh.tracking_number] = sh

        sale_keys = [_source_key(self.source_table, raw) for raw, r in rows
                     if _present(r.get("quantity_sold")) or _present(r.get("sales_revenue"))]
        known_sales = set()
        for chunk in _chunks(sale_keys, 500):
            known_sales.update(k for (k,) in self.db.query(SalesHistory.source_key).filter(SalesHistory.source_key.in_(chunk)).all())
        new_sales: List[Dict[str, Any]] = []

        for raw, row in rows:
            prod, touched = self._product(row)
            new_sale = None

            if prod and _present(row.get("current_stock")):
                wh = self._warehouse(row.get("warehouse_code"))
                inv = self.inventory.get((prod.id, wh.id))
                if not inv:
                    inv = Inventory(product_id=prod.id, warehouse_id=wh.id)
                    self.db.add(inv)
                    self.inventory[(prod.id, wh.id)] = inv
                inv.current_stock = _to_int(row["current_stock"])
                inv.reserved_stock = _to_int(row.get("reserved_stock"))
                inv.in_transit_stock = _to_int(row.get("in_transit_stock"))
                if _present(row.get("reorder_quantity")):
                    inv.reorder_quantity = _to_int(row["reorder_quantity"], 50)
                self.counts["inventory_upserted"] += 1
                touched = True

            if prod and (_present(row.get("quantity_sold")) or _present(row.get("sales_revenue"))):
                key = _source_key(self.source_table, raw)
                if key in known_sales:
                    self.counts["sales_already_present"] += 1
                else:
                    known_sales.add(key)
                    qty = max(1, _to_int(row.get("quantity_sold"), 1))
                    revenue = _to_float(row.get("sales_revenue"), qty * (prod.selling_price or 0.0))
                    new_sale = {
                        "product_id": prod.id,
                        "warehouse_id": self._warehouse(row.get("warehouse_code")).id,
                        "date": _parse_datetime(row.get("transaction_date")),
                        "quantity_sold": qty,
                        "unit_price": round(revenue / qty, 2),
                        "revenue": revenue,
                        "is_promotional": 0,
                        "source_key": key,
                    }
                    new_sales.append(new_sale)
                    self.counts["sales_created"] += 1
                touched = True

            if _present(row.get("supplier_code")) or _present(row.get("supplier_name")):
                sup_code = str(row.get("supplier_code") or row.get("supplier_name")).strip()[:50]
                sup = self.suppliers.get(sup_code.lower())
                if not sup:
                    sup = Supplier(code=sup_code, name=str(row.get("supplier_name") or f"Supplier {sup_code}"))
                    self.db.add(sup)
                    self.db.flush()
                    self.suppliers[sup_code.lower()] = sup
                    self.counts["suppliers_upserted"] += 1
                if prod and (sup.id, prod.id) not in self.supplier_links:
                    self.db.add(SupplierProduct(supplier_id=sup.id, product_id=prod.id, unit_cost=prod.unit_cost))
                    self.supplier_links.add((sup.id, prod.id))
                touched = True

            if self.target_table == "customers":
                cust = self._customer(row.get("customer_code"), row.get("customer_name"))
                if cust:
                    if _present(row.get("customer_name")):
                        cust.name = str(row["customer_name"])[:150]
                    if _present(row.get("customer_email")):
                        cust.email = str(row["customer_email"])[:100]
                    if _present(row.get("customer_tier")):
                        cust.tier = str(row["customer_tier"])[:20]
                    self.counts["customers_upserted"] += 1
                    touched = True

            if self.target_table == "orders" and _present(row.get("order_number")):
                order_no = str(row["order_number"]).strip()[:50]
                order = orders_by_no.get(order_no)
                if not order:
                    order = Order(order_number=order_no, total_amount=0.0)
                    self.db.add(order)
                    self.db.flush()
                    orders_by_no[order_no] = order
                cust = self._customer(row.get("customer_code"), row.get("customer_name"))
                if cust:
                    order.customer_id = cust.id
                order.order_date = _parse_datetime(row.get("transaction_date"))
                if _present(row.get("order_status")):
                    order.status = str(row["order_status"]).upper()[:50]
                if _present(row.get("order_total")):
                    order.total_amount = _to_float(row["order_total"])
                if new_sale is not None:
                    # One order line per new sales row (re-imported rows were already counted).
                    self.db.add(OrderItem(order_id=order.id, product_id=prod.id, quantity=new_sale["quantity_sold"],
                                          unit_price=new_sale["unit_price"], total_price=new_sale["revenue"]))
                    self.counts["order_lines_created"] += 1
                    if not _present(row.get("order_total")):
                        order.total_amount = (order.total_amount or 0.0) + new_sale["revenue"]
                if _present(row.get("shipping_address")):
                    order.shipping_address = str(row["shipping_address"])
                self.counts["orders_upserted"] += 1
                touched = True

            if self.target_table == "shipments" and _present(row.get("tracking_number")):
                trk = str(row["tracking_number"]).strip()[:100]
                shp = shipments_by_trk.get(trk)
                if not shp:
                    shp = Shipment(tracking_number=trk)
                    self.db.add(shp)
                    shipments_by_trk[trk] = shp
                if _present(row.get("order_number")):
                    order = orders_by_no.get(str(row["order_number"]).strip()[:50])
                    if order:
                        shp.order_id = order.id
                if _present(row.get("carrier")):
                    shp.carrier = str(row["carrier"])[:100]
                if _present(row.get("shipment_status")):
                    shp.status = str(row["shipment_status"]).upper()[:50]
                if _present(row.get("shipped_date")):
                    shp.shipped_date = _parse_datetime(row["shipped_date"])
                self.counts["shipments_upserted"] += 1
                touched = True

            if touched:
                self.processed += 1
            elif self.target_table in ("products", "inventory") and not _present(row.get("product_sku")):
                self._skip("no product SKU column mapped")
            elif self.target_table == "orders" and not _present(row.get("order_number")):
                self._skip("no order number column mapped")
            elif self.target_table == "customers" and not _present(row.get("customer_code")):
                self._skip("no customer code column mapped")
            elif self.target_table == "shipments" and not _present(row.get("tracking_number")):
                self._skip("no tracking number column mapped")
            else:
                self._skip("row had no usable mapped values")

        if new_sales:
            self.db.bulk_insert_mappings(SalesHistory, new_sales)
        self.db.commit()

    def summary(self) -> Dict[str, Any]:
        base = {
            "rows_fetched": self.rows_seen,
            "rows_processed": self.processed,
            "rows_skipped": self.skipped,
            "skip_reasons": self.skip_reasons,
            **self.counts,
            "dataset_summary": IngestionService(self.db).get_summary(),
        }
        if self.rows_seen == 0:
            return {**base, "status": "SUCCESS", "message": f"Source table '{self.source_table}' has 0 rows, nothing to import."}
        if self.processed == 0:
            reason = ", ".join(f"{n} rows: {r}" for r, n in self.skip_reasons.items())
            return {**base, "status": "ERROR",
                    "message": f"None of the {self.rows_seen} rows from '{self.source_table}' could be imported into "
                               f"'{self.target_table}' ({reason}). Check the column mapping."}
        return {**base, "status": "SUCCESS",
                "message": f"Imported {self.processed:,} of {self.rows_seen:,} rows from '{self.source_table}' into '{self.target_table}'."}


def _chunks(items: List[Any], size: int) -> Iterable[List[Any]]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


class IngestionService:
    """Convenience wrapper: imports a list of rows in one go, and reports table counts."""
    def __init__(self, db: Session):
        self.db = db

    def ingest_records(self, table_name: str, records: List[Dict[str, Any]], mappings: List[Dict[str, str]],
                       target_table: str = "products", batch_size: int = 5000) -> Dict[str, Any]:
        run = IngestionRun(self.db, table_name, mappings, target_table)
        try:
            for batch in _chunks(records, batch_size):
                run.ingest_batch(batch)
        except Exception as e:
            self.db.rollback()
            return {**run.summary(), "status": "ERROR", "message": f"Import stopped after {run.processed} rows: {e}"}
        return run.summary()

    def get_summary(self) -> Dict[str, Any]:
        """Fetch current counts from internal database"""
        try:
            return {
                "products_mapped": self.db.query(Product).count(),
                "inventory_items_mapped": self.db.query(Inventory).count(),
                "sales_history_records": self.db.query(SalesHistory).count(),
                "suppliers_connected": self.db.query(Supplier).count(),
                "retail_store_spaces": self.db.query(RetailSpace).count(),
                "customers": self.db.query(Customer).count(),
                "orders": self.db.query(Order).count(),
                "shipments": self.db.query(Shipment).count(),
            }
        except Exception:
            return {
                "products_mapped": 0,
                "inventory_items_mapped": 0,
                "sales_history_records": 0,
                "suppliers_connected": 0,
                "retail_store_spaces": 0,
                "customers": 0,
                "orders": 0,
                "shipments": 0,
            }
