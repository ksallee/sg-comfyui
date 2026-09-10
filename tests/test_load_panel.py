"""What the Load panel reads back off a Version: the provenance, and the sentences about its media.

Nothing here touches a site: `describe` is called with a stub client.
"""
from sg_groundtruth.client import FPTError

from comfyui_sg import media, routes

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


# --- what is wrong with the media, and what to do about it -----------------------------------------

def test_a_version_nothing_was_published_to_says_to_publish_to_it():
    v = {"id": 31886, "code": "sh010_uidemo_v003", "published_files": [],
         "published_files_error": ""}
    assert media.no_media(v) == ("Version 31886 (sh010_uidemo_v003) has no media. Publish media to "
                                 "it, or pick another Version.")


def test_files_on_a_root_this_machine_lacks_still_names_the_storage():
    v = {"id": 31886, "code": "sh010_uidemo_v003", "published_files_error": "",
         "published_files": [{"id": 7788, "link": "local", "path": "", "url": "", "name": "",
                              "type": "Rendered Image", "colour": ""}]}
    assert media.no_media(v) == ("Version 31886 (sh010_uidemo_v003) has no media this node can "
                                 "read. Check that the storage holding its files is mounted on "
                                 "this machine.")


def test_a_read_the_site_refused_is_not_blamed_on_the_storage():
    v = {"id": 31886, "code": "sh010_uidemo_v003", "published_files": [],
         "published_files_error": "The published files could not be read. Try again."}
    assert media.no_media(v).endswith("The published files could not be read. Try again.")


def test_one_file_is_one_frame(tmp_path):
    (tmp_path / "plate.1001.png").write_bytes(b"")
    v = {"id": 1, "published_files": [], "sg_path_to_frames": str(tmp_path / "plate.%04d.png")}
    assert media.sources(v) == [("frames", "path to frames — 1 frame")]


# --- how the fallback sources are labelled ---------------------------------------------------------

def test_the_thumbnail_row_says_it_is_a_preview(monkeypatch):
    v = {"id": 1, "published_files": [], "image": "https://s3/t.jpg?sig"}
    monkeypatch.setattr(media, "_download", lambda url: b"jpeg")
    monkeypatch.setattr(media, "_header", lambda blob: {"width": 480, "height": 270})
    assert media.sources(v) == [("thumbnail", "thumbnail — a preview the site made")]
    assert media.describe_format(v, "thumbnail") == (
        "thumbnail, 480x270, a preview the site made. Publish media to read the original.")


def test_a_thumbnail_that_will_not_open_still_says_what_it_is(monkeypatch):
    def refuse(url):
        raise OSError("no route to host")

    v = {"id": 1, "published_files": [], "image": "https://s3/t.jpg?sig"}
    monkeypatch.setattr(media, "_download", refuse)
    assert media.describe_format(v, "thumbnail") == (
        "thumbnail, a preview the site made. Publish media to read the original.")


def test_an_upload_is_described_by_what_its_row_knows():
    v = {"id": 1, "published_files": [],
         "sg_uploaded_movie": {"url": "https://s3/x?sig", "name": "sh010_v001.mov",
                               "content_type": "video/quicktime"}}
    assert media.describe_format(v, "uploaded") == (
        "video/quicktime on the site. Size and depth are read at run time.")


def test_an_upload_with_no_content_type_falls_back_to_its_extension():
    v = {"id": 1, "published_files": [],
         "sg_uploaded_movie": {"url": "https://s3/x?sig", "name": "sh010_v001.mov"}}
    assert media.describe_format(v, "uploaded").startswith("MOV on the site.")


def test_an_uploaded_published_file_is_described_the_same_way():
    pf = {"id": 6900, "link": "upload", "path": "", "url": "https://s3/x?sig",
          "name": "sh010_v001.mov", "content_type": "video/quicktime",
          "type": "Movie", "colour": "ACEScg"}
    v = {"id": 1, "published_files": [pf]}
    assert media.describe_format(v, media.pf_key(pf)) == (
        "video/quicktime on the site. Size and depth are read at run time. "
        "Colour space declared ACEScg.")


# --- the sentence for a Version that is not there ---------------------------------------------------

def test_a_pinned_version_that_does_not_exist_says_so_in_words():
    # The site's own 404 body, whose detail reads `Version: 1 not found`.
    said = routes._sentence(FPTError(
        "Could not read Version 1 from Flow Production Tracking. Check that it still exists, then "
        "run again. The site answered 404. "
        '{"errors":[{"status":404,"code":104,"title":"Not Found","detail":"Version: 1 not found"}]}'))
    assert said == ("Version 1 does not exist on this site. Check the id, then run again. "
                    "Version: 1 not found")


def test_another_entity_missing_reads_the_same_way():
    said = routes._sentence(FPTError('{"errors":[{"detail":"Shot: 42 not found"}]}'))
    assert said.startswith("Shot 42 does not exist on this site. Check the id, then run again.")


def test_a_detail_that_is_not_a_missing_entity_is_left_alone():
    assert routes._sentence(FPTError('{"errors":[{"detail":"Permission denied."}]}')) \
        == "Permission denied."
