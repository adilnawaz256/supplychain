from typing import Dict, Any, List, Optional
from datetime import datetime
import math
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.models.models import Product, Supplier, SupplierProduct, PurchaseOrder, Inventory, SalesHistory

# Business settings that no database table contains. They are reported in the output
# under "settings" so every number shown can be traced back to these values.
ORDER_COST_PER_PO = 50.0           # cost of placing one purchase order (currency units)
HOLDING_COST_RATE_PER_YEAR = 0.15  # yearly holding cost as a fraction of unit cost
OPEN_PO_STATUSES = ("PENDING", "ISSUED", "OPEN")
OTIF_LOW_RISK_MIN_PCT = 90.0       # supplier OTIF >= this -> LOW risk
OTIF_MEDIUM_RISK_MIN_PCT = 80.0    # supplier OTIF >= this -> MEDIUM risk, below -> HIGH


def _to_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _yearly_cost(annual_demand: float, order_qty: float, unit_cost: float) -> float:
    """Yearly ordering + holding cost for a fixed order quantity Q."""
    return (annual_demand / order_qty) * ORDER_COST_PER_PO + (order_qty / 2.0) * unit_cost * HOLDING_COST_RATE_PER_YEAR


class ProcurementOptimizerEngine:
    """
    Module 4: Intelligent Procurement AI Engine.
    Calculates EOQ (Economic Order Quantity) from real sales demand, supplier OTIF metrics
    from the suppliers table, and the yearly cost difference between the current order
    quantity and EOQ.
    """
    def __init__(self, db: Session):
        self.db = db

    def generate_procurement_intelligence(self) -> Dict[str, Any]:
        products = self.db.query(Product).all()
        suppliers = self.db.query(Supplier).all()
        supplier_by_id = {s.id: s for s in suppliers}

        settings = {
            "order_cost_per_po": ORDER_COST_PER_PO,
            "holding_cost_rate_per_year": HOLDING_COST_RATE_PER_YEAR,
            "open_po_statuses": list(OPEN_PO_STATUSES),
            "otif_low_risk_min_pct": OTIF_LOW_RISK_MIN_PCT,
            "otif_medium_risk_min_pct": OTIF_MEDIUM_RISK_MIN_PCT,
        }

        # Stock per product across warehouses (available = current - reserved), plus the
        # configured reorder quantities used as the "current order quantity".
        stock_map: Dict[int, int] = {}
        wh_avail_map: Dict[int, List[Any]] = {}
        reorder_qty_map: Dict[int, List[int]] = {}
        for product_id, wh_id, current_stock, reserved_stock, reorder_quantity in self.db.query(
            Inventory.product_id, Inventory.warehouse_id, Inventory.current_stock, Inventory.reserved_stock, Inventory.reorder_quantity
        ).all():
            available = (current_stock or 0) - (reserved_stock or 0)
            stock_map[product_id] = stock_map.get(product_id, 0) + available
            wh_avail_map.setdefault(product_id, []).append((wh_id, available))
            if reorder_quantity is not None and reorder_quantity > 0:
                reorder_qty_map.setdefault(product_id, []).append(int(reorder_quantity))

        # Open purchase order value (only open statuses)
        total_open_po_cost = float(
            self.db.query(func.coalesce(func.sum(PurchaseOrder.total_cost), 0.0))
            .filter(func.upper(PurchaseOrder.status).in_(OPEN_PO_STATUSES))
            .scalar() or 0.0
        )

        # Real demand per product from sales_history
        sales_map: Dict[int, Dict[str, Any]] = {}
        for pid, total_qty, first_day, last_day in self.db.query(
            SalesHistory.product_id,
            func.sum(SalesHistory.quantity_sold),
            func.min(SalesHistory.date),
            func.max(SalesHistory.date),
        ).group_by(SalesHistory.product_id).all():
            first_dt, last_dt = _to_dt(first_day), _to_dt(last_day)
            if first_dt is None or last_dt is None:
                continue
            span_days = (last_dt.date() - first_dt.date()).days + 1
            sales_map[pid] = {
                "units_sold": float(total_qty or 0),
                "span_days": span_days,
                "first_date": first_dt.date().isoformat(),
                "last_date": last_dt.date().isoformat(),
            }

        # Supplier link per product: cheapest supplier_products row
        link_map: Dict[int, Any] = {}
        for link in self.db.query(SupplierProduct).all():
            current = link_map.get(link.product_id)
            if current is None or (link.unit_cost is not None and (current.unit_cost is None or link.unit_cost < current.unit_cost)):
                link_map[link.product_id] = link

        supplier_performance = []
        for s in suppliers:
            otif = s.otif_score
            if otif is None:
                risk = None
            elif otif >= OTIF_LOW_RISK_MIN_PCT:
                risk = "LOW"
            elif otif >= OTIF_MEDIUM_RISK_MIN_PCT:
                risk = "MEDIUM"
            else:
                risk = "HIGH"
            supplier_performance.append({
                "supplier_id": s.id,
                "code": s.code,
                "name": s.name,
                "rating": s.rating,
                "otif_score_pct": otif,
                "avg_lead_time_days": s.lead_time_avg_days,
                "risk_level": risk
            })

        order_recommendations = []
        skipped = []
        total_potential_savings = 0.0
        savings_items = 0

        for p in products:
            if p.id not in stock_map:
                skipped.append({"product_id": p.id, "sku": p.sku, "reason": "no inventory rows"})
                continue
            if p.reorder_point is None:
                skipped.append({"product_id": p.id, "sku": p.sku, "reason": "reorder_point is empty"})
                continue
            available = stock_map[p.id]
            below_rop = [
                {"warehouse_id": wh, "available_stock": av}
                for wh, av in wh_avail_map.get(p.id, []) if av <= p.reorder_point
            ]
            if not below_rop:
                continue  # every warehouse is above the reorder point: no order needed
            sales = sales_map.get(p.id)
            if not sales or sales["units_sold"] <= 0:
                skipped.append({"product_id": p.id, "sku": p.sku, "reason": "no sales in sales_history, annual demand unknown"})
                continue
            if not p.unit_cost or p.unit_cost <= 0:
                skipped.append({"product_id": p.id, "sku": p.sku, "reason": "unit_cost is empty or 0"})
                continue

            unit_cost = float(p.unit_cost)
            annual_demand = round(sales["units_sold"] * 365.0 / sales["span_days"], 2)
            holding_cost = unit_cost * HOLDING_COST_RATE_PER_YEAR
            eoq_exact = math.sqrt((2 * annual_demand * ORDER_COST_PER_PO) / holding_cost)
            eoq = int(math.ceil(eoq_exact))

            link = link_map.get(p.id)
            supp = supplier_by_id.get(link.supplier_id) if link else None
            moq = link.moq if link and link.moq else None
            rec_qty = max(eoq, moq) if moq else eoq
            estimated_cost = round(rec_qty * unit_cost, 2)

            current_qs = reorder_qty_map.get(p.id)
            current_q = round(sum(current_qs) / len(current_qs), 2) if current_qs else None
            if current_q:
                cost_current = _yearly_cost(annual_demand, current_q, unit_cost)
                cost_rec = _yearly_cost(annual_demand, rec_qty, unit_cost)
                savings: Optional[float] = round(cost_current - cost_rec, 2)
                total_potential_savings += savings
                savings_items += 1
                savings_formula = (
                    f"cost(Q) = D/Q*{ORDER_COST_PER_PO} + Q/2*{unit_cost}*{HOLDING_COST_RATE_PER_YEAR}; "
                    f"cost({current_q}) - cost({rec_qty}) = {round(cost_current, 2)} - {round(cost_rec, 2)} = {savings}"
                )
            else:
                savings = None
                savings_formula = "No inventory.reorder_quantity for this product: current order pattern unknown, savings not computed"

            urgency = "CRITICAL" if (
                p.safety_stock_min is not None and any(w["available_stock"] <= p.safety_stock_min for w in below_rop)
            ) else "HIGH"

            order_recommendations.append({
                "product_id": p.id,
                "sku": p.sku,
                "product_name": p.name,
                "current_stock": available,
                "reorder_point": p.reorder_point,
                "warehouses_at_or_below_rop": below_rop,
                "recommended_po_qty": rec_qty,
                "estimated_order_cost": estimated_cost,
                "supplier_id": supp.id if supp else None,
                "supplier_name": supp.name if supp else None,
                "supplier_otif": supp.otif_score if supp else None,
                "supplier_rating": supp.rating if supp else None,
                "supplier_unit_cost": link.unit_cost if link else None,
                "potential_savings": savings,
                "urgency": urgency,
                "calculation_trace": {
                    "formula": "EOQ = sqrt((2 * D * S) / H)",
                    "annual_demand_D": annual_demand,
                    "annual_demand_source": (
                        f"{sales['units_sold']:g} units sold from {sales['first_date']} to {sales['last_date']} "
                        f"({sales['span_days']} days) * 365 / {sales['span_days']}"
                    ),
                    "order_setup_cost_S": ORDER_COST_PER_PO,
                    "holding_cost_H": round(holding_cost, 4),
                    "holding_cost_formula": f"{unit_cost} * {HOLDING_COST_RATE_PER_YEAR}",
                    "calculated_eoq": eoq,
                    "supplier_moq": moq,
                    "formula_substitution": f"sqrt((2 * {annual_demand} * {ORDER_COST_PER_PO}) / {round(holding_cost, 4)}) = {round(eoq_exact, 2)} -> {eoq} units",
                    "available_stock": available,
                    "current_order_qty": current_q,
                    "savings_formula": savings_formula
                }
            })

        otif_values = [s.otif_score for s in suppliers if s.otif_score is not None]
        avg_otif = round(sum(otif_values) / len(otif_values), 1) if otif_values else None

        return {
            "module_name": "Procurement & Multi-Supplier EOQ Intelligence",
            "module_key": "procurement",
            "database_info": {
                "is_connected": True,
                "source": "Connected PostgreSQL Database",
                "suppliers_evaluated": len(suppliers),
                "reorder_candidates": len(order_recommendations),
                "skipped_products": len(skipped),
                "fallback_used": False
            },
            "settings": settings,
            "calculation_trace": {
                "methodology": "Wilson Economic Order Quantity (EOQ) using demand from sales_history",
                "eoq_formula": "EOQ = sqrt((2 * Annual_Demand * Order_Cost) / Annual_Holding_Cost_Per_Unit)",
                "annual_demand_formula": "Units sold over the product's sales span * 365 / span days",
                "holding_cost_formula": f"Unit Cost * {HOLDING_COST_RATE_PER_YEAR} yearly holding cost rate",
                "order_trigger": "Any warehouse where available stock (current - reserved) <= products.reorder_point; current_stock shown is the total across warehouses",
                "urgency_rule": "CRITICAL if any such warehouse is at/below products.safety_stock_min, else HIGH",
                "savings_formula": (
                    f"cost(Q) = D/Q * {ORDER_COST_PER_PO} + Q/2 * unit_cost * {HOLDING_COST_RATE_PER_YEAR}; "
                    "saving = cost(current Q = avg inventory.reorder_quantity) - cost(recommended Q)"
                ),
                "open_po_value_formula": f"Sum of purchase_orders.total_cost where status in {list(OPEN_PO_STATUSES)}",
                "data_source_tables": "products, inventory, sales_history, supplier_products, suppliers, purchase_orders",
                "explanation": "Calculates the order quantity that minimizes yearly ordering plus holding cost."
            },
            "total_open_po_value": round(total_open_po_cost, 2),
            "potential_savings": round(total_potential_savings, 2) if savings_items else None,
            "suppliers_count": len(suppliers),
            "avg_supplier_otif_pct": avg_otif,
            "supplier_performance": supplier_performance,
            "order_recommendations": order_recommendations,
            "skipped": skipped
        }
