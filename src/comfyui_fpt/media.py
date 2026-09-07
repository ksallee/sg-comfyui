"""Reading media back off a Version: which sources it can deliver, and the frames themselves.

probe 021. A source is offered only when it resolves to a file this machine can open — a
PublishedFile with no path, or a path on a root this machine has not mounted, is absent from the
picker rather than a run that fails at the end.

PublishedFiles come first, because a PublishedFile is the only source that names a *type* (so "the
rendered sequence" and "the mp4" on one Version are distinguishable) and the only one carrying the
colour space the publisher declared. The fixed tiers follow, best quality first.
"""
import os
import re
import sys
from glob import glob

import requests

from sg_groundtruth.client import FPTError

FIELDS = ["code", "image", "sg_uploaded_movie", "sg_path_to_movie", "sg_path_to_frames",
          "sg_first_frame", "sg_last_frame"]

# Provenance the publish node writes (fields.py). Shown on the Load node so an artist can see what
# they are building on before they run anything.
SUMMARY_FIELDS = ["code", "description", "sg_status_list", "created_at", "sg_ai_generator",
                  "sg_ai_model", "sg_ai_prompt", "sg_ai_seed", "sg_ai_sampler", "sg_ai_steps",
                  "sg_ai_cfg"]
SUMMARY_LABELS = {"sg_ai_generator": "made by", "sg_ai_model": "model", "sg_ai_prompt": "prompt",
                  "sg_ai_seed": "seed", "sg_ai_sampler": "sampler", "sg_ai_steps": "steps",
                  "sg_ai_cfg": "cfg", "description": "note"}
# The header carries code, status and date; everything else is a listed fact.
DETAIL_FIELDS = [f for f in SUMMARY_FIELDS if f not in ("code", "sg_status_list", "created_at")]
AI_FIELDS = [f for f in SUMMARY_FIELDS if f.startswith("sg_ai_")]
RELATED_FIELDS = ["entity", "sg_task", "sg_ai_generated_from"]

# Best first. `auto` walks this order and takes the first that resolves. PublishedFiles are not here
# because they are not a fixed set: a Version has none, one or several, and each is its own choice
# (`sources`). These are the tiers a Version has at most one of.
TIERS = [("frames", "path to frames"), ("movie", "path to movie"),
         ("uploaded", "uploaded media"), ("thumbnail", "thumbnail")]

STILL = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".exr")

# docs/quirks — the frame-pattern field is free text with no validation, and printf padding, Shake
# `#` and `@` all occur in the wild. Assuming `%04d` would silently mis-read half of them.
SEQ = re.compile(r"%0?(\d*)d|(#+)|(@+)")

# recipe 004 — a LocalStorage root is per platform and a row may define only one, so the other two
# `local_path_*` read null. Only this machine's key can name a file this machine can open.
LOCAL_PATH = {"darwin": "local_path_mac",
              "win32": "local_path_windows"}.get(sys.platform, "local_path_linux")

# What `sequence.describe_colour` wrote into the description at publish time, read back. Recorded,
# never applied: the value is a claim about the frames, and acting on it would be this project
# making an image (DESIGN). Nothing is inferred and nothing defaults to sRGB.
COLOUR = re.compile(r"^\s*colour space:\s*([^\n(]+)", re.I | re.M)

# A batch is one float32 RGB tensor, so N frames of W×H cost N·W·H·12 bytes to build and that much
# again on the way to VRAM. The cap is here rather than in torch because an allocator's answer to
# "300 frames of 4K" is a stack trace and this one is a sentence naming the resolution and the
# count. 4 GiB is 43 frames of 4K, 172 of HD.
BATCH_BUDGET = 4 * 1024 ** 3
# The widget's own ceiling, so an obvious typo is refused by the editor before anything is read.
MAX_FRAMES = 512

PF_ID = re.compile(r"#(\d+)$")


# --- frame patterns ------------------------------------------------------------------------------

def frame_path(pattern, frame):
    """The pattern with its frame token replaced by one frame number, zero-padded to the token."""
    m = SEQ.search(pattern or "")
    if not m:
        return pattern
    width = int(m.group(1) or 0) if m.group(1) is not None else len(m.group(2) or m.group(3))
    return pattern[:m.start()] + str(int(frame)).zfill(width) + pattern[m.end():]


def frame_glob(pattern):
    """The pattern with its frame token replaced by `*`."""
    m = SEQ.search(pattern or "")
    return pattern if not m else pattern[:m.start()] + "*" + pattern[m.end():]


