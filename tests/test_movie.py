"""The clip a Version reviews: a file already on disk is never transformed."""
import sys
import types

import numpy as np
import pytest

from comfyui_sg import movie

PLAIN = ((1920, 1080), 10.0)


class FakeVideoFromFile:
    """ComfyUI's own VIDEO over a file. A trimmed clip reports the window, not the file."""

    def __init__(self, src, dimensions=PLAIN[0], duration=PLAIN[1]):
        self.src, self.dimensions, self.duration = src, dimensions, duration

    def get_stream_source(self):
        return self.src

    def get_dimensions(self):
        return self.dimensions

    def get_duration(self):
        return self.duration

    def get_frame_count(self):
        return 240

    def get_frame_rate(self):
        return 24.0

    def save_to(self, dest):
        with open(dest, "wb") as fh:
            fh.write(b"encoded")


@pytest.fixture
def comfy_api(monkeypatch):
    """ComfyUI's VIDEO type, stubbed, so the trim guard can be exercised with no ComfyUI."""
    parent, impl = types.ModuleType("comfy_api"), types.ModuleType("comfy_api.input_impl")
    impl.VideoFromFile = FakeVideoFromFile
    parent.input_impl = impl
    monkeypatch.setitem(sys.modules, "comfy_api", parent)
    monkeypatch.setitem(sys.modules, "comfy_api.input_impl", impl)
    return impl


class FakeTensor:
    def __init__(self, array):
        self.array = array

    def cpu(self):
        return self

    def numpy(self):
        return self.array


def test_the_frame_range_is_one_based():
    assert movie.frame_fields(48) == {"sg_first_frame": 1, "sg_last_frame": 48,
                                      "frame_count": 48, "frame_range": "1-48"}


def test_a_batch_frame_becomes_eight_bit_rgb():
    got = movie.to_u8(FakeTensor(np.array([[[0.0, 0.2, 1.0]]], dtype=np.float32)))
    assert got.dtype == np.uint8
    assert got.tolist() == [[[0, 51, 255]]]


def test_a_clip_that_is_a_file_goes_up_as_that_file(comfy_api, tmp_path):
    src = tmp_path / "plate.mov"
    src.write_bytes(b"movie")
    path, how = movie.stage(FakeVideoFromFile(str(src)), tmp_path / "out", "sh010_comp_v001")
    assert path == str(src)
    assert how == "the source file, uploaded unchanged: plate.mov"


def test_a_trimmed_clip_is_encoded_rather_than_filed_as_its_source(comfy_api, tmp_path):
    """corpus 028: `as_trimmed` keeps the source path, so the class alone proves nothing."""
    src = tmp_path / "plate.mov"
    src.write_bytes(b"movie")
    trimmed = FakeVideoFromFile(str(src), duration=2.0)
    path, how = movie.stage(trimmed, tmp_path / "out", "sh010_comp_v001")
    assert path == str(tmp_path / "out" / "sh010_comp_v001.mp4")
    assert how == "encoded by ComfyUI"


def test_a_cropped_clip_is_encoded_too(comfy_api, tmp_path):
    src = tmp_path / "plate.mov"
    src.write_bytes(b"movie")
    cropped = FakeVideoFromFile(str(src), dimensions=(960, 540))
    assert movie.source_file(cropped) == ""


def test_a_clip_held_in_memory_has_no_file_to_leave_untouched(comfy_api, tmp_path):
    assert movie.source_file(FakeVideoFromFile(str(tmp_path / "gone.mov"))) == ""


def test_the_sentence_names_the_count_the_rate_and_the_path_taken(comfy_api, tmp_path):
    count, said = movie.describe(FakeVideoFromFile(str(tmp_path / "x.mov")), "encoded by ComfyUI")
    assert count == 240
    assert said == "240 frames at 24 fps — encoded by ComfyUI"
