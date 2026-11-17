"""The Registry archive leaves out the command-line tools that read a path given to them.

`comfy node publish` uploads every git-tracked file minus `.comfyignore`. The Registry flags a read
from a caller's path (`policy-v0.5: arbitrary-file-read`).
"""
import re
import shutil
import subprocess

import pytest

from conftest import ROOT

pytestmark = pytest.mark.skipif(not shutil.which("git") or not (ROOT / ".git").exists(),
                                reason="needs a git checkout")

READS_A_GIVEN_PATH = ["src/comfyui_sg/instrument.py", "src/comfyui_sg/seed.py"]
IMPORTS_ONE = re.compile(r"^\s*(from|import)\s.*\b(instrument|seed)\b", re.M)


def _shipped():
    """The tracked files `.comfyignore` does not match."""
    git = ["git", "-C", str(ROOT)]
    tracked = subprocess.run([*git, "ls-files"], capture_output=True, text=True).stdout.split()
    ignored = subprocess.run([*git, "-c", f"core.excludesFile={ROOT / '.comfyignore'}",
                              "check-ignore", "--no-index", "--stdin"],
                             input="\n".join(tracked), capture_output=True, text=True)
    return set(tracked) - set(ignored.stdout.split())


def test_tools_that_read_a_given_path_are_not_shipped():
    shipped = _shipped()
    assert "src/comfyui_sg/nodes/publish_version.py" in shipped
    assert [p for p in READS_A_GIVEN_PATH if p in shipped] == []


def test_nothing_shipped_imports_them():
    hits = [p for p in sorted(_shipped()) if p.endswith(".py")
            and IMPORTS_ONE.search((ROOT / p).read_text(encoding="utf-8"))]
    assert hits == []
