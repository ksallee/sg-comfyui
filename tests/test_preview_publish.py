"""What the publish panel is told before a Run: where the files land, or the one sentence why they
cannot."""
from comfyui_sg import publish, routes, site

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
    assert where == [(tmp_path / "sh010/sh010_matte/sh010_matte_v001/sh010_matte_v001.%04d.png").as_posix()]
