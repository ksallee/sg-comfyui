"""The `mask` input: the alpha it writes, the sizes it refuses, and the still it leaves for review.

A refusal names both sizes and reaches no tensor, so it runs anywhere. The join is torch and the
round trip is ComfyUI's own encoder and decoder, so those skip where neither is installed.
"""
import io
import sys

import numpy as np
import pytest
from conftest import DECODES
from PIL import Image

from comfyui_sg import media, sequence
from comfyui_sg.nodes.publish_version import SGPublishVersion, _png

TORCH = pytest.mark.skipif(not hasattr(sys.modules.get("torch"), "Tensor"),
                           reason="the join is torch; conftest stubs it where it is absent")

FORMATS = ["8-bit PNG", "16-bit PNG", "EXR 32-bit float"]


class FakeTensor:
    """A frame `to_u8` can read, so the review still needs no torch."""

    def __init__(self, array):
        self.array = array

    def cpu(self):
        return self

    def numpy(self):
        return self.array


def test_a_mask_of_another_size_is_refused_with_both_sizes():
    with pytest.raises(ValueError) as e:
        sequence.with_alpha(np.zeros((2, 9, 16, 3), np.float32), np.zeros((1, 18, 32), np.float32))
    assert str(e.value) == ("The mask is 32x18 and the frames are 16x9. Wire a mask the size of "
                            "the frames, or unplug it.")


def test_masks_that_are_not_the_frame_count_are_refused_with_both_counts():
    with pytest.raises(ValueError) as e:
        sequence.with_alpha(np.zeros((4, 8, 8, 3), np.float32), np.zeros((2, 8, 8), np.float32))
    assert str(e.value) == ("There are 2 masks and 4 frames. Wire one mask for the batch, or one "
                            "mask per frame.")


def test_a_mask_with_a_clip_and_no_frames_is_refused():
    with pytest.raises(ValueError) as e:
        SGPublishVersion().publish(video=object(), mask=np.zeros((1, 8, 8), np.float32))
    assert str(e.value) == ("The mask is the alpha for the frames, and no frames are wired. Wire "
                            "the frames into images, or unplug the mask.")


@TORCH
def test_the_fourth_channel_is_one_minus_the_mask():
    import torch

    out = sequence.with_alpha(torch.zeros((1, 2, 2, 3)),
                              torch.tensor([[[0.0, 0.25], [0.5, 1.0]]]))
    assert tuple(out.shape) == (1, 2, 2, 4)
    assert out[..., 3].tolist() == [[[1.0, 0.75], [0.5, 0.0]]]


@TORCH
def test_one_mask_applies_to_every_frame_of_the_batch():
    import torch

    out = sequence.with_alpha(torch.zeros((3, 2, 2, 3)), torch.full((2, 2), 0.25))
    assert tuple(out.shape) == (3, 2, 2, 4)
    assert torch.equal(out[..., 3], torch.full((3, 2, 2), 0.75))


@TORCH
def test_a_mask_outside_zero_to_one_is_clamped():
    import torch

    out = sequence.with_alpha(torch.zeros((1, 1, 1, 3)), torch.tensor([[[-2.0]]]))
    assert out[..., 3].tolist() == [[[1.0]]]


def test_the_review_still_keeps_the_alpha():
    frame = FakeTensor(np.array([[[0.0, 0.5, 1.0, 0.25]]], dtype=np.float32))
    with Image.open(io.BytesIO(_png(frame))) as im:
        assert im.mode == "RGBA"
        assert im.getpixel((0, 0)) == (0, 128, 255, 64)


@DECODES
@pytest.mark.parametrize("fmt", FORMATS)
def test_the_written_frame_reads_back_with_the_alpha(tmp_path, monkeypatch, fmt):
    """The decoder SG Load reads a Version with, over the frames this publish wrote.

    32x32, because ComfyUI's decoder pads a frame whose width is not a multiple of 32 and its pad
    filter refuses a 16-bit or float frame of 4 pixels.
    """
    import torch

    monkeypatch.setattr(sequence, "output_dir", lambda: tmp_path)
    images = sequence.with_alpha(torch.full((1, 32, 32, 3), 0.5), torch.full((1, 32, 32), 0.2))
    written = sequence.write_frames(images, "sh010_matte_v001", fmt)

    _, alpha = media._components(str(written[0]), written[0].name)
    assert alpha is not None
    assert float(alpha[0, 0, 0, -1]) == pytest.approx(0.8, abs=1e-4)
