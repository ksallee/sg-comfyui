"""What each Load node actually resolved this run.

A Load node set to "latest" only learns its Version id at execution time, so the prompt graph carries
version_id 0 and the graph walk that records lineage (provenance.loaded_versions) cannot see it.
The node records what it resolved here; the publish node reads back only the entries belonging to its
own ancestors, so two branches of one graph never contaminate each other.

Keyed by node id and overwritten each run, so a stale entry from a previous execution is replaced
rather than accumulating.

Each entry is (version_id, published_file_id). The second is the file the node actually read, and it
is 0 whenever the read came off a path field or an upload, because those are not files the site
knows by id. That distinction is the point: an exact dependency is only claimable where a file was
actually opened, and everywhere else the caller falls back to asking the site.
"""
_resolved = {}


def record(node_id, version_id, published_file_id=0):
    if node_id is not None and version_id:
        _resolved[str(node_id)] = (int(version_id), int(published_file_id or 0))


def _ordered(node_ids):
    return sorted(node_ids, key=lambda n: (0, int(n)) if str(n).isdigit() else (1, str(n)))


def for_nodes(node_ids):
    """Resolved ids for these nodes, in graph order, de-duplicated."""
    out = []
    for nid in _ordered(node_ids):
        v = (_resolved.get(str(nid)) or (0, 0))[0]
        if v and v not in out:
            out.append(v)
    return out


def files_for_nodes(node_ids):
    """{version_id: [published_file_id]} for the nodes that read an actual file.

    A Version absent from this mapping is not a Version without files — it is one this run did not
    open a file from, and the caller has to ask the site which files it has. Present means exact.
    """
    out = {}
    for nid in _ordered(node_ids):
        vid, pfid = _resolved.get(str(nid)) or (0, 0)
        if vid and pfid and pfid not in out.setdefault(vid, []):
            out[vid].append(pfid)
    return out
