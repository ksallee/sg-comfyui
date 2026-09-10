"""Provenance as fields: the names, the concepts, and where the operator's mapping puts them."""
import graphs
from conftest import rows

from comfyui_sg import fields, provenance


def test_the_programmatic_name_is_derived_the_way_the_site_derives_it():
    assert fields.programmatic_name("AI Generated From") == "sg_ai_generated_from"
    assert fields.programmatic_name("AI CFG") == "sg_ai_cfg"


def test_every_declared_field_has_one_programmatic_name():
    names = fields.names()
    assert len(names) == len(fields.FIELDS)
    assert all(n.startswith("sg_") for n in names.values())
    assert set(fields.DEFAULT_MAP.values()) <= set(names.values())


def test_a_concept_with_no_value_is_not_recorded():
    got = fields.concepts(provenance.extract(graphs.prompt_widget_no_sampler()))
    assert "seed" not in got and "steps" not in got
    assert got["prompt"] == "the camera pushes in"


def test_the_numbers_come_from_the_last_sampler():
    got = fields.concepts(provenance.extract(graphs.two_branches()))
    assert got["steps"] == 30
    assert got["cfg"] == 9.0


def test_the_text_joins_every_sampler_so_nothing_is_lost():
    got = fields.concepts(provenance.extract(graphs.two_branches()))
    assert got["seed"] == "111 | 222"
    assert got["sampler"] == "euler | heun"


def test_generated_from_is_a_list_of_entity_hashes():
    got = fields.concepts(provenance.extract(graphs.sdxl_zero_out()), [1042, "1043"])
    assert got["generated_from"] == [{"type": "Version", "id": 1042},
                                     {"type": "Version", "id": 1043}]


def test_description_mode_writes_lines_rather_than_fields():
    prov = provenance.extract(graphs.sdxl_zero_out())
    typed, lines = fields.route(prov, (), None, fields.DESCRIPTION)
    assert typed == {}
    assert any(l.startswith("prompt: a red car") for l in lines)


def test_a_concept_mapped_to_nothing_is_recorded_nowhere():
    prov = provenance.extract(graphs.sdxl_zero_out())
    typed, lines = fields.route(prov, (), {"seed": None, "prompt": fields.DESCRIPTION})
    assert "sg_ai_seed" not in typed
    assert typed["sg_ai_model"] == "sd_xl_base_1.0.safetensors"
    assert lines == ["prompt: a red car | studio light"]


def test_a_field_already_on_the_site_is_not_created_again(fake_sg):
    """probe 019: a display name that exists is silently created a second time as <name>_1."""
    have = {n: {"data_type": {"value": "text"}} for n in fields.names().values()}
    fake_sg.answer("get", "/schema/Version/fields", {"data": have})
    present, created, failed = fields.ensure(fake_sg)
    assert len(present) == len(fields.FIELDS)
    assert created == [] and failed == []
    assert not fake_sg.bodies


def test_the_fields_this_site_has_are_the_ones_it_answers_with(fake_sg):
    fake_sg.answer("get", "/schema/Version/fields",
                   {"data": {"sg_ai_seed": {}, "sg_something_else": {}}})
    assert fields.available(fake_sg) == {"sg_ai_seed"}


def test_unreadable_schema_writes_nothing_optional(fake_sg):
    fake_sg.answer("get", "/schema/Version/fields", rows(), status=403, ok=False)
    assert fields.schema_names(fake_sg) == set()
