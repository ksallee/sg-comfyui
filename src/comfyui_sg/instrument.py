"""Read someone else's ComfyUI workflow and put SG into it.

    python src/comfyui_sg/instrument.py WORKFLOW.json                     # analyse only
    python src/comfyui_sg/instrument.py WORKFLOW.json --out COPY.json --publish 306/296

Run as a file, never `python -m`: `-m` imports the package `__init__` and therefore torch, and a
graph must stay analysable on a machine with neither torch nor a route to the site. Setup path — it
asks the site nothing, and never writes the original file.

The rule is structural, not a list of node names: an **output stream** is any IMAGE link feeding a
sink, plus any IMAGE output nothing consumes, so a workflow built from custom nodes this project has
never heard of still analyses correctly. A sink is where the images stop being images — see
`_is_sink`.

Modern templates put the work inside **subgraphs**, so the analysis runs over a flattened view of the
graph rather than over `wf["nodes"]` — see `_flatten`. A node is therefore addressed by a *path*,
`306/296`, not by an id, and everything here takes and returns those.
"""
import argparse
import json
import re
from collections import namedtuple
from pathlib import Path
from uuid import uuid4

# A sibling module, not `from . import widgets`: this file is run as a file so that `-m` never
# imports the package __init__ and, through it, torch. Its own directory is sys.path[0].
import widgets

# A node whose type says it ends the stream: whatever feeds it is a Version.
SINK_HINTS = ("save", "preview", "combine", "output", "write")
# Frames assembled into another medium end the image stream just as finally as saving them does.
# A type, not a node name, so an unknown video node still reads correctly.
ASSEMBLED = ("VIDEO",)
LOADER_HINTS = ("loadimage", "load_image", "imageload")

PUBLISH = "SGPublishVersion"
LOAD = "SGLoadVersion"

# The declared order, read from the one table rather than repeated. Positional serialisation means
# an off-by-one silently writes a value into the field next door, which is why nothing here is
# typed out a second time.
PUBLISH_WIDGETS = widgets.names(widgets.PUBLISH_FIELDS)
LOAD_WIDGETS = widgets.names(widgets.LOAD_FIELDS)
# site.NO_VALUE, spelled out rather than imported: this module is the setup path and stays free of
# the client. A combo cannot hold "" — the editor would show a value it can never offer back — so an
# unset pick is the visible "no value" the node declares.
NO_VALUE = "(none)"
# Every default mirrors the node class's own. `code_template` is empty because empty means the
# default under Settings, so one edit there reaches every graph this ever wrote; pinning the literal
# template defeated that on every /track-workflow graph. `register_files` is off because a tap added
# to somebody else's graph must not start copying their frames onto a shared volume.
PUBLISH_DEFAULTS = {"project": NO_VALUE, "link": NO_VALUE, "task": NO_VALUE, "status": NO_VALUE,
                    "code_template": "", "register_files": False,
                    "attach_workflow": True, "link_id": 0, "format": "8-bit PNG"}
# `frame` 0 is "wherever this sequence starts", so a plate numbered from 1001 needs nothing typed.
LOAD_DEFAULTS = {"project": NO_VALUE, "link": NO_VALUE, "task": NO_VALUE,
                 "statuses": "", "filters": "", "newest_by": "version number in the name",
                 "source": "auto", "pin_version_id": 0, "frame": 0, "frame_count": 0}


def _stream(descriptor):
    """A stream descriptor — "depth", "matte" — as that stream's `root_name` template.

    A template rather than a literal: `{entity}_depth` names the same thing on every shot.
    """
    return "{entity}_" + descriptor


def widget_values(names, defaults, **values):
    """The positional array, built by name. A name nothing declares is an error, not a no-op."""
    unknown = sorted((set(defaults) | set(values)) - set(names))
    if unknown:
        raise ValueError(f"not widgets of this node: {', '.join(unknown)}")
    v = {**{n: "" for n in names}, **defaults, **values}
    return [v[n] for n in names]


def load(path):
    return json.loads(Path(path).read_text())


def save(wf, path):
    Path(path).write_text(json.dumps(wf, indent=1) + "\n")
    return path


def _defs(wf):
    """{uuid: definition}. A subgraph instance node carries the definition's uuid as its `type`."""
    return {d["id"]: d for d in (wf.get("definitions") or {}).get("subgraphs") or [] if d.get("id")}


