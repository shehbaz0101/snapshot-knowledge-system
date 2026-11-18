"""Contract-compatible entry point for the offline knowledge system."""
import sys
from pathlib import Path

for parent in Path(__file__).resolve().parents:
    if (parent / "harness" / "contract.py").exists():
        sys.path.insert(0, str(parent / "harness"))
        break
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ks import Knowledge


def build():
    """Create an empty knowledge system; the harness supplies snapshots."""
    return Knowledge()
