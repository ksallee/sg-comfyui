#!/usr/bin/env python3
"""Drive one node in a headless ComfyUI and print what the drive returns.

    tools/qa_node.py --start --port 8189 --node SGLoadVersion --drive drive.js --shot out.png

--start launches an isolated ComfyUI with its own port and its own --user-directory, so two agents
do not share settings, workflows or a queue. Without it, the instance already running on --port is
used.

The drive file is the body of an async function receiving ({app, node, wait, $, $$}). Its return
value is printed as JSON, and nothing else is printed.

--frames writes the session as numbered PNGs plus `frames.txt`, an ffmpeg concat list with the
measured time between frames. `tools/capture.py` drives, encodes and cleans up in one command.

Requires playwright, which ComfyUI's venv does not have:

    uv run --with playwright --python 3.11 python tools/qa_node.py --start --node SGLoadVersion
"""
import argparse
import asyncio
import atexit
import base64
import json
import os
import random
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

COMFY = Path(os.environ.get("COMFYUI_PATH", Path.home() / "dev" / "ComfyUI"))
READY = "/object_info/SGLoadVersion"
BASE_PREFIX = "comfyqa-"

# The instances this process started and has not stopped.
# An exit path that skips the teardown leaves a ComfyUI holding a port and a temp tree until the
# machine is restarted. The teardown runs from `finally`, from atexit and from a signal, and each of
# those may run twice.
_running = []


def free_port(start):
    for p in range(start, start + 60):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    raise SystemExit("no free port")


def holder(port):
    """The pid listening on `port`, or 0."""
    r = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
                       capture_output=True, text=True)
    pids = [int(x) for x in r.stdout.split() if x.strip().isdigit()]
    return pids[0] if pids else 0


def pack_name(repo):
    """`[project].name` from the checkout's pyproject.toml."""
    import tomllib
    with open(repo / "pyproject.toml", "rb") as fh:
        return tomllib.load(fh)["project"]["name"]


def start_comfy(port, vue=True, repo=None):
    """Start ComfyUI with its own port, custom_nodes and user directory.

    ComfyUI/custom_nodes/<pack> is a symlink to the main checkout, so without a base directory of
    its own the instance loads that checkout's code instead of `repo`.

    --base-directory resets all the default paths (folder_paths.py:15): custom_nodes, input, output,
    temp, user and models. Models and inputs are pointed back at the real tree, or the instance has
    an empty model list and the loaders fail validation.
    """
    base = Path(tempfile.mkdtemp(prefix=f"{BASE_PREFIX}{port}-"))
    repo = Path(repo or Path(__file__).resolve().parents[1])
    (base / "custom_nodes").mkdir(parents=True, exist_ok=True)
    # The Templates browser and the node footer show this directory name, so it is the Registry
    # name from pyproject rather than the checkout's own name.
    (base / "custom_nodes" / pack_name(repo)).symlink_to(repo)
    userdir = base / "user"
    (userdir / "default").mkdir(parents=True, exist_ok=True)
    # Nodes 2.0 is opt-in per user directory, so a fresh one starts with it off. Without the
    # onboarding keys the first run opens the Templates browser over the canvas, and the selectors
    # below then query a node that is not on screen.
    (userdir / "default" / "comfy.settings.json").write_text(json.dumps({
        "Comfy.VueNodes.Enabled": bool(vue),
        "Comfy.TutorialCompleted": True,
        "Comfy.OnboardingCoachmarks.Seen": True,
    }))
    proc = subprocess.Popen(
        [str(COMFY / "venv" / "bin" / "python"), "main.py", "--port", str(port),
         "--disable-auto-launch", "--base-directory", str(base),
         # --base-directory moved these too. The models and the inputs are in the real tree.
         "--models-directory", str(COMFY / "models"),
         "--input-directory", str(COMFY / "input")],
        cwd=COMFY, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        # Its own process group, so the teardown reaches the processes ComfyUI spawned.
        start_new_session=True)
    _running.append((proc, base))
    return proc, base


def wait_ready(port, timeout=180):
    for _ in range(timeout):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}{READY}", timeout=3).read()
            return True
        except Exception:
            time.sleep(1)
    return False


def launch(port=0, vue=True, repo=None):
    """Start an isolated ComfyUI and return (proc, base, port). `port` 0 picks a random high one.

    A free port stays free only until another harness binds it. Two harnesses starting at once both
    see the port unused, the second fails to bind and exits, and the ready check then reads the first
    instance. The pid listening is compared against the pid just spawned, and a port taken by another
    process is given up.

    Raises RuntimeError, with the instance torn down, if it does not become ready.
    """
    port = port or random.randint(8600, 9400)
    for _ in range(6):
        port = free_port(port)
        proc, base = start_comfy(port, vue=vue, repo=repo)
        if wait_ready(port) and holder(port) == proc.pid:
            return proc, base, port
        stop_comfy(proc, base)
        port += 1
    raise RuntimeError(f"ComfyUI did not come up on a port of its own at or above {port}")


