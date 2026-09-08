"""What each Load node resolved this run, so a publish downstream can credit it.

A Load node resolving by rule only learns its Version id at execution time, so the prompt graph
carries no id for it and `provenance.loaded_versions` has nothing to read. The node records the
answer here; the publish node reads back only the entries belonging to its own ancestors, so two
branches of one graph never contaminate each other.

Keyed by node id and overwritten each run. Each entry is (version_id, published_file_id), and the
file id is 0 where the read came off a path field or an upload — neither is a file the site knows
by id.
"""
_resolved = {}


def record(node_id, version_id, published_file_id=0):
    """Remember what this Load node resolved."""
    if node_id is not None and version_id:
        _resolved[str(node_id)] = (int(version_id), int(published_file_id or 0))


def _ordered(node_ids):
    return sorted(node_ids, key=lambda n: (0, int(n)) if str(n).isdigit() else (1, str(n)))


def for_nodes(node_ids):
    """Resolved Version ids for these nodes, in graph order, de-duplicated."""
    out = []
    for nid in _ordered(node_ids):
        v = (_resolved.get(str(nid)) or (0, 0))[0]
        if v and v not in out:
            out.append(v)
    return out


def files_for_nodes(node_ids):
    """{version_id: [published_file_id]} for the nodes that read an actual file.

    A Version absent from this mapping is one this run did not open a file from, not one without
    files; the caller then has to ask the site. Present means exact.
    """
    out = {}
    for nid in _ordered(node_ids):
        vid, pfid = _resolved.get(str(nid)) or (0, 0)
        if vid and pfid and pfid not in out.setdefault(vid, []):
            out[vid].append(pfid)
    return out
