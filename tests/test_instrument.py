"""Reading someone else's graph: what a stream is called, and what the tool writes into the file."""
import importlib.util
import sys

import graphs
import pytest
from conftest import ROOT

PACKAGE = ROOT / "src" / "comfyui_sg"
# Loaded as a file, the way it is run: `-m` would import the package __init__ and therefore torch.
sys.path.insert(0, str(PACKAGE))
_spec = importlib.util.spec_from_file_location("instrument", PACKAGE / "instrument.py")
instrument = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(instrument)


def test_the_positional_array_is_built_by_name():
    names = instrument.LOAD_WIDGETS
    values = instrument.widget_values(names, instrument.LOAD_DEFAULTS, name_contains="depth")
    assert len(values) == len(names)
    assert values[names.index("name_contains")] == "depth"
    assert values[names.index("frame")] == 0


def test_a_widget_this_node_does_not_have_is_refused():
    with pytest.raises(ValueError) as e:
        instrument.widget_values(instrument.LOAD_WIDGETS, {}, frame_rate=24)
    assert "frame_rate" in str(e.value)


def test_a_tap_added_to_someone_elses_graph_copies_no_frames():
    assert instrument.PUBLISH_DEFAULTS["register_files"] is False


def test_a_stream_is_named_from_what_the_graph_already_says():
    assert instrument.descriptor({"title": "Preview Image (normal_opengl)"}, 0) == "normal_opengl"
    assert instrument.descriptor({"type": "DepthAnythingV2"}, 0) == "depthanythingv2"


def test_a_bare_number_is_not_a_name():
    """ImageFromBatch's batch index reads as "0" for every stream in the graph."""
    assert instrument.descriptor({"type": "PreviewImage", "widgets_values": ["0"]}, 0) == "out0"


def test_two_streams_never_share_a_name():
    wf = graphs.editor_two_previews()
    for node in wf["nodes"][:2]:
        node["title"] = "Pass"
    names = list(instrument.descriptors(wf).values())
    assert len(set(names)) == len(names) == 2
    assert names == ["pass_depthanything", "pass_normalmap"]


def test_each_pass_keeps_the_name_its_author_gave_it():
    assert set(instrument.descriptors(graphs.editor_two_previews()).values()) == {"depth", "normal"}


def test_a_subgraph_boundary_is_not_a_node():
    """The stream leaves node 2 inside instance 5, and is addressed `5/2`."""
    found = instrument.outputs(graphs.editor_subgraph())
    assert [(path, slot) for path, slot, _, _ in found] == [("5/2", 0)]
    assert instrument.descriptors(graphs.editor_subgraph()) == {("5/2", 0): "depth"}


def test_a_loader_is_reported_with_what_it_feeds():
    assert instrument.loaders(graphs.editor_subgraph()) == [("6", "LoadImage", [("5/2", 0)])]


def test_an_image_nothing_consumes_is_a_stream_too():
    wf = graphs.editor_two_previews()
    wf["nodes"].append({"id": 9, "type": "ImageBlur", "title": "Blur",
                        "outputs": [{"type": "IMAGE", "links": []}]})
    found = {(path, slot): consumer for path, slot, _, consumer in instrument.outputs(wf)}
    assert found[("9", 0)] is None
    assert found[("1", 0)] == "PreviewImage"
