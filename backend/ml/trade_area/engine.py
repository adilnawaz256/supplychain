"""Trade Area Modelling & Store Analysis Engine (Module 5).

The Huff Gravity model needs trade-area, distance and store-attribute data
that the database does not hold yet. This engine reports only real facts
(warehouses and their sales revenue) and lists the data still required;
it never invents scores, territories or distances.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.core.database import SessionLocal
from backend.app.models.models import Warehouse, SalesHistory


class TradeAreaModellingEngine:
    """Enterprise Trade Area Catchment & Store Gravity Modeling Engine."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def _get_db(self) -> Session:
        return self.db if self.db is not None else SessionLocal()

    MISSING_DATA = [
        "Trade-area (territory) table: one row per customer zone with its population or market potential (spend).",
        "Store-to-territory distance table: travel distance or time from each store/warehouse to each zone.",
        "Store attribute scores: measured attractiveness inputs per store (e.g. parking, traffic, accessibility, design).",
    ]

    HUFF_TRACE = {
        "methodology": "Huff Spatial Gravity Model",
        "huff_equation": "P(Store j | Zone i) = [Attractiveness_j / Distance_ij^lambda] / Sum_k[Attractiveness_k / Distance_ik^lambda]",
        "expected_capture_formula": "Expected capture_j = Sum_i [ Market potential_i x P(Store j | Zone i) ]",
    }

    def get_trade_area_intelligence(self) -> Dict[str, Any]:
        """Returns real store/revenue facts and reports which data the Huff model still needs.

        The database has no territory, distance or store-score tables, so the Huff
        gravity model is NOT computed; nothing is invented to fill the gap.
        """
        db = self._get_db()
        should_close = (self.db is None)

        try:
            warehouses = db.query(Warehouse).order_by(Warehouse.id).all()

            revenue_rows = (
                db.query(SalesHistory.warehouse_id, func.sum(SalesHistory.revenue))
                .group_by(SalesHistory.warehouse_id)
                .all()
            )
            revenue_by_wh = {wid: float(rev) for wid, rev in revenue_rows if rev is not None}
            total_revenue = sum(revenue_by_wh.values()) if revenue_by_wh else None

            store_colors = ["#2563eb", "#7c3aed", "#059669", "#d97706", "#dc2626"]  # UI palette only
            stores: List[Dict[str, Any]] = []
            for idx, wh in enumerate(warehouses):
                rev = revenue_by_wh.get(wh.id)
                share = (round(rev / total_revenue * 100, 1)
                         if rev is not None and total_revenue else None)
                stores.append({
                    "store_id": wh.code,
                    "store_name": wh.name,
                    "warehouse_code": wh.code,
                    "location": wh.location,
                    "size_sqft": int(wh.capacity_sqft) if wh.capacity_sqft is not None else None,
                    "revenue_usd": round(rev, 2) if rev is not None else None,
                    "revenue_share_pct": share,
                    "parking_spaces": None,
                    "highways": None,
                    "traffic_score": None,
                    "accessibility_score": None,
                    "design_score": None,
                    "business_communities": None,
                    "composite_attractiveness": None,
                    "status": None,
                    "color": store_colors[idx % len(store_colors)],
                    "calculation_trace": {
                        "data_source_tables": "warehouses (code, name, location, capacity_sqft), sales_history (warehouse_id, revenue)",
                        "explanation": "Size and revenue are real; attractiveness scores need store attribute data that is not in the database.",
                    },
                })

            stores_with_rev = [s for s in stores if s["revenue_usd"] is not None]
            top_revenue_store = (max(stores_with_rev, key=lambda s: s["revenue_usd"])["store_name"]
                                 if stores_with_rev else None)

            message = (
                f"Found {len(stores)} store(s)/warehouse(s) and their real sales revenue. "
                "The Huff store-catchment model cannot be calculated yet because the database has no "
                "trade-area, distance or store-score tables. Add that data to enable it."
            )

            return {
                "module_name": "Trade Area Modelling & Store Analysis",
                "module_key": "trade_area",
                "status": "NEEDS_DATA",
                "missing_data": list(self.MISSING_DATA),
                "message": message,
                "database_info": {
                    "is_connected": True,
                    "source": "Internal database (warehouses, sales_history)",
                    "stores_evaluated": len(stores),
                    "trade_areas_modeled": 0,
                    "fallback_used": False,
                },
                "calculation_trace": {
                    **self.HUFF_TRACE,
                    "data_source_tables": "warehouses (code, name, location, capacity_sqft), sales_history (warehouse_id, revenue)",
                    "explanation": (
                        "The Huff model needs, for every customer zone, its market potential and its distance to every store, "
                        "plus an attractiveness score per store. None of these exist in the database yet "
                        "(no territory, distance or store-score tables), so no capture probabilities are calculated. "
                        "Only store names, sizes and real sales revenue are shown."
                    ),
                },
                "summary": {
                    "trade_areas_count": 0,
                    "competing_stores_count": len(stores),
                    "total_market_potential_usd": None,
                    "total_actual_revenue_usd": round(total_revenue, 2) if total_revenue is not None else None,
                    "highest_attractiveness_store": None,
                    "top_revenue_store": top_revenue_store,
                    "primary_model": "Huff Gravity Model (not calculated: missing data)",
                },
                "stores": stores,
                "store_capture_distribution": [],
                "trade_areas": [],
                "recommendations": [],
            }
        finally:
            if should_close:
                db.close()
