"""Locate the sibling corpus repo. Replaced by a real dependency once it is installable.

Repo and package are both `sg-groundtruth`/`sg_groundtruth`. Override with SG_GROUNDTRUTH_PATH.
"""
import os
import sys
from pathlib import Path

PACKAGE = "sg_groundtruth"
SIBLING = "sg-groundtruth"
_here = Path(__file__).resolve().parents[2].parent


def _find():
    root = Path(os.environ.get("SG_GROUNDTRUTH_PATH") or _here / SIBLING)
    if (root / "src" / PACKAGE).is_dir():
        return root
    raise ImportError(f"{PACKAGE} not found (looked in {root}); set SG_GROUNDTRUTH_PATH")


ROOT = _find()
sys.path.insert(0, str(ROOT / "src"))
