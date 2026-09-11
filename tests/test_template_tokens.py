"""The tokens the editor offers inside a template, and the templates Settings has in force."""
import pytest

from comfyui_sg import credentials, naming, routes, sequence, site

KINDS = ("root", "name", "sequence", "still", "movie")

SCHEMA = {"data": {
    "content": {"name": {"value": "Task Name"}, "data_type": {"value": "text"}},
    "step": {"name": {"value": "Pipeline Step"}, "data_type": {"value": "entity"},
             "properties": {"valid_types": {"value": ["Step"]}}},
    "task_assignees": {"name": {"value": "Assigned To"},
                       "data_type": {"value": "multi_entity"},
                       "properties": {"valid_types": {"value": ["HumanUser"]}}},
}}


def listed(kind):
    return [t["token"] for t in naming.tokens(kind)]


def test_every_kind_lists_tokens_and_a_sentence_for_each():
    for kind in KINDS:
        rows = naming.tokens(kind)
        assert rows, kind
        for row in rows:
            assert row["token"].strip()
            assert row["note"].endswith("."), row


def test_the_entity_token_descends_into_the_type_this_node_links():
    rows = {t["token"]: t["type"] for t in naming.tokens("root", "Asset")}
    assert rows["{entity}"] == "Asset"
    assert rows["{sg_task}"] == "Task"
    assert rows["{project}"] == "Project"
    assert rows["{sg_task.Task.step}"] == "Step"
    assert rows["{sg_task.Task.step.Step.short_name}"] == ""


def test_a_project_linking_several_types_offers_them_as_the_hop():
    entity = next(t for t in naming.tokens("root", ["Shot", "Asset"]) if t["token"] == "{entity}")
    assert entity["type"] == ""
    assert entity["types"] == ["Shot", "Asset"]


def test_the_picked_link_type_wins_over_the_profile(monkeypatch):
    monkeypatch.setattr(site, "projects", lambda: [("Sandbox", 1180)])
    monkeypatch.setattr(site, "default_project", lambda: 1180)
    monkeypatch.setattr(site, "for_project", lambda pid=None: {"link_type": "Shot"})
    monkeypatch.setattr(site, "link_types", lambda pid: ["Shot", "Asset"])
    entity = lambda rows: next(t for t in rows if t["token"] == "{entity}")
    assert entity(routes._token_rows("root", "Sandbox", "Asset"))["type"] == "Asset"
    assert entity(routes._token_rows("root", "Sandbox"))["type"] == "Shot"
    monkeypatch.setattr(site, "for_project", lambda pid=None: {})
    assert entity(routes._token_rows("root", "Sandbox"))["types"] == ["Shot", "Asset"]


def test_a_kind_with_no_list_offers_nothing():
    assert naming.tokens("") == []
    assert naming.tokens("published_file") == []


def test_each_shipped_template_uses_tokens_its_kind_offers():
    for kind, template in (("root", naming.DEFAULT_ROOT_TEMPLATE),
                           ("name", naming.DEFAULT_TEMPLATE),
                           ("sequence", sequence.DEFAULT_SEQUENCE_TEMPLATE),
                           ("still", sequence.DEFAULT_STILL_TEMPLATE),
                           ("movie", sequence.DEFAULT_MOVIE_TEMPLATE)):
        offered = {t.strip("{}").split(":")[0] for t in listed(kind)}
        for field in naming.template_fields(template):
            assert field in offered, f"{field} is not offered for {kind}"


def test_a_sequence_path_names_the_frame_and_a_still_or_a_movie_does_not():
    assert "%04d" in listed("sequence")
    assert "%04d" not in listed("still")
    assert "%04d" not in listed("movie")


def test_a_still_is_offered_the_tokens_a_movie_is():
    assert listed("still") == listed("movie")


def test_the_settings_example_writes_a_still_beside_the_version_folder(monkeypatch):
    """Settings renders each path kind on one Shot, its Task and version 3."""
    monkeypatch.setattr(site, "default_project", lambda: 1180)
    monkeypatch.setattr(site, "for_project", lambda pid=None: {})
    monkeypatch.setattr(site, "resolve_paths", lambda *a, **kw: {})
    assert routes._example("still", "") == "sh010/sh010_RTO/sh010_RTO_v003.png"
    assert routes._example("sequence", "") == ("sh010/sh010_RTO/sh010_RTO_v003/"
                                               "sh010_RTO_v003.%04d.png")


def test_a_profile_that_names_neither_template_is_in_force_on_the_shipped_ones():
    assert routes._in_force({}) == {"root_name": naming.DEFAULT_ROOT_TEMPLATE,
                                    "code_template": naming.DEFAULT_TEMPLATE}


def test_a_template_on_the_profile_is_the_one_in_force():
    got = routes._in_force({"root_name": "{entity}_matte"})
    assert got == {"root_name": "{entity}_matte", "code_template": naming.DEFAULT_TEMPLATE}


def test_the_fields_of_a_type_are_read_once_and_sorted_by_display_name(monkeypatch, fake_sg):
    fake_sg.answer("get", "/schema/Task/fields", SCHEMA)
    monkeypatch.setattr(credentials, "client", lambda: fake_sg)
    site.forget_all()
    got = site.schema_fields("Task")
    assert [f["name"] for f in got] == ["task_assignees", "step", "content"]
    assert got[1] == {"name": "step", "display_name": "Pipeline Step", "data_type": "entity",
                      "valid_types": ["Step"]}
    # probe 002: the expensive call, so a second read comes from the cache.
    site.schema_fields("Task")
    assert fake_sg.calls == [("get", "/schema/Task/fields")]
    site.forget_all()


def test_a_type_the_site_refuses_lists_no_fields(monkeypatch, fake_sg):
    monkeypatch.setattr(credentials, "client", lambda: fake_sg)
    site.forget_all()
    assert site.schema_fields("Nope") == []
    site.forget_all()


def test_only_an_entity_type_reaches_the_schema_path():
    assert routes._entity_type({"type": "Task"}) == "Task"
    for bad in ("", "../secrets", "Task/fields", "9lives"):
        with pytest.raises(ValueError):
            routes._entity_type({"type": bad})