def frame_numbers(pattern):
    """(number, path) for every file of a sequence, in frame order.

    The numbers come off disk, not from `sg_first_frame`/`sg_last_frame`: those are a claim a
    publisher made once and nothing keeps them true, and a plate is 1001-based far more often than
    1-based, so the difference between the two is a wrong frame.
    """
    m = SEQ.search(pattern or "")
    if not m:
        return []
    # `\d+` rather than the token's own width: a sequence that runs past its padding (`.9999.png`,
    # `.10000.png`) is still that sequence, and reading 4 digits would drop the frames needing 5.
    rx = re.compile(re.escape(pattern[:m.start()]) + r"(\d+)" + re.escape(pattern[m.end():]) + r"$")
    return sorted((int(hit.group(1)), p) for p in glob(frame_glob(pattern))
                  if (hit := rx.match(p)))


def frame_range(v, key):
    """(first, last, count) of the sequence this source reads, or None when it is not a sequence.

    For the panel, so `frame` is a number the operator can see rather than one they guess at.
    """
    nums = frame_numbers(pattern_of(v, key))
    return (nums[0][0], nums[-1][0], len(nums)) if nums else None


def _frames_on_disk(pattern):
    """"N frames" for a sequence pattern that matches files, "" when it matches none."""
    hits = glob(frame_glob(pattern)) if pattern else []
    return f"{len(hits)} frames" if hits else ""


# --- one Version ---------------------------------------------------------------------------------

def published_files(fpt, version_id):
    """Every PublishedFile on this Version, flattened to what a picker and a loader need.

    recipe 004 — `path` comes back with the LocalStorage join already done, so nothing here reads
    LocalStorage or reassembles a root. A row whose path this platform has no root for reads null,
    which is the storage row's configuration and not something a reader can fix.

    Never raises: a Version whose files cannot be read must still offer its path fields and its
    upload, the same way an unreachable site still lets a graph open.
    """
    from .site import ARRAY_JSON
    try:
        r = fpt.post("/entity/published_files/_search", headers=ARRAY_JSON, json={
            "filters": [["version", "is", {"type": "Version", "id": int(version_id)}]],
            "fields": ["path", "description", "published_file_type"], "page": {"size": 200}})
        if not r.ok:
            return []
        rows = r.json().get("data", [])
    except Exception:
        return []
    out = []
    for d in rows:
        a = d.get("attributes") or {}
        pft = ((d.get("relationships") or {}).get("published_file_type") or {}).get("data") or {}
        m = COLOUR.search(a.get("description") or "")
        out.append({"id": d["id"], "path": (a.get("path") or {}).get(LOCAL_PATH) or "",
                    # A file whose type this site never labelled is still a file (probe 021).
                    "type": pft.get("name") or "published file",
                    "colour": m.group(1).strip() if m else ""})
    return out


def version(fpt, version_id):
    """One Version's media fields plus its PublishedFiles.

    The files are folded in here (the second call probe 021 named) so `sources` and `load` stay pure
    functions of one dict and no caller has to remember to fetch them separately.
    """
    r = fpt.get(f"/entity/versions/{int(version_id)}", params={"fields": ",".join(FIELDS)})
    if not r.ok:
        raise FPTError(f"Version {version_id}: {r.status_code} {r.text[:200]}")
    d = r.json()["data"]
    return {**d.get("attributes", {}), "id": d["id"],
            "published_files": published_files(fpt, version_id)}


def provenance_state(attrs, sources):
    """Whether this Version says how it was made: "generated", "derived" or "unrecorded".

    Deliberately not a yes/no. A Version carrying no AI fields may have come from a tool that
    records nothing, from ComfyUI without this node, or from a camera, so absence is the absence of
    a *record*; rendering it as "not AI generated" would manufacture the assurance this project
    exists to make checkable.
    """
    if any(attrs.get(f) not in (None, "", []) for f in AI_FIELDS):
        return "generated"
    return "derived" if sources else "unrecorded"


def describe(fpt, version_id, statuses=(), colors=None, icons=None):
    """One Version as structured fields, for the editor to render rather than a wall of text.

    Absent fields are omitted rather than shown empty: a site with no provenance fields gets a short
    honest summary, not a column of blanks.
    """
    r = fpt.get(f"/entity/versions/{int(version_id)}",
                params={"fields": ",".join(SUMMARY_FIELDS + RELATED_FIELDS)})
    if not r.ok:
        return {"code": f"Version {version_id}", "error": f"{r.status_code}"}
    d = r.json()["data"]
    a, rel = d.get("attributes", {}), d.get("relationships", {})
    code = a.get("sg_status_list")
    ent = (rel.get("entity") or {}).get("data") or {}
    task = (rel.get("sg_task") or {}).get("data") or {}
    src = (rel.get("sg_ai_generated_from") or {}).get("data") or []
    facts = [{"label": SUMMARY_LABELS.get(f, f), "value": str(a[f]).replace("\n", " ")[:200]}
             for f in DETAIL_FIELDS if a.get(f) not in (None, "", [])]
    return {
        "id": d["id"], "code": a.get("code") or str(d["id"]),
        # site.statuses yields (label, code); an artist reads "Approved", never "apr" (probe 009).
        "status": {"code": code, "label": {c: l for l, c in statuses}.get(code, code or ""),
                   "rgb": (colors or {}).get(code), "icon": (icons or {}).get(code)},
        "link": f'{ent.get("type", "")} {ent.get("name", "")}'.strip(),
        "task": task.get("name") or "",
        "facts": facts,
        "provenance": provenance_state(a, src),
        "generated_from": [x.get("name", str(x.get("id"))) for x in src],
    }


