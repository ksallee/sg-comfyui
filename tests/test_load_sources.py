"""Which sources SG Load offers, what it calls them, and which Version a rule lands on.

Nothing here touches a site: `_published_files` is driven with a stub client, and `resolve.pick`
through the one function it asks the site for.
"""
import os
import sys
import types

import pytest

# pytest makes the repo root a package because ComfyUI's entry point lives in `__init__.py` there,
# and that file's relative import fails outside ComfyUI. A bare module under the name it would be
# imported as keeps the collector from running it. Belongs in tests/conftest.py once there is one.
sys.modules.setdefault("__init__", types.ModuleType("__init__"))

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(_ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(_ROOT, "src"))

from comfyui_sg import media, naming, resolve  # noqa: E402


class Answer:
    def __init__(self, rows=None, ok=True, status=200, text="", json_body=True):
        self.ok, self.status_code, self.text = ok, status, text
        self._rows, self._json = rows or [], json_body

    def json(self):
        if not self._json:
            raise ValueError("Expecting value")
        return {"data": self._rows}


class Site:
    """Just enough of the client for `published_files`."""

    def __init__(self, answer):
        self.answer = answer

    def post(self, *a, **kw):
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def row(pid, path, pft="Rendered Image", description=""):
    return {"id": pid, "attributes": {"path": path, "description": description},
            "relationships": {"published_file_type": {"data": {"name": pft}}}}


LOCAL = {"link_type": "local", "name": "sh010_v001.%04d.png",
         media.LOCAL_PATH: "/vol/sh010_v001.%04d.png"}
UPLOAD = {"link_type": "upload", "name": "sh010_v001.mov", "url": "https://s3/x?sig",
          "type": "Attachment", "id": 2718}
UPLOAD_ZIP = {"link_type": "upload", "name": "sh010_v001.zip", "url": "https://s3/z?sig"}
WEB = {"link_type": "web", "name": "plate.mov", "url": "file:///Users/someone/plate.mov"}


def files(*paths):
    rows, _ = media._published_files(Site(Answer([row(6900 + i, p) for i, p in enumerate(paths)])), 1)
    return rows


# --- which rows survive ---------------------------------------------------------------------------

def test_a_local_row_keeps_its_path():
    got = files(LOCAL)[0]
    assert got["link"] == "local"
    assert got["path"] == "/vol/sh010_v001.%04d.png"
    assert got["name"] == "sh010_v001.%04d.png"
    assert got["url"] == ""


def test_an_upload_row_keeps_its_url():
    got = files(UPLOAD)[0]
    assert got["link"] == "upload"
    assert got["url"] == "https://s3/x?sig"
    assert got["name"] == "sh010_v001.mov"
    assert got["path"] == ""


def test_a_web_row_is_skipped():
    assert files(WEB) == []
    assert [p["link"] for p in files(LOCAL, WEB, UPLOAD)] == ["local", "upload"]


def test_a_local_row_with_no_path_for_this_platform_keeps_its_row():
    got = files({"link_type": "local", "name": "x.png", media.LOCAL_PATH: None})[0]
    assert got["path"] == ""


def test_the_status_code_reaches_the_caller():
    rows, why = media._published_files(Site(Answer(ok=False, status=503, text="upstream")), 1)
    assert rows == []
    assert "503" in why and "upstream" in why

    rows, why = media._published_files(Site(RuntimeError("no route to host")), 1)
    assert rows == [] and "no route to host" in why

    rows, why = media._published_files(Site(Answer(json_body=False)), 1)
    assert rows == [] and "not JSON" in why

    rows, why = media._published_files(Site(Answer([row(1, LOCAL)])), 1)
    assert why == ""


# --- what the picker calls them --------------------------------------------------------------------

def version(*paths):
    return {"id": 1, "code": "sh010_v001", "published_files": files(*paths)}


def test_sources_label_each_row_by_kind():
    v = version(UPLOAD, UPLOAD_ZIP)
    labels = dict(media.sources(v)).values()
    assert "Rendered Image — sh010_v001.mov, uploaded file" in labels
    assert "Rendered Image — sh010_v001.zip, zip on the site" in labels


def test_the_stored_key_still_names_type_file_and_id():
    pf = files(LOCAL)[0]
    assert media.pf_key(pf) == "Rendered Image · sh010_v001.%04d.png #6900"
    assert media.pf_of({"published_files": [pf]}, media.pf_key(pf)) is pf


def test_a_zip_is_never_picked_automatically():
    v = version(UPLOAD_ZIP)
    key = media.pf_key(v["published_files"][0])
    assert media.kind_of(v, key) == "zip"
    assert media.best(v, "image") == ""
    assert media.best(v, "video") == ""


def test_an_uploaded_movie_is_the_video():
    v = version(UPLOAD)
    key = media.pf_key(v["published_files"][0])
    assert media.kind_of(v, key) == "movie"
    assert media.best(v, "video") == key


def test_a_zip_says_so_rather_than_unpacking():
    v = version(UPLOAD_ZIP)
    with pytest.raises(Exception) as e:
        media.load(v, media.pf_key(v["published_files"][0]))
    assert str(e.value) == "This file is a zip and cannot be read yet. Pick another source."


def test_an_upload_is_read_like_an_uploaded_still(monkeypatch):
    v = version(UPLOAD)
    monkeypatch.setattr(media, "_download", lambda url: b"bytes for " + url.encode())
    data, name = media.load(v, media.pf_key(v["published_files"][0]))
    assert data == b"bytes for https://s3/x?sig"
    assert name == "sh010_v001.mov"


# --- newest by version number ----------------------------------------------------------------------

ROWS = [("sh010_comp_v003", "apr", 31), ("sh010_comp_v011", "apr", 12),
        ("sh010_comp_v007", "apr", 44)]


def found(monkeypatch, rows=ROWS):
    monkeypatch.setattr(resolve.site, "find_versions", lambda *a, **kw: list(rows))


def test_a_site_with_a_regex_ranks_by_it(monkeypatch):
    found(monkeypatch)
    vid, code, why = resolve.pick(1, regex=r"^(?P<name>.+)_v(?P<version>\d+)$")
    assert (vid, code) == (12, "sh010_comp_v011")
    assert why == "highest version of 3 matching the project's name convention"


def test_a_plain_site_ranks_by_the_template(monkeypatch):
    found(monkeypatch)
    vid, code, why = resolve.pick(1, template="{root_name}_v{version:03d}")
    assert (vid, code) == (12, "sh010_comp_v011")
    assert why == "highest version of 3 matching the version name template"


def test_the_default_template_is_used_when_the_profile_names_none(monkeypatch):
    found(monkeypatch)
    vid, _, why = resolve.pick(1)
    assert vid == 12 and "version name template" in why


def test_a_template_matching_nothing_falls_back_to_newest_by_id(monkeypatch):
    found(monkeypatch, [("one", "apr", 31), ("two", "apr", 12)])
    vid, code, why = resolve.pick(1)
    assert (vid, code) == (31, "one")
    assert why == "newest by id of 2"


def test_the_derived_regex_names_a_version_group():
    rx = naming.template_regex(naming.DEFAULT_TEMPLATE, {})
    assert naming.parse("sh010_v011", rx)["version"] == 11


def test_the_plain_call_still_returns_a_list():
    """`site.cached_published_files` and the publish panel read this one."""
    assert media.published_files(Site(Answer([row(6900, LOCAL)])), 1)[0]["id"] == 6900
    assert media.published_files(Site(Answer(ok=False, status=503)), 1) == []
