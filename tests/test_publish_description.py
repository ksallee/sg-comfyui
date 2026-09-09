"""What the Version's description says when this site has no field for a fact."""
from comfyui_sg import fields as sg_fields
from comfyui_sg.nodes import publish_version as pv

PROMPT = ("a wide shot of the couple crossing the bridge at dusk, volumetric haze, "
          "35mm anamorphic, shallow depth of field")
PROV = {"generator": "ComfyUI", "comfy_usage_source": "comfyui-frontend",
        "prompts": {"positive": [PROMPT], "negative": ["blurry"]},
        "models": [{"name": "flux1-dev.safetensors"}],
        "samplers": [{"seed": 18446744073709551615, "steps": 20, "cfg": 7.0,
                      "sampler_name": "euler", "scheduler": "normal"}]}
SOURCES = [31752, 31753]


def concepts():
    return sg_fields.concepts(PROV, SOURCES)


def test_a_site_with_every_field_writes_nothing_into_the_description():
    where = sg_fields.targets({}, "fields")
    typed, lines = pv._split(concepts(), where, absent_targets=set())
    assert lines == []
    assert typed["sg_ai_prompt"] == PROMPT
    assert typed["sg_ai_generated_from"] == [{"type": "Version", "id": 31752},
                                             {"type": "Version", "id": 31753}]


def test_a_bare_site_writes_every_fact_as_a_line():
    where = sg_fields.targets({}, "fields")
    absent = {t for t in where.values() if t and t != sg_fields.DESCRIPTION}
    typed, lines = pv._split(concepts(), where, absent)
    assert typed == {}
    assert lines == [
        "made by: ComfyUI (comfyui-frontend)",
        "model: flux1-dev.safetensors",
        f"prompt: {PROMPT}",
        "negative prompt: blurry",
        "seed: 18446744073709551615",
        "sampler: euler/normal",
        "steps: 20",
        "cfg: 7.0",
        "generated from: Version 31752, Version 31753",
    ]


def test_the_prompt_is_written_in_full():
    where = sg_fields.targets({}, "fields")
    absent = {t for t in where.values() if t and t != sg_fields.DESCRIPTION}
    _, lines = pv._split(concepts(), where, absent)
    assert PROMPT in "\n".join(lines)


def test_a_field_this_site_has_is_typed_and_the_rest_are_lines():
    where = sg_fields.targets({}, "fields")
    typed, lines = pv._split(concepts(), where,
                             absent_targets={"sg_ai_seed", "sg_ai_generated_from"})
    assert set(typed) == {"sg_ai_generator", "sg_ai_model", "sg_ai_prompt",
                          "sg_ai_negative_prompt", "sg_ai_sampler", "sg_ai_steps", "sg_ai_cfg"}
    assert lines == ["seed: 18446744073709551615",
                     "generated from: Version 31752, Version 31753"]


def test_a_studios_own_field_is_written_where_the_site_has_it():
    """The documented preferred move: point the mapping at a field the studio already has."""
    where = sg_fields.targets({"seed": "sg_render_seed"}, "fields")
    typed, _ = pv._split(concepts(), where, absent_targets=set())
    assert typed["sg_render_seed"] == "18446744073709551615"


def test_a_concept_mapped_to_nothing_is_recorded_nowhere():
    where = sg_fields.targets({"prompt": None}, "fields")
    typed, lines = pv._split(concepts(), where, absent_targets=set())
    assert "sg_ai_prompt" not in typed
    assert not any(line.startswith("prompt:") for line in lines)


def test_the_description_is_the_note_then_a_blank_line_then_the_facts():
    assert pv._description("Roto matte of the two walkers.", ["seed: 42", "steps: 20"]) == (
        "Roto matte of the two walkers.\n\nseed: 42\nsteps: 20")


def test_the_description_is_the_note_alone_where_every_field_exists():
    assert pv._description("Roto matte of the two walkers.", []) == "Roto matte of the two walkers."


def test_the_description_is_the_facts_alone_where_there_is_no_note():
    assert pv._description("", ["seed: 42"]) == "seed: 42"


def test_an_empty_publish_says_nothing_rather_than_a_blank_line():
    assert pv._description("", []) == ""
