"""Locate the sibling corpus repo. Replaced by a real dependency once it is installable.

The package is `sg_groundtruth`; the checkout directory has been called more than one thing, so both
known names are tried before giving up. Override with FPT_LLM_API_PATH.
"""
import os
import sys
from pathlib import Path

PACKAGE = "sg_groundtruth"
SIBLINGS = ("fpt-llm-api", "sg-groundtruth")
_here = Path(__file__).resolve().parents[2].parent


def _find():
    override = os.environ.get("FPT_LLM_API_PATH")
    for root in ([Path(override)] if override else [_here / n for n in SIBLINGS]):
        if (root / "src" / PACKAGE).is_dir():
            return root
    tried = override or ", ".join(str(_here / n) for n in SIBLINGS)
    raise ImportError(f"{PACKAGE} not found (looked in {tried}); set FPT_LLM_API_PATH")


ROOT = _find()
sys.path.insert(0, str(ROOT / "src"))
