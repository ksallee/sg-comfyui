"""Read someone else's ComfyUI workflow and put Flow PT tracking into it.

Setup path. The operator has a graph that already works; this finds where a Version would come out of
it and where one could go in, then does the wiring. It never rewrites the original file.

The rule is structural, not a list of node names: an **output stream** is any IMAGE link feeding a
sink, plus any IMAGE output nothing consumes. That way a workflow built from custom nodes this project
has never heard of still analyses correctly — which matters, because the graphs worth tracking are
exactly the ones nobody standardised.

A sink is where the images stop being images: either nothing is wired out of it, or what comes out is
another medium. Both halves were measured against 680 real workflows (the ComfyUI template set plus
the three most-starred public collections) — see `_is_sink`.
"""
import json
import re
from copy import deepcopy
from pathlib import Path

# Consume an IMAGE and produce nothing: the end of a stream, so the thing feeding them is a Version.
SINK_HINTS = ("save", "preview", "combine", "output", "write")
# Frames assembled into another medium end the image stream just as finally as saving them does.
# A type, not a node name, so an unknown video node still reads correctly.
ASSEMBLED = ("VIDEO",)
LOADER_HINTS = ("loadimage", "load_image", "imageload")

PUBLISH = "FPTPublishVersion"
LOAD = "FPTLoadVersion"

# ComfyUI serialises widgets positionally, so these must match INPUT_TYPES order (required, then
# optional). Built by name here because an off-by-one silently writes a value into the wrong field.
PUBLISH_WIDGETS = ["code_template", "project", "link_type", "link", "task", "status", "output_name", "note",
                   "source_versions", "attach_workflow", "link_id"]
LOAD_WIDGETS = ["project", "link_type", "link", "task", "name_contains", "statuses",
                 "newest_by", "pin_version_id", "source", "frame", "filters"]
PUBLISH_DEFAULTS = {"code_template": "{entity.code}_{output}_v{version:03d}", "attach_workflow": True, "link_id": 0}
LOAD_DEFAULTS = {"statuses": "", "filters": "", "newest_by": "version number in the name", "source": "auto",
                  "pin_version_id": 0, "frame": 1, "link_type": "(all types)"}


def widgets(names, defaults, **values):
    v = {**{n: "" for n in names}, **defaults, **values}
    return [v[n] for n in names]


def load(path):
    return json.loads(Path(path).read_text())


def save(wf, path):
    Path(path).write_text(json.dumps(wf, indent=1) + "\n")
    return path


def _nodes(wf):
    return {int(n["id"]): n for n in wf.get("nodes", [])}


def _links(wf):
    """{link_id: (origin_node, origin_slot, target_node, target_slot, type)}"""
    out = {}
    for l in wf.get("links", []) or []:
        if isinstance(l, list) and len(l) >= 6:
            out[l[0]] = (l[1], l[2], l[3], l[4], l[5])
    return out


def _is_sink(node):
    """Where an IMAGE stream stops being images.

    Two ways that happens, and the old test only saw the first. `not node.get("outputs")` asked
    whether the node *declares* an output slot, so a save node with a slot nobody wired was missed,
    and `CreateVideo` — which does have a VIDEO output — hid the frame stream behind it. Measured on
    680 real workflows: 196 of them found no publishable stream at all for that reason, every one a
    video graph whose frames were sitting right there on `VAEDecode`.

    Nodes that merely re-express the images — VAEEncode, CLIPVisionEncode, GetImageSize — pass the
    stream on in another form and are deliberately not ends.
    """
    live = [o for o in node.get("outputs") or [] if o.get("links")]
    if any(h in (node.get("type") or "").lower() for h in SINK_HINTS) and not live:
        return True
    return any(o.get("type") in ASSEMBLED for o in live)


def _is_loader(node):
    return any(h in (node.get("type") or "").lower().replace(" ", "") for h in LOADER_HINTS)


def descriptor(node, slot, sink_title=""):
    """What a stream IS, in one token: depth, normal_opengl, mask.

    Taken from what the graph already says — a node title the author set, a render-pass widget, or the
    sink's label — because the operator named these things and we should not rename them. This is what
    a proposed code is built from, and it is the reason three passes do not collapse onto one name.
    """
    # widgets_values is a list on most nodes and a dict on some (VHS_VideoCombine writes
    # {frame_rate, loop_count, filename_prefix}). Slicing a dict raises, which took the whole CLI
    # down on 2 of 680 real workflows.
    w = node.get("widgets_values") or []
    w = list(w.values()) if isinstance(w, dict) else list(w)
    for cand in (node.get("title"), *(str(x) for x in w[:1]),
                 sink_title, node.get("type")):
        if not cand or not isinstance(cand, str):
            continue
        tok = re.sub(r"[^A-Za-z0-9]+", "_", cand).strip("_").lower()
        # A sink label like "Preview Image (normal_opengl)" carries the useful part in parentheses.
        inner = re.search(r"\(([^)]+)\)", cand)
        if inner:
            tok = re.sub(r"[^A-Za-z0-9]+", "_", inner.group(1)).strip("_").lower()
        # A bare number is a widget value, not a name — ImageFromBatch's batch index reads as "0",
        # which says nothing about the pass and, worse, reads the same for every such stream in the
        # graph. Collapsing two passes onto one code is the failure this function exists to prevent.
        if tok.isdigit():
            continue
        if tok and tok not in ("preview_image", "save_image", "image", "previewimage", "saveimage"):
            return tok[:32]
    return f"out{slot}"


