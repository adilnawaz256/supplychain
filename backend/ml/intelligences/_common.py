"""Shared data loading, formatting and payload helpers for the 9 intelligences."""
import math
from statistics import NormalDist
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

CURRENCY = "$"
ORDER_COST = 50.0          # cost of placing one purchase order
HOLDING_RATE = 0.20        # yearly holding cost as a share of unit cost
COST_FALLBACK_RATIO = 0.6  # unit cost = 60% of price when the product has no cost


class NeedsData(Exception):
    """Raised when the tables an intelligence needs are empty."""


class Data:
    """Lazily loads the tables the intelligences read, once per calculation."""

    def __init__(self, db: Session):
        self.bind = db.get_bind()
        self._cache: Dict[str, pd.DataFrame] = {}

    def _q(self, key: str, sql: str, dates: tuple = ()) -> pd.DataFrame:
        if key not in self._cache:
            with self.bind.connect() as conn:
                df = pd.read_sql(text(sql), conn)
            for col in dates:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            self._cache[key] = df
        return self._cache[key]

    @property
    def products(self) -> pd.DataFrame:
        return self._q("products", """
            SELECT p.id AS product_id, p.sku, p.name, p.unit_cost, p.selling_price, p.lead_time_days,
                   p.lead_time_sd_days, p.ordering_cost, p.holding_rate, p.availability_risk,
                   p.supplier_count_risk, p.standardization_risk, p.price_volatility_risk,
                   COALESCE(c.name, 'General') AS category
            FROM products p LEFT JOIN product_categories c ON c.id = p.category_id""")

    @property
    def trade_areas(self) -> pd.DataFrame:
        return self._q("trade_areas", "SELECT code, country, population, households, market_potential, growth_rate, "
                                      "competition_index FROM trade_areas")

    @property
    def trade_area_stores(self) -> pd.DataFrame:
        return self._q("trade_area_stores", "SELECT code, name, size_sqft, attractiveness FROM trade_area_stores")

    @property
    def trade_area_distances(self) -> pd.DataFrame:
        return self._q("trade_area_distances", "SELECT trade_area_code, store_code, distance FROM trade_area_distances")

    @property
    def sales(self) -> pd.DataFrame:
        df = self._q("sales", """
            SELECT product_id, warehouse_id, date, quantity_sold AS qty, unit_price AS price, revenue
            FROM sales_history""", dates=("date",))
        return df.dropna(subset=["date"])

    @property
    def inventory(self) -> pd.DataFrame:
        return self._q("inventory", """
            SELECT product_id, SUM(current_stock) AS stock FROM inventory GROUP BY product_id""")

    @property
    def warehouses(self) -> pd.DataFrame:
        return self._q("warehouses", "SELECT id AS warehouse_id, code, name, location, capacity_sqft FROM warehouses")

    @property
    def orders(self) -> pd.DataFrame:
        return self._q("orders", """
            SELECT o.id AS order_id, o.customer_id, o.warehouse_id, o.order_date, o.total_amount,
                   c.customer_code, c.name AS customer_name
            FROM orders o LEFT JOIN customers c ON c.id = o.customer_id""", dates=("order_date",))

    @property
    def order_items(self) -> pd.DataFrame:
        return self._q("order_items", "SELECT order_id, product_id, quantity, total_price FROM order_items")

    @property
    def suppliers(self) -> pd.DataFrame:
        return self._q("suppliers", """
            SELECT id AS supplier_id, code, name, lead_time_avg_days, rating, otif_score FROM suppliers""")

    @property
    def supplier_products(self) -> pd.DataFrame:
        return self._q("supplier_products", """
            SELECT supplier_id, product_id, unit_cost, lead_time_days, moq FROM supplier_products""")

    @property
    def purchase_orders(self) -> pd.DataFrame:
        return self._q("purchase_orders", "SELECT supplier_id, total_cost FROM purchase_orders")

    @property
    def retail_spaces(self) -> pd.DataFrame:
        return self._q("retail_spaces", """
            SELECT store_id, product_id, category, allocated_space_sqm FROM retail_spaces""")

    def product_costs(self) -> pd.DataFrame:
        """Products with a usable unit cost (falls back to a share of the average selling price)."""
        p = self.products.copy()
        for c in ["unit_cost", "selling_price", "lead_time_days", "lead_time_sd_days", "ordering_cost", "holding_rate",
                  "availability_risk", "supplier_count_risk", "standardization_risk", "price_volatility_risk"]:
            p[c] = pd.to_numeric(p[c], errors="coerce")
        s = self.sales
        if not s.empty:
            avg_price = s.groupby("product_id")["revenue"].sum() / s.groupby("product_id")["qty"].sum().replace(0, np.nan)
            p["avg_price"] = p["product_id"].map(avg_price)
        else:
            p["avg_price"] = np.nan
        p["avg_price"] = p["avg_price"].fillna(p["selling_price"]).fillna(0.0)
        p["unit_cost"] = p["unit_cost"].where(p["unit_cost"] > 0, p["avg_price"] * COST_FALLBACK_RATIO)
        p["lead_time_days"] = p["lead_time_days"].fillna(7).clip(lower=1)
        p["lead_time_sd_days"] = p["lead_time_sd_days"].fillna(0.0)
        p["ordering_cost"] = p["ordering_cost"].where(p["ordering_cost"] > 0, ORDER_COST)
        p["holding_rate"] = p["holding_rate"].where(p["holding_rate"] > 0, HOLDING_RATE)
        return p


