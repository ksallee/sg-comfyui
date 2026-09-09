"""One declared order, shared by five files. A widget out of step silently loads the value next door.

Nothing here spells the order out: it is read from `widgets.py`, from the classes, from the JS and
from every shipped graph, and the test is that they agree.
"""
import inspect
import json
import re

import pytest
from conftest import ROOT, stub_site

from comfyui_sg import widgets
from comfyui_sg.nodes.load_version import SGLoadVersion
from comfyui_sg.nodes.publish_version import SGPublishVersion
from test_instrument import instrument

# The only input types ComfyUI draws as a widget. A combo declares its choices in place of a type
# name, so a list IS a widget.
WIDGET_TYPES = {"INT", "FLOAT", "STRING", "BOOLEAN", "COMBO"}
GRAPHS = sorted(ROOT.glob("example_workflows/*.json")) + sorted(ROOT.glob("tools/workflows/*.json"))
DECLARED = {"SGPublishVersion": widgets.PUBLISH_FIELDS, "SGLoadVersion": widgets.LOAD_FIELDS}
KIND_TYPES = {"text": str, "multiline": str, "int": int, "bool": bool, "combo": str}


def declared_widgets(spec):
    """The widget names a class declares, in order — the order widgets_values is written in."""
    names = []
    for section in ("required", "optional"):
        for name, v in (spec.get(section) or {}).items():
            kind = v[0] if v else None
            if isinstance(kind, list) or kind in WIDGET_TYPES:
                names.append(name)
    return names


def test_the_publish_class_declares_the_table_in_order(monkeypatch):
    stub_site(monkeypatch)
    assert declared_widgets(SGPublishVersion.INPUT_TYPES()) == widgets.names(widgets.PUBLISH_FIELDS)


def test_the_load_class_declares_the_table_in_order(monkeypatch):
    stub_site(monkeypatch)
    assert declared_widgets(SGLoadVersion.INPUT_TYPES()) == widgets.names(widgets.LOAD_FIELDS)


def test_the_required_widgets_are_the_first_ones_declared():
    """ComfyUI's required/optional split is presentation; the array spans both in declared order."""
    names = widgets.names(widgets.LOAD_FIELDS)
    assert tuple(names[:len(widgets.LOAD_REQUIRED)]) == widgets.LOAD_REQUIRED


def test_instrument_reads_the_table_rather_than_repeating_it():
    """`import widgets` and `def widgets` share a name in instrument.py; the order still holds."""
    assert instrument.PUBLISH_WIDGETS == widgets.names(widgets.PUBLISH_FIELDS)
    assert instrument.LOAD_WIDGETS == widgets.names(widgets.LOAD_FIELDS)


def test_the_smoke_test_and_the_editor_count_the_same_types_as_widgets():
    smoke = (ROOT / "tools" / "smoke.py").read_text()
    js = (ROOT / "web" / "sg_entity_picker.js").read_text()
    in_smoke = set(re.findall(r'"(\w+)"',
                              re.search(r"WIDGET_TYPES = \{([^}]*)\}", smoke).group(1)))
    in_js = set(re.findall(r'"(\w+)"',
                           re.search(r"WIDGET_TYPES = new Set\(\[([^\]]*)\]", js).group(1)))
    assert in_smoke == in_js == WIDGET_TYPES


@pytest.mark.parametrize("path", GRAPHS, ids=lambda p: p.name)
def test_every_shipped_graph_holds_one_value_per_declared_widget(path):
    for node, fields in sg_nodes(json.loads(path.read_text())):
        values = node.get("widgets_values") or []
        assert len(values) == len(fields), \
            f'{node["type"]}#{node["id"]} in {path.name} has {len(values)} values for ' \
            f"{len(fields)} widgets"


@pytest.mark.parametrize("path", GRAPHS, ids=lambda p: p.name)
def test_every_saved_value_suits_the_widget_it_sits_in(path):
    for node, fields in sg_nodes(json.loads(path.read_text())):
        for value, f in zip(node.get("widgets_values") or [], fields):
            if value is None:
                continue
            assert isinstance(value, KIND_TYPES[f.kind]), \
                f'{node["type"]}#{node["id"]} in {path.name}: {f.name} holds {value!r}'


def sg_nodes(graph):
    """(node, declared fields) for every SG node in a saved graph, subgraphs included."""
    containers = [graph] + list((graph.get("definitions") or {}).get("subgraphs") or [])
    for container in containers:
        for node in container.get("nodes") or []:
            if node.get("type") in DECLARED:
                yield node, DECLARED[node["type"]]


def defaults_in_three_places():
    """(field, node method, instrument's defaults) for every field that declares a default."""
    out = []
    for fields, method, table in ((widgets.LOAD_FIELDS, SGLoadVersion.load,
                                  instrument.LOAD_DEFAULTS),
                                 (widgets.PUBLISH_FIELDS, SGPublishVersion.publish,
                                  instrument.PUBLISH_DEFAULTS)):
        for f in fields:
            if f.default is None:
                continue
            out.append(pytest.param(f, method, table, id=f.name))
    return out


def _agree(a, b):
    """Equal, or both the empty answer: a combo's "nothing picked" is spelled "" and ()."""
    return a == b or (a in ("", (), []) and b in ("", (), []))


@pytest.mark.parametrize("field,method,table", defaults_in_three_places())
def test_a_default_is_the_same_in_all_three_places(field, method, table):
    """widgets.Field, the node method's keyword, and instrument's table are one value."""
    signature = inspect.signature(method).parameters.get(field.name)
    if signature is not None and signature.default is not inspect.Parameter.empty:
        assert _agree(signature.default, field.default), f"{field.name} in {method.__qualname__}"
    if field.name in table:
        assert _agree(table[field.name], field.default), f"{field.name} in instrument.py"
