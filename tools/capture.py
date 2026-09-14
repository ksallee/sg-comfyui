#!/usr/bin/env python3
"""Record one drive against an isolated ComfyUI and encode it as MP4, WebM and animated WebP.

    tools/capture.py --drive tools/drive_clip_01_publish_pick.js --out ~/Desktop/clips/01_pick \\
                     --node SGPublishVersion --repo ~/dev/sg-comfyui

Writes `<out>.mp4`, `<out>.webm` and `<out>.webp`, then removes the frames. The instance is started
and stopped here, so two clips do not share settings, a queue or a publish.

Re-encode a clip whose frames are gone, with the same hold cap:

    tools/capture.py --tighten ~/Desktop/clips/01_pick.mp4 --out ~/Desktop/clips/01_pick

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
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_node                                                    # noqa: E402

KIT = Path(__file__).resolve().parent / "clip_kit.js"

# The page is captured at twice its CSS size: Playwright's own recorder is too soft for UI text.
# MP4 and WebM are encoded above the CSS size. The WebP loop is smaller.
WIDTH = 1600
WEBP_WIDTH = 800
WEBP_FPS = 8

# A drive waits on the site, on a queue and on the editor settling, and the recorder keeps one frame
# for the length of that wait. HOLD is the longest such wait left in the clip.
HOLD = 0.8
# freezedetect's noise ceiling and the shortest stretch it reports.
QUIET = "-60dB"
FLOOR = 0.3


def ffmpeg(args, label):
    """Run ffmpeg, and exit naming `label` when it fails."""
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"ffmpeg failed for {label}: {r.stderr.strip()[:400]}")


def encode(source, out, fps, pre=""):
    """Encode the three files from `source`, the ffmpeg input arguments, with `pre` filtered first."""
    lead = f"{pre}," if pre else ""
    scale = f"scale={WIDTH}:-2:flags=lanczos"
    runs = [
        # yuv420p and even dimensions, or Safari and the social players refuse the file.
        # faststart puts the index first, so the file plays before it has downloaded.
        (f"{out}.mp4", ["-vf", f"{lead}{scale},format=yuv420p", "-r", str(fps),
                        "-c:v", "libx264", "-crf", "20", "-preset", "slow",
                        "-movflags", "+faststart"]),
        (f"{out}.webm", ["-vf", f"{lead}{scale},format=yuv420p", "-r", str(fps),
                         "-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0", "-row-mt", "1"]),
        (f"{out}.webp", ["-vf", f"{lead}scale={WEBP_WIDTH}:-2:flags=lanczos", "-r", str(WEBP_FPS),
                         "-c:v", "libwebp", "-q:v", "62", "-compression_level", "6",
                         "-loop", "0", "-an"]),
    ]
    sizes = {}
    for path, args in runs:
        ffmpeg([*source, *args, path], path)
        sizes[Path(path).suffix.lstrip(".")] = Path(path).stat().st_size
    return sizes


def cap_listing(frames, cap=HOLD):
    """Cap every duration in the concat list at `cap` seconds. Returns the seconds before and after."""
    listing = frames / "frames.txt"
    before = after = 0.0
    lines = []
    for line in listing.read_text().splitlines():
        if line.startswith("duration "):
            held = float(line.split()[1])
            before += held
            after += min(held, cap)
            lines.append(f"duration {min(held, cap):.3f}")
        else:
            lines.append(line)
    listing.write_text("\n".join(lines) + "\n")
    return round(before, 2), round(after, 2)


def probe(video, entries):
    """One ffprobe field of `video`, as text."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", entries, "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"ffprobe failed for {video}: {r.stderr.strip()[:400]}")
    return r.stdout.strip().rstrip(",")


def freezes(video):
    """Stretches of `video` where the picture does not change, as (start, end) seconds."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video),
                        "-vf", f"freezedetect=n={QUIET}:d={FLOOR}", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    spans, start = [], None
    for line in r.stderr.splitlines():
        if "freeze_start" in line:
            start = float(line.rsplit(":", 1)[1])
        elif "freeze_end" in line and start is not None:
            spans.append((start, float(line.rsplit(":", 1)[1])))
            start = None
    if start is not None:
        spans.append((start, float(probe(video, "format=duration"))))
    return spans


def cap_video(video, cap=HOLD):
    """A `select` chain dropping each freeze past `cap`, with the seconds before and after it."""
    rate = float(Fraction(probe(video, "stream=r_frame_rate")))     # ffprobe writes "12/1"
    before = float(probe(video, "format=duration"))
    spans = [(s, e) for s, e in freezes(video) if e - s > cap]
    # freeze_end is the frame that changed. Half a frame short of it keeps that frame.
    drop = [(s + cap, e - 0.5 / rate) for s, e in spans]
    drop = [(a, b) for a, b in drop if b > a]
    cut = sum(b - a for a, b in drop)
    if not drop:
        return "", round(before, 2), round(before, 2)
    gate = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in drop)
    return f"select='not({gate})',setpts=N/FRAME_RATE/TB", round(before, 2), round(before - cut, 2)


def retighten(video, out, fps, cap=HOLD):
    """Re-encode `video` and its two companions with every hold capped at `cap` seconds."""
    pre, before, after = cap_video(video, cap)
    # x264 cannot read the file it is writing, so the three encodes read a copy.
    work = Path(tempfile.mkdtemp(prefix="clipsource-"))
    copy = work / video.name
    shutil.copy2(video, copy)
    try:
        files = encode(["-i", str(copy)], out, fps, pre)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return {"seconds": {"before": before, "after": after}, "files": files}


def record(a, out):
    """Drive an isolated ComfyUI, cap the holds in what it recorded, and encode the three files."""
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

    before, after = cap_listing(frames, a.hold)
    result["seconds"] = {"before": before, "after": after}
    result["files"] = encode(["-f", "concat", "-safe", "0", "-i", str(frames / "frames.txt")],
                             out, a.fps)
    if a.keep_frames:
        result["frames_dir"] = str(frames)
    else:
        shutil.rmtree(frames, ignore_errors=True)
    return result


def main():
    ap = argparse.ArgumentParser(prog="capture.py", description=__doc__.split("\n")[0])
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument("--drive", help="the clip's drive file")
    source.add_argument("--tighten", help="an encoded clip to re-encode with its holds capped")
    ap.add_argument("--out", required=True, help="path without an extension")
    ap.add_argument("--node", default="", help="node type to place before driving")
    ap.add_argument("--repo", default="", help="checkout to load as the node pack")
    ap.add_argument("--prelude", default="", help="JS prepended to the drive, after the kit")
    ap.add_argument("--port", type=int, default=0,
                    help="0 picks a random high port")
    ap.add_argument("--fps", type=float, default=12)
    ap.add_argument("--scale", type=float, default=2)
    ap.add_argument("--viewport", default="1100x950")
    ap.add_argument("--hold", type=float, default=HOLD,
                    help="seconds one unchanging picture stays on screen")
    ap.add_argument("--keep-frames", action="store_true", help="leave the PNGs beside the clip")
    a = ap.parse_args()

    out = Path(a.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)

    if a.tighten:
        result = retighten(Path(a.tighten).expanduser(), out, a.fps, a.hold)
    else:
        result = record(a, out)

    print(json.dumps(result, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
