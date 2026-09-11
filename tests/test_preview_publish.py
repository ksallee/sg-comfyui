"""What the publish panel is told before a Run: where the files are written, or why they cannot
be."""
import sys

import pytest

from comfyui_sg import publish, routes, site

# A directory mode does not stop a write on Windows, so the state cannot be produced there.
POSIX_MODES = pytest.mark.skipif(sys.platform == "win32",
                                 reason="a read-only directory needs a POSIX mode")

WIDGETS = {"register_files": True, "images": ["6", 0], "code_template": "sh010_matte_v001",
           "root_name": "sh010_matte"}


def test_a_storage_that_cannot_be_resolved_is_a_sentence_not_a_path(monkeypatch):
    monkeypatch.setattr(site, "client", lambda: None)
    monkeypatch.setattr(publish, "storages", lambda sg: [])
    where, alert = routes._files_preview(WIDGETS, {}, 1, "Shot", 2, 0)

    assert where == []
    assert alert == ("Create Published Files is ticked, but the paths could not be worked out. "
                     "This site has no Local File Storage, so nothing can be published to it. Add "
                     "one in Flow Production Tracking, under Site Preferences then File "
                     "Management.")


def test_a_storage_that_resolves_answers_with_the_path(tmp_path, monkeypatch):
    monkeypatch.setattr(site, "client", lambda: None)
    monkeypatch.setattr(publish, "storages",
                        lambda sg: [{"id": 7, "code": "primary", "mac_path": str(tmp_path),
                                     "linux_path": str(tmp_path), "windows_path": str(tmp_path)}])
    monkeypatch.setattr(site, "resolve_paths", lambda *a, **kw: {"entity": "sh010"})
    where, alert = routes._files_preview(WIDGETS, {}, 1, "Shot", 2, 0)

    assert alert == ""
    # The frame count is a run-time fact, so the readout names both paths: a batch of one is a
    # still, and two or more are a sequence.
    assert where == [
        {"label": "frames path", "path": (
            tmp_path / "sh010/sh010_matte/sh010_matte_v001/sh010_matte_v001.%04d.png").as_posix()},
        {"label": "still path",
         "path": (tmp_path / "sh010/sh010_matte/sh010_matte_v001.png").as_posix()}]


def test_a_root_that_is_not_mounted_is_the_sentence_the_run_would_raise(tmp_path, monkeypatch):
    gone = tmp_path / "sgtest"
    monkeypatch.setattr(site, "client", lambda: None)
    monkeypatch.setattr(publish, "storages",
                        lambda sg: [{"id": 7, "code": "primary", "mac_path": str(gone),
                                     "linux_path": str(gone), "windows_path": str(gone)}])
    monkeypatch.setattr(site, "resolve_paths", lambda *a, **kw: {"entity": "sh010"})
    where, alert = routes._files_preview(WIDGETS, {}, 1, "Shot", 2, 0)

    assert len(where) == 2
    assert alert == (f"The storage root {gone} is not mounted on this machine. Mount it, then run "
                     f"again.")


@POSIX_MODES
def test_a_root_that_is_mounted_and_read_only_is_refused_before_the_run(tmp_path, monkeypatch):
    """The panel asks the run's own guard, so a read-only share is not a publish that reads VALID."""
    root = tmp_path / "readonly"
    root.mkdir()
    root.chmod(0o500)
    monkeypatch.setattr(site, "client", lambda: None)
    monkeypatch.setattr(publish, "storages",
                        lambda sg: [{"id": 7, "code": "primary", "mac_path": str(root),
                                     "linux_path": str(root), "windows_path": str(root)}])
    monkeypatch.setattr(site, "resolve_paths", lambda *a, **kw: {"entity": "sh010"})
    try:
        where, alert = routes._files_preview(WIDGETS, {}, 1, "Shot", 2, 0)
    finally:
        root.chmod(0o700)

    assert len(where) == 2
    assert alert == (f"The storage root {root} is not writable by ComfyUI. Give it write access, "
                     f"then run again.")


def test_the_client_is_not_named_before_a_run():
    """Whoever POSTs /prompt names the client, and no Run has been submitted yet."""
    rows = routes._concept_rows({"generator": "ComfyUI"}, {"generator": "sg_ai_generator"},
                                ["sg_ai_generator"])

    assert rows == [{"name": "ai_generator", "label": "made by", "value": "ComfyUI",
                     "into_description": False,
                     "note": "The client that submits the Run is recorded with it."}]


def test_a_concept_with_no_value_says_so_instead():
    rows = routes._concept_rows({}, {"seed": "sg_ai_seed"}, ["sg_ai_seed"])

    assert rows[0]["value"] == "" and rows[0]["note"] == "Not in this graph."
