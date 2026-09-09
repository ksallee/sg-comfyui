"""What every test needs before the first import: the package on the path, and the fakes.

Nothing here reaches the site. `sg_groundtruth`, `numpy`, `Pillow` and `requests` are the only
third-party imports the suite requires; a machine that also has torch and a ComfyUI checkout runs the
tests that decode real pixels, and every other machine skips those (`DECODES`).
"""
import os
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Reading a frame is ComfyUI's own decoder's job, so the tests that read one need a checkout of it.
COMFYUI = os.environ.get("COMFYUI_PATH", os.path.expanduser("~/dev/ComfyUI"))
if os.path.isdir(COMFYUI) and COMFYUI not in sys.path:
    sys.path.append(COMFYUI)

# The node modules import torch at module scope and call it only inside a run, so a bare module
# object is enough to make every module importable on a machine that has no torch.
try:
    import torch                        # noqa: F401
except ImportError:
    sys.modules.setdefault("torch", types.ModuleType("torch"))


def _can_decode():
    try:
        import comfy_api.latest._input_impl.video_types    # noqa: F401
        import comfy_extras.nodes_images                   # noqa: F401
    except Exception:
        return False
    return hasattr(sys.modules.get("torch"), "Tensor")


CAN_DECODE = _can_decode()
# For a test that decodes pixels rather than one that only names a file.
DECODES = pytest.mark.skipif(not CAN_DECODE,
                             reason="torch and a ComfyUI checkout read the pixels; set COMFYUI_PATH")

# The repo root holds ComfyUI's entry point `__init__.py`, so pytest collects the root as a package
# and imports that file under the name `__init__`, where its relative import cannot resolve. The
# entry point has nothing to collect, so it is answered with a stub before pytest asks.
_entry = types.ModuleType("__init__")
_entry.__file__ = str(ROOT / "__init__.py")
sys.modules.setdefault("__init__", _entry)

from comfyui_sg import lineage           # noqa: E402  — after sys.path is set


@pytest.fixture(autouse=True)
def clear_lineage():
    """What one test's Load node recorded must not be visible to the next."""
    lineage._resolved.clear()
    yield
    lineage._resolved.clear()


class FakeResponse:
    """One canned HTTP answer, shaped like `requests`."""

    def __init__(self, payload=None, status=200, ok=True):
        self.payload, self.status_code, self.ok = payload, status, ok
        self.text = "" if payload is None else str(payload)

    def json(self):
        return self.payload


class FakeSG:
    """A client that answers from a table instead of a site. `answer` registers one route."""

    def __init__(self, site="https://sg.example.com"):
        self.site = site
        self.calls = []
        self.bodies = []
        self._answers = []

    def answer(self, method, contains, payload, status=200, ok=True):
        self._answers.append((method.lower(), contains, FakeResponse(payload, status, ok)))
        return self

    def _reply(self, method, path):
        self.calls.append((method, path))
        for m, contains, response in reversed(self._answers):
            if m == method and contains in path:
                return response
        return FakeResponse({"errors": [{"title": "no such route"}]}, 404, False)

    def get(self, path, **kw):
        return self._reply("get", path)

    def post(self, path, **kw):
        self.bodies.append((path, kw.get("json")))
        return self._reply("post", path)


@pytest.fixture
def fake_sg():
    """A client answering canned JSON:API envelopes."""
    return FakeSG()


def rows(*entities):
    """A JSON:API list envelope."""
    return {"data": list(entities)}


def row(id, type="Version", relationships=None, **attributes):
    """One JSON:API resource."""
    out = {"id": id, "type": type, "attributes": attributes}
    if relationships:
        out["relationships"] = relationships
    return out


@pytest.fixture
def sequence_on_disk(tmp_path):
    """Write a PNG sequence and return its frame pattern.

    Each frame is filled with a colour that spells its own number, so a test can say which frames
    came back and in what order (`frame_number`).
    """
    from PIL import Image

    def write(first=1001, count=48, size=(16, 9), stem="plate", into=None):
        folder = Path(into or tmp_path)
        folder.mkdir(parents=True, exist_ok=True)
        for n in range(first, first + count):
            Image.new("RGB", size, (n % 256, (n // 256) % 256, 0)).save(
                folder / f"{stem}.{n:04d}.png")
        return str(folder / f"{stem}.%04d.png")

    return write


def frame_number(frame):
    """The frame number `sequence_on_disk` painted into a frame, whatever type it came back as."""
    import numpy as np

    if hasattr(frame, "getpixel"):
        r, g, b = frame.convert("RGB").getpixel((0, 0))
    else:
        a = np.asarray(frame.cpu().numpy() if hasattr(frame, "cpu") else frame)
        while a.ndim > 1:
            a = a[0]
        r, g, b = (float(x) for x in a[:3])
        if max(r, g, b) <= 1.0:
            r, g, b = (round(x * 255) for x in (r, g, b))
    return int(round(r)) + int(round(g)) * 256


def stub_site(monkeypatch, projects=(("Sandbox", 1180),), links=(("sh010 (Shot)", "Shot", 7514),),
              statuses=(("In Progress", "ip"), ("Approved", "apr")), profile=None):
    """Answer the picker lookups INPUT_TYPES makes, without a site."""
    from comfyui_sg import site

    p = profile or {}
    monkeypatch.setattr(site, "default_project", lambda: projects[0][1] if projects else 0)
    monkeypatch.setattr(site, "projects", lambda: list(projects))
    monkeypatch.setattr(site, "project_name", lambda pid=None: projects[0][0] if projects else "")
    monkeypatch.setattr(site, "links", lambda pid, **kw: list(links))
    monkeypatch.setattr(site, "statuses", lambda pid, *a, **kw: list(statuses))
    monkeypatch.setattr(site, "tasks_for", lambda *a, **kw: [("comp", 900)])
    monkeypatch.setattr(site, "entities", lambda *a, **kw: [("sh010", 7514)])
    monkeypatch.setattr(site, "for_project", lambda pid=None: p)
    monkeypatch.setattr(site, "profile", lambda: p)
    return p
