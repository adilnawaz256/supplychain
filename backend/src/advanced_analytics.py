# Backward compatibility alias - Canonical implementation moved to backend/ml/scripts/advanced_analytics.py
from backend.ml.scripts.advanced_analytics import *
if __name__ == "__main__":
    import sys
    from backend.ml.scripts import advanced_analytics
    if hasattr(advanced_analytics, "main"):
        advanced_analytics.main()
