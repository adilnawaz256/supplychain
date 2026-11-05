# Backward compatibility alias - Canonical implementation moved to backend/ml/scripts/policy_simulation.py
from backend.ml.scripts.policy_simulation import *
if __name__ == "__main__":
    import sys
    from backend.ml.scripts import policy_simulation
    if hasattr(policy_simulation, "main"):
        policy_simulation.main()