def stop_comfy(proc, base):
    """Terminate the instance and its process group, then remove its base directory."""
    if (proc, base) in _running:
        _running.remove((proc, base))
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (OSError, ProcessLookupError):
        proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (OSError, ProcessLookupError):
            proc.kill()
    shutil.rmtree(base, ignore_errors=True)


def stop_all():
    for proc, base in list(_running):
        stop_comfy(proc, base)


atexit.register(stop_all)


def _on_signal(sig, frame):
    raise SystemExit(128 + sig)


for _sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    signal.signal(_sig, _on_signal)


# Two evaluations, not one. The node definitions, the default workflow ComfyUI loads over them and
# the node placement all complete before a capture starts, so a clip opens on the graph under test
# rather than on ComfyUI's template.
PREPARE = """async ({node_type}) => {
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
  // lands drops its default on top of the node under test.
  for (let i = 0; i < 40; i++) { if (app.graph._nodes?.length) break; await wait(250); }
  await wait(500);
  // The minimap sits over the bottom-right of every capture and is not a seeded setting.
  // The frame counter sits over the bottom-left and is drawn on the canvas, where CSS cannot reach it.
  if (!document.getElementById("sg-qa-style")) {
    const st = document.createElement("style"); st.id = "sg-qa-style";
    st.textContent = ".minimap-main-container { display: none !important; }";
    document.head.appendChild(st);
  }
  app.canvas.show_info = false;
  app.graph.clear();
  window.__sg = {node: null};
  if (node_type) {
    const node = window.LiteGraph.createNode(node_type);
    if (!node) return {error: `node type not registered: ${node_type}`};
    node.pos = [60, 60];
    app.graph.add(node);
    window.__sg.node = node;
  }
  await wait(400);
  return {};
}"""

DRIVE = """async ({drive}) => {
  const app = window.comfyAPI.app.app;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const node = window.__sg?.node || null;
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => [...document.querySelectorAll(s)];
  const fn = new Function("ctx", `return (async () => { const {app, node, wait, $, $$} = ctx; ${drive} })()`);
  return await fn({app, node, wait, $, $$});
}"""


USAGE_SOURCE = "sg-comfyui qa_node.py"


async def _identify(route):
    """Name this harness as the submitting client in the body of each /prompt.

    `comfy_usage_source` is `extra_data.comfy_usage_source` on whatever POSTed `/prompt`
    (execution.py:224), not an environment variable, and a Version uses it to explain a missing
    workflow. The frontend writes `"comfyui-frontend"` into the body, and the server reads the
    `Comfy-Usage-Source` header only where the body omits the key (server.py:1120), so a run driven
    from here is recorded as a person pressing Run unless the body sets the field.
    """
    r = route.request
    if r.method != "POST" or not r.post_data:
        return await route.continue_()
    try:
        body = json.loads(r.post_data)
        body.setdefault("extra_data", {})["comfy_usage_source"] = USAGE_SOURCE
    except Exception:
        return await route.continue_()
    await route.continue_(post_data=json.dumps(body))


TAIL = 1.2          # seconds the last frame of a clip is held


class Screencast:
    """A CDP screencast into `directory`: numbered PNGs and an ffmpeg concat list of durations.

    CDP emits a frame when the page paints, not on a clock, so a settled canvas emits nothing for
    seconds at a time. `fps` is a ceiling on the frames kept. `frames.txt` records how long each one
    was on screen, which is what makes an encode play at the speed it was driven.
    """

    def __init__(self, directory, fps):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.gap = 1.0 / fps
        self.times = []
        self.n = 0
        self.acks = set()

    async def start(self, page):
        self.cdp = await page.context.new_cdp_session(page)
        self.cdp.on("Page.screencastFrame", self._frame)
        await self.cdp.send("Page.startScreencast", {"format": "png", "everyNthFrame": 1})

    def _frame(self, params):
        # Acknowledge each frame, kept or not. The page sends the next one only after the ack.
        task = asyncio.ensure_future(
            self.cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]}))
        self.acks.add(task)
        task.add_done_callback(self.acks.discard)
        ts = params.get("metadata", {}).get("timestamp") or time.time()
        if self.times and ts - self.times[-1] < self.gap:
            return
        self.n += 1
        (self.dir / f"{self.n:06d}.png").write_bytes(base64.b64decode(params["data"]))
        self.times.append(ts)

    async def stop(self):
        await self.cdp.send("Page.stopScreencast")
        await asyncio.sleep(0.2)
        lines = []
        for i, t in enumerate(self.times):
            nxt = self.times[i + 1] if i + 1 < len(self.times) else t + TAIL
            lines.append(f"file '{i + 1:06d}.png'\nduration {max(nxt - t, 1e-3):.3f}")
        if self.times:
            lines.append(f"file '{len(self.times):06d}.png'")   # concat applies the last duration
        (self.dir / "frames.txt").write_text("\n".join(lines) + "\n")
        return {"frames": self.n, "seconds": round(self.times[-1] - self.times[0] + TAIL, 2)
                if self.times else 0}


