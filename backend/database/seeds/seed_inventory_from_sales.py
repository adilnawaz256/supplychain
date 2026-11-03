"""Create SAMPLE stock-on-hand rows from sales history, so inventory-based modules can be demoed.

    python backend/database/seeds/seed_inventory_from_sales.py [--replace] [--database-url URL]

For every product-warehouse pair that has sales, stock = the product's average daily demand x a random
"days of cover" (fixed seed, so re-runs give the same numbers). Demand is per product across all warehouses
because that is what InventoryRiskEngine divides each line's stock by. Cover is set against the product's
lead time so the dashboards show every risk level: ~12% CRITICAL (runs out before a delivery), ~10% HIGH,
~48% MEDIUM, ~30% LOW (over 60 days of supply).
These are not real stock counts: replace them with an inventory import when real data is available.
"""
import argparse
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(os.path.dirname(os.path.dirname(_here)))
for _p in (_root, os.path.join(_root, "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

SEED = 42


def build(engine) -> pd.DataFrame:
    with engine.connect() as conn:
        pairs = pd.read_sql(text("""
            SELECT DISTINCT product_id, warehouse_id FROM sales_history
            WHERE product_id IS NOT NULL AND warehouse_id IS NOT NULL"""), conn)
        prod = pd.read_sql(text("""
            SELECT s.product_id, SUM(s.quantity_sold) AS units, MIN(s.date) AS first_sale, MAX(s.date) AS last_sale,
                   MAX(p.lead_time_days) AS lead_time
            FROM sales_history s JOIN products p ON p.id = s.product_id
            GROUP BY s.product_id"""), conn)
    if pairs.empty:
        raise SystemExit("sales_history is empty: load sales first (load_retail_dataset.py).")
    first, last = pd.to_datetime(prod["first_sale"]), pd.to_datetime(prod["last_sale"])
    prod["daily"] = prod["units"].astype(float) / ((last.dt.normalize() - first.dt.normalize()).dt.days + 1)
    prod["lead_time"] = prod["lead_time"].fillna(7).astype(float)
    sales = pairs.merge(prod[["product_id", "daily", "lead_time"]], on="product_id")
    daily, lt = sales["daily"].to_numpy(), sales["lead_time"].to_numpy()

    rng = np.random.default_rng(SEED)
    n = len(sales)
    band = rng.choice(4, size=n, p=[0.12, 0.10, 0.48, 0.30])
    medium_lo = lt + 4
    medium_hi = np.maximum(medium_lo + 1, 60)
    cover = np.select(
        [band == 0, band == 1, band == 2],
        [rng.uniform(0, 0.9, n) * lt, lt + rng.uniform(0.2, 3, n), rng.uniform(medium_lo, medium_hi)],
        rng.uniform(65, 150, n),
    )
    stock = np.ceil(daily * cover).astype(int)
    stock[band == 0] = np.floor(daily * cover).astype(int)[band == 0]
    restock = last.max()
    return pd.DataFrame({
        "product_id": sales["product_id"].astype(int),
        "warehouse_id": sales["warehouse_id"].astype(int),
        "current_stock": stock,
        "reserved_stock": 0,
        "in_transit_stock": 0,
        "reorder_quantity": np.maximum(np.ceil(daily * 30), 1).astype(int),
        "last_restock_date": restock.to_pydatetime(),
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replace", action="store_true", help="delete existing inventory rows first")
    ap.add_argument("--database-url", help="defaults to DATABASE_URL from the backend settings")
    args = ap.parse_args()

    from backend.app.core.database import Base, engine as default_engine
    import backend.app.models.models  # noqa: F401
    engine = create_engine(args.database_url) if args.database_url else default_engine

    with engine.connect() as conn:
        existing = conn.execute(text("SELECT COUNT(*) FROM inventory")).scalar()
    if existing and not args.replace:
        raise SystemExit(f"inventory already has {existing:,} rows; pass --replace to overwrite them.")

    df = build(engine)
    table = Base.metadata.tables["inventory"]
    records = df.to_dict("records")
    for r in records:
        for k, v in r.items():
            if isinstance(v, np.generic):
                r[k] = v.item()
    with engine.begin() as conn:
        if existing:
            conn.execute(text("DELETE FROM inventory"))
        for i in range(0, len(records), 1000):
            conn.execute(table.insert().values(records[i:i + 1000]))
        if engine.dialect.name == "postgresql":
            conn.execute(text("SELECT setval(pg_get_serial_sequence('inventory', 'id'), (SELECT MAX(id) FROM inventory))"))
    print(f"Inserted {len(records):,} sample inventory rows "
          f"({(df.current_stock == 0).sum():,} out of stock, {df.product_id.nunique():,} products, "
          f"{df.warehouse_id.nunique():,} warehouses).")


if __name__ == "__main__":
    main()
