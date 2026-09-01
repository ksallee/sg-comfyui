"""Locate the sibling corpus repo. Replaced by a real dependency once fpt-llm-api is installable."""
import os
import sys
from pathlib import Path

_default = Path(__file__).resolve().parents[2].parent / "fpt-llm-api"
ROOT = Path(os.environ.get("FPT_LLM_API_PATH", _default))
if not (ROOT / "src" / "fpt_llm_api").is_dir():
    raise ImportError(f"fpt-llm-api not found at {ROOT}; set FPT_LLM_API_PATH")
sys.path.insert(0, str(ROOT / "src"))
