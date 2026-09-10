"""Where the frames land: the storage, the path under its root, and the platform it is written for."""
import sys

import pytest

from comfyui_sg import sequence

# A directory mode does not stop a write on Windows, so the state cannot be produced there.
POSIX_MODES = pytest.mark.skipif(sys.platform == "win32",
                                 reason="a read-only directory needs a POSIX mode")

STORAGES = [
    {"id": 1, "code": "primary", "mac_path": "/Volumes/proj", "linux_path": "/mnt/proj",
     "windows_path": "X:\\proj"},
    {"id": 2, "code": "scratch", "mac_path": "/Volumes/scratch"},
]
VALUES = {"entity": "sh010", "root_name": "sh010_comp", "version_name": "sh010_comp_v003",
          "ext": ".png"}


def test_the_storage_is_chosen_by_code_never_by_position():
    assert sequence.storage_row(STORAGES, "scratch")["id"] == 2


def test_no_storage_of_that_name_lists_the_ones_there():
    with pytest.raises(RuntimeError) as e:
        sequence.storage_row(STORAGES, "nearline")
    assert "primary, scratch" in str(e.value)


def test_several_storages_and_no_choice_is_refused():
    with pytest.raises(RuntimeError) as e:
        sequence.storage_row(STORAGES)
    assert "Pick Storage under Settings, then SG" in str(e.value)


def test_a_platform_the_storage_has_no_root_for_is_not_offered():
    assert sequence.platforms_of(STORAGES[1]) == ["mac"]
    assert sequence.platform_for(STORAGES[1], "windows") == "mac"
    assert sequence.platform_for(STORAGES[0], "linux") == "linux"


def test_the_frame_token_survives_the_path_render():
    """`%04d` in a path is the FRAME; only `{version:03d}` is the publish revision."""
    got = sequence.pattern("/Volumes/proj", sequence.DEFAULT_SEQUENCE_TEMPLATE, VALUES, 3, ".png")
    assert got == "/Volumes/proj/sh010/sh010_comp/sh010_comp_v003/sh010_comp_v003.%04d.png"


def test_a_template_cannot_walk_out_of_the_storage_root():
    """A published file has to sit under the root the site resolves. A walk out of the root is
    neutralised before the check, and the check refuses anything left."""
    got = sequence.pattern("/Volumes/proj", "../{entity}/{version_name}.%04d{ext}",
                           dict(VALUES, entity="../sh010"), 3, ".png")
    assert got.startswith("/Volumes/proj/")
    assert ".." not in got


def test_windows_notation_is_backslashes_after_the_root_only(monkeypatch):
    monkeypatch.setattr(sequence, "THIS_PLATFORM", "mac")
    got = sequence.on_platform("/Volumes/proj/sh010/plate.%04d.png", "/Volumes/proj",
                               STORAGES[0], "windows")
    assert got == "X:\\proj\\sh010\\plate.%04d.png"


def test_a_path_outside_the_root_is_left_alone(monkeypatch):
    monkeypatch.setattr(sequence, "THIS_PLATFORM", "mac")
    assert sequence.on_platform("/tmp/plate.png", "/Volumes/proj", STORAGES[0], "windows") \
        == "/tmp/plate.png"


def test_a_root_spelled_with_backslashes_still_matches_the_path(monkeypatch):
    """The path is rendered with forward slashes (`_clean`), so the prefix test has to see past
    the spelling of the root the publisher ran on."""
    monkeypatch.setattr(sequence, "THIS_PLATFORM", "windows")
    got = sequence.on_platform("X:/proj/sh010/plate.%04d.png", "X:\\proj", STORAGES[0], "linux")
    assert got == "/mnt/proj/sh010/plate.%04d.png"


def test_the_extension_follows_the_files_not_the_template():
    assert sequence.swap_ext("/Volumes/proj/sh010/plate.%04d.exr", ".png") \
        == "/Volumes/proj/sh010/plate.%04d.png"


def test_a_template_with_no_extension_keeps_its_frame_token():
    assert sequence.swap_ext("/Volumes/proj/sh010/plate.%04d", ".png") \
        == "/Volumes/proj/sh010/plate.%04d.png"


def test_the_movie_sits_beside_the_folder_with_no_frame_token():
    assert sequence.single("/Volumes/proj/sh010/plate.%04d.png") == "/Volumes/proj/sh010/plate.png"
    assert sequence.single("/Volumes/proj/sh010/plate.mov") == "/Volumes/proj/sh010/plate.mov"


def test_path_cache_is_what_is_left_after_the_root():
    assert sequence.relative("/Volumes/proj", "/Volumes/proj/sh010/plate.0001.png") \
        == "sh010/plate.0001.png"


def test_the_colour_space_is_recorded_as_declared_never_guessed():
    assert sequence.describe_colour("") == ""
    assert sequence.describe_colour("ACEScg") == \
        "colour space: ACEScg (declared by the publisher, not converted)"


def test_an_unmounted_root_names_the_path_and_what_to_do(tmp_path):
    with pytest.raises(RuntimeError) as e:
        sequence.check_root(str(tmp_path / "not_here"))
    assert str(e.value).endswith("is not mounted on this machine. Mount it, then run again.")


@POSIX_MODES
def test_a_read_only_root_is_refused_before_anything_is_written(tmp_path):
    root = tmp_path / "readonly"
    root.mkdir()
    root.chmod(0o500)
    try:
        with pytest.raises(RuntimeError) as e:
            sequence.check_root(str(root))
    finally:
        root.chmod(0o700)
    assert str(e.value).endswith("is not writable by ComfyUI. Give it write access, then run again.")