def _edges(container):
    """[(origin_id, origin_slot, target_id, target_slot, type)] for a graph or a definition.

    Same five values either way, spelled differently: the top level stores a link as a six-element
    array, a subgraph definition as an object. Both are in the file at once, so both are read here.
    """
    out = []
    for l in container.get("links") or []:
        if isinstance(l, list) and len(l) >= 6:
            out.append((l[1], l[2], l[3], l[4], l[5]))
        elif isinstance(l, dict) and l.get("origin_id") is not None:
            out.append((l["origin_id"], l.get("origin_slot") or 0,
                        l.get("target_id"), l.get("target_slot") or 0, l.get("type")))
    return out


SEP = "/"
Flat = namedtuple("Flat", "nodes links subs labels")


def _flatten(wf):
    """The graph ComfyUI actually executes, with subgraph boundaries removed.

    A subgraph instance is a relay, not a node. Inside the definition, a link out of `inputNode`
    slot k continues whatever the instance's input k was fed; a link into `outputNode` slot j is
    what the instance's output j hands on. Splicing those pairs is the whole trick, and it handles
    nesting for free, because a definition may instantiate another one.

    Returns
      nodes   {path: node}    real nodes only — an instance is a relay and never appears
      links   [(opath, oslot, tpath, tslot, type)]   boundaries spliced out
      subs    {path: (instance node, definition)}
      labels  {(path, slot): label}   the name the definition's own output slot gives that stream
    A path is `306/296`: instance 306 at the top level, node 296 inside it. Top-level nodes keep the
    bare id, so a graph with no subgraph reads exactly as it did before.
    """
    defs = _defs(wf)
    nodes, subs, labels, raw, relay = {}, {}, {}, [], set()

    def walk(container, prefix, q, stack):
        # An instance's two sides need two names: `p` is its input side — the port an outside link
        # targets and the definition's inputNode continues — and `p^` its output side.
        inst = {str(n.get("id")) for n in container.get("nodes") or [] if n.get("type") in defs}
        bi = (container.get("inputNode") or {}).get("id") if q is not None else None
        bo = (container.get("outputNode") or {}).get("id") if q is not None else None
        outs = container.get("outputs") or []
        for o, os_, t, ts, ty in _edges(container):
            op, tp = prefix + str(o), prefix + str(t)
            src = (q, os_) if q is not None and o == bi else (op + "^" if str(o) in inst else op, os_)
            leaves = q is not None and t == bo
            dst = (q + "^", ts) if leaves else (tp, ts)
            raw.append((src[0], src[1], dst[0], dst[1], ty))
            if leaves and ts < len(outs):
                lbl = outs[ts].get("label") or outs[ts].get("localized_name") or outs[ts].get("name")
                if lbl:
                    labels[src] = lbl
        for n in container.get("nodes") or []:
            p = prefix + str(n.get("id"))
            d = defs.get(n.get("type"))
            if d is None:
                nodes[p] = n
                continue
            subs[p] = (n, d)
            relay.add(p)
            relay.add(p + "^")
            # A definition that reaches itself would recurse forever; nothing sane writes one, but
            # the file is someone else's and this is a setup tool, not a validator.
            if d["id"] not in stack:
                walk(d, p + SEP, p, stack + (d["id"],))

    walk(wf, "", None, ())

    by_port = {}
    for e in raw:
        by_port.setdefault((e[0], e[1]), []).append(e)

    def reach(t, ts, seen):
        if t not in relay:
            return [(t, ts)]
        if (t, ts) in seen:
            return []
        seen = seen | {(t, ts)}
        return [r for e in by_port.get((t, ts), []) for r in reach(e[2], e[3], seen)]

    links = [(o, os_, t2, ts2, ty) for o, os_, t, ts, ty in raw if o not in relay
             for t2, ts2 in reach(t, ts, frozenset())]
    return Flat(nodes, links, subs, labels)


def _live(flat):
    """{path: {slot}} — output slots that actually feed something once the boundaries are gone.

    A node's own `outputs[].links` cannot answer this inside a subgraph: a link to the definition's
    `outputNode` looks live whether or not the instance that uses it is wired to anything.
    """
    out = {}
    for o, os_, _, _, _ in flat.links:
        out.setdefault(o, set()).add(os_)
    return out