# --- choosing a source ---------------------------------------------------------------------------

def pf_key(pf):
    """What the `source` combo holds for one PublishedFile: type, filename, then id.

    The type and the filename are how a person tells "the rendered sequence" from "the mp4" on a
    Version that published both; the id is the tiebreak two publishes of one stream differ by, and
    never the label. It is also the stored widget value, so a file later renamed or re-typed stops
    matching and the node says so by name rather than loading the wrong file.
    """
    return f'{pf["type"]} · {os.path.basename(pf["path"])} #{pf["id"]}'


def pf_of(v, key):
    """The PublishedFile a `source` value names, or None if it names a tier."""
    m = PF_ID.search(str(key or ""))
    if not m:
        return None
    return next((p for p in v.get("published_files") or [] if p["id"] == int(m.group(1))), None)


def colour_of(v, key):
    """The colour space this source declares, or "" when nothing was declared — never a guess.

    Only a PublishedFile carries one: `sg_path_to_frames` is a path and an upload is bytes, and
    neither has anywhere to say what the pixels claim to be.
    """
    return (pf_of(v, key) or {}).get("colour", "")


def sources(v):
    """(key, label) for every source this Version can actually deliver, best first."""
    out = []
    for pf in v.get("published_files") or []:
        detail = _pf_detail(pf)
        if detail:
            out.append((pf_key(pf), f'{pf["type"]} — {os.path.basename(pf["path"])}, {detail}'))
    for key, label in TIERS:
        detail = _resolve(v, key)
        if detail:
            out.append((key, f"{label} — {detail}"))
    return out


def _pf_detail(pf):
    """What one PublishedFile would deliver, or "" if it would deliver nothing here."""
    path = pf.get("path") or ""
    if not path:
        return ""            # probe 021 — a PublishedFile need not carry a path at all
    if SEQ.search(path):
        return _frames_on_disk(path)
    return "1 file" if os.path.exists(path) else ""


def _resolve(v, key):
    """A short description of what one tier would deliver, or "" if it would deliver nothing."""
    if key == "frames":
        return _frames_on_disk(v.get("sg_path_to_frames"))
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


def pattern_of(v, key):
    """The frame pattern this source reads one file at a time, or "" if it is a single file.

    A sequence is the only source a batch can be *selected* from: everything else is one blob, and a
    movie's frames come out of decoding it rather than off disk.
    """
    pf = pf_of(v, key)
    pat = pf["path"] if pf else (v.get("sg_path_to_frames") or "" if key == "frames" else "")
    return pat if pat and SEQ.search(pat) else ""


# --- reading it ----------------------------------------------------------------------------------

def load(v, key, frame=1):
    """(bytes, filename) for one source. Raises with the reason rather than returning something wrong."""
    pf = pf_of(v, key)
    if pf:
        if not pf["path"]:
            raise FPTError(f'PublishedFile {pf["id"]} has no path on this platform ({LOCAL_PATH})')
        return _at_frame(pf["path"], frame)
    if key == "frames":
        return _at_frame(v.get("sg_path_to_frames"), frame)
    if key == "movie":
        p = v["sg_path_to_movie"]
        return _read(p), os.path.basename(p)
    if key == "uploaded":
        mv = v["sg_uploaded_movie"]
        return _download(mv["url"]), mv.get("name") or "uploaded"
    if key == "thumbnail":
        return _download(v["image"]), f"{v.get('code') or v['id']}_thumb.jpg"
    raise FPTError(f"unknown source {key!r}")


def _read(path):
    with open(path, "rb") as fh:
        return fh.read()


def _at_frame(pattern, frame):
    """(bytes, filename) for one file of a sequence, or for a path with no frame token at all.

    `frame` is the number in the filename. A frame the sequence does not have is refused with the
    range it does have: returning a different frame than the one asked for is the failure this node
    exists to make impossible.
    """
    path = frame_path(pattern, frame)
    if os.path.exists(path):
        return _read(path), os.path.basename(path)
    nums = frame_numbers(pattern)
    if not nums:
        raise FPTError(f"no frames match {pattern!r}")
    raise FPTError(f"{os.path.basename(pattern)} has no frame {frame}. It runs "
                   f"{nums[0][0]}-{nums[-1][0]}, {len(nums)} frames.")


