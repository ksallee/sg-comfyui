"""Reading frames back: a frame is the number in the filename, and a batch is refused before torch."""
import os

import pytest
from conftest import DECODES, frame_number
from sg_groundtruth.client import FPTError

from comfyui_sg import media

FIRST, COUNT = 1001, 48


@pytest.fixture
def version(sequence_on_disk):
    """A Version whose frames are on this machine, numbered 1001-1048."""
    return {"id": 1, "code": "sh010_comp_v001", "sg_path_to_frames": sequence_on_disk(FIRST, COUNT),
            "published_files": []}


def test_the_frame_token_is_padded_to_its_own_width():
    assert media.frame_path("plate.%04d.exr", 7) == "plate.0007.exr"
    assert media.frame_path("plate.####.exr", 7) == "plate.0007.exr"
    assert media.frame_path("plate.@@.exr", 7) == "plate.07.exr"
    assert media.frame_path("plate.%d.exr", 7) == "plate.7.exr"
    assert media.frame_path("plate.exr", 7) == "plate.exr"


def test_a_sequence_past_its_padding_is_still_that_sequence(tmp_path, sequence_on_disk):
    pattern = sequence_on_disk(first=9999, count=3)
    assert [n for n, _ in media.frame_numbers(pattern)] == [9999, 10000, 10001]


@DECODES
def test_frame_zero_is_wherever_the_sequence_starts(version):
    got, _ = media.load_frames(version, "frames", 0, 1)
    assert len(got) == 1
    assert frame_number(got[0]) == FIRST


@DECODES
def test_frame_is_a_number_not_a_position(version):
    """1003 means plate.1003.png, not the third frame of the sequence."""
    got, _ = media.load_frames(version, "frames", 1003, 1)
    assert frame_number(got[0]) == 1003


def test_a_frame_the_sequence_does_not_have_names_the_range(version):
    with pytest.raises(FPTError) as e:
        media.load_frames(version, "frames", 999, 1)
    said = str(e.value)
    assert "no frame 999" in said
    assert "between 1001 and 1048" in said
    assert "48 frames" in said


@DECODES
def test_count_zero_reads_to_the_end_of_the_sequence(version):
    got, _ = media.load_frames(version, "frames", 0, 0)
    assert len(got) == COUNT
    assert [frame_number(f) for f in got[:3]] == [1001, 1002, 1003]
    assert frame_number(got[-1]) == 1048


@DECODES
def test_a_batch_that_runs_out_comes_back_short_rather_than_padded(version):
    got, _ = media.load_frames(version, "frames", 0, 100)
    assert len(got) == COUNT


@DECODES
def test_a_batch_starting_mid_sequence_ends_with_the_sequence(version):
    got, _ = media.load_frames(version, "frames", 1040, 20)
    assert [frame_number(f) for f in got] == list(range(1040, 1049))


@DECODES
def test_a_batch_past_the_budget_says_how_many_fit(version):
    """The refusal comes before torch is asked to allocate."""
    with pytest.raises(FPTError) as e:
        media.load_frames(version, "frames", 0, 0, budget=1 / 2 ** 20)
    assert "would need" in str(e.value)
    assert f"frame_count to {media.frames_that_fit((16, 9), media.budget_bytes(1 / 2 ** 20))}" \
        in str(e.value)


def test_how_many_frames_fit_is_the_batchs_own_size():
    assert media.frames_that_fit((1920, 1080), 4 * 2 ** 30) == 172
    assert media.frames_that_fit((3840, 2160), 4 * 2 ** 30) == 43
    assert media.frames_that_fit((3840, 2160), 1) == 1


def test_a_small_budget_reads_as_itself_rather_than_as_zero():
    assert media.gib(0.05 * 2 ** 30) == "0.05"
    assert media.gib(4 * 2 ** 30) == "4"


def test_a_budget_under_a_tenth_of_a_gib_is_named_in_the_refusal():
    with pytest.raises(FPTError) as e:
        media._budget((1920, 1080), 20, media.budget_bytes(0.05))
    assert str(e.value) == ("Set frame_count to 2 or less at this resolution. 20 frames of "
                            "1920×1080 would need 0.463 GiB as one batch; the limit is 0.05 GiB, "
                            "batch_budget_gib in profile.local.json.")


def test_no_budget_set_is_the_built_in_fallback():
    assert media.budget_bytes(0) == media.DEFAULT_BUDGET_GIB * 2 ** 30
    assert media.budget_bytes("not a number") == media.DEFAULT_BUDGET_GIB * 2 ** 30


def test_a_budget_below_zero_falls_back_to_the_default():
    assert media.budget_bytes(-4) == media.budget_bytes(0)


def test_a_pattern_that_matches_nothing_says_so(tmp_path):
    v = {"sg_path_to_frames": str(tmp_path / "nothing.%04d.png"), "published_files": []}
    with pytest.raises(FPTError) as e:
        media.load_frames(v, "frames", 0, 1)
    assert "No files match the frame pattern" in str(e.value)


def test_a_published_file_is_the_source_a_person_picks(version):
    path = version["sg_path_to_frames"]
    version["published_files"] = [{"id": 7788, "link": "local", "path": path, "url": "",
                                   "name": os.path.basename(path),
                                   "type": "Rendered Image", "colour": "ACEScg"}]
    key = media.pf_key(version["published_files"][0])
    assert key.endswith("#7788")
    assert media.kind_of(version, key) == "sequence"
    assert media.colour_of(version, key) == "ACEScg"
    assert media.best(version, "image") == key


def test_a_version_that_can_deliver_nothing_offers_nothing():
    assert media.sources({"published_files": [], "sg_path_to_frames": "/nowhere/x.%04d.exr"}) == []
