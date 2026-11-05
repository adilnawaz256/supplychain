# Backward compatibility alias - Canonical implementation moved to backend/ml/scripts/retail_kpi_metrics.py
from backend.ml.scripts.retail_kpi_metrics import *
if __name__ == "__main__":
    import sys
    from backend.ml.scripts import retail_kpi_metrics
    if hasattr(retail_kpi_metrics, "main"):
        retail_kpi_metrics.main()
