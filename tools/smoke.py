#!/usr/bin/env python3
"""Load each shipped workflow in a real ComfyUI and check its widget values survive the round trip.

    tools/smoke.py                 # the workflows in tools/workflows/
    tools/smoke.py --port 8999     # a port nothing else is running on

Requires playwright, which ComfyUI's venv does not have:

    uv run --with playwright --python 3.11 python tools/smoke.py --port 8999

Add `--with sg-groundtruth` where the interpreter running this does not have it. Without it the node
pack fails to import and each graph reports no SG node instead of failing.

`widgets_values` is positional, and loading a saved graph in a real ComfyUI is what shows a value
that has shifted into the widget next door.

Exit status is the number of workflows that failed.
"""
import argparse
import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

sys.path.insert(0, str(HERE))   # run as a file, so its directory is not on the path yet
import qa_node                                                              # noqa: E402

# `filters` is a mirror: the node fills it from the site with the filter the other widgets add up
# to, so the stored value is a starting point and not a value to restore.
MIRRORED = {"filters"}

# The only input types ComfyUI draws as a widget. Everything else is a socket and takes no slot in
# widgets_values.
WIDGET_TYPES = {"INT", "FLOAT", "STRING", "BOOLEAN", "COMBO"}

DRIVE = """
const graph = %s;
await app.loadGraphData(graph);
await wait(6000);
const want = %s;
const out = [];
for (const [nodeId, values] of Object.entries(want)) {
  const n = app.graph._nodes.find((x) => String(x.id) === String(nodeId));
  if (!n) { out.push({node: nodeId, error: "node not in the loaded graph"}); continue; }
  const bad = [];
  for (const [name, expected] of Object.entries(values)) {
    const w = n.widgets.find((x) => x.name === name);
    const got = w ? w.value : undefined;
    // A project saved as "(none)" is no choice, and the picker resolves it to the project under
    // Settings on load (sg_entity_picker.selectProject). That is a resolution, not a shift.
    if (name === "project" && expected === "(none)" && got && got !== "(none)") continue;
    if (String(got) !== String(expected)) bad.push({widget: name, expected, got});
  }
  out.push({node: `${n.type}#${nodeId}`, checked: Object.keys(values).length, bad});
}
return out;
"""


def declared(node_type, port):
    """The widget names this class declares, in the order widgets_values is written in.

    Read from the running server rather than from the class: importing the nodes imports torch,
    which the interpreter running playwright does not have, and /object_info is the same INPUT_TYPES.
    """
    url = f"http://127.0.0.1:{port}/object_info/{node_type}"
    spec = json.load(urllib.request.urlopen(url, timeout=60))[node_type]["input"]
    names = []
    for section in ("required", "optional"):
        for name, v in (spec.get(section) or {}).items():
            kind = v[0] if v else None
            # An allowlist, not a denylist: a denylist counts a new socket type as a widget, which
            # reports the one-slot displacement this tool looks for against every graph at once. A
            # combo declares its choices in place of a type name, so a list is a widget.
            if isinstance(kind, list) or kind in WIDGET_TYPES:
                names.append(name)
    return names


def expected(graph, port):
    """({node id: {widget: value}}, [misalignment]) read out of a saved graph by position.

    Keyed by node id, not node type: one graph can have three publish nodes, and keying by type
    compares the first against the last one's stored values.
    """
    want, misaligned = {}, []
    for n in graph.get("nodes", []):
        t = n.get("type", "")
        if not t.startswith("SG"):
            continue
        vals = n.get("widgets_values") or []
        names = declared(t, port)
        # A count that does not match the class means each value from the divergence on loads into
        # the wrong widget. That is the failure, not a reason to skip the graph.
        if len(vals) != len(names):
            misaligned.append(f"{t}#{n.get('id')}: file has {len(vals)} values, class declares"
                              f" {len(names)} — every value from the divergence on lands in the"
                              f" wrong widget")
            continue
        want[str(n.get("id"))] = {k: v for k, v in zip(names, vals) if k not in MIRRORED}
    return want, misaligned


def check(path, port, workdir):
    """Load one workflow in the running instance and print the result. True where it failed."""
    graph = json.loads(path.read_text())
    want, misaligned = expected(graph, port)
    if misaligned:
        print(f"  {path.name:26s} FAIL")
        for m in misaligned:
            print(f"      {m}")
        return True
    if not want:
        print(f"  {path.name:26s} no SG node in this graph")
        return False

    drive = workdir / "drive.js"
    drive.write_text(DRIVE % (json.dumps(graph), json.dumps(want)))
    out = subprocess.run([sys.executable, str(HERE / "qa_node.py"),
                          "--port", str(port), "--drive", str(drive)],
                         capture_output=True, text=True)
    try:
        rows = json.loads(out.stdout)
    except json.JSONDecodeError:
        print(f"  {path.name:26s} HARNESS FAILED\n{out.stdout[-400:]}{out.stderr[-400:]}")
        return True
    bad = [r for r in rows if r.get("error") or r.get("bad")]
    if not bad:
        n = sum(r.get("checked", 0) for r in rows)
        print(f"  {path.name:26s} ok ({n} widgets over {len(rows)} node(s))")
        return False
    print(f"  {path.name:26s} FAIL")
    for r in bad:
        for b in r.get("bad", []):
            print(f"      {r['node']}.{b['widget']}: file has {b['expected']!r},"
                  f" loaded as {b['got']!r}")
        if r.get("error"):
            print(f"      {r['node']}: {r['error']}")
    return True


def main():
    ap = argparse.ArgumentParser(prog="smoke.py", description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8999)
    ap.add_argument("--dir", default=str(HERE / "workflows"))
    a = ap.parse_args()

    files = sorted(Path(a.dir).glob("*.json"))
    if not files:
        print(f"no workflows in {a.dir}")
        return 0

    try:
        proc, base, port = qa_node.launch(a.port, repo=REPO)
    except RuntimeError as e:
        print(e)
        return 1
    try:
        with tempfile.TemporaryDirectory(prefix="smoke-") as tmp:
            failed = sum(check(f, port, Path(tmp)) for f in files)
    finally:
        qa_node.stop_comfy(proc, base)
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
