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
from backend.app.models.models import Warehouse, SalesHistory, TradeArea, TradeAreaStore, TradeAreaDistance

DISTANCE_DECAY = 2.0
STORE_COLORS = ["#2563eb", "#7c3aed", "#059669", "#d97706", "#dc2626"]  # UI palette only


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

    def _huff(self, db: Session) -> Optional[Dict[str, Any]]:
        """Huff gravity model over trade_areas, trade_area_stores and trade_area_distances; None if any is empty."""
        try:
            areas = db.query(TradeArea).order_by(TradeArea.code).all()
            stores = db.query(TradeAreaStore).order_by(TradeAreaStore.code).all()
            dist_rows = db.query(TradeAreaDistance).all()
        except Exception:  # tables not created yet on this database
            db.rollback()
            return None
        if not (areas and stores and dist_rows):
            return None

        dist = {(d.trade_area_code, d.store_code): float(d.distance) for d in dist_rows}
        attract = {s.code: float(s.attractiveness if s.attractiveness is not None else (s.size_sqft or 0)) for s in stores}

        # Actual revenue per trade area: sales of the warehouse named after the area's country.
        revenue_rows = (
            db.query(Warehouse.name, func.sum(SalesHistory.revenue))
            .join(SalesHistory, SalesHistory.warehouse_id == Warehouse.id)
            .group_by(Warehouse.name)
            .all()
        )
        revenue_by_country = {name: float(rev or 0) for name, rev in revenue_rows}

        capture = {s.code: 0.0 for s in stores}
        area_rows: List[Dict[str, Any]] = []
        for a in areas:
            pulls = {}
            for s in stores:
                d = dist.get((a.code, s.code))
                if d is not None:
                    pulls[s.code] = attract[s.code] / max(d, 0.1) ** DISTANCE_DECAY
            total_pull = sum(pulls.values())
            if total_pull <= 0:
                continue
            potential = float(a.market_potential or 0)
            shares = {c: p / total_pull for c, p in pulls.items()}
            for c, sh in shares.items():
                capture[c] += sh * potential
            winner = max(shares, key=shares.get)
            area_rows.append({
                "trade_area_code": a.code,
                "country": a.country,
                "population": a.population,
                "market_potential_usd": round(potential, 2),
                "growth_rate_pct": round(a.growth_rate * 100, 2) if a.growth_rate is not None else None,
                "competition_index": a.competition_index,
                "actual_revenue_usd": round(revenue_by_country.get(a.country, 0.0), 2),
                "store_probabilities_pct": {c: round(sh * 100, 1) for c, sh in shares.items()},
                "distances": {c: dist.get((a.code, c)) for c in shares},
                "most_likely_store": next(s.name for s in stores if s.code == winner),
            })
        if not area_rows:
            return None

        total_potential = sum(r["market_potential_usd"] for r in area_rows)
        ranked = sorted(stores, key=lambda s: capture[s.code], reverse=True)
        out_stores = []
        for idx, s in enumerate(stores):
            cap = capture[s.code]
            share = round(cap / total_potential * 100, 1) if total_potential else None
            rank = ranked.index(s)
            out_stores.append({
                "store_id": s.code,
                "store_name": s.name,
                "warehouse_code": s.code,
                "location": None,
                "size_sqft": s.size_sqft,
                "revenue_usd": None,
                "revenue_share_pct": None,
                "parking_spaces": s.parking_spaces,
                "highways": s.highways,
                "traffic_score": s.traffic,
                "accessibility_score": s.accessibility,
                "design_score": s.design,
                "business_communities": s.business_communities,
                "composite_attractiveness": round(attract[s.code], 2),
                "expected_capture_usd": round(cap, 2),
                "market_share_pct": share,
                "status": "MARKET LEADER" if rank == 0 else ("UNDERPERFORMING" if rank == len(stores) - 1 else "COMPETITIVE"),
                "color": STORE_COLORS[idx % len(STORE_COLORS)],
                "calculation_trace": {
                    "data_source_tables": "trade_area_stores (attractiveness, size, parking, highways, scores), trade_area_distances, trade_areas (market_potential)",
                    "explanation": f"Pull on each area = attractiveness / distance^{DISTANCE_DECAY:g}; capture = share x market potential, summed over {len(area_rows)} areas.",
                },
            })

        leader, weakest = ranked[0], ranked[-1]
        top_attr = max(stores, key=lambda s: attract[s.code])
        recommendations = [
            {"store": leader.name, "action": "Maintain",
             "reason": f"Captures the most market potential (${capture[leader.code]:,.0f})."},
            {"store": weakest.name, "action": "Review location",
             "reason": f"Captures the least (${capture[weakest.code]:,.0f}); its distance and attractiveness lose most areas."},
        ]
        return {
            "module_name": "Trade Area Modelling & Store Analysis",
            "module_key": "trade_area",
            "status": "READY",
            "missing_data": [],
            "message": (f"Huff model over {len(area_rows)} trade areas and {len(stores)} stores: "
                        f"{leader.name} captures the most market potential, {weakest.name} the least."),
            "database_info": {
                "is_connected": True,
                "source": "Internal database (trade_areas, trade_area_stores, trade_area_distances, sales_history)",
                "stores_evaluated": len(stores),
                "trade_areas_modeled": len(area_rows),
                "fallback_used": False,
            },
            "calculation_trace": {
                **self.HUFF_TRACE,
                "distance_decay_lambda": DISTANCE_DECAY,
                "data_source_tables": "trade_areas (market_potential), trade_area_stores (attractiveness), trade_area_distances (distance), sales_history (revenue)",
                "explanation": ("Store attributes, distances and market potential come from the trade-area input file; "
                                "treat the result as a model, not as observed visits."),
            },
            "summary": {
                "trade_areas_count": len(area_rows),
                "competing_stores_count": len(stores),
                "total_market_potential_usd": round(total_potential, 2),
                "total_actual_revenue_usd": round(sum(r["actual_revenue_usd"] for r in area_rows), 2),
                "highest_attractiveness_store": top_attr.name,
                "top_capture_store": leader.name,
                "top_revenue_store": None,
                "primary_model": "Huff Gravity Model",
            },
            "stores": out_stores,
            "store_capture_distribution": [
                {"store_id": s.code, "store_name": s.name, "expected_capture_usd": round(capture[s.code], 2),
                 "market_share_pct": round(capture[s.code] / total_potential * 100, 1) if total_potential else None}
                for s in ranked
            ],
            "trade_areas": sorted(area_rows, key=lambda r: r["market_potential_usd"], reverse=True),
            "recommendations": recommendations,
        }

    def get_trade_area_intelligence(self) -> Dict[str, Any]:
        """Runs the Huff model when the trade-area tables hold data; otherwise returns real
        store/revenue facts and lists the data the model still needs (nothing is invented)."""
        db = self._get_db()
        should_close = (self.db is None)

        try:
            huff = self._huff(db)
            if huff is not None:
                return huff

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
