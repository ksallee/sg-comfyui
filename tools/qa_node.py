#!/usr/bin/env python3
"""Drive one node in a real ComfyUI, headless, and print only what was asked for.

Why a script and not a browser MCP: an MCP returns an accessibility snapshot and a console log on
every call, which is most of what a UI session costs. Published benchmarks put a ten-step task at
~114k tokens through Playwright MCP against ~27k through a CLI that writes to disk and lets the
agent read only what it needs. This is that shape, narrowed to one job.

    tools/qa_node.py --start --port 8189 --node FPTLoadVersion --drive drive.js --shot out.png

--start launches an isolated ComfyUI: its own port AND its own --user-directory, so two agents never
share settings, workflows or a queue. Without it, an already-running instance on --port is used.

The drive file is the body of an async function receiving ({app, node, wait, $, $$}). Whatever it
returns is printed as JSON. Nothing else is printed, so the agent pays for its own answer only.
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

COMFY = Path(os.environ.get("COMFYUI_PATH", Path.home() / "dev" / "ComfyUI"))
READY = "/object_info/FPTLoadVersion"


def free_port(start):
    for p in range(start, start + 60):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    raise SystemExit("no free port")


def start_comfy(port, vue=True, repo=None):
    """An instance of our own: own port, own custom_nodes, own user directory.

    --base-directory relocates custom_nodes, input, output, temp, user AND models — it resets every
    default path (folder_paths.py:15), which the help text does not say. So models and inputs are
    pointed back at the real tree explicitly; without that an isolated instance sees an empty model
    list and every loader fails validation.

    The isolation is what matters: ComfyUI/custom_nodes/<pack> is a symlink to the MAIN checkout, so
    without a base directory every instance loads main's code and an agent verifies someone else's
    work instead of its own.
    """
    base = Path(tempfile.mkdtemp(prefix=f"comfyqa-{port}-"))
    repo = Path(repo or Path(__file__).resolve().parents[1])
    (base / "custom_nodes").mkdir(parents=True, exist_ok=True)
    (base / "custom_nodes" / repo.name).symlink_to(repo)
    userdir = base / "user"
    (userdir / "default").mkdir(parents=True, exist_ok=True)
    # Nodes 2.0 is opt-in and per user directory, so a fresh one starts with it off. The onboarding
    # keys matter as much: without them the first run opens the Templates browser over the canvas,
    # and every selector below is querying a node nobody can see.
    (userdir / "default" / "comfy.settings.json").write_text(json.dumps({
        "Comfy.VueNodes.Enabled": bool(vue),
        "Comfy.TutorialCompleted": True,
        "Comfy.OnboardingCoachmarks.Seen": True,
    }))
    proc = subprocess.Popen(
        [str(COMFY / "venv" / "bin" / "python"), "main.py", "--port", str(port),
         "--disable-auto-launch", "--base-directory", str(base),
         # base-directory took these with it; the weights and plates live in the real tree.
         "--models-directory", str(COMFY / "models"),
         "--input-directory", str(COMFY / "input")],
        cwd=COMFY, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc, base


def wait_ready(port, timeout=180):
    import urllib.request
    for _ in range(timeout):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}{READY}", timeout=3).read()
            return True
        except Exception:
            time.sleep(1)
    return False


BOOT = """async ({node_type, drive}) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  // The graph exists before the node definitions are registered, so wait for the type itself.
  for (let i = 0; i < 240; i++) {
    try {
      if (window.comfyAPI?.app?.app?.graph &&
          (!node_type || window.LiteGraph?.registered_node_types?.[node_type])) break;
    } catch (e) {}
    await wait(250);
  }
  const app = window.comfyAPI.app.app;
  // ComfyUI loads its default workflow asynchronously after the graph exists. Clearing before that
  // lands means it drops its default on top of the node under test — the drive script sees the
  // right thing and the screenshot shows someone else's graph.
  for (let i = 0; i < 40; i++) { if (app.graph._nodes?.length) break; await wait(250); }
  await wait(500);
  app.graph.clear();
  let node = null;
  if (node_type) {
    node = window.LiteGraph.createNode(node_type);
    if (!node) return {error: `node type not registered: ${node_type}`};
    node.pos = [60, 60];
    app.graph.add(node);
  }
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => [...document.querySelectorAll(s)];
  const fn = new Function("ctx", `return (async () => { const {app, node, wait, $, $$} = ctx; ${drive} })()`);
  return await fn({app, node, wait, $, $$});
}"""


USAGE_SOURCE = "comfyui-fpt qa_node.py"


def _identify(route):
    """Say who queued the prompt, in the body, on the way out.

    `comfy_usage_source` is not an environment variable: it is `extra_data.comfy_usage_source` on
    whatever POSTed `/prompt` (execution.py:224), and it is the field a Version later uses to explain
    a missing workflow. The frontend hardcodes `"comfyui-frontend"` in the body, and the server reads
    the `Comfy-Usage-Source` header only when the body omits the key (server.py:1120) — so a run
    driven from here would claim to be a person clicking Run unless the body itself is corrected.
    """
    r = route.request
    if r.method != "POST" or not r.post_data:
        return route.continue_()
    try:
        body = json.loads(r.post_data)
        body.setdefault("extra_data", {})["comfy_usage_source"] = USAGE_SOURCE
    except Exception:
        return route.continue_()
    route.continue_(post_data=json.dumps(body))


def main():
    ap = argparse.ArgumentParser(prog="qa_node.py", description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8188)
    ap.add_argument("--start", action="store_true", help="launch an isolated ComfyUI on --port")
    ap.add_argument("--node", default="", help="node type to place before driving")
    ap.add_argument("--drive", default="", help="file with the async body to run; - for stdin")
    ap.add_argument("--shot", default="", help="write a screenshot here")
    ap.add_argument("--video", default="", help="record the session to this .webm")
    ap.add_argument("--viewport", default="1100x950",
                    help="browser size WxH; a recording wants a fixed aspect, not a crop")
    ap.add_argument("--repo", default="", help="checkout to load as the node pack (default: this one)")
    ap.add_argument("--keep", action="store_true", help="leave the instance running")
    # The notice a node draws when Nodes 2.0 is off is a thing to look at, so it has to be reachable
    # from here; the setting is per user directory, which only --start owns.
    ap.add_argument("--no-vue", action="store_true", help="start with Comfy.VueNodes.Enabled false")
    a = ap.parse_args()

    proc = userdir = None
    port = a.port
    if a.start:
        port = free_port(a.port)
        proc, userdir = start_comfy(port, vue=not a.no_vue, repo=a.repo)
        if not wait_ready(port):
            print(json.dumps({"error": f"ComfyUI did not come up on {port}"}))
            proc.terminate()
            return 1

    drive = ""
    if a.drive:
        drive = sys.stdin.read() if a.drive == "-" else Path(a.drive).read_text()

    if a.video:
        Path(a.video).parent.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright
    out = {}
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            # Video is a context setting, not a page one, and the file is only finalised when the
            # context closes — so the path is read back after, never before.
            vw, vh = (int(x) for x in a.viewport.lower().split("x"))
            ctx = b.new_context(viewport={"width": vw, "height": vh},
                                **({"record_video_dir": str(Path(a.video).parent),
                                    "record_video_size": {"width": vw, "height": vh}}
                                   if a.video else {}))
            pg = ctx.new_page()
            # ComfyUI asks "leave site?" whenever the graph is dirty; nothing here needs saving.
            pg.on("dialog", lambda d: d.accept())
            pg.route("**/prompt", _identify)
            pg.goto(f"http://127.0.0.1:{port}/", wait_until="domcontentloaded")
            out = pg.evaluate(BOOT, {"node_type": a.node, "drive": drive or "return {};"})
            if a.shot:
                Path(a.shot).parent.mkdir(parents=True, exist_ok=True)
                pg.screenshot(path=a.shot)
            src = pg.video.path() if a.video else None
            ctx.close()          # flushes the video
            b.close()
            if src:
                Path(src).replace(a.video)
                out["video"] = a.video
    finally:
        if proc and not a.keep:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except Exception:
                proc.kill()
            shutil.rmtree(userdir, ignore_errors=True)
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