def _is_sink(node, live):
    """Whether an IMAGE stream stops being images here.

    Two ways it stops: the node's type says it saves or previews, or a live output of it carries
    another medium. A save node is an end whether or not it also hands the picture on, so
    `SaveImage` feeding an `ImageCompare` still ends the stream. Nodes that merely re-express the
    images — VAEEncode, CLIPVisionEncode, GetImageSize — pass the stream on in another form and are
    deliberately not ends.

    `live` is the set of output slots `_live` found, not what the node declares.
    """
    outs = node.get("outputs") or []
    if any(h in (node.get("type") or "").lower() for h in SINK_HINTS):
        return True
    return any(outs[s].get("type") in ASSEMBLED for s in live if s < len(outs))


def _is_loader(node):
    return any(h in (node.get("type") or "").lower().replace(" ", "") for h in LOADER_HINTS)


def _slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()


# A name a stream may never take, however it was arrived at. A widget value is a naming candidate,
# so the switch settings are here too: a boolean says nothing about the stream.
DROP = ("preview_image", "save_image", "image", "previewimage", "saveimage",
        "none", "true", "false", "enable", "disable")
# ...and more that a *sink* or a *slot* may not lend it: a node whose whole job is to end the stream
# is named after the medium, not after this picture. The node's own type is exempt — it is the last
# candidate there is, and `vaedecode` beats `out0`.
NAMELESS = DROP + ("images", "video", "mask", "output", "value", "result", "frames", "any",
                   "preview_video", "previewvideo", "save_video", "savevideo",
                   "create_video", "createvideo", "preview_any", "previewany",
                   "save_animated_webp", "saveanimatedwebp", "save_animated_png",
                   "saveanimatedpng", "save_webm", "savewebm", "vhs_videocombine",
                   "save_image_advanced", "saveimageadvanced")


def descriptor(node, slot, sink_title="", out_label="", scope=""):
    """What a stream IS, in one token: depth, normal_opengl, mask.

    Taken from what the graph already says — a node title the author set, a render-pass widget, the
    sink's label, the name on the subgraph output it leaves through, or the subgraph's own name —
    because the operator named these things and we should not rename them. This is what a proposed
    code is built from, and it is the reason three passes do not collapse onto one name.

    `scope` is the enclosing subgraph's name, and its useful half is the *opposite* half from a sink
    label's: "Preview Image (normal_opengl)" says what it is inside the brackets, "Depth Estimation
    (Depth Anything 3)" says it before them and names a model inside. So the trailing bracket is
    dropped rather than preferred, and `scope` is tried late — after everything nearer the stream.
    """
    # widgets_values is a list on most nodes and a dict on some (VHS_VideoCombine writes
    # {frame_rate, loop_count, filename_prefix}), and slicing a dict raises.
    w = node.get("widgets_values") or []
    w = list(w.values()) if isinstance(w, dict) else list(w)
    # (text, the bracket is the useful half, tokens this candidate is not allowed to be)
    cands = [(node.get("title"), True, DROP), *((str(x), True, DROP) for x in w[:1]),
             (sink_title, True, NAMELESS), (out_label, True, NAMELESS),
             (re.sub(r"\s*\([^)]*\)\s*$", "", scope or ""), False, NAMELESS),
             (node.get("type"), True, DROP)]
    for cand, bracket_wins, drop in cands:
        if not cand or not isinstance(cand, str):
            continue
        inner = re.search(r"\(([^)]+)\)", cand) if bracket_wins else None
        # A sink label like "Preview Image (normal_opengl)" carries the useful part in parentheses.
        tok = _slug(inner.group(1) if inner else cand)
        # A bare number is a widget value, not a name: ImageFromBatch's batch index reads as "0" and
        # a luma coefficient slugs down to digits, and both read the same for every stream in the
        # graph. Collapsing two passes onto one code is the failure this function exists to prevent.
        if re.fullmatch(r"[\d_]+", tok):
            continue
        if tok and tok not in drop:
            return tok[:32]
    return f"out{slot}"


def _scope(flat, path):
    """The name of the subgraph a stream sits in, "" at the top level."""
    parent = path.rpartition(SEP)[0]
    if not parent or parent not in flat.subs:
        return ""
    inst, d = flat.subs[parent]
    return inst.get("title") or d.get("name") or ""