def descriptors(wf):
    """{(node_id, slot): name} — what each stream is called, unique within this graph.

    `descriptor` names a stream from what the graph says about it, which is right but not
    necessarily distinct: the two symmetric tails of a two-shot video template describe themselves
    identically, and two Versions sharing one code is the collapse `code = auto` cannot recover
    from. The node id breaks the tie, and the slot breaks it again for the node that feeds three
    previews off one body — (id, slot) is what the graph guarantees is unique, so that is the floor.
    """
    nodes = _nodes(wf)
    raw, counts = [], {}
    for oid, slot, _, sink in outputs(wf):
        d = descriptor(nodes.get(oid, {}), slot, sink or "")
        raw.append((oid, slot, d))
        counts[d] = counts.get(d, 0) + 1
    out, used = {}, set()
    for oid, slot, d in raw:
        name = d if counts[d] == 1 else f"{d}_{oid}"
        if name in used:
            name = f"{d}_{oid}_{slot}"
        out[(oid, slot)] = name
        used.add(name)
    return out


def outputs(wf):
    """[(origin_id, origin_slot, label, consumed_by)] — every IMAGE stream worth publishing."""
    nodes, links = _nodes(wf), _links(wf)
    found, seen = [], set()
    for nid, n in nodes.items():
        if not _is_sink(n):
            continue
        for inp in n.get("inputs") or []:
            if inp.get("type") != "IMAGE" or inp.get("link") is None:
                continue
            l = links.get(inp["link"])
            if not l:
                continue
            key = (l[0], l[1])
            if key in seen:
                continue
            seen.add(key)
            origin = nodes.get(l[0], {})
            found.append((l[0], l[1], origin.get("title") or origin.get("type") or "?",
                          n.get("title") or n.get("type")))
    # An IMAGE output nothing consumes is a stream too — often exactly the pass someone forgot to save.
    for nid, n in nodes.items():
        # ...but not a sink's own pass-through. A save node that hands the image straight back out
        # would otherwise report the same picture twice, once named for the node that made it and
        # once for the node that saved it. The first is the useful name, and it is already recorded.
        if _is_sink(n) and any(i.get("type") == "IMAGE" and i.get("link") is not None
                               for i in n.get("inputs") or []):
            continue
        for slot, o in enumerate(n.get("outputs") or []):
            if o.get("type") == "IMAGE" and not (o.get("links") or []) and (nid, slot) not in seen:
                seen.add((nid, slot))
                found.append((nid, slot, n.get("title") or n.get("type") or "?", None))
    return found


def loaders(wf):
    """[(id, label, [(target_id, target_slot)])] — image inputs a Load node could replace."""
    nodes, links = _nodes(wf), _links(wf)
    out = []
    for nid, n in nodes.items():
        if not _is_loader(n):
            continue
        targets = []
        for slot, o in enumerate(n.get("outputs") or []):
            if o.get("type") != "IMAGE":
                continue
            for lid in o.get("links") or []:
                l = links.get(lid)
                if l:
                    targets.append((l[2], l[3]))
        out.append((nid, n.get("title") or n.get("type"), targets))
    return out


def _add_node(wf, ntype, pos, widgets, title, inputs=(), outs=()):
    nid = int(wf.get("last_node_id", 0)) + 1
    wf["last_node_id"] = nid
    wf.setdefault("nodes", []).append({
        "id": nid, "type": ntype, "pos": list(pos), "size": [400, 300], "flags": {},
        "order": len(wf["nodes"]), "mode": 0,
        "inputs": [dict(i) for i in inputs], "outputs": [dict(o) for o in outs],
        "properties": {"Node name for S&R": ntype}, "widgets_values": widgets, "title": title,
    })
    return nid


def _add_link(wf, src, src_slot, dst, dst_slot, type_):
    lid = int(wf.get("last_link_id", 0)) + 1
    wf["last_link_id"] = lid
    wf.setdefault("links", []).append([lid, src, src_slot, dst, dst_slot, type_])
    return lid


