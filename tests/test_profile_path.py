"""Which profile the nodes read, and what `/sg/paths` tells a tool running outside ComfyUI."""
import json

import pytest

from comfyui_sg import credentials, routes, site


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    """A protected user directory and a pack directory, as a Registry install has them."""
    store, pack = tmp_path / "store", tmp_path / "pack"
    store.mkdir()
    pack.mkdir()
    monkeypatch.setattr(credentials, "store_dir", lambda: store)
    monkeypatch.setattr(site, "ROOT", pack)
    return store, pack


def write(d, project="1180"):
    (d / site.PROFILE_NAME).write_text(json.dumps({"projects": {project: {}}}))


def test_the_protected_directory_wins_when_both_hold_one(dirs):
    store, pack = dirs
    write(store)
    write(pack, "9")
    assert site.profile_path() == store / site.PROFILE_NAME
    assert list(site.profile()["projects"]) == ["1180"]


def test_the_pack_directory_is_read_when_it_is_the_only_one(dirs):
    store, pack = dirs
    write(pack)
    assert site.profile_path() == pack / site.PROFILE_NAME


def test_a_first_write_goes_to_the_protected_directory(dirs):
    store, pack = dirs
    assert site.profile_path() == store / site.PROFILE_NAME
    site.save_profile({"projects": {}})
    assert (store / site.PROFILE_NAME).is_file()
    assert not (pack / site.PROFILE_NAME).exists()


def test_the_route_answers_the_path_the_profile_is_read_from(dirs):
    store, pack = dirs
    write(pack)
    assert routes._paths() == {"profile": str(pack / site.PROFILE_NAME), "store": str(store)}


def test_the_route_answers_where_the_next_write_lands(dirs):
    """The inspector passes this to --out, so it must name the file Settings would write."""
    store, _ = dirs
    site.save_profile({"projects": {}})
    assert routes._paths()["profile"] == str(store / site.PROFILE_NAME)


def test_the_route_reaches_the_site_for_nothing(dirs, monkeypatch):
    def refuse():
        raise AssertionError("the route asked for a client")

    monkeypatch.setattr(credentials, "client", refuse)
    assert routes._paths()["profile"]
