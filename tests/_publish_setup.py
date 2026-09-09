"""Path wiring the test_publish_* files share. Not a conftest: it changes nothing for anyone else.

    ~/dev/ComfyUI/venv/bin/python -m pytest tests --import-mode=importlib --confcutdir=tests

Both flags are needed, and for one reason: the repo root carries the `__init__.py` ComfyUI reads.
Without them pytest takes the whole checkout for a package, imports that file, and either fails on
its relative import or runs `routes.register()` against a server that is not there.

The package under test lives in `src/` and nothing installs it; ComfyUI's own encoder is read from
the checkout, which is `~/dev/ComfyUI` unless COMFYUI_PATH says otherwise. A machine with neither
skips rather than fails, so these run in a checkout with no ComfyUI beside it.
"""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COMFY = Path(os.environ.get("COMFYUI_PATH", Path.home() / "dev" / "ComfyUI"))

for _d in (REPO / "src", COMFY):
    if _d.is_dir() and str(_d) not in sys.path:
        sys.path.insert(0, str(_d))


def encoder():
    """ComfyUI's own `_encode_image`, or None where this machine has no ComfyUI to read it from."""
    try:
        from comfy_extras.nodes_images import _encode_image
    except Exception:
        return None
    return _encode_image


def decoded(path):
    """(the encoded stream's pixel format, its first pixel as a float 0-1).

    PyAV, which is what ComfyUI's encoder writes with, so this reads the file the way the format
    itself defines it rather than the way a library guesses.
    """
    import av
    import numpy as np

    with av.open(str(path)) as container:
        frame = next(container.decode(container.streams.video[0]))
        name = frame.format.name
        if name.startswith("gbrp"):                      # EXR: planar float, G first
            a = frame.to_ndarray()
            return name, float(a.reshape(a.shape[0], -1)[0, 0])
        a = frame.to_ndarray(format=name)
        scale = 255.0 if a.dtype == np.uint8 else 65535.0
        return name, float(a.reshape(-1)[0]) / scale
