
#!/usr/bin/env python3
"""Advance Analytics Module (Pricing Optimization, Demand Pattern, Newsvendor).

Alias and wrapper for advanced_analytics.py to support both advance_analytics.py
and advanced_analytics.py naming conventions across CLI and application imports.
"""

import sys
from pathlib import Path

# Ensure src/ is on path
src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

try:
    from advanced_analytics import (
        main,
        run,
        classify_demand_pattern,
        compute_price_elasticity,
        optimize_prices_for_top_skus,
        single_period_ordering,
        resolve_unit_costs,
        weekly_price_sales
    )
except ImportError:
    from src.advanced_analytics import (
        main,
        run,
        classify_demand_pattern,
        compute_price_elasticity,
        optimize_prices_for_top_skus,
        single_period_ordering,
        resolve_unit_costs,
        weekly_price_sales
    )

if __name__ == "__main__":
    main()
