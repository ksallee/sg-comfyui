"""SG Load reads what is in the file: 16-bit levels, float range, and the alpha behind the mask.

The fixtures are written at test time by ComfyUI's own encoder rather than committed, so what is
read back is exactly what core writes. Everything here needs ComfyUI on the path; without it the
whole module skips.
"""
import pytest
from conftest import CAN_DECODE

from comfyui_sg import media

if not CAN_DECODE:                       # nothing below this line imports without the decoder
    pytest.skip("torch and a ComfyUI checkout read the pixels; set COMFYUI_PATH",
                allow_module_level=True)

import torch                                                 # noqa: E402
from comfy_extras.nodes_images import _encode_image          # noqa: E402

# Wide enough that the decoder's 32-pixel alignment path is not the thing under test.
W, H = 256, 8
# 256 columns two 16-bit codes apart: every value is inside the first 8-bit code, so a read that
# quantises to 8 bits has nothing left to tell them apart.
STEP = 2 / 65535.0


def ramp(step=STEP, channels=1):
    """A [H,W,channels] ramp whose neighbouring columns differ by `step`."""
    one = (torch.arange(W, dtype=torch.float32) * step).view(1, W, 1).repeat(H, 1, 1)
    return torch.cat([one] * channels, dim=-1)


def write(tmp_path, name, tensor, fmt, depth):
    p = str(tmp_path / name)
    with open(p, "wb") as fh:
        fh.write(_encode_image(tensor, fmt, depth, "linear"))
    return p


def sequence(tmp_path, tensor=None, count=3, fmt="png", depth="16-bit", first=1001):
    """A `.%04d.png` sequence on disk, and the Version dict that names it."""
    tensor = ramp() if tensor is None else tensor
    for i in range(count):
        write(tmp_path, f"plate.{first + i:04d}.{fmt}", tensor, fmt, depth)
    return {"id": 1, "published_files": [],
            "sg_path_to_frames": str(tmp_path / f"plate.%04d.{fmt}")}


def levels(images):
    return len(torch.unique(images[..., 0]))


# --- precision ------------------------------------------------------------------------------------

def test_16_bit_grey_keeps_every_level(tmp_path):
    p = write(tmp_path, "g16.png", ramp(), "png", "16-bit")
    images, alpha = media._components(p, "g16.png")
    assert images.dtype is torch.float32
    assert tuple(images.shape) == (1, H, W, 3)
    assert levels(images) == 256
    assert float(images.max()) == pytest.approx((W - 1) * STEP, abs=1e-6)
    assert alpha is None


def test_16_bit_rgb_keeps_every_level(tmp_path):
    images, _ = media._components(write(tmp_path, "rgb16.png", ramp(channels=3), "png", "16-bit"),
                                  "rgb16.png")
    assert levels(images) == 256
    assert float(images.max()) == pytest.approx((W - 1) * STEP, abs=1e-6)


def test_pillow_loses_what_the_decoder_keeps(tmp_path):
    """The same two files through Pillow, which is why it is not on this path."""
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image")
    rgb = write(tmp_path, "rgb16.png", ramp(channels=3), "png", "16-bit")
    with Image.open(rgb) as im:
        assert len(np.unique(np.array(im.convert("RGB"))[..., 0])) == 2
    grey = write(tmp_path, "g16.png", ramp(), "png", "16-bit")
    with Image.open(grey) as im:
        # Not merely coarser: the brightest pixel reads full white where the file says 510/65535.
        assert np.array(im.convert("RGB")).max() == 255


