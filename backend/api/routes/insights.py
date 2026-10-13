"""Home-dashboard insights: runs every ML engine on the data imported into the internal
database and returns each answer together with a plain-language walk-through of how the
number was produced, using the real values from the calculation."""
from typing import Any, Callable, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.models import (
    Customer, Inventory, Order, Product, PurchaseOrder, RetailSpace, SalesHistory,
    Shipment, Supplier, Warehouse, WorkspacePipelineConfig,
)
from backend.app.services.services import SupplyChainService
from backend.app.services import jobs, snapshots
from backend.app.models.models import BackgroundJob
from backend.ml.forecasting.daily_model import backtest, build_daily_series, fit

router = APIRouter()


def _money(v: float) -> str:
    v = float(v or 0)
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:.2f}M"
    if abs(v) >= 10_000:
        return f"${v / 1_000:.1f}K"
    return f"${v:,.2f}"


def _num(v: float) -> str:
    return f"{float(v or 0):,.0f}"


def _data_counts(db: Session) -> Dict[str, int]:
    return {
        "products": db.query(Product).count(),
        "warehouses": db.query(Warehouse).count(),
        "inventory": db.query(Inventory).count(),
        "sales_history": db.query(SalesHistory).count(),
        "suppliers": db.query(Supplier).count(),
        "customers": db.query(Customer).count(),
        "orders": db.query(Order).count(),
        "purchase_orders": db.query(PurchaseOrder).count(),
        "shipments": db.query(Shipment).count(),
        "retail_spaces": db.query(RetailSpace).count(),
    }


