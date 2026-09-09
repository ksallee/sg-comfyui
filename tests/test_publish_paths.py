"""Where a published file lands: the extension swap, and the root a path field is written under."""
import pytest

from comfyui_sg import sequence

MAC = {"code": "primary", "mac_path": "/Volumes/FPT", "windows_path": "X:\\shows",
       "linux_path": "/mnt/fpt"}


@pytest.mark.parametrize("path,ext,want", [
    ("/root/sh010/sh010_matte_v001.png", ".exr", "/root/sh010/sh010_matte_v001.exr"),
    ("/root/sh010/sh010_matte_v001.exr", ".png", "/root/sh010/sh010_matte_v001.png"),
    # No extension to replace: the last dotted piece is the frame number.
    ("/root/sh010/sh010_matte_v001.%04d", ".exr", "/root/sh010/sh010_matte_v001.%04d.exr"),
    ("/root/sh010/sh010_matte_v001.####", ".png", "/root/sh010/sh010_matte_v001.####.png"),
    ("/root/sh010/sh010_matte_v001.@@@@", ".png", "/root/sh010/sh010_matte_v001.@@@@.png"),
    # Nothing dotted at all, and a dot that belongs to a directory rather than to a file.
    ("/root/sh010/sh010_matte_v001", ".png", "/root/sh010/sh010_matte_v001.png"),
    ("/root/v1.0/sh010_matte", ".png", "/root/v1.0/sh010_matte.png"),
])
def test_swap_ext(path, ext, want):
    assert sequence.swap_ext(path, ext) == want


def test_the_frame_token_survives_a_pattern_with_no_extension():
    out = sequence.pattern("/Volumes/FPT", "{entity}/{version_name}.%04d",
                           {"entity": "sh010", "version_name": "sh010_matte_v001"}, 1, ".exr")
    assert out == "/Volumes/FPT/sh010/sh010_matte_v001.%04d.exr"


def test_on_platform_writes_a_windows_root_with_backslashes():
    out = sequence.on_platform("/Volumes/FPT/sh010/sh010_matte_v001.%04d.exr",
                               "/Volumes/FPT", MAC, "windows")
    assert out == "X:\\shows\\sh010\\sh010_matte_v001.%04d.exr"


def test_on_platform_matches_a_root_written_the_other_way_round():
    """A Windows publisher renders a forward-slashed path against a raw `X:\\shows` root."""
    out = sequence.on_platform("X:/shows/sh010/sh010_matte_v001.%04d.exr",
                               "X:\\shows", MAC, "linux")
    assert out == "/mnt/fpt/sh010/sh010_matte_v001.%04d.exr"


def test_on_platform_leaves_this_machines_own_platform_alone():
    path = "/Volumes/FPT/sh010/f.%04d.exr"
    assert sequence.on_platform(path, "/Volumes/FPT", MAC, sequence.THIS_PLATFORM) == path


def test_on_platform_leaves_a_path_outside_the_root_alone():
    path = "/somewhere/else/f.%04d.exr"
    assert sequence.on_platform(path, "/Volumes/FPT", MAC, "windows") == path


def test_on_platform_leaves_a_platform_the_storage_does_not_define():
    path = "/Volumes/FPT/sh010/f.%04d.exr"
    row = {"code": "primary", "mac_path": "/Volumes/FPT"}
    assert sequence.on_platform(path, "/Volumes/FPT", row, "windows") == path


def test_a_site_with_no_storage_says_so():
    with pytest.raises(RuntimeError) as e:
        sequence.storage_row([], "")
    assert str(e.value) == ("This site has no Local File Storage, so nothing can be published to "
                            "it. Add one in Flow Production Tracking, under Site Preferences then "
                            "File Management.")


def test_an_unnamed_storage_among_several_names_the_setting():
    with pytest.raises(RuntimeError) as e:
        sequence.storage_row([MAC, {"code": "renders", "mac_path": "/Volumes/R"}], "")
    assert str(e.value) == ("No storage is chosen, and this site has 2 to choose from. Pick "
                            "Storage under Settings, then SG: primary, renders.")


def test_the_two_default_templates_put_the_movie_beside_the_frames_folder():
    """A sequence is many files and earns a folder; a movie is one and sits beside it."""
    vals = {"entity": "sh010", "root_name": "sh010_RTO", "version_name": "sh010_RTO_v003"}
    frames = sequence.pattern("/Volumes/FPT", sequence.DEFAULT_SEQUENCE_TEMPLATE,
                              dict(vals, ext=".exr"), 3, ".exr")
    movie = sequence.pattern("/Volumes/FPT", sequence.DEFAULT_MOVIE_TEMPLATE,
                             dict(vals, ext=".mov"), 3, ".mov")
    assert frames == "/Volumes/FPT/sh010/sh010_RTO/sh010_RTO_v003/sh010_RTO_v003.%04d.exr"
    assert movie == "/Volumes/FPT/sh010/sh010_RTO/sh010_RTO_v003.mov"