# --- formatting (used for KPI text; tables send raw numbers) ---------------------------------

def money(v: Optional[float]) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    v = float(v)
    sign = "-" if v < 0 else ""
    a = abs(v)
    if a >= 1_000_000_000:
        return f"{sign}{CURRENCY}{a / 1e9:.1f}B"
    if a >= 1_000_000:
        return f"{sign}{CURRENCY}{a / 1e6:.2f}M"
    if a >= 10_000:
        return f"{sign}{CURRENCY}{a / 1e3:.1f}K"
    if a >= 100:
        return f"{sign}{CURRENCY}{a:,.0f}"
    return f"{sign}{CURRENCY}{a:,.2f}"


def num(v: Optional[float], dp: int = 0) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    v = float(v)
    if abs(v) >= 1_000_000:
        return f"{v / 1e6:.2f}M"
    return f"{v:,.{dp}f}"


def pct(v: Optional[float], dp: int = 1, signed: bool = False) -> str:
    """v is already in percent units (12.5 -> '12.5%')."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:+.{dp}f}%" if signed else f"{v:.{dp}f}%"


def z_score(service_level: float) -> float:
    return NormalDist().inv_cdf(min(max(service_level, 0.5), 0.999))


def abc_class(values: pd.Series, a: float = 0.80, b: float = 0.95) -> pd.Series:
    """A = items making up the first 80% of the total, B = next 15%, C = the rest."""
    order = values.sort_values(ascending=False)
    total = order.sum()
    if total <= 0:
        return pd.Series("C", index=values.index)
    cum = order.cumsum() / total
    prev = cum.shift(fill_value=0)
    cls = np.where(prev < a, "A", np.where(prev < b, "B", "C"))
    return pd.Series(cls, index=order.index).reindex(values.index)


def demand_class(series: np.ndarray, adi_cut: float = 1.32, cv2_cut: float = 0.49) -> str:
    """Syntetos-Boylan classification from a zero-filled demand series."""
    nz = series[series > 0]
    if len(nz) == 0:
        return "No demand"
    adi = len(series) / len(nz)
    cv2 = (nz.std() / nz.mean()) ** 2 if len(nz) > 1 and nz.mean() > 0 else 0.0
    if adi < adi_cut:
        return "Smooth" if cv2 < cv2_cut else "Erratic"
    return "Intermittent" if cv2 < cv2_cut else "Lumpy"


def short(name: Any, n: int = 28) -> str:
    s = str(name or "")
    return s if len(s) <= n else s[: n - 1] + "…"


def clean(obj: Any) -> Any:
    """Make a payload JSON-safe: numpy scalars to Python, NaN/inf to None, floats rounded."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 4)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    if obj is pd.NaT:
        return None
    return obj


def kpi(label: str, value: str, sub: str = "", tone: str = "neutral", icon: str = "box",
        trend: Optional[str] = None) -> Dict[str, Any]:
    """tone: good | bad | warn | info | neutral; trend: up | down | None (arrow next to sub)."""
    return {"label": label, "value": value, "sub": sub, "tone": tone, "icon": icon, "trend": trend}


def col(key: str, label: str, fmt: str = "text", **extra) -> Dict[str, Any]:
    """fmt: text | int | num | num2 | money | pct | pct_signed | pp | days | pill | trend | bold_int."""
    return {"key": key, "label": label, "format": fmt, **extra}


def page(*, input_: Dict[str, str], algorithm: Dict[str, str], output: Dict[str, str],
         kpis: List[Dict], charts: List[Dict], table: Dict[str, Any], notes: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"status": "ready", "pipeline": {"input": input_, "algorithm": algorithm, "output": output},
            "kpis": kpis, "charts": charts, "table": table, "notes": notes or []}


def date_range_text(s: pd.Series) -> str:
    if s.empty:
        return ""
    return f"{s.min():%d %b %Y} – {s.max():%d %b %Y}"