def test_exr_reads_values_above_one(tmp_path):
    steps = torch.tensor([0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0])
    row = steps.repeat(W // len(steps) + 1)[:W].view(1, W, 1).repeat(H, 1, 1)
    p = write(tmp_path, "hdr.exr", torch.cat([row] * 3, dim=-1), "exr", "32-bit float")
    images, _ = media._components(p, "hdr.exr")
    assert float(images.max()) == 8.0
    assert images[0, 0, :7, 0].tolist() == steps.tolist()


def test_pillow_cannot_open_an_exr(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    p = write(tmp_path, "hdr.exr", ramp(channels=3), "exr", "32-bit float")
    with pytest.raises(Exception):
        Image.open(p).load()


# --- alpha and the mask ---------------------------------------------------------------------------

def test_rgba_comes_back_with_its_alpha(tmp_path):
    rgba = torch.cat([ramp(1 / 255.0, 3), torch.full((H, W, 1), 0.25)], dim=-1)
    images, alpha = media._components(write(tmp_path, "a.png", rgba, "png", "8-bit"), "a.png")
    assert tuple(images.shape) == (1, H, W, 3)
    assert tuple(alpha.shape) == (1, H, W, 1)
    # The node's own rule, which is ComfyUI's convention.
    mask = 1.0 - alpha[..., -1]
    assert tuple(mask.shape) == (1, H, W)
    assert float(mask.mean()) == pytest.approx(0.75, abs=1 / 255.0)


def test_a_source_with_no_alpha_reports_none(tmp_path):
    v = sequence(tmp_path)
    images, alpha = media.load_frames(v, "frames", 0, 0)
    assert tuple(images.shape) == (3, H, W, 3)
    assert alpha is None


def test_the_node_appends_mask_last():
    node = pytest.importorskip("comfyui_sg.nodes.load_version").SGLoadVersion
    assert node.RETURN_NAMES == ("image", "version_id", "code", "colour_space", "video", "mask")
    assert node.RETURN_TYPES == ("IMAGE", "INT", "STRING", "STRING", "VIDEO", "MASK")
    # Appended, never inserted: every earlier slot keeps its index in graphs already saved.
    assert node.RETURN_NAMES[:5] == ("image", "version_id", "code", "colour_space", "video")


# --- a sequence off disk --------------------------------------------------------------------------

def test_a_16_bit_sequence_stacks_at_full_precision(tmp_path):
    v = sequence(tmp_path, count=3)
    images, _ = media.load_frames(v, "frames", 0, 0)
    assert tuple(images.shape) == (3, H, W, 3)
    assert levels(images) == 256


def test_frame_is_the_number_in_the_filename(tmp_path):
    v = sequence(tmp_path, count=3, first=1001)
    images, _ = media.load_frames(v, "frames", 1002, 2)
    assert tuple(images.shape) == (2, H, W, 3)
    with pytest.raises(Exception) as e:
        media.load_frames(v, "frames", 1010, 1)
    assert "1001" in str(e.value) and "1003" in str(e.value)


def test_frame_size_reads_the_header(tmp_path):
    v = sequence(tmp_path)
    assert media.frame_size(v, "frames") == (W, H)


def test_frames_of_different_sizes_are_refused_by_name(tmp_path):
    v = sequence(tmp_path, count=2)
    odd = torch.zeros((H * 2, W, 1))
    write(tmp_path, "plate.1003.png", odd, "png", "16-bit")
    with pytest.raises(Exception) as e:
        media.load_frames(v, "frames", 0, 0)
    assert "plate.1003.png" in str(e.value)


def test_the_budget_refuses_and_says_how_many_fit(tmp_path):
    v = sequence(tmp_path, count=3)
    one = W * H * 3 * 4
    with pytest.raises(Exception) as e:
        media.load_frames(v, "frames", 0, 0, budget=2 * one / 2 ** 30)
    assert f"{W}×{H}" in str(e.value)


def test_a_non_positive_budget_falls_back_to_the_default():
    assert media.budget_bytes(0) == media.DEFAULT_BUDGET_GIB * 2 ** 30
    assert media.budget_bytes(-4) == media.DEFAULT_BUDGET_GIB * 2 ** 30
    assert media.budget_bytes("") == media.DEFAULT_BUDGET_GIB * 2 ** 30
    assert media.budget_bytes("nonsense") == media.DEFAULT_BUDGET_GIB * 2 ** 30
    assert media.budget_bytes(2) == 2 * 2 ** 30


def test_frame_count_declares_the_default_its_signature_takes():
    import inspect

    from comfyui_sg import widgets
    node = pytest.importorskip("comfyui_sg.nodes.load_version").SGLoadVersion
    declared = widgets.field(widgets.LOAD_FIELDS, "frame_count").default
    for fn in (node.load, node.IS_CHANGED):
        assert inspect.signature(fn).parameters["frame_count"].default == declared


# --- a movie, one frame at a time -------------------------------------------------------------------

def movie(tmp_path, frames=8, width=W, height=H, name="plate.mp4"):
    """A short mp4 written by ComfyUI's own encoder, and the Version dict that names it."""
    from fractions import Fraction

    from comfy_api.latest._input_impl import VideoFromComponents
    from comfy_api.latest._util import VideoComponents

    ramp = torch.linspace(0, 1, width).view(1, 1, width, 1).repeat(frames, height, 1, 3).clone()
    for i in range(frames):
        ramp[i] *= (i + 1) / frames
    path = str(tmp_path / name)
    VideoFromComponents(VideoComponents(images=ramp, frame_rate=Fraction(24))).save_to(path)
    return path, {"id": 1, "published_files": [], "sg_path_to_frames": "",
                  "sg_path_to_movie": path}


def test_a_movie_decodes_to_the_same_pixels_as_core(tmp_path):
    from comfy_api.latest._input_impl.video_types import VideoFromFile

    path, v = movie(tmp_path, frames=6)
    images, alpha = media.load_frames(v, "movie", 0, 0)
    core = VideoFromFile(path).get_components()
    assert tuple(images.shape) == tuple(core.images.shape)
    assert torch.equal(images, core.images)
    assert alpha is None and core.alpha is None


def test_a_movie_whose_width_is_not_a_multiple_of_32_decodes_the_same(tmp_path):
    from comfy_api.latest._input_impl.video_types import VideoFromFile

    path, v = movie(tmp_path, frames=4, width=40, height=24, name="odd.mp4")
    images, _ = media.load_frames(v, "movie", 0, 0)
    assert torch.equal(images, VideoFromFile(path).get_components().images)


def test_frame_counts_decoded_frames_in_a_movie(tmp_path):
    _, v = movie(tmp_path, frames=8)
    images, _ = media.load_frames(v, "movie", 3, 2)
    assert tuple(images.shape) == (2, H, W, 3)
    whole, _ = media.load_frames(v, "movie", 0, 0)
    assert torch.equal(images, whole[2:4])


def test_a_movie_says_how_many_frames_it_has(tmp_path):
    _, v = movie(tmp_path, frames=8)
    # Off the container header, so the panel can warn about a batch before the run rather than
    # after it. A movie is numbered from 1.
    assert media.frame_range(v, "movie") == (1, 8, 8)


def test_a_movie_on_no_machine_here_reports_no_range():
    v = {"id": 1, "published_files": [],
         "sg_uploaded_movie": {"url": "https://s3/x?sig", "name": "plate.mov"}}
    assert media.frame_range(v, "uploaded") is None


def test_a_movie_past_the_budget_is_refused_before_it_is_all_decoded(tmp_path, monkeypatch):
    _, v = movie(tmp_path, frames=64)
    seen = []
    real = media._frames_of

    def counted(*a, **kw):
        for got in real(*a, **kw):
            seen.append(got[2])
            yield got

    monkeypatch.setattr(media, "_frames_of", counted)
    two = 2 * W * H * 3 * 4 / 2 ** 30
    with pytest.raises(Exception) as e:
        media.load_frames(v, "movie", 0, 0, budget=two)
    assert f"3 frames of {W}×{H}" in str(e.value)
    assert "frame_count to 2" in str(e.value)
    # Three decoded of sixty-four: the ceiling refuses as the batch grows, not after the file is read.
    assert len(seen) == 3
