"""What each Load node resolved this run, read back by the publish node in its own branch."""
from comfyui_sg import lineage


def test_only_this_branchs_loads_are_credited():
    lineage.record("3", 1042)
    lineage.record("9", 1099)
    assert lineage.for_nodes({"3", "12"}) == [1042]


def test_a_version_two_nodes_read_is_credited_once():
    lineage.record("3", 1042)
    lineage.record("4", 1042)
    assert lineage.for_nodes({"3", "4"}) == [1042]


def test_graph_order_not_the_order_the_nodes_ran():
    lineage.record("12", 1012)
    lineage.record("3", 1003)
    assert lineage.for_nodes({"12", "3"}) == [1003, 1012]


def test_a_read_that_opened_no_file_records_no_file():
    lineage.record("3", 1042)                 # a path field or an upload: no file the site knows
    lineage.record("4", 1043, 7788)
    assert lineage.files_for_nodes({"3", "4"}) == {1043: [7788]}


def test_a_node_that_resolved_nothing_is_not_an_ancestor():
    lineage.record("3", 0)
    assert lineage.for_nodes({"3"}) == []
