"""Load the retail dataset (Data.xlsx + Trade_Area_Synthetic_Inputs.xlsx) into the database.

Source: https://github.com/ahmedkhancgt/supply-chain/tree/claude/python-file-review-ikw2q4/data

    python backend/database/seeds/load_retail_dataset.py --data-dir path/to/data [--download] [--wipe | --wipe-all]

--download   fetch the two Excel files from GitHub into --data-dir first
--wipe       delete all business data and saved ML results first (keeps users, roles, settings)
--wipe-all   also delete users, roles, permissions, team members, audit log and connector settings

Cleaning matches the original analysis scripts: drop exact duplicates, cancelled invoices ("C..."),
non-product stock codes and rows with quantity or price <= 0.
"""
import argparse
import os
import sys
import time
import urllib.request

_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(os.path.dirname(os.path.dirname(_here)))
for _p in (_root, os.path.join(_root, "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

GITHUB_RAW = "https://raw.githubusercontent.com/ahmedkhancgt/supply-chain/claude/python-file-review-ikw2q4/data"
FILES = ["Data.xlsx", "Trade_Area_Synthetic_Inputs.xlsx"]
NON_PRODUCT_STOCK_CODES = {"POST", "M", "MANUAL", "D", "DOT", "BANK CHARGES", "C2", "PADS", "CRUK", "AMAZONFEE", "S"}
BATCH = 1000

BUSINESS_TABLES = [
    "order_items", "orders", "purchase_order_items", "purchase_orders", "shipments", "retail_spaces",
    "inventory_transactions", "sales_history", "inventory", "supplier_products", "suppliers", "customers",
    "product_forecasts", "products", "product_categories", "warehouses", "trade_area_distances",
    "trade_area_stores", "trade_areas", "ml_result_snapshots", "background_jobs",
]
ACCOUNT_TABLES = ["users", "roles", "permission_settings", "workspace_members", "audit_logs",
                  "workspace_pipeline_configs", "microsoft_oauth_connections"]


def download(data_dir: str) -> None:
    os.makedirs(data_dir, exist_ok=True)
    for f in FILES:
        print(f"Downloading {f} ...")
        urllib.request.urlretrieve(f"{GITHUB_RAW}/{f}", os.path.join(data_dir, f))


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.drop_duplicates()
    df = df.dropna(subset=["Invoice", "Description", "Quantity", "InvoiceDate", "Price"])
    df = df[~df["Invoice"].astype(str).str.startswith("C")]
    df = df[~df["StockCode"].astype(str).str.upper().isin(NON_PRODUCT_STOCK_CODES)]
    df = df[(df["Quantity"] > 0) & (df["Price"] > 0)].copy()
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["StockCode"] = df["StockCode"].astype(str).str.strip()
    df["Description"] = df["Description"].astype(str).str.strip()
    df["Country"] = df["Country"].astype(str).str.strip()
    return df.reset_index(drop=True)


def _mode(s: pd.Series):
    m = s.mode()
    return m.iloc[0] if len(m) else None


def build_tables(df: pd.DataFrame, ta_xlsx: str) -> dict:
    t = {}
    cats = sorted(df["category"].dropna().unique())
    t["product_categories"] = pd.DataFrame({"id": range(1, len(cats) + 1), "name": cats})
    cat_id = dict(zip(cats, t["product_categories"]["id"]))

    g = df.groupby("StockCode")
    prod = pd.DataFrame({
        "sku": g.size().index,
        "name": g["Description"].agg(_mode).str.slice(0, 200).values,
        "category_id": g["category"].agg(_mode).map(cat_id).values,
        "subcategory": g["subcategory"].agg(_mode).values,
        "unit": "Units",
        "unit_cost": g["Cost"].mean().round(4).values,
        "selling_price": g["Price"].mean().round(4).values,
        "lead_time_days": g["lead_time_days"].mean().round().astype(int).values,
        "lead_time_sd_days": g["lead_time_sd_days"].mean().values,
        "ordering_cost": g["ordering_cost_per_order"].mean().values,
        "holding_rate": g["holding_rate"].mean().values,
        "availability_risk": g["availability"].mean().values,
        "supplier_count_risk": g["no_suppliers"].mean().values,
        "standardization_risk": g["standard"].mean().values,
        "price_volatility_risk": g["price_fluctuation"].mean().values,
        "safety_stock_min": 0,
        "reorder_point": 0,
    })
    prod.insert(0, "id", range(1, len(prod) + 1))
    t["products"] = prod
    pid = dict(zip(prod["sku"], prod["id"]))

    sups = sorted(df["supplier"].dropna().unique())
    sup = pd.DataFrame({"id": range(1, len(sups) + 1), "code": [f"SUP-{i:03d}" for i in range(1, len(sups) + 1)],
                        "name": sups, "lead_time_avg_days": df.groupby("supplier")["lead_time_days"].mean().round()
                        .reindex(sups).astype(int).values, "is_active": 1})
    t["suppliers"] = sup
    sid = dict(zip(sups, sup["id"]))
    primary = g["supplier"].agg(_mode)
    t["supplier_products"] = pd.DataFrame({
        "supplier_id": primary.map(sid).values, "product_id": primary.index.map(pid),
        "unit_cost": g["Cost"].mean().round(4).values, "lead_time_days": prod["lead_time_days"].values, "moq": 1})

    countries = sorted(df["Country"].unique())
    ta_by_country = df.groupby("Country")["Trade_Area_ID"].agg(_mode)
    t["warehouses"] = pd.DataFrame({"id": range(1, len(countries) + 1), "code": [c[:50] for c in countries],
                                    "name": countries, "location": [f"{c} ({ta_by_country.get(c, '')})" for c in countries],
                                    "capacity_sqft": 50000, "is_active": 1})
    wid = dict(zip(countries, t["warehouses"]["id"]))

    custs = sorted(df["Customer ID"].dropna().astype(int).unique())
    t["customers"] = pd.DataFrame({"id": range(1, len(custs) + 1), "customer_code": [str(c) for c in custs],
                                   "name": [f"Customer {c}" for c in custs], "tier": "STANDARD"})
    cid = dict(zip(custs, t["customers"]["id"]))

    df = df.assign(revenue=(df["Quantity"] * df["Price"]).round(4), product_id=df["StockCode"].map(pid),
                   warehouse_id=df["Country"].map(wid))
    inv = df.groupby("Invoice").agg(order_date=("InvoiceDate", "min"), customer=("Customer ID", "first"),
                                    country=("Country", "first"), total_amount=("revenue", "sum"))
    orders = pd.DataFrame({"id": range(1, len(inv) + 1), "order_number": inv.index.astype(str),
                           "customer_id": inv["customer"].map(lambda c: cid.get(int(c)) if pd.notna(c) else None).values,
                           "warehouse_id": inv["country"].map(wid).values, "order_date": inv["order_date"].values,
                           "status": "COMPLETED", "total_amount": inv["total_amount"].round(2).values})
    t["orders"] = orders
    oid = dict(zip(inv.index, orders["id"]))
    t["order_items"] = pd.DataFrame({"order_id": df["Invoice"].map(oid), "product_id": df["product_id"],
                                     "quantity": df["Quantity"].astype(int), "unit_price": df["Price"],
                                     "total_price": df["revenue"]})
    t["sales_history"] = pd.DataFrame({"product_id": df["product_id"], "warehouse_id": df["warehouse_id"],
                                       "date": df["InvoiceDate"], "quantity_sold": df["Quantity"].astype(int),
                                       "unit_price": df["Price"], "revenue": df["revenue"], "is_promotional": 0,
                                       "source_key": [f"retail:{i}" for i in df.index]})

    census = pd.read_excel(ta_xlsx, sheet_name="Trade_Area_Census")
    stores = pd.read_excel(ta_xlsx, sheet_name="Store_Attributes")
    dist = pd.read_excel(ta_xlsx, sheet_name="Distance_Matrix")
    t["trade_areas"] = pd.DataFrame({
        "code": census["Trade_Area_ID"], "country": census["Country"], "population": census["Population_SYN"],
        "households": census["Households_SYN"], "expenditure_per_household": census["Expenditure_Grocery_SYN"],
        "market_potential": census["Market_Potential_SYN"], "growth_rate": census["Growth_Rate_SYN"],
        "competition_index": census["Competition_Index_SYN"]})
    t["trade_area_stores"] = pd.DataFrame({
        "code": stores["Store_ID"], "name": stores["Store"], "size_sqft": stores["Size_SYN"],
        "parking_spaces": stores["Parking_Spaces_SYN"], "highways": stores["Highways_SYN"],
        "traffic": stores["Traffic_SYN"], "accessibility": stores["Accessibility_SYN"], "design": stores["Design_SYN"],
        "business_communities": stores["Business_Communities_SYN"], "attractiveness": stores["Attractiveness_Scaled"]})
    long = dist.melt(id_vars=["Trade_Area_ID", "Country"], var_name="col", value_name="distance")
    long["store_code"] = long["col"].str.extract(r"(S\d+)")[0]
    t["trade_area_distances"] = long.rename(columns={"Trade_Area_ID": "trade_area_code"})[
        ["trade_area_code", "store_code", "distance"]]
    return t


def wipe(engine, tables) -> None:
    with engine.begin() as conn:
        existing = set(engine.dialect.get_table_names(conn))
        tables = [x for x in tables if x in existing]
        if engine.dialect.name == "postgresql":
            conn.execute(text(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE"))
        else:
            for x in tables:
                conn.execute(text(f"DELETE FROM {x}"))
    print(f"Wiped {len(tables)} tables: {', '.join(tables)}")


def insert(engine, name: str, df: pd.DataFrame) -> None:
    from backend.app.core.database import Base
    table = Base.metadata.tables[name]
    df = df.astype(object).where(pd.notna(df), None)
    records = df.to_dict("records")
    for r in records:
        for k, v in r.items():
            if isinstance(v, np.generic):
                r[k] = v.item()
            elif isinstance(v, pd.Timestamp):
                r[k] = v.to_pydatetime()
    t0 = time.time()
    with engine.begin() as conn:
        for i in range(0, len(records), BATCH):
            conn.execute(table.insert().values(records[i:i + BATCH]))
        if engine.dialect.name == "postgresql" and "id" in df.columns:
            conn.execute(text(f"SELECT setval(pg_get_serial_sequence('{name}', 'id'), (SELECT MAX(id) FROM {name}))"))
    print(f"  {name}: {len(records):,} rows ({time.time() - t0:.1f}s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--wipe", action="store_true")
    ap.add_argument("--wipe-all", action="store_true")
    ap.add_argument("--database-url", help="defaults to DATABASE_URL from the backend settings")
    args = ap.parse_args()

    from backend.app.core.database import Base, add_missing_columns, engine as default_engine
    import backend.app.models.models  # noqa: F401
    engine = create_engine(args.database_url) if args.database_url else default_engine

    if args.download:
        download(args.data_dir)
    raw = pd.read_excel(os.path.join(args.data_dir, "Data.xlsx"))
    df = clean(raw)
    print(f"Data.xlsx: {len(raw):,} raw rows -> {len(df):,} clean rows")
    tables = build_tables(df, os.path.join(args.data_dir, "Trade_Area_Synthetic_Inputs.xlsx"))

    Base.metadata.create_all(bind=engine)
    add_missing_columns(engine)
    if args.wipe or args.wipe_all:
        wipe(engine, BUSINESS_TABLES + (ACCOUNT_TABLES if args.wipe_all else []))
    order = ["product_categories", "products", "suppliers", "supplier_products", "warehouses", "customers",
             "orders", "order_items", "sales_history", "trade_areas", "trade_area_stores", "trade_area_distances"]
    print("Loading:")
    for name in order:
        insert(engine, name, tables[name])
    print("Done.")


if __name__ == "__main__":
    main()