def add_publish(wf, origin_id, origin_slot, widgets, title="Flow PT Publish Version"):
    """Tap an existing IMAGE stream. Additive — whatever already consumed it still does."""
    nodes = _nodes(wf)
    ox, oy = nodes[origin_id].get("pos", [0, 0])[:2]
    nid = _add_node(wf, PUBLISH, (ox + 480, oy + 120), widgets, title,
                    inputs=[{"name": "images", "type": "IMAGE", "link": None}])
    lid = _add_link(wf, origin_id, origin_slot, nid, 0, "IMAGE")
    for n in wf["nodes"]:
        if n["id"] == nid:
            n["inputs"][0]["link"] = lid
        if n["id"] == origin_id:
            o = (n.get("outputs") or [])[origin_slot]
            o["links"] = (o.get("links") or []) + [lid]
    return nid


def replace_loader(wf, loader_id, widgets, title="Flow PT Load Version"):
    """Feed what a loader fed, from Flow PT instead. The loader is left in place but unwired, so the
    operator can see what was replaced and put it back."""
    nodes = _nodes(wf)
    targets = next((t for i, _, t in loaders(wf) if i == loader_id), [])
    lx, ly = nodes[loader_id].get("pos", [0, 0])[:2]
    nid = _add_node(wf, LOAD, (lx, ly - 40), widgets, title,
                    outs=[{"name": "image", "type": "IMAGE", "links": []},
                          {"name": "version_id", "type": "INT", "links": []},
                          {"name": "code", "type": "STRING", "links": []}])
    wf["links"] = [l for l in wf.get("links", [])
                   if not (isinstance(l, list) and len(l) >= 6 and l[1] == loader_id)]
    for n in wf["nodes"]:
        if n["id"] == loader_id:
            for o in n.get("outputs") or []:
                o["links"] = []
    for tid, tslot in targets:
        lid = _add_link(wf, nid, 0, tid, tslot, "IMAGE")
        for n in wf["nodes"]:
            if n["id"] == nid:
                n["outputs"][0]["links"].append(lid)
            if n["id"] == tid:
                for inp in n.get("inputs") or []:
                    if inp.get("link") is not None and inp.get("type") == "IMAGE":
                        pass
                if tslot < len(n.get("inputs") or []):
                    n["inputs"][tslot]["link"] = lid
    return nid


def report(wf, name="", template=""):
    outs, lds = outputs(wf), loaders(wf)
    names = descriptors(wf)
    lines = [f"{name or 'workflow'}: {len(wf.get('nodes', []))} nodes"]
    lines.append(f"  publishable streams ({len(outs)}):")
    for oid, slot, label, sink in outs:
        d = names[(oid, slot)]
        proposed = (template.replace("{output}", d).replace("{version}", "001")
                    if template else f"...{d}...")
        lines.append(f"    node {oid}[{slot}] {label}" + (f"  -> {sink}" if sink else "  (unconsumed)"))
        lines.append(f"        output_name={d!r}   proposed code: {proposed}")
    lines.append(f"  image inputs a Load could replace ({len(lds)}):")
    for lid, label, targets in lds:
        lines.append(f"    node {lid} {label}  feeds {len(targets)} input(s)")
    return "\n".join(lines)


def _cli(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="comfyui_fpt.instrument", description=__doc__.split("\n")[0])
    ap.add_argument("workflow")
    ap.add_argument("--out", help="write an instrumented copy here; omit to only analyse")
    ap.add_argument("--publish", action="append", default=[], metavar="NODE[:SLOT]",
                    help="tap this IMAGE stream with a publish node; repeatable")
    ap.add_argument("--load", action="append", default=[], type=int, metavar="NODE",
                    help="replace this loader with a Load node; repeatable")
    ap.add_argument("--code", default="auto")
    ap.add_argument("--template", default="", help="the show's convention, to show proposed codes")
    ap.add_argument("--project", default="")
    ap.add_argument("--link", default="")
    a = ap.parse_args(argv)

    wf = load(a.workflow)
    print(report(wf, Path(a.workflow).name, a.template))
    if not a.out:
        return 0

    common = dict(project=a.project, link=a.link)
    nodes = _nodes(wf)
    names = descriptors(wf)
    sinks = {(o, s): k for o, s, _, k in outputs(wf)}
    for spec in a.publish:
        nid, _, slot = spec.partition(":")
        nid, slot = int(nid), int(slot or 0)
        d = names.get((nid, slot)) or descriptor(nodes.get(nid, {}), slot, sinks.get((nid, slot)) or "")
        w = widgets(PUBLISH_WIDGETS, PUBLISH_DEFAULTS, code=a.code, output_name=d, **common)
        new = add_publish(wf, nid, slot, w, title=f"Flow PT Publish — {d}")
        print(f"  + publish node {new} tapping {nid}[{slot}]  output_name={d!r}")
    for lid in a.load:
        new = replace_loader(wf, lid, widgets(LOAD_WIDGETS, LOAD_DEFAULTS, **common))
        print(f"  + load node {new} replacing loader {lid}")
    save(wf, a.out)
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
