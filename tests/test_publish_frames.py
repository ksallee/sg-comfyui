"""What `format` writes: the extension, the bit depth, and the sentence with no encoder.

The bit depth is read back off the written file with PyAV, the library ComfyUI's own encoder writes
with, so the file is read the way its format defines it rather than the way a library guesses.
"""
import sys

import numpy as np
import pytest
from conftest import DECODES

from comfyui_sg import sequence

# 100/65535: too small for 8 bits to hold at all, exact at 16, exact as a float. One value tells the
# three formats apart without asserting anything about rounding.
FAINT = 100.0 / 65535.0

FORMATS = [
    ("8-bit PNG", ".png", "rgb24", 0.0),
    ("16-bit PNG", ".png", "rgb48be", FAINT),
    ("EXR 32-bit float", ".exr", "gbrpf32le", FAINT),
]


def decoded(path):
    """(the encoded stream's pixel format, its first pixel as a float 0-1)."""
    import av

    with av.open(str(path)) as container:
        frame = next(container.decode(container.streams.video[0]))
        name = frame.format.name
        if name.startswith("gbrp"):                      # EXR: planar float, G first
            a = frame.to_ndarray()
            return name, float(a.reshape(a.shape[0], -1)[0, 0])
        a = frame.to_ndarray(format=name)
        scale = 255.0 if a.dtype == np.uint8 else 65535.0
        return name, float(a.reshape(-1)[0]) / scale


@pytest.fixture
def batch():
    import torch

    return torch.full((2, 4, 4, 3), FAINT)


@pytest.mark.parametrize("fmt,ext,_pix,_value", FORMATS)
def test_extension_follows_the_format(fmt, ext, _pix, _value):
    assert sequence.extension(fmt) == ext


def test_an_unknown_format_is_the_default():
    assert sequence.extension("") == sequence.extension(sequence.DEFAULT_FORMAT) == ".png"


@DECODES
@pytest.mark.parametrize("fmt,ext,pix,value", FORMATS)
def test_write_frames_holds_the_bit_depth(tmp_path, monkeypatch, batch, fmt, ext, pix, value):
    monkeypatch.setattr(sequence, "output_dir", lambda: tmp_path)
    written = sequence.write_frames(batch, "sh010_matte_v001", fmt)

    assert [p.name for p in written] == [f"sh010_matte_v001.000{i}{ext}" for i in (1, 2)]
    for p in written:
        assert decoded(p) == (pix, pytest.approx(value, abs=1e-9))


@DECODES
def test_a_missing_encoder_says_what_to_do(tmp_path, monkeypatch, batch):
    monkeypatch.setattr(sequence, "output_dir", lambda: tmp_path)
    monkeypatch.setitem(sys.modules, "comfy_extras.nodes_images", None)
    with pytest.raises(RuntimeError) as e:
        sequence.write_frames(batch, "sh010_matte_v001", "EXR 32-bit float")
    assert str(e.value) == ("Writing EXR 32-bit float needs ComfyUI 0.34.0 or newer. Update "
                            "ComfyUI, or pick 8-bit PNG.")
