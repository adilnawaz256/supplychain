# Backward compatibility alias - Canonical implementation moved to backend/ml/scripts/supplier_segmentation.py
from backend.ml.scripts.supplier_segmentation import *
if __name__ == "__main__":
    import sys
    from backend.ml.scripts import supplier_segmentation
    if hasattr(supplier_segmentation, "main"):
        supplier_segmentation.main()
