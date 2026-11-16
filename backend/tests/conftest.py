import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# The backend route validates through the engine, so a source checkout
# must expose its src/ package to backend tests.
ENGINE_SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(ENGINE_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_SRC_ROOT))
