"""Customer Segmentation & Lifetime Value (LTV) Engine (Module 3).

Computes per-customer RFM (Recency, Frequency, Monetary) strictly from the
`customers`, `orders` and `order_items` tables, clusters customers with a real
K-Means model into Low / Mid / High LTV tiers and evaluates a real Random Forest
classifier on a held-out split. Nothing is invented: when a value cannot be
computed from the database it is returned as None (or the item is omitted).
"""

from typing import Dict, Any, List, Optional
from collections import defaultdict

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.database import SessionLocal
from backend.app.models.models import Customer, Order, OrderItem

# ---- Business settings (not stored in any table) -----------------------------
CHURN_RISK_DAYS = 90          # High-LTV customer with recency above this is "at risk"
N_CLUSTERS = 3                # K-Means clusters -> High / Mid / Low LTV
KMEANS_N_INIT = 10
RANDOM_STATE = 0
CLASSIFIER_TEST_SIZE = 0.25
MIN_CUSTOMERS_FOR_CLASSIFIER = 30
MIN_CLASS_MEMBERS_FOR_CLASSIFIER = 2
RF_N_ESTIMATORS = 200
MAX_AT_RISK_RETURNED = 8
MAX_SAMPLE_CUSTOMERS = 20

PRIMARY_ALGORITHM = "K-Means Clustering (k=3, log1p-standardized RFM) + Random Forest RFM Classifier"
SEGMENT_ORDER = ["High_ltv", "Mid_ltv", "Low_ltv"]


def _settings() -> Dict[str, Any]:
    return {
        "churn_risk_days": CHURN_RISK_DAYS,
        "kmeans_clusters": N_CLUSTERS,
        "kmeans_n_init": KMEANS_N_INIT,
        "random_state": RANDOM_STATE,
        "classifier_test_size": CLASSIFIER_TEST_SIZE,
        "min_customers_for_classifier": MIN_CUSTOMERS_FOR_CLASSIFIER,
        "min_class_members_for_classifier": MIN_CLASS_MEMBERS_FOR_CLASSIFIER,
        "random_forest_n_estimators": RF_N_ESTIMATORS,
    }


