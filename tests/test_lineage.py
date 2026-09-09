"""What each Load node resolved this run, read back by the publish node in its own branch."""
from comfyui_sg import lineage


def loads(*node_ids, **inputs):
    """A PROMPT whose every named node is an SG Load with the same inputs."""
    return {str(n): {"class_type": lineage.CLASS_TYPE,
                     "inputs": dict({"project": "Sandbox", "link": "Shot sh010"}, **inputs)}
            for n in node_ids}


def test_only_this_branchs_loads_are_credited():
    p = loads(3, 9)
    lineage.record("3", 1042, prompt=p)
    lineage.record("9", 1099, prompt=p)
    assert lineage.for_nodes({"3", "12"}, p) == [1042]


def test_a_version_two_nodes_read_is_credited_once():
    p = loads(3, 4)
    lineage.record("3", 1042, prompt=p)
    lineage.record("4", 1042, prompt=p)
    assert lineage.for_nodes({"3", "4"}, p) == [1042]


def test_graph_order_not_the_order_the_nodes_ran():
    p = loads(3, 12)
    lineage.record("12", 1012, prompt=p)
    lineage.record("3", 1003, prompt=p)
    assert lineage.for_nodes({"12", "3"}, p) == [1003, 1012]


def test_a_read_that_opened_no_file_records_no_file():
    p = loads(3, 4)
    lineage.record("3", 1042, prompt=p)          # a path field or an upload: no file the site knows
    lineage.record("4", 1043, 7788, prompt=p)
    assert lineage.files_for_nodes({"3", "4"}, p) == {1043: [7788]}


def test_a_node_that_resolved_nothing_is_not_an_ancestor():
    p = loads(3)
    lineage.record("3", 0, prompt=p)
    assert lineage.for_nodes({"3"}, p) == []


# --- one server, many graphs ----------------------------------------------------------------------

def test_another_graphs_node_1_is_not_this_graphs_node_1():
    first = loads(1)
    lineage.record("1", 31995, prompt=first)
    later = {"1": {"class_type": "LoadImage", "inputs": {"image": "plate.png"}}}
    assert lineage.for_nodes({"1"}, later) == []
    assert lineage.files_for_nodes({"1"}, later) == {}


def test_a_load_node_asked_for_something_else_is_not_credited():
    p = loads(1, pin_version_id=31995)
    lineage.record("1", 31995, 7788, prompt=p)
    other = loads(1, pin_version_id=31996)
    assert lineage.for_nodes({"1"}, other) == []
    assert lineage.files_for_nodes({"1"}, other) == {}


def test_the_same_node_running_again_is_still_credited():
    p = loads(1, 2)
    lineage.record("1", 31995, prompt=p)
    lineage.record("2", 31996, prompt=p)
    assert lineage.for_nodes({"1", "2"}, p) == [31995, 31996]


def test_a_run_forgets_what_the_graph_before_it_left():
    lineage.record("1", 31995, prompt=loads(1))
    lineage.record("5", 32001, prompt=loads(5))
    assert list(lineage._resolved) == ["5"]
