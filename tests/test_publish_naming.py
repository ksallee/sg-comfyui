"""The root name and the version number, rendered once and read the same by name and path."""
import pytest

from comfyui_sg import naming, sequence, site, version_name                         # noqa: E402

PROFILE = {"root_name": "{entity}_{sg_task.Task.step.Step.short_name}",
           "code_template": "{root_name}_v{version:03d}",
           "published_files": {"storage": "primary"}}
STORAGES = [{"id": 1, "code": "primary", "mac_path": "/Volumes/FPT",
             "windows_path": "X:\\shows", "linux_path": "/mnt/fpt"}]


@pytest.fixture
def offline(monkeypatch):
    """The site, answering for one Shot with one Task, so nothing here needs a connection."""
    values = {"entity": "sh010", "sg_task.Task.step.Step.short_name": "RTO"}
    monkeypatch.setattr(site, "for_project", lambda pid=None: dict(PROFILE))
    monkeypatch.setattr(site, "resolve_paths",
                        lambda paths, *a, **k: {p: values.get(p, "") for p in paths})
    monkeypatch.setattr(site, "find_versions",
                        lambda *a, **k: [("sh010_RTO_v002", "rev", 2),
                                         ("sh010_RTO_v001", "apr", 1)])
    return values


def test_the_next_name_follows_the_versions_already_there(offline):
    assert version_name.next_name("", 1180, "Shot", 5, 7) == ("sh010_RTO_v003", 3)


def test_a_literal_template_is_used_as_it_stands(offline):
    assert version_name.next_name("plate_hero", 1180, "Shot", 5, 7) == ("plate_hero", 1)


def test_an_empty_token_drops_out_with_its_separator(monkeypatch, offline):
    monkeypatch.setattr(site, "resolve_paths",
                        lambda paths, *a, **k: {p: ("sh010" if p == "entity" else "")
                                                for p in paths})
    # And it is a different stream, so it numbers from one: sh010_RTO_v002 is not an sh010_v.
    assert version_name.next_name("", 1180, "Shot", 5, 0)[0] == "sh010_v001"


def test_the_root_renders_its_own_tokens(offline):
    vals = {"entity": "sh010"}
    assert version_name.root_of("{entity}_matte", vals) == "sh010_matte"
    assert version_name.root_of("{entity}_v{version:03d}", vals, 3) == "sh010_v003"


def test_the_name_and_the_path_agree_on_the_root(offline):
    code, version_no = version_name.next_name("", 1180, "Shot", 5, 7)
    pl = sequence.plan(PROFILE, STORAGES, code, version_no, 1180, "Shot", 5, 7)
    assert pl.name == "sh010_RTO"
    assert code == f"{pl.name}_v003"
    # Against the root the plan resolved, which is this machine's own: the storage row defines one
    # per platform and the tests run on all three. A path is always written forward-slashed, a
    # Windows root is not, so the root is spelled the way the path spells it.
    root = pl.root.replace("\\", "/")
    assert sequence.destination(pl, pl.seq_template, ".exr", version_no) == (
        f"{root}/sh010/sh010_RTO/sh010_RTO_v003/sh010_RTO_v003.%04d.exr")


def test_a_versioned_root_template_renders_the_same_everywhere(offline):
    """The failure this closes: next_name rendered the root without the number and the path with
    it, so the Version's code and the folder its frames landed in named two different things."""
    root_t = "{entity}_matte_v{version:03d}"
    code, version_no = version_name.next_name("{root_name}", 1180, "Shot", 5, 7, root_t)
    pl = sequence.plan(dict(PROFILE, root_name=root_t), STORAGES, code, version_no, 1180, "Shot",
                       5, 7)
    assert code == f"sh010_matte_v{version_no:03d}"
    assert pl.name == code
    assert pl.values["root_name"] == code


def test_a_template_asking_for_a_link_it_has_not_got_names_the_picker(offline):
    assert version_name.missing_fields("", "", 1180, 0, 0) == ["link"]
    assert version_name.missing_fields("", "", 1180, 5, 0) == []
    assert version_name.missing_fields("{task}_v{version:03d}", "", 1180, 5, 0) == ["task"]


def test_the_frame_token_is_the_frame_and_not_the_version():
    """`naming.normalise_template` reads any printf pad as the version, which is right for a code
    template and would freeze a sequence to one frame in a path."""
    assert naming.render("v%04d", {}, 3) == "v0003"
    out = sequence.pattern("/r", "{version_name}.%04d", {"version_name": "a_v003"}, 3, ".exr")
    assert out == "/r/a_v003.%04d.exr"


def test_plan_names_every_token_that_came_back_blank(monkeypatch, offline):
    monkeypatch.setattr(site, "resolve_paths", lambda paths, *a, **k: {p: "" for p in paths})
    pl = sequence.plan(PROFILE, STORAGES, "x_v001", 1, 1180, "Shot", 5, 7)
    # root_name, version_name and ext are filled by the plan itself and are never "unresolved".
    assert pl.blank == ["entity", "sg_task.Task.step.Step.short_name"]
