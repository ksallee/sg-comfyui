"""What the Load panel reads back off a Version: the provenance, and the sentences about its media.

Nothing here touches a site: `describe` is driven with a stub client.
"""
from comfyui_sg import media

# What publish writes when the site has none of the nine fields (publish_version._description):
# the note, a blank line, then one line per fact.
DESCRIPTION = (
    "Scene concept from the Flow Production Tracking example.\n"
    "\n"
    "made by: ComfyUI (sg-comfyui qa_node.py)\n"
    "model: flux1-dev-fp8.safetensors\n"
    "prompt: concept art, derelict orbital station interior\n"
    "seed: 1001\n"
    "sampler: euler/simple\n"
    "steps: 20\n"
    "cfg: 1.0"
)


class Answer:
    def __init__(self, attributes, relationships=None):
        self.ok, self.status_code, self.text = True, 200, ""
        self._body = {"data": {"id": 32008, "attributes": attributes,
                               "relationships": relationships or {}}}

    def json(self):
        return self._body


class Site:
    """Just enough of the client for `describe`."""

    def __init__(self, answer):
        self.answer = answer

    def get(self, *a, **kw):
        return self.answer


def describe(attributes, relationships=None):
    return media.describe(Site(Answer(attributes, relationships)), 32008)


def facts(described):
    return {f["label"]: f["value"] for f in described["facts"]}


# --- provenance written to the description ---------------------------------------------------------

def test_the_description_is_read_back_as_facts():
    got = facts(describe({"code": "mov_test_concept_v001", "description": DESCRIPTION}))
    assert got["note"] == "Scene concept from the Flow Production Tracking example."
    assert got["made by"] == "ComfyUI (sg-comfyui qa_node.py)"
    assert got["model"] == "flux1-dev-fp8.safetensors"
    assert got["seed"] == "1001"
    assert got["cfg"] == "1.0"


def test_a_description_that_carries_the_facts_reads_as_generated():
    d = describe({"code": "mov_test_concept_v001", "description": DESCRIPTION})
    assert d["provenance"] == "generated"


def test_the_typed_fields_still_read_as_generated():
    d = describe({"code": "x", "description": "A note.", "sg_ai_seed": "1001"})
    assert d["provenance"] == "generated"
    assert facts(d) == {"note": "A note.", "seed": "1001"}


def test_a_description_naming_only_its_sources_reads_as_derived():
    d = describe({"code": "x", "description": "A note.\n\ngenerated from: Version 31995"})
    assert d["provenance"] == "derived"
    assert facts(d)["generated from"] == "Version 31995"


def test_a_note_with_no_facts_under_it_is_still_a_note():
    d = describe({"code": "x", "description": "Plate scanned at 4K: reel 3."})
    assert d["provenance"] == "unrecorded"
    assert facts(d) == {"note": "Plate scanned at 4K: reel 3."}


def test_a_typed_field_wins_over_the_same_fact_in_the_description():
    d = describe({"code": "x", "description": DESCRIPTION, "sg_ai_seed": "42"})
    assert facts(d)["seed"] == "42"


def test_facts_alone_leave_no_note():
    d = describe({"code": "x", "description": "seed: 1001"})
    assert facts(d) == {"seed": "1001"}
    assert d["provenance"] == "generated"