async def session(port, a, drive):
    """Open a browser on `port`, run `drive`, and take the captures `a` asks for."""
    from playwright.async_api import async_playwright
    out = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        # Video is a context setting, not a page one, and the file is finalised when the context
        # closes, so it is moved into place after the close.
        vw, vh = (int(x) for x in a.viewport.lower().split("x"))
        ctx = await b.new_context(viewport={"width": vw, "height": vh},
                                  device_scale_factor=a.scale,
                                  **({"record_video_dir": str(Path(a.video).parent),
                                      "record_video_size": {"width": vw, "height": vh}}
                                     if a.video else {}))
        pg = await ctx.new_page()
        # ComfyUI asks "leave site?" while the graph is dirty. Nothing here is saved.
        pg.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
        await pg.route("**/prompt", _identify)
        await pg.goto(f"http://127.0.0.1:{port}/", wait_until="domcontentloaded")
        out = await pg.evaluate(PREPARE, {"node_type": a.node})
        cast = None
        if not out.get("error") and a.frames:
            cast = Screencast(a.frames, a.fps)
            await cast.start(pg)
        if not out.get("error"):
            out = await pg.evaluate(DRIVE, {"drive": drive or "return {};"})
        if cast:
            out["screencast"] = await cast.stop()
        if a.shot:
            Path(a.shot).parent.mkdir(parents=True, exist_ok=True)
            await pg.screenshot(path=a.shot)
        src = await pg.video.path() if a.video else None
        await ctx.close()          # flushes the video
        await b.close()
        if src:
            Path(src).replace(a.video)
            out["video"] = a.video
    return out


def main():
    ap = argparse.ArgumentParser(prog="qa_node.py", description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=0,
                    help="8188 by default, or a random high port with --start")
    ap.add_argument("--start", action="store_true", help="launch an isolated ComfyUI on --port")
    ap.add_argument("--node", default="", help="node type to place before driving")
    ap.add_argument("--drive", default="", help="file with the async body to run; - for stdin")
    ap.add_argument("--shot", default="", help="write a screenshot here")
    ap.add_argument("--video", default="", help="record the session to this .webm")
    ap.add_argument("--frames", default="", help="write the session here as PNGs and frames.txt")
    ap.add_argument("--fps", type=float, default=12, help="frames a second --frames keeps, at most")
    ap.add_argument("--scale", type=float, default=1,
                    help="device pixel ratio; 2 keeps UI text readable")
    ap.add_argument("--viewport", default="1100x950",
                    help="browser size WxH; a recording needs a fixed aspect ratio")
    ap.add_argument("--repo", default="", help="checkout to load as the node pack (default: this one)")
    ap.add_argument("--keep", action="store_true", help="leave the instance running")
    # The setting is per user directory, which only --start owns.
    ap.add_argument("--no-vue", action="store_true", help="start with Comfy.VueNodes.Enabled false")
    a = ap.parse_args()

    proc = base = None
    port = a.port or 8188
    if a.start:
        try:
            proc, base, port = launch(a.port, vue=not a.no_vue, repo=a.repo)
        except RuntimeError as e:
            print(json.dumps({"error": str(e)}))
            return 1

    out = {}
    try:
        drive = ""
        if a.drive:
            drive = sys.stdin.read() if a.drive == "-" else Path(a.drive).read_text()
        if a.video:
            Path(a.video).parent.mkdir(parents=True, exist_ok=True)
        out = asyncio.run(session(port, a, drive))
    finally:
        if proc and not a.keep:
            stop_comfy(proc, base)
    if proc and a.keep:
        # --keep hands the instance on. The port it got is rarely the port asked for, so a second
        # drive is told which one to use. A drive pointed at the port asked for would reach whatever
        # else is listening there and read that server's state.
        _running.remove((proc, base))
        out["port"] = port
        out["base"] = str(base)
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
