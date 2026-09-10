"""One frame is a file, not a sequence: what is registered, what `path_cache` is set to, and the
field left empty.

Nothing decodes here. `write_frames` is ComfyUI's encoder and is stood in for: what is under test
is the path the site is given.
"""
import pytest

from comfyui_sg import publish, sequence, site
from comfyui_sg.nodes.publish_version import SGPublishVersion

PROFILE = {"published_files": {"path_template": "{root_name}/{version_name}/"
                                                "{version_name}.%04d{ext}"}}


@pytest.fixture
def storage(tmp_path, monkeypatch):
    """A storage whose root is a directory on this machine, whatever the platform."""
    root = tmp_path / "FPT"
    root.mkdir()
    row = {"id": 7, "code": "primary", "mac_path": str(root), "linux_path": str(root),
           "windows_path": str(root)}
    monkeypatch.setattr(publish, "storages", lambda sg: [row])
    monkeypatch.setattr(site, "resolve_paths", lambda *a, **kw: {"entity": "sh010"})
    return root


@pytest.fixture
def wrote(monkeypatch, tmp_path):
    """`write_frames` without an encoder: N empty files, named the way ComfyUI's own writer does."""
    def fake(images, stem, fmt=""):
        out = []
        for i in range(1, len(images) + 1):
            p = tmp_path / f"{stem}.{i:04d}.png"
            p.write_bytes(b"")
            out.append(p)
        return out
    monkeypatch.setattr(sequence, "write_frames", fake)


def stage(n, storage, profile=None):
    """`_stage` for a batch of `n` frames, with nothing but the frames asked for."""
    return SGPublishVersion._stage([object()] * n, "", "sh010_matte_v001", 1, n, "",
                                   True, False, profile or PROFILE, None, 1, "Shot", 2, 0)


def test_one_frame_registers_the_file_that_is_on_disk(storage, wrote):
    staged = stage(1, storage)
    assert staged["frames_pattern"] == (storage / "sh010/sh010_matte_v001/sh010_matte_v001.0001.png").as_posix()
    assert staged["frames_code"] == "sh010_matte_v001.0001.png"


def test_a_sequence_keeps_the_pattern(storage, wrote):
    staged = stage(3, storage)
    assert staged["frames_pattern"] == (storage / "sh010/sh010_matte_v001/sh010_matte_v001.%04d.png").as_posix()


def test_one_frame_writes_no_frame_path_on_the_version_and_says_so(storage, wrote):
    staged = stage(1, storage)
    assert "frames_field" not in staged
    assert staged["frames_note"] == ("This publish is a single image, so no frame path was "
                                     "written on the Version.")


def test_a_sequence_writes_the_frame_path(storage, wrote):
    staged = stage(3, storage)
    assert staged["frames_field"].endswith("sh010_matte_v001.%04d.png")
    assert "frames_note" not in staged


def test_path_cache_holds_the_registered_path(storage, wrote, monkeypatch):
    """What the create is given, and what it is told to cache, name the same file."""
    sent = []
    monkeypatch.setattr(publish, "published_files_of", lambda *a, **kw: ([], ""))
    monkeypatch.setattr(publish, "published_file_type", lambda *a, **kw: (None, ""))
    monkeypatch.setattr(publish, "create_published_file",
                        lambda sg, pid, code, name, path, body: (sent.append((path, body)) or
                                                                 (7021, {})))
    staged = stage(1, storage)
    notes = SGPublishVersion._register(None, staged, 1, 32002, 1, "Shot", 2, 0, 1, "", "", [])

    path, body = sent[0]
    assert path == (storage / "sh010/sh010_matte_v001/sh010_matte_v001.0001.png").as_posix()
    assert body["path_cache"] == "sh010/sh010_matte_v001/sh010_matte_v001.0001.png"
    assert notes[-1] == ("Registered 1 frame as sh010_matte_v001.0001.png, "
                         "PublishedFile 7021. " + path)