def descriptors(wf):
    """{(path, slot): name} — what each stream is called, unique within this graph.

    `descriptor` names a stream from what the graph says about it, which is right but not necessarily
    distinct, and two Versions sharing one code is a collapse `code = auto` cannot recover from. The
    node type breaks the tie where it can, the path where it cannot, and the slot breaks it again for
    a node feeding three previews off one body — (path, slot) is the floor the graph guarantees.
    """
    flat = _flatten(wf)
    raw, counts = [], {}
    for path, slot, _, sink in outputs(wf):
        d = descriptor(flat.nodes.get(path, {}), slot, sink or "",
                       flat.labels.get((path, slot), ""), _scope(flat, path))
        raw.append((path, slot, d))
        counts[d] = counts.get(d, 0) + 1
    # When two streams describe themselves the same way, the graph's own next word for them is the
    # node type. Only when that repeats too does the path decide, and a path is not a name at all.
    kinds = {p: _slug(flat.nodes.get(p, {}).get("type") or "") for p, _, _ in raw}
    pairs = {}
    for path, _, d in raw:
        pairs[(d, kinds[path])] = pairs.get((d, kinds[path]), 0) + 1
    out, used = {}, set()
    for path, slot, d in raw:
        tie, kind = path.replace(SEP, "_"), kinds[path]
        name = d
        if counts[d] > 1:
            named = kind and kind not in d and pairs[(d, kind)] == 1
            name = f"{d}_{kind}" if named else f"{d}_{tie}"
        if name in used:
            name = f"{d}_{tie}_{slot}"
        out[(path, slot)] = name
        used.add(name)
    return out


def outputs(wf):
    """[(origin_path, origin_slot, label, consumed_by)] — every IMAGE stream worth publishing."""
    flat = _flatten(wf)
    live = _live(flat)
    incoming = {(t, ts): (o, os_) for o, os_, t, ts, _ in flat.links}
    found, seen = [], set()
    for path, n in flat.nodes.items():
        if not _is_sink(n, live.get(path, set())):
            continue
        for slot, inp in enumerate(n.get("inputs") or []):
            key = incoming.get((path, slot))
            if inp.get("type") != "IMAGE" or key is None or key in seen:
                continue
            seen.add(key)
            origin = flat.nodes.get(key[0], {})
            found.append((key[0], key[1], origin.get("title") or origin.get("type") or "?",
                          n.get("title") or n.get("type")))
    # An IMAGE output nothing consumes is a stream too — often exactly the pass someone forgot to save.
    for path, n in flat.nodes.items():
        # ...but not a sink's own pass-through. A save node that hands the image straight back out
        # would otherwise report the same picture twice, once named for the node that made it and
        # once for the node that saved it. The first is the useful name, and it is already recorded.
        if _is_sink(n, live.get(path, set())) and any(
                i.get("type") == "IMAGE" and (path, s) in incoming
                for s, i in enumerate(n.get("inputs") or [])):
            continue
        for slot, o in enumerate(n.get("outputs") or []):
            if (o.get("type") == "IMAGE" and slot not in live.get(path, set())
                    and (path, slot) not in seen):
                seen.add((path, slot))
                found.append((path, slot, n.get("title") or n.get("type") or "?", None))
    return found


def loaders(wf):
    """[(path, label, [(target_path, target_slot)])] — image loaders a Load node could replace."""
    flat = _flatten(wf)
    out = []
    for path, n in flat.nodes.items():
        if not _is_loader(n):
            continue
        image = {s for s, o in enumerate(n.get("outputs") or []) if o.get("type") == "IMAGE"}
        targets = [(t, ts) for o, os_, t, ts, _ in flat.links if o == path and os_ in image]
        out.append((path, n.get("title") or n.get("type"), targets))
    return out


def _bump(wf, key):
    """The next node or link id, kept in step everywhere the file records one.

    ComfyUI counts nodes and links once for the whole document and mirrors the counter into every
    subgraph definition's `state`. Reading only the top-level counter hands out an id a definition
    has already used, and the editor then loads two things as one.
    """
    mirror = {"last_node_id": "lastNodeId", "last_link_id": "lastLinkId"}[key]
    defs = list(_defs(wf).values())
    n = max([int(wf.get(key) or 0)] + [int((d.get("state") or {}).get(mirror) or 0) for d in defs]) + 1
    wf[key] = n
    for d in defs:
        d.setdefault("state", {})[mirror] = n
    return n


