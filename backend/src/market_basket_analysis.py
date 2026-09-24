# Backward compatibility alias - Canonical implementation moved to backend/ml/scripts/market_basket_analysis.py
from backend.ml.scripts.market_basket_analysis import *
if __name__ == "__main__":
    import sys
    from backend.ml.scripts import market_basket_analysis
    if hasattr(market_basket_analysis, "main"):
        market_basket_analysis.main()
