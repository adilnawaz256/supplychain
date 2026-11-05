# Backward compatibility alias - Canonical implementation moved to backend/ml/scripts/assortment_planning.py
from backend.ml.scripts.assortment_planning import *
if __name__ == "__main__":
    import sys
    from backend.ml.scripts import assortment_planning
    if hasattr(assortment_planning, "main"):
        assortment_planning.main()
