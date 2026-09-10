"""What each Load node resolved this run, so a publish downstream can credit it.

A Load node resolving by rule only learns its Version id at execution time, so the prompt graph
carries no id for it and `provenance.loaded_versions` has nothing to read. The node records the
answer here; the publish node reads back only the entries belonging to its own ancestors, so two
branches of one graph never contaminate each other.

Keyed by node id, which one ComfyUI server hands to every graph it runs: node 1 of the graph open
now is a different node from node 1 of the graph before it, and crediting the earlier one would
write a Version's provenance to a source it never read. So an entry also carries a fingerprint of
the Load node as it ran, its class and its inputs off the PROMPT it was given, and is credited only
to a node that is still an `SGLoadVersion` with those inputs. ComfyUI hands a node no prompt id, so
the fingerprint is the guarantee. Dropping what no longer matches is hygiene.

Each entry is (version_id, published_file_id, fingerprint). The file id is 0 where the read came
off a path field or an upload, since neither is a file the site knows by id.
"""
import json

CLASS_TYPE = "SGLoadVersion"

_resolved = {}


def fingerprint(prompt, node_id):
    """The Load node at this id as the PROMPT states it, or "" when that node is not one.

    "" never matches a recorded entry, so a graph whose node 1 is a LoadImage credits nothing.
    """
    node = (prompt or {}).get(str(node_id)) or {}
    if node.get("class_type") != CLASS_TYPE:
        return ""
    return json.dumps(node.get("inputs") or {}, sort_keys=True, default=str)


def record(node_id, version_id, published_file_id=0, prompt=None):
    """Remember what this Load node resolved, against the graph it resolved it in."""
    _forget_stale(prompt)
    if node_id is not None and version_id:
        _resolved[str(node_id)] = (int(version_id), int(published_file_id or 0),
                                   fingerprint(prompt, node_id))


def _forget_stale(prompt):
    """Drop every entry this graph cannot own, so an old run does not sit here until the restart."""
    for nid, entry in list(_resolved.items()):
        if entry[2] != fingerprint(prompt, nid):
            del _resolved[nid]


def _entry(node_id, prompt):
    """This node's record, but only where the node in the graph now is the one that made it."""
    entry = _resolved.get(str(node_id))
    fp = fingerprint(prompt, node_id)
    return entry if entry and fp and entry[2] == fp else None


def _ordered(node_ids):
    return sorted(node_ids, key=lambda n: (0, int(n)) if str(n).isdigit() else (1, str(n)))


def for_nodes(node_ids, prompt):
    """Resolved Version ids for these nodes, in graph order, de-duplicated."""
    out = []
    for nid in _ordered(node_ids):
        entry = _entry(nid, prompt)
        if entry and entry[0] and entry[0] not in out:
            out.append(entry[0])
    return out


def files_for_nodes(node_ids, prompt):
    """{version_id: [published_file_id]} for the nodes that read an actual file.

    A Version absent from this mapping is one this run did not open a file from, not one without
    files; the caller then has to ask the site. Present means exact.
    """
    out = {}
    for nid in _ordered(node_ids):
        entry = _entry(nid, prompt)
        if not entry:
            continue
        vid, pfid = entry[0], entry[1]
        if vid and pfid and pfid not in out.setdefault(vid, []):
            out[vid].append(pfid)
    return out
