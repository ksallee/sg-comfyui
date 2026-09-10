"""What the two classes declare, and what they refuse before the site is touched."""
import json

import pytest
from conftest import ROOT, stub_site

from comfyui_sg import site, version_name
from comfyui_sg.nodes.load_version import SGLoadVersion
from comfyui_sg.nodes.publish_version import SGPublishVersion

# Every graph that ships or is used here: a Load node's slots are read by index in all of them.
GRAPHS = (sorted(ROOT.glob("example_workflows/*.json")) + sorted(ROOT.glob("tools/workflows/*.json"))
          + sorted(ROOT.glob("tools/experiments/*.json")))


def test_provenance_comes_from_the_hidden_inputs_not_from_asking(monkeypatch):
    stub_site(monkeypatch)
    hidden = SGPublishVersion.INPUT_TYPES()["hidden"]
    assert hidden["prompt"] == "PROMPT"
    assert hidden["extra_pnginfo"] == "EXTRA_PNGINFO"
    assert hidden["unique_id"] == "UNIQUE_ID"
    assert SGLoadVersion.INPUT_TYPES()["hidden"] == {"unique_id": "UNIQUE_ID", "prompt": "PROMPT"}


def test_every_output_is_named(monkeypatch):
    assert len(SGLoadVersion.RETURN_TYPES) == len(SGLoadVersion.RETURN_NAMES)
    assert SGLoadVersion.RETURN_NAMES[0] == "image"
    assert SGPublishVersion.RETURN_TYPES == ()


def test_the_load_outputs_are_the_frozen_order():
    """An output is positional: a saved graph names the slot by index, so this order is fixed."""
    assert SGLoadVersion.RETURN_NAMES == ("image", "video", "mask", "version_id", "code",
                                          "colour_space")
    assert SGLoadVersion.RETURN_TYPES == ("IMAGE", "VIDEO", "MASK", "INT", "STRING", "STRING")


@pytest.mark.parametrize("path", GRAPHS, ids=lambda p: p.name)
def test_every_saved_load_node_holds_that_order(path):
    """A graph whose outputs are out of step wires the next slot along when it loads."""
    for node in json.loads(path.read_text()).get("nodes") or []:
        if node.get("type") == "SGLoadVersion":
            names = tuple(o.get("name") for o in node.get("outputs") or [])
            assert names == SGLoadVersion.RETURN_NAMES, f'#{node["id"]} in {path.name}'


def test_the_statuses_tooltip_names_this_projects_own_codes(monkeypatch):
    """SG has no "approved" concept; the codes differ per project (probe 009)."""
    stub_site(monkeypatch)
    spec = SGLoadVersion.INPUT_TYPES()["optional"]["statuses"]
    assert "In Progress, Approved" in spec[1]["tooltip"]


def test_the_editors_own_choice_is_accepted():
    assert SGLoadVersion.VALIDATE_INPUTS(project="Sandbox") is True
    assert SGPublishVersion.VALIDATE_INPUTS(project="Sandbox") is True


def test_a_name_that_needs_a_link_says_which_field_to_fill(monkeypatch):
    stub_site(monkeypatch)
    assert version_name.missing_fields("", "", 1180, 0, 0) == ["link"]
    assert version_name.missing_fields("", "", 1180, 7514, 0) == []
    assert version_name.missing_fields("", "{entity}_{task}", 1180, 0, 0) == ["link", "task"]


def test_a_literal_name_is_used_as_written(monkeypatch):
    stub_site(monkeypatch)
    assert version_name.next_name("hero_plate", 1180, "Shot", 7514, 0) == ("hero_plate", 1)


def test_the_next_version_follows_what_is_already_on_the_link(monkeypatch):
    stub_site(monkeypatch)
    monkeypatch.setattr(site, "resolve_paths", lambda *a, **kw: {"entity": "sh010"})
    monkeypatch.setattr(site, "find_versions", lambda *a, **kw: [("sh010_v001", "apr", 1)])
    assert version_name.next_name("", 1180, "Shot", 7514, 0, "{entity}") == ("sh010_v002", 2)


def test_a_version_in_the_root_name_is_the_one_being_published(monkeypatch):
    stub_site(monkeypatch)
    monkeypatch.setattr(site, "resolve_paths", lambda *a, **kw: {"entity": "sh010"})
    monkeypatch.setattr(site, "find_versions", lambda *a, **kw: [])
    code, number = version_name.next_name("", 1180, "Shot", 7514, 0, "{entity}_v{version:03d}")
    assert number == 1
    assert code.startswith("sh010_v001")


def test_a_python_filter_is_translated_to_the_rest_spelling():
    """probe 030: a TD reaching for a filter types shotgun_api3's spelling."""
    got = SGLoadVersion._filters('{"filter_operator": "any", '
                                 '"filters": [["sg_status_list", "in", ["apr"]]]}')
    assert got == {"logical_operator": "or", "conditions": [["sg_status_list", "in", ["apr"]]]}


def test_a_filter_that_is_not_json_is_refused_rather_than_ignored():
    with pytest.raises(ValueError) as e:
        SGLoadVersion._filters("[[not json")
    assert "not valid JSON" in str(e.value)
    assert SGLoadVersion._filters("") is None


def test_a_hand_edited_statuses_string_is_read_as_a_list():
    from comfyui_sg.nodes.load_version import _as_list

    assert _as_list("apr, rev") == ["apr", "rev"]
    assert _as_list(["apr", "rev"]) == ["apr", "rev"]
    assert _as_list("") == []


def test_nothing_wired_in_is_refused_by_name(monkeypatch):
    stub_site(monkeypatch)
    with pytest.raises(ValueError) as e:
        SGPublishVersion().publish()
    assert "Connect an image to images" in str(e.value)


def test_a_batch_of_frames_with_no_movie_refuses_to_lose_the_rest(monkeypatch):
    stub_site(monkeypatch)
    with pytest.raises(ValueError) as e:
        SGPublishVersion().publish(images=[object(), object()], link_id=7514)
    assert "Tick Create Published Files" in str(e.value)


def test_a_batch_with_no_frames_is_refused_before_the_site_is_touched(monkeypatch):
    stub_site(monkeypatch)
    monkeypatch.setattr(site, "client", lambda: pytest.fail("the site was touched"))
    with pytest.raises(ValueError):
        SGPublishVersion().publish(images=[], link_id=7514)
