"""6. Market Basket: products bought together (support, confidence, lift over order baskets)."""
import math
from collections import Counter
from itertools import combinations
from typing import Dict

import pandas as pd

from ._common import Data, NeedsData, col, kpi, num, page, pct, short

MAX_BASKET_ITEMS = 60      # very large wholesale baskets pair everything with everything; leave them out
MIN_SUPPORT_SHARE = 0.002  # a pair must be in at least 0.2% of baskets ...
MIN_SUPPORT_COUNT = 3      # ... and at least 3 baskets
MAX_RULES = 500
MIN_PAIRS = 10            # lower the support threshold until at least this many pairs qualify


def compute(d: Data) -> Dict:
    items = d.order_items
    if items.empty:
        raise NeedsData("order items")
    baskets = items.groupby("order_id")["product_id"].agg(lambda x: sorted(set(x)))
    n_tx = len(baskets)
    single = Counter()
    pairs = Counter()
    used = 0
    for prods in baskets:
        single.update(prods)
        if 2 <= len(prods) <= MAX_BASKET_ITEMS:
            pairs.update(combinations(prods, 2))
            used += 1
    # Start at 0.2% of baskets and step down (never below 3 baskets) until enough pairs qualify,
    # so large catalogues with sparse baskets still produce rules.
    counts = sorted(pairs.values(), reverse=True)
    min_count = MIN_SUPPORT_COUNT
    for share in (MIN_SUPPORT_SHARE, 0.001, 0.0005, 0.00025):
        candidate = max(MIN_SUPPORT_COUNT, math.ceil(share * n_tx))
        if sum(1 for c in counts[:MIN_PAIRS] if c >= candidate) >= MIN_PAIRS:
            min_count = candidate
            break

    p = d.products.set_index("product_id")
    name = p["name"].to_dict()
    cat = p["category"].to_dict()
    rules = []
    for (a, b), n_ab in pairs.items():
        if n_ab < min_count:
            continue
        for x, y in ((a, b), (b, a)):
            conf = n_ab / single[x]
            lift = conf / (single[y] / n_tx)
            if lift <= 1:
                continue
            rules.append({"a": x, "b": y, "support": n_ab / n_tx * 100, "confidence": conf * 100, "lift": lift,
                          "transactions": n_ab})
    rules.sort(key=lambda r: (-r["lift"], -r["confidence"]))
    total_rules = len(rules)
    rules = rules[:MAX_RULES]

    rows = []
    for i, r in enumerate(rules, 1):
        opp = ("High" if r["lift"] >= 3 and r["confidence"] >= 30 else "Medium" if r["lift"] >= 1.5 else "Low")
        action = ("Promote together" if opp == "High" and r["confidence"] >= 50 else "Bundle offer" if opp == "High"
                  else "Display together" if opp == "Medium" else "Cross-sell at checkout")
        rows.append({"rule_id": f"RULE-{i:04d}", "product_a": name.get(r["a"], f"Product {r['a']}"),
                     "product_b": name.get(r["b"], f"Product {r['b']}"), "category": cat.get(r["a"], "General"),
                     "support": r["support"], "confidence": r["confidence"], "lift": r["lift"],
                     "transactions": r["transactions"], "opportunity": opp, "action": action})
    df = pd.DataFrame(rows, columns=["rule_id", "product_a", "product_b", "category", "support", "confidence", "lift",
                                     "transactions", "opportunity", "action"])
    top = df.head(1)
    top_text = f"{short(top.iloc[0].product_a, 18)} → {short(top.iloc[0].product_b, 18)}" if len(top) else "—"
    top_sub = (f"Lift: {top.iloc[0].lift:.2f} | Confidence: {top.iloc[0].confidence:.1f}%" if len(top)
               else f"No pair reached {min_count} baskets yet")

    cats = df["category"].value_counts()
    main = cats.index[:5].tolist()
    by_cat = [{"name": c, "value": int(cats[c])} for c in main]
    if len(cats) > 5:
        by_cat.append({"name": "Others", "value": int(cats.iloc[5:].sum())})
    sc = df.head(400)
    groups = [{"name": c, "points": [{"x": float(r.support), "y": float(r.confidence), "z": float(r.lift),
                                      "label": f"{short(r.product_a, 20)} → {short(r.product_b, 20)}"}
                                     for r in sc[sc["category"] == c].itertuples()]} for c in main]
    others = sc[~sc["category"].isin(main)]
    if len(others):
        groups.append({"name": "Others", "points": [{"x": float(r.support), "y": float(r.confidence), "z": float(r.lift),
                                                     "label": f"{short(r.product_a, 20)} → {short(r.product_b, 20)}"}
                                                    for r in others.itertuples()]})

    return page(
        input_={"title": "Transaction data (orders, order_items)",
                "scope": f"{n_tx:,} baskets · {len(items):,} lines",
                "columns": "Order ID, Product, Quantity"},
        algorithm={"title": "Apriori Association Rules",
                   "description": f"Counts how often products share a basket; pairs in ≥ {min_count} baskets become rules scored by support, confidence and lift (> 1 = real link)."},
        output={"title": "market_basket_results",
                "description": "Product pairs with support, confidence, lift and a cross-sell action."},
        kpis=[
            kpi("Total Transactions", num(n_tx), "Baskets analyzed", "info", "calendar"),
            kpi("Unique Products", num(len(single)), "Products in analysis", "info", "box"),
            kpi("Association Rules", num(total_rules), f"Rules with min. support ({min_count} baskets)", "neutral", "share"),
            kpi("Avg. Confidence", pct(df["confidence"].mean()) if len(df) else "—", "Across the rules shown", "good", "shield"),
            kpi("Top Cross-Sell Opportunity", top_text, top_sub, "warn", "star"),
        ],
        charts=[
            {"type": "hbar", "title": "Top 10 Product Associations (by Lift)",
             "data": [{"name": f"{short(r.product_a, 16)} → {short(r.product_b, 16)}", "value": float(r.lift)}
                      for r in df.head(10).itertuples()], "valueFormat": "num2", "wideLabels": True},
            {"type": "scatter", "title": "Support vs Confidence", "xLabel": "Support (%)", "yLabel": "Confidence (%)",
             "groups": groups, "sized": True, "xFormat": "pct", "yFormat": "pct"},
            {"type": "donut", "title": "Rules by Product Category", "centerValue": num(len(df)), "centerLabel": "Rules",
             "data": by_cat, "valueFormat": "int", "showPercent": True},
        ],
        table={
            "title": "Market Basket Results", "searchPlaceholder": "Search products...",
            "columns": [
                col("rule_id", "Rule ID"), col("product_a", "Product A (Antecedent)"), col("product_b", "Product B (Consequent)"),
                col("category", "Category", "pill"),
                col("support", "Support", "pct2"), col("confidence", "Confidence", "pct"), col("lift", "Lift", "num2"),
                col("transactions", "Transactions", "int"),
                col("opportunity", "Opportunity", "trend", trends={"High": "up", "Medium": "ok", "Low": "down"}),
                col("action", "Action"),
            ],
            "filters": ["category", "opportunity"],
            "sort": {"key": "lift", "dir": "desc"},
            "rows": df.to_dict("records"),
        },
        notes=[f"{n_tx - used:,} baskets with a single product or more than {MAX_BASKET_ITEMS} products are counted "
               "for support but not paired."] if n_tx - used else [],
    )
