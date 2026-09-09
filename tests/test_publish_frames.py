"""What `format` writes: the extension, the bit depth, and the sentence with no encoder."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _publish_setup as setup                                                      # noqa: E402

pytest.importorskip("torch")
if setup.encoder() is None:
    pytest.skip("no ComfyUI to read the encoder from", allow_module_level=True)

import torch                                                                       # noqa: E402

from comfyui_sg import sequence                                                     # noqa: E402

# 100/65535: too small for 8 bits to hold at all, exact at 16, exact as a float. One value tells
# the three formats apart without asserting anything about rounding.
FAINT = 100.0 / 65535.0

FORMATS = [
    ("8-bit PNG", ".png", "rgb24", 0.0),
    ("16-bit PNG", ".png", "rgb48be", FAINT),
    ("EXR 32-bit float", ".exr", "gbrpf32le", FAINT),
]


@pytest.fixture
def batch():
    return torch.full((2, 4, 4, 3), FAINT)


@pytest.mark.parametrize("fmt,ext,_pix,_value", FORMATS)
def test_extension_follows_the_format(fmt, ext, _pix, _value):
    assert sequence.extension(fmt) == ext


def test_an_unknown_format_is_the_default():
    assert sequence.extension("") == sequence.extension(sequence.DEFAULT_FORMAT) == ".png"


@pytest.mark.parametrize("fmt,ext,pix,value", FORMATS)
def test_write_frames_holds_the_bit_depth(tmp_path, monkeypatch, batch, fmt, ext, pix, value):
    monkeypatch.setattr(sequence, "output_dir", lambda: tmp_path)
    written = sequence.write_frames(batch, "sh010_matte_v001", fmt)

    assert [p.name for p in written] == [f"sh010_matte_v001.000{i}{ext}" for i in (1, 2)]
    for p in written:
        assert setup.decoded(p) == (pix, pytest.approx(value, abs=1e-9))


def test_a_missing_encoder_says_what_to_do(tmp_path, monkeypatch, batch):
    monkeypatch.setattr(sequence, "output_dir", lambda: tmp_path)
    monkeypatch.setitem(sys.modules, "comfy_extras.nodes_images", None)
    with pytest.raises(RuntimeError) as e:
        sequence.write_frames(batch, "sh010_matte_v001", "EXR 32-bit float")
    assert str(e.value) == ("Writing EXR 32-bit float needs ComfyUI 0.34.0 or newer. Update "
                            "ComfyUI, or pick 8-bit PNG.")