def _add_node(wf, container, ntype, pos, widgets, title, inputs=(), outs=()):
    nid = _bump(wf, "last_node_id")
    container.setdefault("nodes", []).append({
        "id": nid, "type": ntype, "pos": list(pos), "size": [400, 300], "flags": {},
        "order": len(container["nodes"]), "mode": 0,
        "inputs": [dict(i) for i in inputs], "outputs": [dict(o) for o in outs],
        "properties": {"Node name for S&R": ntype}, "widgets_values": widgets, "title": title,
    })
    return nid


def _add_link(wf, container, src, src_slot, dst, dst_slot, type_):
    """A link, spelled the way its container spells links — see `_edges`."""
    lid = _bump(wf, "last_link_id")
    container.setdefault("links", []).append(
        [lid, src, src_slot, dst, dst_slot, type_] if container is wf else
        {"id": lid, "origin_id": src, "origin_slot": src_slot,
         "target_id": dst, "target_slot": dst_slot, "type": type_})
    return lid


def _holder(wf, path):
    """(container, local id) — the graph or definition that literally holds the node at `path`."""
    parent, _, local = path.rpartition(SEP)
    return (wf if not parent else _flatten(wf).subs[parent][1]), int(local)


def _instances(wf, def_id):
    """Every instance node of a definition, wherever it sits. No corpus graph instantiates one
    definition twice, but a definition is shared state and this is someone else's file."""
    where = [wf] + list(_defs(wf).values())
    return [n for c in where for n in c.get("nodes") or [] if n.get("type") == def_id]


def _promote(wf, path, slot, name):
    """Give a stream inside a subgraph an output slot at the top level; return its (path, slot) there.

    This is what dragging an interior output onto the subgraph's output panel does in the editor: the
    definition gains an output, its instance gains the matching slot, and an interior link runs to the
    definition's `outputNode` — or nothing is added at all, where the stream already leaves through an
    output (`_sub_output`). Either way it is additive: everything already wired stays wired.

    A publish node placed *inside* the definition would need none of this, and is the wrong trade: it
    would run once per instance of a definition that is shared state, and it would hide the project
    and link pickers a level down from the operator who has to fill them in.
    """
    while SEP in path:
        parent, _, inner = path.rpartition(SEP)
        d = _flatten(wf).subs[parent][1]
        slot, path = _sub_output(wf, d, int(inner), slot, name), parent
    return path, slot


def _sub_output(wf, d, inner_id, inner_slot, name):
    """The slot this stream already leaves the subgraph through, or a new one for it.

    Reuse first: a template that exposes its `depth` pass has said what the stream is called and
    where it comes out, and a second slot beside it is the tool talking over the operator.

    Only where that slot has exactly one feeder. Templates carry stale links into outputs they later
    rewired, and a slot fed by two nodes would publish whichever the editor happened to resolve.
    """
    bo = (d.get("outputNode") or {}).get("id", -20)
    feeds = {}
    for l in d.get("links") or []:
        if isinstance(l, dict) and l.get("target_id") == bo:
            feeds.setdefault(l.get("target_slot") or 0, []).append(l)
    for j, ls in feeds.items():
        if (j < len(d.get("outputs") or []) and len(ls) == 1
                and ls[0].get("origin_id") == inner_id and (ls[0].get("origin_slot") or 0) == inner_slot):
            return j
    return _add_sub_output(wf, d, inner_id, inner_slot, name)


def _add_sub_output(wf, d, inner_id, inner_slot, name):
    j = len(d.setdefault("outputs", []))
    lid = _bump(wf, "last_link_id")
    bo = (d.get("outputNode") or {}).get("id", -20)
    # A link to an output slot the definition no longer declares is already dead — the editor cannot
    # draw it — and left in place it would land on the slot being added here. Dropped in the copy.
    d["links"] = [l for l in d.get("links") or []
                  if not (isinstance(l, dict) and l.get("target_id") == bo
                          and (l.get("target_slot") or 0) >= j)]
    box = (d.get("outputNode") or {}).get("bounding") or [0, 0, 128, 68]
    d["outputs"].append({"id": str(uuid4()), "name": name, "localized_name": name,
                         "type": "IMAGE", "linkIds": [lid],
                         "pos": [box[0] + 24, box[1] + 24 + 20 * j]})
    if len(box) >= 4:
        box[3] = max(box[3], 48 + 20 * (j + 1))
    d.setdefault("links", []).append({"id": lid, "origin_id": inner_id, "origin_slot": inner_slot,
                                      "target_id": bo, "target_slot": j, "type": "IMAGE"})
    for n in d.get("nodes") or []:
        if n.get("id") == inner_id and inner_slot < len(n.get("outputs") or []):
            o = n["outputs"][inner_slot]
            o["links"] = (o.get("links") or []) + [lid]
    for n in _instances(wf, d["id"]):
        n.setdefault("outputs", []).append({"name": name, "type": "IMAGE", "links": []})
    return j