def _download(url):
    """probe 021 — the field value IS a presigned S3 URL, so this is an unauthenticated GET.
    Sending the Flow PT bearer token here would leak it to S3."""
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    return r.content


def load_frames(v, key, start=0, count=1):
    """`count` PIL images from frame `start`. One item is exactly what a single-frame read returns.

    `start` is the frame NUMBER — the one in the filename and the one Flow PT shows — not a position
    in the list. `start` 0 is the first frame the source actually has, and `count` 0 is every frame
    from there to the end.

    Fewer than `count` come back when the source runs out: a short batch is a fact about the media,
    and padding it to the number asked for would be this node inventing frames.
    """
    count, start = int(count), int(start)
    pat = pattern_of(v, key)
    if pat:
        nums = frame_numbers(pat)
        if not nums:
            raise FPTError(f"no frames match {pat!r}")
        first = nums[0][0] if start <= 0 else start
        at = next((i for i, (n, _) in enumerate(nums) if n == first), None)
        if at is None:
            raise FPTError(
                f"{os.path.basename(pat)} has no frame {first}. It runs {nums[0][0]}-{nums[-1][0]}, "
                f"{len(nums)} frames. `frame` is the number in the filename, not a position in the "
                f"list, and 0 starts at whatever the sequence itself starts at.")
        chosen = [path for _, path in (nums[at:] if count <= 0 else nums[at:at + count])]
        # The budget is checked against what is there, not what was asked for: a 6-frame sequence
        # never has to refuse frame_count 500, and a 500-frame one still does.
        return _stack(_stills(chosen), len(chosen),
                      f"{os.path.basename(pat)} has no frame {first}")
    # Not a sequence: one blob, and a movie's frames come out of decoding it. A container carries no
    # frame numbers, so here `start` counts decoded frames from 1 and 0 means the same as 1.
    at = max(start, 1)
    data, filename = load(v, key, at)
    return _stack(_decode(data, filename, at), count, f"{filename} has no frame {at}")


def _stills(paths):
    from PIL import Image
    for p in paths:
        yield Image.open(p).convert("RGB"), os.path.basename(p)


def _decode(data, filename, start=1):
    """Frames out of one blob: a still is itself, a movie is decoded from `start` to its end."""
    import io

    from PIL import Image

    if filename.lower().endswith(STILL):
        yield Image.open(io.BytesIO(data)).convert("RGB"), filename
        return
    try:
        import av   # ships with ComfyUI for its video nodes; see DESIGN
    except ImportError:
        raise FPTError(f"{filename} is not a still and PyAV is not installed to decode it")
    with av.open(io.BytesIO(data)) as container:
        stream = container.streams.video[0]
        for i, got in enumerate(container.decode(stream), start=1):
            if i >= int(start):
                yield got.to_image().convert("RGB"), f"{filename} frame {i}"


def _stack(frames, count, empty):
    """The frames that will become one IMAGE batch, refused before torch has to refuse them.

    Both checks are here rather than at the tensor because both have an answer a person can act on
    and neither survives the trip: an allocator's reply to 300 frames of 4K is a stack trace, and
    torch's reply to a size change mid-sequence names two shapes and no filename.
    """
    out = []
    for img, name in frames:
        if not out:
            _budget(img.size, max(count, 1))
        elif img.size != out[0].size:
            w, h = img.size
            w0, h0 = out[0].size
            raise FPTError(
                f"{name} is {w}×{h} but this batch started {w0}×{h0}: frames of different sizes "
                f"cannot stack into one IMAGE. Load the runs separately, or resize before the batch.")
        out.append(img)
        # `count` 0 is "everything there is". A sequence knows how many that is before it reads
        # anything and arrives here with a real number; a movie does not, so the budget is checked
        # against what has accumulated.
        if count <= 0:
            _budget(out[0].size, len(out))
        elif len(out) >= count:
            break
    if not out:
        raise FPTError(empty)
    return out


def _budget(size, count):
    """Refuse a batch past BATCH_BUDGET, naming the resolution and how many frames do fit at it."""
    w, h = size
    need = w * h * 3 * 4 * int(count)     # float32 RGB, which is what an IMAGE tensor holds
    if need > BATCH_BUDGET:
        fits = max(BATCH_BUDGET // (w * h * 3 * 4), 1)
        raise FPTError(
            f"{count} frames of {w}×{h} is {need / 2 ** 30:.1f} GiB as one IMAGE batch, past the "
            f"{BATCH_BUDGET / 2 ** 30:.0f} GiB this node will build. At this resolution "
            f"frame_count tops out at {fits}; read the rest in a second pass from a later `frame`.")
