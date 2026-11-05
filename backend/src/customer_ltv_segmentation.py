# Backward compatibility alias - Canonical implementation moved to backend/ml/scripts/customer_ltv_segmentation.py
from backend.ml.scripts.customer_ltv_segmentation import *
if __name__ == "__main__":
    import sys
    from backend.ml.scripts import customer_ltv_segmentation
    if hasattr(customer_ltv_segmentation, "main"):
        customer_ltv_segmentation.main()
