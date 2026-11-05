# Backward compatibility alias - Canonical implementation moved to backend/ml/scripts/trade_area_modelling.py
from backend.ml.scripts.trade_area_modelling import *
if __name__ == "__main__":
    import sys
    from backend.ml.scripts import trade_area_modelling
    if hasattr(trade_area_modelling, "main"):
        trade_area_modelling.main()
