"""The 9 supply-chain intelligences shown on the Intelligence tab.

Each one reads the imported tables, runs its algorithm and returns one page payload:
pipeline (input -> algorithm -> output), KPI cards, three charts and a results table.
"""
from typing import Any, Callable, Dict

from sqlalchemy.orm import Session

from . import assortment, basket, customers, demand, inventory, pricing, suppliers, trade_area
from ._common import Data, NeedsData, clean

INTELLIGENCES: Dict[str, Dict[str, Any]] = {
    "demand": {"number": 1, "name": "Demand Forecasting", "compute": demand.compute,
               "question": "What will demand be for each product in the next 12 weeks?",
               "scopes": ["Scope: Product", "Weekly", "All warehouses"]},
    "inventory": {"number": 2, "name": "Inventory Planning", "compute": inventory.compute_planning,
                  "question": "How much stock should we hold and when to reorder?",
                  "scopes": ["Scope: Product", "Last 120 days", "Stock on hand"]},
    "policy": {"number": 3, "name": "Inventory Policy Simulation", "compute": inventory.compute_policy,
               "question": "Which reorder policy gives the best service level at the lowest cost?",
               "scopes": ["Scope: Product", "Top 25 products", "Daily replay"]},
    "pricing": {"number": 4, "name": "Pricing & Demand", "compute": pricing.compute,
                "question": "What is the optimal price to maximize revenue or profit?",
                "scopes": ["Scope: Product", "Weekly price", "All warehouses"]},
    "customers": {"number": 5, "name": "Customer Value (LTV)", "compute": customers.compute,
                  "question": "Which customers are most valuable and how do we grow them?",
                  "scopes": ["Scope: Customer", "Orders", "Full history"]},
    "basket": {"number": 6, "name": "Market Basket", "compute": basket.compute,
               "question": "Which products are commonly bought together?",
               "scopes": ["Scope: Product", "Order baskets", "Full history"]},
    "suppliers": {"number": 7, "name": "Supplier Segmentation", "compute": suppliers.compute,
                  "question": "Which suppliers are strategic, at risk or non-critical, and how should we manage them?",
                  "scopes": ["Scope: Supplier", "Spend × Risk", "All products"]},
    "assortment": {"number": 8, "name": "Assortment Planning", "compute": assortment.compute,
                   "question": "Which products should we stock and how much space should each category get?",
                   "scopes": ["Scope: Category", "Product", "Last 12 months"]},
    "trade_area": {"number": 9, "name": "Trade Area", "compute": trade_area.compute,
                   "question": "Which store will customers in each area choose, and how much of the market will each capture?",
                   "scopes": ["Scope: Trade area", "Stores", "Huff model"]},
}


def snapshot_key(intel_id: str) -> str:
    return f"intelligence_{intel_id}"


def compute_intelligence(db: Session, intel_id: str) -> Dict[str, Any]:
    meta = INTELLIGENCES[intel_id]
    base = {"id": intel_id, "number": meta["number"], "name": meta["name"], "question": meta["question"],
            "scopes": meta["scopes"]}
    try:
        result = meta["compute"](Data(db))
    except NeedsData as e:
        result = {"status": "needs_data", "message": f"Waiting for data: import {e} to switch this on."}
    except Exception as e:  # keep the page usable and show what failed
        db.rollback()
        result = {"status": "error", "message": f"The calculation failed on the current data: {e}"}
    return clean({**base, **result})


def snapshot_sources() -> list:
    """(key, label, fn) entries for the saved-results job, one per intelligence."""
    def make(intel_id: str) -> Callable[[Session], Dict[str, Any]]:
        return lambda db: compute_intelligence(db, intel_id)
    return [(snapshot_key(i), f"Intelligence: {m['name']}", make(i)) for i, m in INTELLIGENCES.items()]
