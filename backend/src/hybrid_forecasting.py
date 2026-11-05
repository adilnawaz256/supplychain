# Backward compatibility alias - Canonical implementation moved to backend/ml/scripts/hybrid_forecasting.py
from backend.ml.scripts.hybrid_forecasting import *
if __name__ == "__main__":
    import sys
    from backend.ml.scripts import hybrid_forecasting
    if hasattr(hybrid_forecasting, "main"):
        hybrid_forecasting.main()
