import os
import sys
import uvicorn

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_backend_dir)

for _p in [_backend_dir, _root_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.app.main import app

if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