def add_publish(wf, origin_path, origin_slot, widgets, title="SG Publish", name="image"):
    """Tap an existing IMAGE stream. Additive — whatever already consumed it still does.

    A stream inside a subgraph is taken at the instance's output first — the one it already leaves
    through, or a new one called `name` — so the publish node itself always sits at the top level
    where its pickers are.
    """
    path, slot = _promote(wf, str(origin_path), origin_slot, name)
    origin = next(n for n in wf["nodes"] if str(n["id"]) == path)
    ox, oy = origin.get("pos", [0, 0])[:2]
    # Both slots, in declared order. `video` is left unwired — this taps an IMAGE stream — but a
    # slot the file never mentions is a slot the operator has nothing to drop a clip onto.
    nid = _add_node(wf, wf, PUBLISH, (ox + 480, oy + 120), widgets, title,
                    inputs=[{"name": "images", "type": "IMAGE", "link": None},
                            {"name": "video", "type": "VIDEO", "link": None}])
    lid = _add_link(wf, wf, origin["id"], slot, nid, 0, "IMAGE")
    wf["nodes"][-1]["inputs"][0]["link"] = lid
    o = origin["outputs"][slot]
    o["links"] = (o.get("links") or []) + [lid]
    return nid


def replace_loader(wf, loader_path, widgets, title="SG Load"):
    """Feed what a loader fed, from SG instead. The loader is left in place but unwired, so the
    operator can see what was replaced and put it back.

    The rewiring happens in whatever container the loader sits in, so a loader inside a subgraph is
    replaced inside that same subgraph rather than promoted out. Crossing the boundary here would
    mean rewriting the *interior* node's input, and a definition's interior is shared by every
    instance of it — additive on the way out, destructive on the way in.
    """
    loader_path = str(loader_path)
    container, local = _holder(wf, loader_path)
    loader = next(n for n in container["nodes"] if n.get("id") == local)
    image = {s for s, o in enumerate(loader.get("outputs") or []) if o.get("type") == "IMAGE"}
    targets = [(t, ts) for o, os_, t, ts, _ in _edges(container) if o == local and os_ in image]
    lx, ly = loader.get("pos", [0, 0])[:2]
    # Every output the class declares, in order: a slot missing here is a wire the operator cannot
    # make without deleting the node and adding it again.
    nid = _add_node(wf, container, LOAD, (lx, ly - 40), widgets, title,
                    outs=[{"name": "images", "type": "IMAGE", "links": []},
                          {"name": "version_id", "type": "INT", "links": []},
                          {"name": "code", "type": "STRING", "links": []},
                          {"name": "colour_space", "type": "STRING", "links": []},
                          {"name": "video", "type": "VIDEO", "links": []},
                          {"name": "mask", "type": "MASK", "links": []}])
    new = container["nodes"][-1]
    cut = {l[0] if isinstance(l, list) else l.get("id") for l in container.get("links") or []
           if (l[1] if isinstance(l, list) else l.get("origin_id")) == local}
    container["links"] = [l for l in container.get("links") or []
                          if (l[0] if isinstance(l, list) else l.get("id")) not in cut]
    for o in loader.get("outputs") or []:
        o["links"] = []
    # A link the loader fed straight to the subgraph's own output is recorded on that output too.
    for o in container.get("outputs") or []:
        o["linkIds"] = [i for i in o.get("linkIds") or [] if i not in cut]
    boundary = (container.get("outputNode") or {}).get("id")
    by_id = {n.get("id"): n for n in container.get("nodes") or []}
    # A LoadImage feeds a MASK as well as an IMAGE, and only the IMAGE is rewired. Whoever took the
    # mask is told the link is gone rather than left pointing at an id nothing answers to.
    for n in container.get("nodes") or []:
        for i in n.get("inputs") or []:
            if i.get("link") in cut:
                i["link"] = None
    for tid, tslot in targets:
        lid = _add_link(wf, container, nid, 0, tid, tslot, "IMAGE")
        new["outputs"][0]["links"].append(lid)
        if tid == boundary:
            outs = container.get("outputs") or []
            if tslot < len(outs):
                outs[tslot]["linkIds"] = (outs[tslot].get("linkIds") or []) + [lid]
        elif tid in by_id and tslot < len(by_id[tid].get("inputs") or []):
            by_id[tid]["inputs"][tslot]["link"] = lid
    return nid


