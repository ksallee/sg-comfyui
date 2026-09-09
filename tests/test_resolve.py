"""Picking one Version from a rule: what the fields add up to, and what newest means."""
import pytest

from comfyui_sg import resolve, site

CONVENTION = r"(?P<name>.+)_v(?P<version>\d+)$"
# Newest by id is not newest by version: v002 was re-published after v010 landed.
ROWS = [("sh010_comp_v002", "apr", 900), ("sh010_comp_v010", "apr", 100)]


def rows_are(monkeypatch, rows):
    monkeypatch.setattr(site, "find_versions", lambda *a, **kw: list(rows))


def test_the_filter_is_what_the_widgets_add_up_to():
    got = resolve.filters_for(1180, "Shot", 7514, 900, "depth pass", ["apr", "rev"])
    assert ["project", "is", {"type": "Project", "id": 1180}] in got
    assert ["entity", "is", {"type": "Shot", "id": 7514}] in got
    assert ["sg_task", "is", {"type": "Task", "id": 900}] in got
    assert ["code", "contains", "depth"] in got and ["code", "contains", "pass"] in got
    assert ["sg_status_list", "in", ["apr", "rev"]] in got


def test_extra_conditions_narrow_and_never_replace():
    base = [["project", "is", {"type": "Project", "id": 1}]]
    assert resolve.combine(base, [["sg_ai_model", "contains", "flux"]]) == \
        base + [["sg_ai_model", "contains", "flux"]]


def test_a_group_appends_as_one_element():
    """probe 030 — a dict carries its own logical_operator and is one element, not many."""
    base = [["project", "is", {"type": "Project", "id": 1}]]
    group = {"logical_operator": "or", "conditions": [["code", "contains", "a"]]}
    assert resolve.combine(base, group) == base + [group]


def test_nothing_matching_names_the_link_the_operator_picked(monkeypatch):
    rows_are(monkeypatch, [])
    vid, code, why = resolve.pick(1180, "Shot", 7514, statuses=["apr"], where="sh010")
    assert (vid, code) == (0, "")
    assert "No Version on sh010" in why and "status apr" in why


def test_the_highest_version_wins_over_the_newest_id(monkeypatch):
    rows_are(monkeypatch, ROWS)
    vid, code, why = resolve.pick(1180, order=resolve.BY_VERSION, regex=CONVENTION)
    assert (vid, code) == (100, "sh010_comp_v010")
    assert "highest version" in why


def test_created_at_is_the_order_the_operator_asked_for(monkeypatch):
    rows_are(monkeypatch, ROWS)
    vid, _, why = resolve.pick(1180, order=resolve.BY_CREATED, regex=CONVENTION)
    assert vid == 900
    assert why == "newest by created_at of 2"


def test_a_site_with_no_convention_still_ranks_by_version(monkeypatch):
    rows_are(monkeypatch, ROWS)
    vid, code, _ = resolve.pick(1180, order=resolve.BY_VERSION, regex="")
    assert (vid, code) == (100, "sh010_comp_v010")