def _engine(eid: str, name: str, question: str, tables: List[str], needs: Dict[str, str],
            counts: Dict[str, int], view: str, compute: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    base = {"id": eid, "name": name, "question": question, "tables": tables, "view": view}
    missing = [label for table, label in needs.items() if counts.get(table, 0) == 0]
    if missing:
        return {**base, "status": "needs_data",
                "answer": f"Waiting for data: import {', '.join(missing)} to switch this on.",
                "headline": "—", "steps": []}
    try:
        return {**base, "status": "ready", **compute()}
    except Exception as e:
        return {**base, "status": "error", "headline": "—",
                "answer": f"The engine failed on the current data: {e}", "steps": []}


def _demand(db: Session, service: SupplyChainService) -> Dict[str, Any]:
    top = (db.query(SalesHistory.product_id, func.sum(SalesHistory.quantity_sold).label("units"))
           .group_by(SalesHistory.product_id).order_by(func.sum(SalesHistory.quantity_sold).desc()).limit(25).all())
    ids = [pid for pid, _ in top]
    rows = db.query(SalesHistory.product_id, SalesHistory.date, SalesHistory.quantity_sold)\
        .filter(SalesHistory.product_id.in_(ids)).all()
    by_product: Dict[int, list] = {}
    for pid, d, q in rows:
        by_product.setdefault(pid, []).append((d, q))

    next30 = 0.0
    abs_err = actual = 0.0
    tested = 0
    days_used = 0
    intermittent = 0
    holdouts = set()
    for pid in ids:
        series = build_daily_series(by_product.get(pid, []))
        if not series:
            continue
        model = fit(series)
        days_used = max(days_used, model["days_used"])
        intermittent += model["method"] == "croston"
        next30 += sum(model["level"] * f for f in model["dow_factors"]) / 7 * 30
        bt = backtest(series)
        if bt and bt["actual_units"] > 0:
            holdouts.add(bt["holdout_days"])
            abs_err += bt["abs_error_units"]
            actual += bt["actual_units"]
            tested += 1
    accuracy = round(max(0.0, 100 - abs_err / actual * 100), 1) if actual else None
    window = f"{max(holdouts)} days" if len(holdouts) == 1 else f"{min(holdouts) if holdouts else 7}-{max(holdouts) if holdouts else 28} days"

    steps = [
        f"We added up units sold per day for your top {len(ids)} products from the sales_history table (up to {days_used} days each).",
        "For each product we keep a running 'typical day' number: every new day moves it 30% towards what really sold. Recent days count more than old ones.",
        "We also learn weekday patterns, e.g. if Saturdays sell 20% more than an average day, Saturday forecasts get x1.2.",
        f"{intermittent} of these products only sell on some days. For them we use Croston's method instead: "
        "(typical size of a sale) / (typical days between sales) = average units per day.",
        f"Typical day x weekday factor, added up over the next 30 days, gives {_num(next30)} units in total.",
    ]
    if accuracy is not None:
        steps.append(
            f"To check ourselves we hid the last {window} of sales for {tested} products and predicted each product's total for that period "
            "(28 days when there is enough history, otherwise 7): "
            f"{_num(actual)} units really sold and the per-product misses add up to {_num(abs_err)} units, so accuracy = 100% - "
            f"({_num(abs_err)} / {_num(actual)}) = {accuracy}%."
        )
    else:
        steps.append("Accuracy needs at least 21 days of sales per product, so it is not measured yet.")
    return {
        "headline": f"{_num(next30)} units",
        "metric_label": "expected demand, next 30 days",
        "secondary": f"{accuracy}% accurate on the last {window}" if accuracy is not None else "accuracy: need 21+ days of sales",
        "accuracy_window": window if accuracy is not None else None,
        "answer": f"Your top {len(ids)} products should sell about {_num(next30)} units over the next 30 days.",
        "steps": steps,
        "accuracy_pct": accuracy,
        "trust": "real",
    }


def _stockout(service: SupplyChainService) -> Dict[str, Any]:
    risks = service.risk_engine.get_all_inventory_risks()
    no_demand = sum(1 for r in risks if r.get("avg_daily_demand") is None)
    crit = [r for r in risks if r["stockout_risk_level"] == "CRITICAL"]
    high = [r for r in risks if r["stockout_risk_level"] == "HIGH"]
    ex = (crit or high or risks)[0]
    return {
        "headline": f"{len(crit) + len(high)} of {len(risks)}",
        "metric_label": "stock lines at risk of running out",
        "secondary": f"{len(crit)} critical, {len(high)} high",
        "answer": f"{len(crit)} product-warehouse lines will likely run out before a new delivery can arrive, and {len(high)} more are at or below their reorder point.",
        "steps": [
            "For every product in every warehouse we take the stock on hand from the inventory table.",
            "Daily demand = units sold / number of days covered by that product's sales history.",
            "Days of stock left = stock on hand / daily demand.",
            "CRITICAL if stock is below the safety stock, or days left is shorter than the supplier lead time (it will run out before a new order arrives). HIGH if stock is at or below the reorder point.",
            (f"Example - {ex['sku']} at {ex['warehouse_name']}: {ex['current_stock']} in stock / {ex['avg_daily_demand']} sold per day = "
             f"{ex['days_of_inventory']} days left, lead time is {ex['lead_time_days']} days, safety stock {ex['safety_stock']} -> {ex['stockout_risk_level']}."
             if ex.get("avg_daily_demand") is not None else
             f"Example - {ex['sku']} at {ex['warehouse_name']}: {ex['current_stock']} in stock, safety stock {ex['safety_stock']}, "
             f"reorder point {ex['reorder_point']} -> {ex['stockout_risk_level']} (no sales history yet, so days-left can't be calculated)."),
        ],
        "example": {"sku": ex["sku"], "product_name": ex["product_name"], "level": ex["stockout_risk_level"]},
        "trust": "real",
    }


def _inventory_value(db: Session, service: SupplyChainService) -> Dict[str, Any]:
    total = float(db.query(func.coalesce(func.sum(Inventory.current_stock * Product.unit_cost), 0.0))
                  .join(Product, Inventory.product_id == Product.id).scalar() or 0.0)
    risks = service.risk_engine.get_all_inventory_risks()
    unit_cost = {p.id: p.unit_cost or 0 for p in db.query(Product.id, Product.unit_cost).all()}
    excess = [r for r in risks if r["stockout_risk_level"] == "LOW"]
    excess_value = sum(r["current_stock"] * unit_cost.get(r["product_id"], 0) for r in excess)
    lines = db.query(Inventory).count()
    return {
        "headline": _money(total),
        "metric_label": "money sitting in stock",
        "secondary": f"{_money(excess_value)} of it is overstock" if excess else "no overstock lines",
        "answer": f"You hold {_money(total)} of stock across {lines} product-warehouse lines; {len(excess)} lines carry more than 60 days of supply.",
        "steps": [
            "For each inventory row: stock on hand x the product's unit cost.",
            f"Add all {lines} rows together = {_money(total)}.",
            f"Overstock = lines with more than 60 days of supply or more than 4x the reorder point. {len(excess)} lines qualify, worth {_money(excess_value)}.",
        ],
        "trust": "real",
    }


def _settings_line(settings: Dict[str, Any]) -> str:
    if not settings:
        return ""
    shown = ", ".join(f"{k.replace('_', ' ')} = {v}" for k, v in settings.items()
                      if isinstance(v, (int, float, str)) and k != "note")
    return f"Business settings used (not stored in your data, can be changed in code): {shown}."


def _procurement(service: SupplyChainService) -> Dict[str, Any]:
    p = service.procurement_engine.generate_procurement_intelligence()
    recs = p.get("order_recommendations", [])
    total_cost = sum(r.get("estimated_order_cost") or 0 for r in recs)
    savings = p.get("potential_savings")
    otif = p.get("avg_supplier_otif_pct")
    steps = [
        "A product needs ordering when any warehouse's available stock (stock minus reserved) is at or below its reorder point.",
        "Yearly demand = units sold in sales_history x 365 / number of days those sales cover.",
        "Order size = Economic Order Quantity: square root of (2 x yearly demand x cost per order / yearly storage cost per unit), "
        "and at least the supplier's minimum order quantity.",
    ]
    if recs:
        ct = recs[0].get("calculation_trace", {})
        steps.append(f"Example - {recs[0]['sku']}: {ct.get('annual_demand_source', '')}; order {recs[0].get('recommended_po_qty')} units "
                     f"from {recs[0].get('supplier_name') or 'no linked supplier'}.")
    steps.append("Saving = yearly order+storage cost at your current reorder quantity minus the cost at the suggested quantity"
                 + ("." if savings is not None else " (not shown: your inventory rows have no reorder quantity)."))
    steps.append(f"Supplier on-time score: {otif}% average." if otif is not None else "Supplier on-time score: not in your data.")
    steps.append(_settings_line(p.get("settings", {})))
    return {
        "headline": f"{len(recs)} orders",
        "metric_label": "purchase orders suggested",
        "secondary": f"{_money(savings)} possible yearly saving" if savings is not None else "saving: needs reorder quantities",
        "answer": f"Place {len(recs)} purchase orders worth {_money(total_cost)} in total.",
        "steps": steps,
        "trust": "real",
    }


def _pricing(service: SupplyChainService) -> Dict[str, Any]:
    p = service.get_pricing_optimization()
    s = p.get("summary", {})
    opts = p.get("optimizations") or []
    fitted = [o for o in opts if o.get("elasticity") is not None]
    no_var = sum(1 for o in opts if o.get("action") == "NOT_ENOUGH_PRICE_VARIATION")
    uplift = s.get("avg_profit_uplift_potential_pct")
    steps = [
        "'Elasticity' = how strongly sales react to price (2.0 means a 1% price cut lifts sales about 2%).",
        "It is measured from your own sales: for each product we take the days it sold at different prices and fit a line through "
        "log(units sold) vs log(price). This needs at least a few different prices.",
        "Profit-maximising price = unit cost x elasticity / (elasticity - 1); the change is limited to a maximum % per step.",
        f"{s.get('elasticity_estimated_count', 0)} products had enough price changes to measure; "
        f"{no_var} products always sold at one price, so no suggestion is possible for them yet.",
    ]
    if fitted:
        o = fitted[0]
        steps.append(f"Example - {o.get('sku_code')}: elasticity {o.get('elasticity')} from {o.get('price_points')} days "
                     f"(fit quality r2 = {o.get('r_squared')}); suggested price ${o.get('recommended_price')} vs ${o.get('current_price')} today.")
    steps.append(f"Demand patterns from your daily sales: {s.get('smooth_demand_pct')}% of products sell steadily, "
                 f"{s.get('lumpy_or_intermittent_pct')}% sell only on some days.")
    steps.append(_settings_line(p.get("settings", {})))
    has = s.get("optimized_sku_count", 0) > 0
    return {
        "headline": f"+{uplift}%" if uplift is not None else "—",
        "metric_label": "average profit uplift from suggested prices" if uplift is not None else "no price suggestions yet",
        "secondary": f"{s.get('optimized_sku_count', 0)} products to re-price" if has else "needs sales at different prices",
        "answer": (f"{s.get('optimized_sku_count', 0)} products have a better price than today's, measured from your price history."
                   if has else "Your sales show only one price per product, so price sensitivity can't be measured yet."),
        "steps": steps,
        "trust": "real",
    }


def _policy(service: SupplyChainService) -> Dict[str, Any]:
    p = service.get_policy_simulation()
    s = p.get("summary", {})
    comp = p.get("policy_comparison", [])
    best = next((c for c in comp if c.get("policy") == s.get("top_performing_policy")), None)
    if not best:
        return {"headline": "—", "metric_label": "best restocking rule", "secondary": None,
                "answer": "Not enough sales history to test restocking rules yet (needs 28+ days per product, plus unit cost and lead time).",
                "steps": [_settings_line(p.get("settings", {}))], "trust": "real"}
    steps = [
        f"We replay the real day-by-day sales of {s.get('skus_evaluated', 0)} top-selling products against {s.get('policies_tested_count', 0)} restocking rules.",
        "Each rule decides when to reorder and how much (e.g. 'order Q units when stock drops to s', or 'top up to a level every week'). "
        "New stock arrives after the product's real lead time.",
        "For every rule we count: demand we could fill, storage cost (stock x unit cost x yearly rate) and ordering cost (a fixed cost per order).",
        f"Winner = cheapest rule that still fills the target share of demand: {best.get('policy_label')} - fills {best.get('avg_fill_rate_pct')}% "
        f"of demand at ${best.get('avg_total_cost')} average total cost per product.",
    ]
    cap = s.get("capital_efficiency_gain_pct")
    if cap is not None:
        steps.append(f"Compared with the '{s.get('capital_efficiency_baseline_policy')}' rule it holds "
                     + (f"{cap}% less stock value." if cap >= 0 else f"{abs(cap)}% more stock value, but orders far less often, so total cost is lower."))
    steps.append(_settings_line(p.get("settings", {})))
    return {
        "headline": str(best.get("policy_label")),
        "metric_label": "cheapest restocking rule",
        "secondary": f"fills {best.get('avg_fill_rate_pct')}% of demand",
        "answer": f"Replaying your real sales, '{best.get('policy_label')}' is the cheapest rule that meets the fill-rate target.",
        "steps": steps,
        "trust": "real",
    }


def _customers(service: SupplyChainService) -> Dict[str, Any]:
    p = service.get_customer_ltv()
    s = p.get("summary", {})
    segs = p.get("segments_rollup", [])
    top = segs[0] if segs else {}
    acc = s.get("ml_classifier_accuracy_pct")
    return {
        "headline": f"{s.get('high_ltv_share_pct')}%" if s.get("high_ltv_share_pct") is not None else "—",
        "metric_label": "of revenue from your best customers",
        "secondary": f"{s.get('at_risk_vip_count')} top customers haven't ordered recently" if s.get("at_risk_vip_count") is not None else None,
        "answer": f"{top.get('customer_count', 0)} of {s.get('total_customers_analyzed', 0)} customers bring {top.get('revenue_share_pct', 0)}% of revenue.",
        "steps": [
            "From the orders table we score every customer who has ordered on 3 things: days since last order, number of orders, and total spend (RFM).",
            "K-Means clustering groups customers with similar scores into High / Mid / Low value groups.",
            (f"A Random Forest model checked on held-out customers predicts the group correctly {acc}% of the time."
             if acc is not None else "Model accuracy is only measured with 30+ customers, so it isn't shown yet."),
            f"Top group: {top.get('customer_count', 0)} customers, average spend ${top.get('avg_spend_per_customer', 0)}, "
            f"last order about {top.get('avg_recency_days', 0)} days before your latest order date.",
            _settings_line(p.get("settings", {})),
        ],
        "trust": "real",
    }


def _cross_sell(service: SupplyChainService) -> Dict[str, Any]:
    p = service.get_market_basket()
    s = p.get("summary", {})
    rule = (p.get("association_rules") or [{}])[0]
    steps = [
        "We look at every order basket (order_items) and count which products are bought together. A pair only counts if it shows up in enough baskets, so one-off coincidences are ignored.",
        "Confidence = of baskets with product A, how many also had B. Lift = how much more likely B is when A is in the basket than normally (above 1 means a real link).",
    ]
    if rule:
        steps.append(f"Strongest pair: '{rule.get('antecedent')}' -> '{rule.get('consequent')}': confidence {rule.get('confidence_pct')}%, lift {rule.get('lift')}x.")
    steps.append(_settings_line(p.get("settings", {})))
    return {
        "headline": f"{s.get('active_bundle_opportunities', 0)} bundles",
        "metric_label": "cross-sell bundles found",
        "secondary": f"{s.get('total_rules_discovered', 0)} buy-together rules",
        "answer": f"Found {s.get('total_rules_discovered', 0)} 'bought together' patterns in your order baskets.",
        "steps": steps,
        "trust": "real",
    }


def _assortment(service: SupplyChainService) -> Dict[str, Any]:
    a = service.assortment_engine.generate_assortment_intelligence()
    skus = a.get("sku_assortment", [])
    stars = [x for x in skus if x.get("classification") == "STAR_PRODUCT"]
    ex = skus[0] if skus else {}
    window = (a.get("database_info") or {}).get("sales_window", "the last 90 days")
    return {
        "headline": f"{len(stars)} stars",
        "metric_label": "best-earning products per shelf space",
        "secondary": f"{a.get('low_productivity_sku_count', 0)} weak products",
        "answer": f"{len(stars)} of {len(skus)} shelved products earn the most per square metre; {a.get('low_productivity_sku_count', 0)} earn too little for their space.",
        "steps": [
            f"For each product with a shelf record (retail_spaces) we take its sales in {window}.",
            "Revenue per m2 = sales revenue / shelf area. Sell-through = units sold / (units sold + units on display).",
            "GMROI = gross margin earned / money tied up in the displayed stock; above 1 means the shelf pays for itself.",
            f"Example - {ex.get('sku')}: {_money(ex.get('revenue_90d') or 0)} on {ex.get('allocated_space_sqm')} m2 = "
            f"{_money(ex.get('revenue_per_sqm') or 0)}/m2, GMROI {ex.get('gmroi')}." if ex else "No shelved products yet.",
            _settings_line(a.get("settings", {})),
        ],
        "trust": "real",
    }


def _trade_area(service: SupplyChainService) -> Dict[str, Any]:
    t = service.get_trade_area()
    s = t.get("summary", {})
    if t.get("status") == "NEEDS_DATA":
        missing = t.get("missing_data") or []
        return {
            "status": "needs_data",
            "headline": "—",
            "answer": t.get("message") or "Needs territory and distance data that your database doesn't have yet.",
            "steps": [str(m) if not isinstance(m, dict) else (m.get("description") or m.get("name") or str(m)) for m in missing],
        }
    return {
        "headline": str(s.get("highest_attractiveness_store") or "—"),
        "metric_label": "most attractive location",
        "secondary": None,
        "answer": f"{s.get('highest_attractiveness_store')} pulls the most shoppers out of {s.get('competing_stores_count', 0)} sites.",
        "steps": ["Huff gravity model: the chance a shopper goes to a store = its attractiveness / distance squared, compared with all other stores."],
        "trust": "real",
    }


def _pipeline(db: Session) -> Dict[str, Any]:
    cfg = db.query(WorkspacePipelineConfig).filter(WorkspacePipelineConfig.workspace_key == "default").first()
    return {
        "is_connected": bool(cfg and cfg.is_connected == 1),
        "source": {
            "host": cfg.host if cfg else None,
            "database": cfg.database_name if cfg else None,
        },
        "last_ingested_at": cfg.last_ingested_at.isoformat() if cfg and cfg.last_ingested_at else None,
        "imports": (cfg.ingestion_history or []) if cfg else [],
    }


def compute_home_insights(db: Session) -> Dict[str, Any]:
    counts = _data_counts(db)
    first_sale, last_sale = db.query(func.min(SalesHistory.date), func.max(SalesHistory.date)).one()
    service = SupplyChainService(db)

    engines = [
        _engine("demand", "Demand Forecast", "How much will we sell next month?",
                ["sales_history", "products"], {"sales_history": "sales history"}, counts, "intelligence",
                lambda: _demand(db, service)),
        _engine("stockout", "Stockout Risk", "What is about to run out?",
                ["inventory", "products", "sales_history"], {"inventory": "inventory (stock on hand)"}, counts, "alerts",
                lambda: _stockout(service)),
        _engine("inventory_value", "Inventory Value", "How much money is tied up in stock?",
                ["inventory", "products"], {"inventory": "inventory (stock on hand)"}, counts, "intelligence",
                lambda: _inventory_value(db, service)),
        _engine("procurement", "Purchase Planning", "What should we order, and how much?",
                ["products", "inventory", "suppliers"], {"inventory": "inventory", "suppliers": "suppliers"}, counts, "intelligence",
                lambda: _procurement(service)),
        _engine("pricing", "Price Optimisation", "Are our prices right?",
                ["products", "sales_history"], {"sales_history": "sales history"}, counts, "intelligence",
                lambda: _pricing(service)),
        _engine("policy", "Restocking Rules", "Which reorder rule works best?",
                ["sales_history", "inventory", "products"], {"sales_history": "sales history", "inventory": "inventory"}, counts, "intelligence",
                lambda: _policy(service)),
        _engine("customers", "Customer Value", "Who are our best customers?",
                ["customers", "orders"], {"customers": "customers", "orders": "orders"}, counts, "intelligence",
                lambda: _customers(service)),
        _engine("cross_sell", "Bought Together", "What do customers buy together?",
                ["orders", "order_items"], {"orders": "orders"}, counts, "intelligence",
                lambda: _cross_sell(service)),
        _engine("assortment", "Shelf Space", "Which products earn their shelf space?",
                ["retail_spaces", "sales_history"], {"retail_spaces": "shelf space (retail_spaces)", "sales_history": "sales history"}, counts, "intelligence",
                lambda: _assortment(service)),
        _engine("trade_area", "Store Catchment", "Which location attracts the most shoppers?",
                ["warehouses", "sales_history"], {"warehouses": "warehouses"}, counts, "intelligence",
                lambda: _trade_area(service)),
    ]

    return {
        "pipeline": _pipeline(db),
        "data": {
            "counts": counts,
            "sales_from": first_sale.isoformat() if first_sale else None,
            "sales_to": last_sale.isoformat() if last_sale else None,
        },
        "engines": engines,
        "ready_count": sum(1 for e in engines if e["status"] == "ready"),
    }


def _latest_job(db: Session, kind: str):
    job = db.query(BackgroundJob).filter(BackgroundJob.kind == kind).order_by(BackgroundJob.id.desc()).first()
    return jobs.job_to_dict(job) if job else None


@router.get("/api/insights/home", tags=["Home Insights"])
def get_home_insights(db: Session = Depends(get_db)):
    payload, computed_at = snapshots.get_or_compute(db, "insights_home")
    return {
        **payload,
        "pipeline": _pipeline(db),
        "computed_at": computed_at.isoformat() if computed_at else None,
        "ml_job": _latest_job(db, snapshots.ML_JOB_KIND),
        "import_job": _latest_job(db, "import"),
    }


@router.post("/api/insights/recalculate", tags=["Home Insights"])
def recalculate_insights(db: Session = Depends(get_db)):
    """Recalculate every ML result in the background; poll /api/jobs/{id} for progress."""
    return snapshots.start_recalculation(db, reason="manual")


@router.get("/api/jobs/{job_id}", tags=["Background Jobs"])
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(BackgroundJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs.job_to_dict(job)


@router.get("/api/jobs", tags=["Background Jobs"])
def list_jobs(limit: int = 20, db: Session = Depends(get_db)):
    rows = db.query(BackgroundJob).order_by(BackgroundJob.id.desc()).limit(min(limit, 100)).all()
    return [jobs.job_to_dict(j) for j in rows]