def report(wf, name="", template=""):
    flat = _flatten(wf)
    outs, lds = outputs(wf), loaders(wf)
    names = descriptors(wf)
    counted = len(flat.nodes) + len(flat.subs)
    lines = [f"{name or 'workflow'}: {counted} nodes"
             + (f" ({len(flat.subs)} of them subgraphs)" if flat.subs else "")]
    lines.append(f"  publishable streams ({len(outs)}):")
    for path, slot, label, sink in outs:
        d = names[(path, slot)]
        proposed = (template.replace("{root_name}", _stream(d)).replace("{version}", "001")
                    if template else f"...{d}...")
        where = f'  in subgraph "{_scope(flat, path)}"' if SEP in path else ""
        lines.append(f"    node {path}[{slot}] {label}"
                     + (f"  -> {sink}" if sink else "  (unconsumed)") + where)
        lines.append(f"        root name={_stream(d)!r}   proposed code: {proposed}")
    lines.append(f"  image inputs a Load could replace ({len(lds)}):")
    for path, label, targets in lds:
        where = f'  in subgraph "{_scope(flat, path)}"' if SEP in path else ""
        lines.append(f"    node {path} {label}  feeds {len(targets)} input(s)" + where)
    return "\n".join(lines)


def _cli(argv=None):
    ap = argparse.ArgumentParser(prog="comfyui_sg.instrument", description=__doc__.split("\n")[0])
    ap.add_argument("workflow")
    ap.add_argument("--out", help="write an instrumented copy here; omit to only analyse")
    ap.add_argument("--publish", action="append", default=[], metavar="NODE[:SLOT]",
                    help="tap this IMAGE stream with a publish node; repeatable. NODE is what the "
                         "report printed — an id, or a path like 306/296 inside a subgraph")
    ap.add_argument("--load", action="append", default=[], metavar="NODE",
                    help="replace this loader with a Load node; repeatable")
    ap.add_argument("--template", default="", help="the show's convention, to show proposed codes")
    ap.add_argument("--project", default="")
    ap.add_argument("--link", default="")
    a = ap.parse_args(argv)

    wf = load(a.workflow)
    print(report(wf, Path(a.workflow).name, a.template))
    if not a.out:
        return 0

    # Only what was actually asked for: an empty --project must leave the default alone, not write
    # "" into a combo that cannot hold it.
    common = {k: v for k, v in (("project", a.project), ("link", a.link)) if v}
    flat = _flatten(wf)
    names = descriptors(wf)
    sinks = {(o, s): k for o, s, _, k in outputs(wf)}
    for spec in a.publish:
        stem, sep, tail = spec.rpartition(":")
        path, slot = (stem, int(tail)) if sep and tail.isdigit() else (spec, 0)
        d = names.get((path, slot)) or descriptor(
            flat.nodes.get(path, {}), slot, sinks.get((path, slot)) or "",
            flat.labels.get((path, slot), ""), _scope(flat, path))
        w = widget_values(PUBLISH_WIDGETS, PUBLISH_DEFAULTS, root_name=_stream(d), **common)
        top = path.split(SEP)[0]
        crossed = SEP in path
        was = len(_flatten(wf).subs[top][0].get("outputs") or []) if crossed else 0
        # Every tap re-reads the graph, because promoting a stream out of a subgraph changes it.
        new = add_publish(wf, path, slot, w, title=f"SG Publish — {d}", name=d)
        note = ""
        if crossed:
            grew = len(_flatten(wf).subs[top][0].get("outputs") or []) > was
            note = (f"  (subgraph {top} gained an output {d!r})" if grew
                    else f"  (through subgraph {top}'s existing output)")
        print(f"  + publish node {new} tapping {path}[{slot}]  root name={_stream(d)!r}{note}")
    for path in a.load:
        new = replace_loader(wf, path,
                             widget_values(LOAD_WIDGETS, LOAD_DEFAULTS, **common))
        stem = str(path).rpartition(SEP)[0]
        print(f"  + load node {stem + SEP if stem else ''}{new} replacing loader {path}"
              + (f"  (inside subgraph {stem})" if stem else ""))
    save(wf, a.out)
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
