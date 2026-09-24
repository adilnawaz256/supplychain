# Backward compatibility alias - Canonical implementation moved to backend/ml/scripts/inventory_planning.py
from backend.ml.scripts.inventory_planning import *
if __name__ == "__main__":
    import sys
    from backend.ml.scripts import inventory_planning
    if hasattr(inventory_planning, "main"):
        inventory_planning.main()