class CustomerLTVSegmentationEngine:
    """Enterprise Customer Segmentation, RFM Scoring & LTV Analysis Engine."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def _get_db(self) -> Session:
        return self.db if self.db is not None else SessionLocal()

    # ------------------------------------------------------------------ data
    def _load_rfm(self, db: Session):
        """Return (rows, reference_date). rows only include customers that have orders."""
        orders = (
            db.query(Order.id, Order.customer_id, Order.order_date, Order.total_amount)
            .filter(Order.customer_id.isnot(None))
            .all()
        )
        if not orders:
            return [], None

        # Order value from order_items for orders whose total_amount is null/0
        need_items = [o[0] for o in orders if not o[3]]
        item_totals: Dict[int, float] = {}
        if need_items:
            item_rows = (
                db.query(OrderItem.order_id, func.sum(OrderItem.total_price))
                .group_by(OrderItem.order_id)
                .all()
            )
            item_totals = {oid: float(s or 0.0) for oid, s in item_rows}

        reference_date = max(o[2] for o in orders if o[2] is not None) if any(o[2] for o in orders) else None

        per_cust: Dict[int, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "last": None, "spend": 0.0})
        for oid, cid, odate, amount in orders:
            value = float(amount) if amount else item_totals.get(oid, 0.0)
            st = per_cust[cid]
            st["count"] += 1
            st["spend"] += value
            if odate is not None and (st["last"] is None or odate > st["last"]):
                st["last"] = odate

        customers = {c.id: c for c in db.query(Customer.id, Customer.customer_code, Customer.name).all()}

        rows = []
        for cid, st in per_cust.items():
            if st["last"] is None or reference_date is None:
                continue  # recency cannot be computed without an order date
            c = customers.get(cid)
            rows.append({
                "db_id": cid,
                "customer_id": (c.customer_code if c is not None else None),
                "name": (c.name if c is not None else None),
                "recency_days": max(0, (reference_date - st["last"]).days),
                "frequency_orders": st["count"],
                "monetary_spend": st["spend"],
                "last_order_date": st["last"],
            })
        return rows, reference_date

    # ------------------------------------------------------------------ main
    def get_customer_ltv_intelligence(self) -> Dict[str, Any]:
        """Customer segmentation, RFM and retention metrics computed from live database records."""
        db = self._get_db()
        should_close = (self.db is None)
        try:
            rows, reference_date = self._load_rfm(db)
            if not rows:
                return self._empty_response("No customer orders found in the orders table; nothing to segment.")

            notes: List[str] = []
            n = len(rows)
            R = np.array([r["recency_days"] for r in rows], dtype=float)
            F = np.array([r["frequency_orders"] for r in rows], dtype=float)
            M = np.array([r["monetary_spend"] for r in rows], dtype=float)
            X_raw = np.column_stack([R, F, M])

            # RFM tercile scores (P33/P66 cutoffs of the real distribution)
            p33_r, p66_r = np.percentile(R, [33, 66])
            p33_f, p66_f = np.percentile(F, [33, 66])
            p33_m, p66_m = np.percentile(M, [33, 66])

            # ---- K-Means segmentation
            labels: Optional[List[str]] = None
            if n >= N_CLUSTERS:
                from sklearn.cluster import KMeans
                from sklearn.preprocessing import StandardScaler
                X_log = np.log1p(np.clip(X_raw, 0, None))
                X_std = StandardScaler().fit_transform(X_log)
                n_distinct = len(np.unique(X_std, axis=0))
                if n_distinct >= N_CLUSTERS:
                    km = KMeans(n_clusters=N_CLUSTERS, n_init=KMEANS_N_INIT, random_state=RANDOM_STATE)
                    cl = km.fit_predict(X_std)
                    means = sorted(((float(M[cl == k].mean()), k) for k in range(N_CLUSTERS)), reverse=True)
                    cluster_to_seg = {k: SEGMENT_ORDER[i] for i, (_, k) in enumerate(means)}
                    labels = [cluster_to_seg[int(k)] for k in cl]
                else:
                    notes.append(f"Only {n_distinct} distinct RFM profiles; K-Means needs at least {N_CLUSTERS}. Segments not computed.")
            else:
                notes.append(f"Only {n} customers with orders; K-Means needs at least {N_CLUSTERS}. Segments not computed.")

            # ---- Random Forest classifier
            accuracy_pct: Optional[float] = None
            confusion_records: List[Dict[str, Any]] = []
            feature_importances: Optional[Dict[str, float]] = None
            classifier_eval: Dict[str, Any] = {"evaluated": False}
            if labels is not None:
                from collections import Counter
                counts = Counter(labels)
                if n < MIN_CUSTOMERS_FOR_CLASSIFIER:
                    notes.append(f"Classifier not evaluated: {n} customers with orders (< {MIN_CUSTOMERS_FOR_CLASSIFIER} required).")
                elif min(counts.values()) < MIN_CLASS_MEMBERS_FOR_CLASSIFIER or len(counts) < 2:
                    notes.append(f"Classifier not evaluated: a segment has fewer than {MIN_CLASS_MEMBERS_FOR_CLASSIFIER} members.")
                else:
                    from sklearn.ensemble import RandomForestClassifier
                    from sklearn.model_selection import train_test_split
                    from sklearn.metrics import accuracy_score, confusion_matrix
                    y = np.array(labels)
                    try:
                        X_tr, X_te, y_tr, y_te = train_test_split(
                            X_raw, y, test_size=CLASSIFIER_TEST_SIZE, random_state=RANDOM_STATE, stratify=y)
                        rf = RandomForestClassifier(n_estimators=RF_N_ESTIMATORS, random_state=RANDOM_STATE)
                        rf.fit(X_tr, y_tr)
                        pred = rf.predict(X_te)
                        accuracy_pct = round(float(accuracy_score(y_te, pred)) * 100, 1)
                        present = [s for s in SEGMENT_ORDER if s in counts]
                        cm = confusion_matrix(y_te, pred, labels=present)
                        for i, a in enumerate(present):
                            for j, p in enumerate(present):
                                confusion_records.append({"actual": a, "predicted": p, "count": int(cm[i, j])})
                        feature_importances = {
                            name: round(float(v), 4)
                            for name, v in zip(["recency_days", "frequency_orders", "monetary_spend"], rf.feature_importances_)
                        }
                        classifier_eval = {
                            "evaluated": True,
                            "train_size": int(len(y_tr)),
                            "test_size": int(len(y_te)),
                            "split": f"stratified train/test, test={CLASSIFIER_TEST_SIZE}, random_state={RANDOM_STATE}",
                            "target": "K-Means segment label",
                        }
                    except ValueError as exc:
                        notes.append(f"Classifier not evaluated: {exc}")

            # ---- per-customer items
            customers: List[Dict[str, Any]] = []
            seg_stats = {s: {"count": 0, "total_spend": 0.0, "recencies": [], "frequencies": []} for s in SEGMENT_ORDER}
            at_risk: List[Dict[str, Any]] = []
            ref_str = reference_date.date().isoformat() if hasattr(reference_date, "date") else str(reference_date)

            for idx, rc in enumerate(rows):
                r_score = 5 if rc["recency_days"] <= p33_r else (3 if rc["recency_days"] <= p66_r else 1)
                f_score = 5 if rc["frequency_orders"] >= p66_f else (3 if rc["frequency_orders"] >= p33_f else 1)
                m_score = 5 if rc["monetary_spend"] >= p66_m else (3 if rc["monetary_spend"] >= p33_m else 1)
                overall = round((r_score + f_score + m_score) / 3.0, 2)
                seg = labels[idx] if labels is not None else None
                if seg == "High_ltv":
                    churn_risk = "HIGH" if rc["recency_days"] > CHURN_RISK_DAYS else "LOW"
                elif seg is not None:
                    churn_risk = "MEDIUM" if rc["recency_days"] > CHURN_RISK_DAYS else "LOW"
                else:
                    churn_risk = None

                item = {
                    "customer_id": rc["customer_id"],
                    "name": rc["name"],
                    "recency_days": rc["recency_days"],
                    "frequency_orders": rc["frequency_orders"],
                    "monetary_spend": round(rc["monetary_spend"], 2),
                    "rfm_recency_score": r_score,
                    "rfm_frequency_score": f_score,
                    "rfm_monetary_score": m_score,
                    "overall_rfm_score": overall,
                    "ltv_segment": seg,
                    "churn_risk": churn_risk,
                    "calculation_trace": {
                        "recency_formula": f"Days between customer's last order ({rc['last_order_date'].date().isoformat()}) and latest order date in dataset ({ref_str}) = {rc['recency_days']}",
                        "frequency_formula": f"Count of orders = {rc['frequency_orders']}",
                        "monetary_formula": f"Sum of order values (orders.total_amount, or sum(order_items.total_price) when total_amount is null/0) = {round(rc['monetary_spend'], 2)}",
                        "ltv_definition": "LTV = historical monetary spend (no projection)",
                        "rfm_scores": f"Recency={r_score}/5, Frequency={f_score}/5, Monetary={m_score}/5 (tercile cutoffs P33/P66 of real distribution)",
                        "composite_score_formula": "Overall RFM = (R + F + M) / 3",
                        "segment_source": "K-Means cluster label" if seg is not None else "Not computed",
                        "data_source_tables": "customers, orders, order_items",
                    },
                }
                customers.append(item)
                if seg is not None:
                    st = seg_stats[seg]
                    st["count"] += 1
                    st["total_spend"] += rc["monetary_spend"]
                    st["recencies"].append(rc["recency_days"])
                    st["frequencies"].append(rc["frequency_orders"])
                    if seg == "High_ltv" and rc["recency_days"] > CHURN_RISK_DAYS:
                        at_risk.append(item)

            customers.sort(key=lambda c: c["monetary_spend"], reverse=True)
            at_risk.sort(key=lambda c: c["monetary_spend"], reverse=True)

            total_cust = len(customers)
            total_revenue = float(M.sum())

            color_map = {"High_ltv": "#10b981", "Mid_ltv": "#3b82f6", "Low_ltv": "#94a3b8"}
            action_map = {
                "High_ltv": "Retain: prioritise service and inventory availability for these accounts.",
                "Mid_ltv": "Grow: target with cross-sell to increase order frequency and value.",
                "Low_ltv": "Reactivate: target with replenishment reminders.",
            }
            segments_rollup: List[Dict[str, Any]] = []
            if labels is not None:
                for seg_name in SEGMENT_ORDER:
                    sd = seg_stats[seg_name]
                    cnt = sd["count"]
                    spend = sd["total_spend"]
                    segments_rollup.append({
                        "segment": seg_name,
                        "segment_label": seg_name.replace("_", " ").title(),
                        "customer_count": cnt,
                        "customer_share_pct": round(cnt / total_cust * 100, 1) if total_cust else None,
                        "total_spend": round(spend, 2),
                        "revenue_share_pct": round(spend / total_revenue * 100, 1) if total_revenue > 0 else None,
                        "avg_spend_per_customer": round(spend / cnt, 2) if cnt else None,
                        "avg_recency_days": round(float(np.mean(sd["recencies"])), 1) if sd["recencies"] else None,
                        "avg_frequency_orders": round(float(np.mean(sd["frequencies"])), 1) if sd["frequencies"] else None,
                        "color": color_map[seg_name],
                        "recommended_action": action_map[seg_name],
                    })

            high = next((s for s in segments_rollup if s["segment"] == "High_ltv"), None)
            high_ltv_share = high["revenue_share_pct"] if high else None

            # ---- recommendations (only from computed numbers)
            recommendations: List[Dict[str, Any]] = []
            if at_risk:
                at_risk_spend = sum(c["monetary_spend"] for c in at_risk)
                share = round(at_risk_spend / total_revenue * 100, 1) if total_revenue > 0 else None
                recommendations.append({
                    "title": "Re-engage At-Risk High-LTV Accounts",
                    "impact": f"{len(at_risk)} accounts, {round(at_risk_spend, 2)} historical spend" + (f" ({share}% of total)" if share is not None else ""),
                    "details": f"{len(at_risk)} High-LTV customers have not ordered for more than {CHURN_RISK_DAYS} days before {ref_str}.",
                    "urgency": "HIGH",
                })
            if high is not None and high["customer_count"]:
                recommendations.append({
                    "title": "Concentration in High-LTV Segment",
                    "impact": f"{high['customer_share_pct']}% of customers generate {high['revenue_share_pct']}% of spend",
                    "details": f"{high['customer_count']} High-LTV customers averaging {high['avg_spend_per_customer']} spend and {high['avg_frequency_orders']} orders.",
                    "urgency": "MEDIUM",
                })

            return {
                "module_name": "Customer Segmentation & Lifetime Value",
                "module_key": "customer_ltv",
                "database_info": {
                    "is_connected": True,
                    "source": "Connected Database (customers, orders, order_items)",
                    "customers_analyzed": total_cust,
                    "total_portfolio_revenue": round(total_revenue, 2),
                    "reference_date": ref_str,
                    "fallback_used": False,
                },
                "settings": _settings(),
                "calculation_trace": {
                    "methodology": PRIMARY_ALGORITHM,
                    "reference_date": f"Latest order_date in orders table: {ref_str}",
                    "recency_formula": "Days between the customer's last order and the reference date",
                    "frequency_formula": "Number of orders per customer",
                    "monetary_formula": "Sum of orders.total_amount (sum(order_items.total_price) when total_amount is null/0)",
                    "ltv_definition": "LTV = historical monetary spend; no forward projection",
                    "segmentation": f"K-Means (k={N_CLUSTERS}, n_init={KMEANS_N_INIT}, random_state={RANDOM_STATE}) on standardized log1p(R,F,M); clusters ranked by mean monetary -> High/Mid/Low LTV",
                    "classifier": "RandomForestClassifier predicting K-Means segment from raw R,F,M",
                    "classifier_evaluation": classifier_eval,
                    "feature_importances": feature_importances,
                    "at_risk_rule": f"High-LTV and recency_days > {CHURN_RISK_DAYS}",
                    "scope": "Only customers with at least one order are analyzed",
                    "data_source_tables": "customers (customer_code, name), orders (customer_id, order_date, total_amount), order_items (order_id, total_price)",
                    "notes": notes,
                },
                "summary": {
                    "total_customers_analyzed": total_cust,
                    "total_portfolio_ltv": round(total_revenue, 2),
                    "avg_customer_ltv": round(total_revenue / total_cust, 2) if total_cust else None,
                    "high_ltv_share_pct": high_ltv_share,
                    "at_risk_vip_count": len(at_risk) if labels is not None else None,
                    "ml_classifier_accuracy_pct": accuracy_pct,
                    "primary_algorithm": PRIMARY_ALGORITHM,
                },
                "segments_rollup": segments_rollup,
                "at_risk_vip_customers": at_risk[:MAX_AT_RISK_RETURNED],
                "confusion_records": confusion_records,
                "sample_customers": customers[:MAX_SAMPLE_CUSTOMERS],
                "recommendations": recommendations,
            }
        finally:
            if should_close:
                db.close()

    def _empty_response(self, note: str = "") -> Dict[str, Any]:
        return {
            "module_name": "Customer Segmentation & Lifetime Value",
            "module_key": "customer_ltv",
            "database_info": {
                "is_connected": True,
                "source": "Connected Database (customers, orders, order_items)",
                "customers_analyzed": 0,
                "total_portfolio_revenue": None,
                "reference_date": None,
                "fallback_used": False,
            },
            "settings": _settings(),
            "calculation_trace": {"methodology": PRIMARY_ALGORITHM, "notes": [note] if note else []},
            "summary": {
                "total_customers_analyzed": 0,
                "total_portfolio_ltv": None,
                "avg_customer_ltv": None,
                "high_ltv_share_pct": None,
                "at_risk_vip_count": None,
                "ml_classifier_accuracy_pct": None,
                "primary_algorithm": PRIMARY_ALGORITHM,
            },
            "segments_rollup": [],
            "at_risk_vip_customers": [],
            "confusion_records": [],
            "sample_customers": [],
            "recommendations": [],
        }
