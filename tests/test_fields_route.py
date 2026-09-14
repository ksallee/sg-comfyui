"""What Settings, then SG, SG Site Setup reads and writes: the survey, the create, the refusal."""
import pytest

from comfyui_sg import credentials, fields, routes

SCHEMA = "/schema/Version/fields"


def having(fake_sg, *names):
    return fake_sg.answer("get", SCHEMA, {"data": {n: {"data_type": {"value": "text"}} for n in names}})


def test_the_survey_names_every_field_both_ways(fake_sg):
    having(fake_sg, "sg_ai_seed", "sg_something_else")
    got = fields.survey(fake_sg)
    assert got["total"] == 9
    assert got["present"] == [{"display": "AI Seed", "name": "sg_ai_seed"}]
    assert len(got["missing"]) == 8
    assert {"display": "AI CFG", "name": "sg_ai_cfg"} in got["missing"]


def test_the_survey_reads_the_schema_once(fake_sg):
    """probe 002: the expensive call, so the readout never loops over the nine fields."""
    having(fake_sg, *fields.names().values())
    fields.survey(fake_sg)
    assert fake_sg.calls == [("get", SCHEMA)]


def test_an_unreadable_schema_says_what_the_site_answered(fake_sg):
    fake_sg.answer("get", SCHEMA, {"errors": [{"title": "Permission denied."}]}, 403, False)
    with pytest.raises(fields.Refused) as e:
        fields.survey(fake_sg)
    assert e.value.status == 403


def test_the_outcome_is_one_row_per_field():
    rows = fields.outcome([("AI Seed", "sg_ai_seed", "text")], [("AI CFG", "1234")],
                          [("AI Steps", "sg_ai_steps", "number", "The site said no.")])
    assert rows == [
        {"display": "AI Seed", "name": "sg_ai_seed", "state": "ok"},
        {"display": "AI CFG", "name": "sg_ai_cfg", "state": "created"},
        {"display": "AI Steps", "name": "sg_ai_steps", "state": "failed", "why": "The site said no."},
    ]


def test_creating_on_a_site_that_has_them_all_creates_nothing(monkeypatch, fake_sg):
    having(fake_sg, *fields.names().values())
    monkeypatch.setattr(credentials, "client", lambda: fake_sg)
    got = routes._fields_create()
    assert (got["present"], got["created"], got["failed"], got["total"]) == (9, 0, 0, 9)
    assert [r["state"] for r in got["rows"]] == ["ok"] * 9
    assert "advice" not in got and not fake_sg.bodies


def test_a_refused_field_carries_the_site_sentence_and_who_to_ask(monkeypatch, fake_sg):
    having(fake_sg, "sg_ai_seed")
    fake_sg.answer("post", SCHEMA, {"errors": [{"title": "Permission denied."}]}, 403, False)
    monkeypatch.setattr(credentials, "client", lambda: fake_sg)
    got = routes._fields_create()
    assert (got["present"], got["created"], got["failed"]) == (1, 0, 8)
    assert "Permission denied." in got["rows"][-1]["why"]
    assert got["advice"] == routes.FIELDS_REFUSED


def test_a_refused_schema_read_says_who_can_do_it_instead():
    said = routes._fields_error(fields.Refused("The site answered 403.", 403))
    assert said.endswith(routes.FIELDS_REFUSED)


def test_a_failure_that_is_not_a_refusal_offers_no_admin():
    assert routes.FIELDS_REFUSED not in routes._fields_error(RuntimeError(credentials.SETUP))
