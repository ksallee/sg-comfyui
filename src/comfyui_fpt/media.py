"""Reading media back off a Version. probe 021.

Three tiers, best quality first, and only the ones a given Version can actually deliver are offered —
the operator picks, because only they know whether the shared root is mounted.

PublishedFiles are deliberately NOT a tier yet. probe 021: on the one site available, Image, Rendered
Image, Texture and USD PublishedFiles carry no `path` at all, and Version.published_files is filled on
2 of 53 Versions. Unproven, so unbuilt. The finding says what would close it.
"""
import os
import re
from glob import glob

import requests

from . import _deps  # noqa: F401
from fpt_llm_api.client import FPTError

FIELDS = ["code", "image", "sg_uploaded_movie", "sg_path_to_movie", "sg_path_to_frames",
          "sg_first_frame", "sg_last_frame"]

# Best first. `auto` walks this order and takes the first that resolves.
TIERS = [("frames", "path to frames"), ("movie", "path to movie"),
         ("uploaded", "uploaded media"), ("thumbnail", "thumbnail")]

STILL = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".exr")

# docs/quirks — the field is free text with no validation. printf padding, Shake `#` and `@` all occur
# in the wild, so match several notations; assuming %04d would silently mis-read half of them.
SEQ = re.compile(r"%0?(\d*)d|(#+)|(@+)")


def frame_path(pattern, frame):
    m = SEQ.search(pattern or "")
    if not m:
        return pattern
    width = int(m.group(1) or 0) if m.group(1) is not None else len(m.group(2) or m.group(3))
    return pattern[:m.start()] + str(int(frame)).zfill(width) + pattern[m.end():]


def frame_glob(pattern):
    m = SEQ.search(pattern or "")
    return pattern if not m else pattern[:m.start()] + "*" + pattern[m.end():]


def version(fpt, version_id):
    r = fpt.get(f"/entity/versions/{int(version_id)}", params={"fields": ",".join(FIELDS)})
    if not r.ok:
        raise FPTError(f"Version {version_id}: {r.status_code} {r.text[:200]}")
    d = r.json()["data"]
    return {**d.get("attributes", {}), "id": d["id"]}


def sources(v):
    """(key, label) for every tier this Version can actually deliver, best first.

    A path field that is filled but points at nothing is not a source — that is the whole reason the
    operator gets a choice rather than a guess.
    """
    out = []
    for key, label in TIERS:
        detail = _resolve(v, key)
        if detail:
            out.append((key, f"{label} — {detail}"))
    return out


def _resolve(v, key):
    """A short human description of what this tier would deliver, or "" if it would deliver nothing."""
    if key == "frames":
        pat = v.get("sg_path_to_frames")
        hits = sorted(glob(frame_glob(pat))) if pat else []
        return f"{len(hits)} frames" if hits else ""
    if key == "movie":
        p = v.get("sg_path_to_movie")
        return os.path.basename(p) if p and os.path.exists(p) else ""
    if key == "uploaded":
        mv = v.get("sg_uploaded_movie")
        return (mv or {}).get("name", "uploaded") if isinstance(mv, dict) and mv.get("url") else ""
    if key == "thumbnail":
        # probe 013 — a transcode still in flight serves a placeholder from this path, not the media.
        img = v.get("image")
        return "thumbnail" if isinstance(img, str) and "/images/status/transient/" not in img else ""
    return ""


def load(v, key, frame=1):
    """(bytes, filename) for one tier. Raises with the reason rather than returning something wrong."""
    if key == "frames":
        pat = v.get("sg_path_to_frames")
        path = frame_path(pat, frame)
        if not os.path.exists(path):
            hits = sorted(glob(frame_glob(pat)))
            if not hits:
                raise FPTError(f"no frames match {pat!r}")
            path = hits[min(max(int(frame) - 1, 0), len(hits) - 1)]
        return open(path, "rb").read(), os.path.basename(path)
    if key == "movie":
        p = v["sg_path_to_movie"]
        return open(p, "rb").read(), os.path.basename(p)
    if key == "uploaded":
        mv = v["sg_uploaded_movie"]
        return _download(mv["url"]), mv.get("name") or "uploaded"
    if key == "thumbnail":
        return _download(v["image"]), f"{v.get('code') or v['id']}_thumb.jpg"
    raise FPTError(f"unknown source {key!r}")


def _download(url):
    """probe 021 — the field value IS a presigned S3 URL, so this is an unauthenticated GET. Sending
    the Flow PT bearer token here would leak it to S3."""
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    return r.content


def to_image(data, filename, frame=1):
    """PIL image from whatever the tier returned. A movie is decoded to one frame."""
    from PIL import Image
    import io

    if filename.lower().endswith(STILL):
        return Image.open(io.BytesIO(data)).convert("RGB")
    try:
        import av   # ships with ComfyUI for its video nodes; see DESIGN
    except ImportError:
        raise FPTError(f"{filename} is not a still and PyAV is not installed to decode it")
    with av.open(io.BytesIO(data)) as container:
        stream = container.streams.video[0]
        for i, got in enumerate(container.decode(stream), start=1):
            if i >= int(frame):
                return got.to_image().convert("RGB")
    raise FPTError(f"{filename} has no frame {frame}")
