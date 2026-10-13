import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.models.models import Product, Inventory, Supplier, PurchaseOrder
from backend.ml.risk.engine import InventoryRiskEngine
from backend.ml.procurement.engine import ProcurementOptimizerEngine
from backend.ml.assortment.engine import AssortmentOptimizerEngine

UNIFIED_REC_CACHE: Dict[str, Any] = {"timestamp": 0, "data": []}

class UnifiedRecommendationEngine:
    """
    Standardized Recommendation Engine for Wisualyst Platform.
    Aggregates and standardizes intelligence insights across Inventory AI, Demand AI, Procurement AI, and Assortment AI.
    """
    def __init__(self, db: Session):
        self.db = db
        self.risk_engine = InventoryRiskEngine(db)
        self.procurement_engine = ProcurementOptimizerEngine(db)
        self.assortment_engine = AssortmentOptimizerEngine(db)

    def get_unified_recommendations(self) -> List[Dict[str, Any]]:
        global UNIFIED_REC_CACHE
        now = time.time()
        if (now - UNIFIED_REC_CACHE["timestamp"]) < 30 and UNIFIED_REC_CACHE["data"]:
            return UNIFIED_REC_CACHE["data"]

        recommendations = []
        rec_counter = 1

        # Real unit costs in one query (risk results carry no unit_cost)
        unit_cost_map = {pid: cost for pid, cost in self.db.query(Product.id, Product.unit_cost).all()}

        # 1. Inventory & Stockout Risk Recommendations
        risks = self.risk_engine.get_all_inventory_risks()
        for r in risks:
            if r["stockout_risk_level"] in ["CRITICAL", "HIGH"]:
                qty = r.get("recommended_order_quantity")
                unit_cost = unit_cost_map.get(r["product_id"])
                impact = round(float(qty) * float(unit_cost), 2) if (qty is not None and unit_cost) else None
                doi = r.get("days_of_inventory")
                summary = (
                    f"Product {r['sku']} has {doi} days of stock remaining at {r['warehouse_name']}"
                    if doi is not None else
                    f"Product {r['sku']} has {r['current_stock']} units at {r['warehouse_name']} (no sales history, days of stock unknown)"
                )
                lead = f" Lead time is {r['lead_time_days']} days." if r.get("lead_time_days") is not None else ""
                recommendations.append({
                    "recommendation_id": f"REC_INV_{rec_counter:03d}",
                    "module": "inventory",
                    "entity_type": "sku",
                    "entity_id": r["sku"],
                    "severity": "critical" if r["stockout_risk_level"] == "CRITICAL" else "high",
                    "title": f"Stockout Risk: {r['product_name']}",
                    "summary": summary,
                    "reason": r.get("reasoning", "") + lead,
                    "financial_impact": impact,
                    "financial_impact_basis": (
                        f"order value = {qty} units * {unit_cost} unit cost" if impact is not None else "unit cost or order quantity unknown"
                    ),
                    "confidence": None,
                    "recommended_action": f"Issue purchase order for {qty} units." if qty else "Review stock position; no order quantity computed.",
                    "alternative_action": None,
                    "status": "open"
                })
                rec_counter += 1

        # 2. Procurement & EOQ Recommendations
        proc_intel = self.procurement_engine.generate_procurement_intelligence()
        for po_rec in proc_intel.get("order_recommendations", []):
            supplier_txt = f" with supplier {po_rec['supplier_name']}" if po_rec.get("supplier_name") else " (no supplier linked in supplier_products)"
            otif_txt = f" Supplier OTIF is {po_rec['supplier_otif']}%." if po_rec.get("supplier_otif") is not None else ""
            recommendations.append({
                "recommendation_id": f"REC_PROC_{rec_counter:03d}",
                "module": "procurement",
                "entity_type": "sku",
                "entity_id": po_rec["sku"],
                "severity": po_rec["urgency"].lower(),
                "title": f"EOQ Purchase Order Recommendation for {po_rec['product_name']}",
                "summary": f"Place PO of {po_rec['recommended_po_qty']} units{supplier_txt}",
                "reason": (
                    f"{len(po_rec.get('warehouses_at_or_below_rop') or [])} warehouse(s) at/below reorder point {po_rec['reorder_point']}; "
                    f"total available stock is {po_rec['current_stock']} units.{otif_txt}"
                ),
                "financial_impact": po_rec["potential_savings"],
                "financial_impact_basis": (
                    "yearly ordering+holding cost saving vs current reorder quantity"
                    if po_rec["potential_savings"] is not None else "current order quantity unknown, saving not computed"
                ),
                "confidence": None,
                "recommended_action": f"Issue purchase order for {po_rec['recommended_po_qty']} units (Est. cost {po_rec['estimated_order_cost']}).",
                "alternative_action": None,
                "status": "open"
            })
            rec_counter += 1

        # 3. Retail Assortment & Space Recommendations
        assort_intel = self.assortment_engine.generate_assortment_intelligence()
        for item in assort_intel.get("sku_assortment", []):
            if item["classification"] in ["UNDERPERFORMER", "SLOW_MOVER"]:
                recommendations.append({
                    "recommendation_id": f"REC_ASST_{rec_counter:03d}",
                    "module": "assortment",
                    "entity_type": "sku",
                    "entity_id": item["sku"],
                    "severity": "medium",
                    "title": f"Reallocate Shelf Space for {item['product_name']}",
                    "summary": f"Product {item['sku']} is generating {item['revenue_per_sqm']}/sqm revenue (GMROI {item['gmroi']}) over the last 90 days",
                    "reason": f"Occupying {item['allocated_space_sqm']} sqm with sell-through of {item['sell_through_pct']}% ({item['units_sold_90d']} units, revenue {item['revenue_90d']} in the window).",
                    "financial_impact": None,
                    "financial_impact_basis": "not computable: no data on revenue gained from reallocated space",
                    "confidence": None,
                    "recommended_action": f"Review the {item['allocated_space_sqm']} sqm allocated to {item['sku']} (classified {item['classification']}).",
                    "alternative_action": None,
                    "status": "open"
                })
                rec_counter += 1

        return recommendations
