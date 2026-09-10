#!/usr/bin/env python3
"""Record one drive against an isolated ComfyUI and encode it as MP4, WebM and animated WebP.

    tools/capture.py --drive tools/drive_clip_01_publish_pick.js --out ~/Desktop/clips/01_pick \\
                     --node SGPublishVersion --repo ~/dev/sg-comfyui

Writes `<out>.mp4`, `<out>.webm` and `<out>.webp`, then removes the frames. The instance is started
and stopped here, so two clips do not share settings, a queue or a publish.

Requires ffmpeg on PATH, and playwright:

    uv run --with playwright --python 3.11 python tools/capture.py --drive ... --out ...
"""
import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_node                                                    # noqa: E402

KIT = Path(__file__).resolve().parent / "clip_kit.js"

# The page is captured at twice its CSS size: Playwright's own recorder is too soft for UI text.
# MP4 and WebM are encoded above the CSS size. The WebP loop is smaller.
WIDTH = 1600
WEBP_WIDTH = 800
WEBP_FPS = 8


def encode(frames, out, fps):
    """Encode the three files from the concat list `qa_node.Screencast` wrote beside the frames."""
    listing = ["-f", "concat", "-safe", "0", "-i", str(frames / "frames.txt")]
    scale = f"scale={WIDTH}:-2:flags=lanczos"
    runs = [
        # yuv420p and even dimensions, or Safari and the social players refuse the file.
        # faststart puts the index first, so the file plays before it has downloaded.
        (f"{out}.mp4", ["-vf", f"{scale},format=yuv420p", "-r", str(fps),
                        "-c:v", "libx264", "-crf", "20", "-preset", "slow",
                        "-movflags", "+faststart"]),
        (f"{out}.webm", ["-vf", f"{scale},format=yuv420p", "-r", str(fps),
                         "-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0", "-row-mt", "1"]),
        (f"{out}.webp", ["-vf", f"scale={WEBP_WIDTH}:-2:flags=lanczos", "-r", str(WEBP_FPS),
                         "-c:v", "libwebp", "-q:v", "62", "-compression_level", "6", "-loop", "0", "-an"]),
    ]
    sizes = {}
    for path, args in runs:
        r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                            *listing, *args, path], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"ffmpeg failed for {path}: {r.stderr.strip()[:400]}")
        sizes[Path(path).suffix.lstrip(".")] = Path(path).stat().st_size
    return sizes


def main():
    ap = argparse.ArgumentParser(prog="capture.py", description=__doc__.split("\n")[0])
    ap.add_argument("--drive", required=True, help="the clip's drive file")
    ap.add_argument("--out", required=True, help="path without an extension")
    ap.add_argument("--node", default="", help="node type to place before driving")
    ap.add_argument("--repo", default="", help="checkout to load as the node pack")
    ap.add_argument("--prelude", default="", help="JS prepended to the drive, after the kit")
    ap.add_argument("--port", type=int, default=0,
                    help="0 picks a random high port")
    ap.add_argument("--fps", type=float, default=12)
    ap.add_argument("--scale", type=float, default=2)
    ap.add_argument("--viewport", default="1100x950")
    ap.add_argument("--keep-frames", action="store_true", help="leave the PNGs beside the clip")
    a = ap.parse_args()

    out = Path(a.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    frames = Path(tempfile.mkdtemp(prefix="clipframes-"))
    drive = "\n".join([KIT.read_text(), a.prelude, Path(a.drive).read_text()])

    proc, base, port = qa_node.launch(a.port, repo=a.repo)
    try:
        args = argparse.Namespace(node=a.node, shot="", video="", frames=str(frames),
                                  fps=a.fps, scale=a.scale, viewport=a.viewport)
        result = asyncio.run(qa_node.session(port, args, drive))
    finally:
        qa_node.stop_comfy(proc, base)

    cast = result.get("screencast") or {}
    if not cast.get("frames"):
        raise SystemExit(f"nothing was captured: {json.dumps(result, default=str)[:400]}")
    result["files"] = encode(frames, out, a.fps)
    if a.keep_frames:
        result["frames_dir"] = str(frames)
    else:
        shutil.rmtree(frames, ignore_errors=True)
    print(json.dumps(result, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
