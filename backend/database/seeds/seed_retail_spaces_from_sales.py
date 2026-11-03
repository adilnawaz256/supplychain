"""Create SAMPLE shelf-space rows from sales history, so the Shelf Space (assortment) module can be demoed.

    python backend/database/seeds/seed_retail_spaces_from_sales.py [--replace] [--database-url URL]

The retail dataset has no planogram, so for every product with sales this writes one retail_spaces row
(the assortment engine reads one row per product), placed in the warehouse/store that sells it most:
display units = the product's average daily demand x a random "days on display" (fixed seed, so re-runs
give the same numbers), shelf capacity from a random 50-95% fill, and floor space from the shelf capacity.
Days on display are spread so the dashboards show every class: fast sellers on lean shelves become
STAR / CORE products, slow sellers on large shelves become SLOW_MOVER / UNDERPERFORMER.
These are not real shelf measurements: replace them with a retail_spaces import when real data is available.
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
SQM_PER_SHELF_UNIT = 0.02


def build(engine) -> pd.DataFrame:
    with engine.connect() as conn:
        prod = pd.read_sql(text("""
            SELECT s.product_id, SUM(s.quantity_sold) AS units, MIN(s.date) AS first_sale, MAX(s.date) AS last_sale,
                   MAX(c.name) AS category
            FROM sales_history s
            JOIN products p ON p.id = s.product_id
            LEFT JOIN product_categories c ON c.id = p.category_id
            GROUP BY s.product_id"""), conn)
        top_store = pd.read_sql(text("""
            SELECT DISTINCT ON (s.product_id) s.product_id, w.code AS store_id
            FROM sales_history s JOIN warehouses w ON w.id = s.warehouse_id
            GROUP BY s.product_id, w.code
            ORDER BY s.product_id, SUM(s.quantity_sold) DESC"""), conn)
    if prod.empty:
        raise SystemExit("sales_history is empty: load sales first (load_retail_dataset.py).")
    first, last = pd.to_datetime(prod["first_sale"]), pd.to_datetime(prod["last_sale"])
    prod["daily"] = prod["units"].astype(float) / ((last.dt.normalize() - first.dt.normalize()).dt.days + 1)
    df = prod.merge(top_store, on="product_id", how="left")

    rng = np.random.default_rng(SEED)
    n = len(df)
    band = rng.choice(3, size=n, p=[0.30, 0.45, 0.25])
    days_on_display = np.select([band == 0, band == 1], [rng.uniform(2, 10, n), rng.uniform(10, 40, n)],
                                rng.uniform(40, 180, n))
    display = np.maximum(np.ceil(df["daily"].to_numpy() * days_on_display), 1).astype(int)
    capacity = np.maximum(np.ceil(display / rng.uniform(0.5, 0.95, n)), display).astype(int)
    sqm = np.clip(np.round(capacity * SQM_PER_SHELF_UNIT * rng.uniform(0.6, 1.4, n), 2), 0.25, 12.0)
    return pd.DataFrame({
        "store_id": df["store_id"].fillna("UNASSIGNED").astype(str).str.slice(0, 50),
        "product_id": df["product_id"].astype(int),
        "category": df["category"].fillna("General").astype(str).str.slice(0, 100),
        "allocated_space_sqm": sqm,
        "display_units": display,
        "shelf_capacity": capacity,
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replace", action="store_true", help="delete existing retail_spaces rows first")
    ap.add_argument("--database-url", help="defaults to DATABASE_URL from the backend settings")
    args = ap.parse_args()

    from backend.app.core.database import Base, engine as default_engine
    import backend.app.models.models  # noqa: F401
    engine = create_engine(args.database_url) if args.database_url else default_engine

    with engine.connect() as conn:
        existing = conn.execute(text("SELECT COUNT(*) FROM retail_spaces")).scalar()
    if existing and not args.replace:
        raise SystemExit(f"retail_spaces already has {existing:,} rows; pass --replace to overwrite them.")

    df = build(engine)
    table = Base.metadata.tables["retail_spaces"]
    records = df.to_dict("records")
    for r in records:
        for k, v in r.items():
            if isinstance(v, np.generic):
                r[k] = v.item()
    with engine.begin() as conn:
        if existing:
            conn.execute(text("DELETE FROM retail_spaces"))
        for i in range(0, len(records), 1000):
            conn.execute(table.insert().values(records[i:i + 1000]))
        if engine.dialect.name == "postgresql":
            conn.execute(text("SELECT setval(pg_get_serial_sequence('retail_spaces', 'id'), (SELECT MAX(id) FROM retail_spaces))"))
    print(f"Inserted {len(records):,} sample retail_spaces rows "
          f"({df.product_id.nunique():,} products, {df.store_id.nunique():,} stores, "
          f"{df.allocated_space_sqm.sum():,.0f} m2 in total).")


if __name__ == "__main__":
    main()
