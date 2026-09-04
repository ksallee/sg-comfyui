#!/usr/bin/env python3
"""Load every shipped workflow in a real ComfyUI and check it survives the round trip.

Three bugs shipped in one day behind passing assertions, and every one of them needed a saved graph
to be *loaded* before it showed: widget values displaced by the DOM pickers, a version number that
collided because a frame suffix hid it from its own convention, and a preview that under-reported
lineage. Node inspection caught none of them. This does the one thing that did.

    tools/smoke.py                 # every workflow in workflows/
    tools/smoke.py --port 8999     # somewhere nothing else is running

Exit status is the number of workflows that failed, so it works in a pipeline.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

# Keyed by node id, not node type: publish_passes carries three FPTPublishVersion nodes and keying
# by type compared the first against the last one's stored values.
#
# `filters` is excluded on purpose. It is a live mirror — the node fills it from the site with the
# filter the other widgets add up to — so the stored value is a starting point, not a thing to
# restore. Comparing it reports a mismatch every time the mirror works.
MIRRORED = {"filters"}

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
    if (String(got) !== String(expected)) bad.push({widget: name, expected, got});
  }
  out.push({node: `${n.type}#${nodeId}`, checked: Object.keys(values).length, bad});
}
return out;
"""


def declared(node_type, port):
    """The widget names this class declares, in order — the order widgets_values is written in.

    Asked of the running server rather than the class: importing the nodes drags in torch, which the
    interpreter holding playwright does not have, and /object_info is the same INPUT_TYPES anyway.
    """
    import urllib.request
    url = f"http://127.0.0.1:{port}/object_info/{node_type}"
    spec = json.load(urllib.request.urlopen(url, timeout=60))[node_type]["input"]
    names = []
    for section in ("required", "optional"):
        for name, v in (spec.get(section) or {}).items():
            kind = v[0] if v else None
            if kind in ("IMAGE", "LATENT", "MODEL", "CLIP", "VAE", "CONDITIONING"):
                continue     # a socket, never a widget, so it takes no slot in widgets_values
            names.append(name)
    return names


def main():
    ap = argparse.ArgumentParser(prog="smoke.py", description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8999)
    ap.add_argument("--dir", default=str(REPO / "workflows"))
    a = ap.parse_args()

    files = sorted(Path(a.dir).glob("*.json"))
    if not files:
        print(f"no workflows in {a.dir}")
        return 0

    sys.path.insert(0, str(HERE))
    import qa_node
    port = qa_node.free_port(a.port)
    proc, base = qa_node.start_comfy(port, repo=REPO)
    if not qa_node.wait_ready(port):
        print(f"ComfyUI did not come up on {port}")
        proc.terminate()
        return 1
    failed = 0
    for f in files:
        graph = json.loads(f.read_text())
        want, skipped = {}, []
        # Read the expected values straight out of the file, by position, using the class's own
        # declared order — the same mapping the frontend must reproduce on load.
        for n in graph.get("nodes", []):
            t = n.get("type", "")
            if not t.startswith("FPT"):
                continue
            vals = n.get("widgets_values") or []
            names = declared(t, port)
            if len(vals) != len(names):
                skipped.append(f"{t}: file has {len(vals)} values, class declares {len(names)}")
                continue
            pairs = {k: v for k, v in zip(names, vals) if k not in MIRRORED}
            want[str(n.get("id"))] = pairs
        if not want:
            print(f"  {f.name:26s} no FPT node to check" + (f"  [{'; '.join(skipped)}]" if skipped else ""))
            continue

        drive = DRIVE % (json.dumps(graph), json.dumps(want))
        tmp = Path("/tmp/smoke_drive.js")
        tmp.write_text(drive)
        out = subprocess.run([sys.executable, str(HERE / "qa_node.py"),
                              "--port", str(port), "--drive", str(tmp)],
                             capture_output=True, text=True)
        try:
            rows = json.loads(out.stdout)
        except Exception:
            print(f"  {f.name:26s} HARNESS FAILED\n{out.stdout[-400:]}{out.stderr[-400:]}")
            failed += 1
            continue
        bad = [r for r in rows if r.get("error") or r.get("bad")]
        if bad:
            failed += 1
            print(f"  {f.name:26s} FAIL")
            for r in bad:
                for b in r.get("bad", []):
                    print(f"      {r['node']}.{b['widget']}: file has {b['expected']!r},"
                          f" loaded as {b['got']!r}")
                if r.get("error"):
                    print(f"      {r['node']}: {r['error']}")
        else:
            n = sum(r.get("checked", 0) for r in rows)
            print(f"  {f.name:26s} ok ({n} widgets over {len(rows)} node(s))")
        if skipped:
            print(f"      note: {'; '.join(skipped)}")
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except Exception:
        proc.kill()
    shutil.rmtree(base, ignore_errors=True)
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
