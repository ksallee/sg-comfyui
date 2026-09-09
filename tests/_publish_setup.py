"""What the frame tests need beyond conftest: the real torch, and ComfyUI's own encoder.

conftest stubs `torch` so every module imports on a machine that has none, which is right for the
rest of the suite and not enough here: `_encode_image` is the thing under test and it wants tensors.
So the stub is swapped for the genuine article where one is installed, and put back where it is not.

ComfyUI itself is read from `~/dev/ComfyUI` unless COMFYUI_PATH says otherwise. A machine with
neither skips rather than fails, which is what CI does.
"""
import os
import sys
from pathlib import Path

COMFY = Path(os.environ.get("COMFYUI_PATH", Path.home() / "dev" / "ComfyUI"))

if COMFY.is_dir() and str(COMFY) not in sys.path:
    sys.path.insert(0, str(COMFY))


def real_torch():
    """The installed torch, or None. conftest's stub is restored where there is none."""
    stub = sys.modules.get("torch")
    if stub is not None and hasattr(stub, "full"):
        return stub
    if stub is not None:
        del sys.modules["torch"]
    try:
        import torch
    except ImportError:
        torch = None
    if torch is None or not hasattr(torch, "full"):
        if stub is not None:
            sys.modules["torch"] = stub
        return None
    return torch


def encoder():
    """ComfyUI's own `_encode_image`, or None where this machine cannot import it."""
    if real_torch() is None:
        return None
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
