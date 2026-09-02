"""What each Fetch node actually resolved this run.

A Fetch node set to "latest" only learns its Version id at execution time, so the prompt graph carries
version_id 0 and the graph walk that records lineage (provenance.fetched_versions) cannot see it.
The node records what it resolved here; the publish node reads back only the entries belonging to its
own ancestors, so two branches of one graph never contaminate each other.

Keyed by node id and overwritten each run, so a stale entry from a previous execution is replaced
rather than accumulating.
"""
_resolved = {}


def record(node_id, version_id):
    if node_id is not None and version_id:
        _resolved[str(node_id)] = int(version_id)


def for_nodes(node_ids):
    """Resolved ids for these nodes, in graph order, de-duplicated."""
    out = []
    for nid in sorted(node_ids, key=lambda n: (0, int(n)) if str(n).isdigit() else (1, str(n))):
        v = _resolved.get(str(nid))
        if v and v not in out:
            out.append(v)
    return out
