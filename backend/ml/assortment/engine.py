from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models.models import Product, ProductCategory, RetailSpace, Inventory, SalesHistory

# Business settings (no table holds these); reported under "settings"
WINDOW_DAYS = 90
STAR_MIN_GMROI = 3.0
STAR_MIN_SELL_THROUGH_PCT = 70.0
CORE_MIN_GMROI = 1.5
UNDERPERFORMER_MAX_SELL_THROUGH_PCT = 40.0


def _to_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


class AssortmentOptimizerEngine:
    """
    Module 8: Retail Assortment & Space Optimizer Engine.
    Calculates GMROI (Gross Margin Return on Investment), sell-through rates,
    space productivity (Revenue / Sq. Meter), display unit utilization, and space allocation optimization.
    """
    def __init__(self, db: Session):
        self.db = db

    def generate_assortment_intelligence(self) -> Dict[str, Any]:
        products = self.db.query(Product).all()

        # Bulk-fetch categories in 1 query
        cat_rows = self.db.query(ProductCategory).all()
        cat_map = {c.id: c.name for c in cat_rows}

        # Bulk-fetch retail space per product in 1 query instead of N+1 per-product lookups
        space_rows = self.db.query(RetailSpace).all()
        space_map = {sp.product_id: sp for sp in space_rows}

        # Sales window: the last WINDOW_DAYS days up to the latest sale date in sales_history
        latest_sale = _to_dt(self.db.query(func.max(SalesHistory.date)).scalar())
        window_start = latest_sale - timedelta(days=WINDOW_DAYS) if latest_sale else None
        sales_map: Dict[int, Any] = {}
        if latest_sale is not None:
            sales_rows = self.db.query(
                SalesHistory.product_id,
                func.sum(SalesHistory.quantity_sold),
                func.sum(SalesHistory.revenue)
            ).filter(SalesHistory.date > window_start, SalesHistory.date <= latest_sale)\
             .group_by(SalesHistory.product_id).all()
            sales_map = {row[0]: (row[1] or 0, row[2] or 0.0) for row in sales_rows}
        window_label = (
            f"{window_start.date().isoformat()} (exclusive) to {latest_sale.date().isoformat()} ({WINDOW_DAYS} days up to the latest sale)"
            if latest_sale else None
        )

        sku_assortment = []
        excluded = []
        total_allocated_sqm = 0.0
        total_revenue = 0.0

        for p in products:
            sp = space_map.get(p.id)
            if sp is None or not sp.allocated_space_sqm or sp.allocated_space_sqm <= 0:
                excluded.append({"product_id": p.id, "sku": p.sku, "reason": "no retail_spaces row with allocated_space_sqm > 0"})
                continue
            allocated_sqm = float(sp.allocated_space_sqm)
            display_units = sp.display_units
            shelf_cap = sp.shelf_capacity
            total_allocated_sqm += allocated_sqm

            qty_sold, revenue = sales_map.get(p.id, (0, 0.0))
            total_revenue += revenue

            # Gross Margin & GMROI (needs display units and unit cost to value inventory)
            if p.selling_price is not None and p.unit_cost is not None:
                gross_margin = p.selling_price - p.unit_cost
                total_margin = gross_margin * qty_sold
            else:
                total_margin = None
            avg_inv_val = float(display_units * p.unit_cost) if (display_units and p.unit_cost) else None
            gmroi = round(total_margin / avg_inv_val, 2) if (total_margin is not None and avg_inv_val) else None

            # Sell-Through Rate
            denom = qty_sold + (display_units or 0)
            sell_through_pct = round(qty_sold / denom * 100.0, 1) if (denom > 0 and display_units is not None) else None

            rev_per_sqm = round(revenue / allocated_sqm, 2)

            # Productivity Classification (cutoffs are settings)
            if gmroi is None or sell_through_pct is None:
                classif = "INSUFFICIENT_DATA"
            elif gmroi >= STAR_MIN_GMROI and sell_through_pct >= STAR_MIN_SELL_THROUGH_PCT:
                classif = "STAR_PRODUCT"
            elif gmroi >= CORE_MIN_GMROI:
                classif = "CORE_STABLE"
            elif sell_through_pct < UNDERPERFORMER_MAX_SELL_THROUGH_PCT:
                classif = "UNDERPERFORMER"
            else:
                classif = "SLOW_MOVER"

            sku_assortment.append({
                "product_id": p.id,
                "sku": p.sku,
                "product_name": p.name,
                "category": cat_map.get(p.category_id) if p.category_id is not None else (sp.category or None),
                "allocated_space_sqm": allocated_sqm,
                "display_units": display_units,
                "shelf_capacity": shelf_cap,
                "space_utilization_pct": round((display_units / shelf_cap) * 100.0, 1) if (shelf_cap and display_units is not None) else None,
                "units_sold_90d": qty_sold,
                "revenue_90d": round(revenue, 2),
                "revenue_per_sqm": rev_per_sqm,
                "gmroi": gmroi,
                "sell_through_pct": sell_through_pct,
                "classification": classif,
                "calculation_trace": {
                    "sales_window": window_label,
                    "gmroi_formula": "GMROI = ((Selling Price - Unit Cost) * Units Sold) / (Display Units * Unit Cost)",
                    "sell_through_formula": "Sell-Through = (Units Sold / (Units Sold + Display Units)) * 100%",
                    "revenue_per_sqm_formula": "Revenue / Allocated Square Meters",
                    "calculated_gmroi": gmroi,
                    "calculated_sell_through": f"{sell_through_pct}%" if sell_through_pct is not None else None,
                    "calculated_rev_per_sqm": f"${rev_per_sqm}",
                    "data_source_tables": "retail_spaces (allocated_space_sqm, display_units), products (unit_cost, selling_price), sales_history (quantity_sold, revenue)"
                }
            })

        # Sort SKUs by revenue productivity
        sku_assortment.sort(key=lambda x: x["revenue_per_sqm"], reverse=True)

        gmrois = [x["gmroi"] for x in sku_assortment if x["gmroi"] is not None]
        sts = [x["sell_through_pct"] for x in sku_assortment if x["sell_through_pct"] is not None]
        avg_gmroi = round(sum(gmrois) / len(gmrois), 2) if gmrois else None
        avg_sell_through = round(sum(sts) / len(sts), 1) if sts else None
        low_productivity_count = sum(1 for x in sku_assortment if x["classification"] in ["UNDERPERFORMER", "SLOW_MOVER"])

        return {
            "module_name": "Retail Assortment & Space Optimizer",
            "module_key": "assortment",
            "database_info": {
                "is_connected": True,
                "source": "Connected PostgreSQL Database",
                "products_evaluated": len(sku_assortment),
                "products_excluded": len(excluded),
                "sales_window": window_label,
                "total_allocated_sqm": round(total_allocated_sqm, 1),
                "fallback_used": False
            },
            "settings": {
                "window_days": WINDOW_DAYS,
                "star_min_gmroi": STAR_MIN_GMROI,
                "star_min_sell_through_pct": STAR_MIN_SELL_THROUGH_PCT,
                "core_min_gmroi": CORE_MIN_GMROI,
                "underperformer_max_sell_through_pct": UNDERPERFORMER_MAX_SELL_THROUGH_PCT,
            },
            "calculation_trace": {
                "methodology": "Space Productivity & GMROI Space-Allocation Optimization",
                "gmroi_equation": "GMROI = Gross Margin $ in window / (Display Units * Unit Cost)",
                "sales_window": window_label,
                "classification_rules": (
                    f"STAR: GMROI >= {STAR_MIN_GMROI} and sell-through >= {STAR_MIN_SELL_THROUGH_PCT}%; "
                    f"CORE: GMROI >= {CORE_MIN_GMROI}; UNDERPERFORMER: sell-through < {UNDERPERFORMER_MAX_SELL_THROUGH_PCT}%; else SLOW_MOVER"
                ),
                "sell_through_equation": "Sell-Through Rate = [Units Sold / (Units Sold + Shelf Display Units)] * 100%",
                "rev_per_sqm_equation": "Revenue Productivity = Total Category Revenue / Allocated Linear Shelf Space (sqm)",
                "data_source_tables": "retail_spaces (allocated_space_sqm, display_units), products (selling_price, unit_cost), sales_history",
                "explanation": "Calculates space elasticity to reallocate low-productivity shelf space to high-GMROI star products."
            },
            "total_allocated_space_sqm": round(total_allocated_sqm, 1),
            "avg_store_gmroi": avg_gmroi,
            "avg_sell_through_pct": avg_sell_through,
            "revenue_per_sqm_avg": round(total_revenue / total_allocated_sqm, 2) if total_allocated_sqm > 0 else None,
            "low_productivity_sku_count": low_productivity_count,
            "sku_assortment": sku_assortment,
            "excluded": excluded
        }
