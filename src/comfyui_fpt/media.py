"""Reading media back off a Version. probe 021.

Tiers, best quality first, and only the ones a given Version can actually deliver are offered — the
operator picks, because only they know whether the shared root is mounted.

PublishedFiles WERE deliberately not a tier, and the reason is worth keeping rather than deleting.
probe 021: on the one site available, Image, Rendered Image, Texture and USD PublishedFiles carried
no `path` at all, and Version.published_files was filled on 2 of 53 Versions. Unproven, so unbuilt.

What closed it is that this repo now writes them. A publish registers a PublishedFile per file and
the server resolves the path in the 201 itself — `local_path_mac`, `relative_path` and
`path_cache_storage` all filled from one create (recipe 004) — so the tier has real files to read.
They come FIRST: a PublishedFile is the only tier that names a *type*, so "the rendered sequence"
and "the mp4" on one Version are distinguishable, and the only one carrying the colour space the
publisher declared.

The rule that made the design good did not change, and it is what keeps probe 021's finding honest:
a tier is offered only when it can actually deliver. A PublishedFile with no path, or a path on a
root this machine has not mounted, is absent from the picker rather than a run that fails at the end.

Still unproven, and the same shape of gap as before: a path resolved for a platform other than this
one — the only LocalStorage row here defines `mac_path` and leaves the other two null, so
`local_path_windows` and `local_path_linux` read null on every row written (recipe 004) — and a site
whose PublishedFiles were written by a real publisher rather than by this node.
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
AI_FIELDS = [f for f in SUMMARY_FIELDS if f.startswith("sg_ai_")]


def provenance_state(attrs, sources):
    """Whether this Version says how it was made: generated, derived, or unrecorded.

    Deliberately not a yes/no. A Version carrying no AI fields was not necessarily made by a
    human — it may have come from a tool that records nothing, or from ComfyUI without this node, or
    from a camera. Absence is the absence of a *record*, and rendering it as "not AI generated" would
    manufacture exactly the assurance this project exists to make checkable. The same reason there is
    no "approved" concept: we do not invent vocabulary the data cannot support.
    """
    if any(attrs.get(f) not in (None, "", []) for f in AI_FIELDS):
        return "generated"
    return "derived" if sources else "unrecorded"

# Best first. `auto` walks this order and takes the first that resolves. PublishedFiles are not in
# here because they are not a fixed set: a Version has none, one or several, and each is its own
# choice (`sources`). These are the tiers a Version has at most one of.
TIERS = [("frames", "path to frames"), ("movie", "path to movie"),
         ("uploaded", "uploaded media"), ("thumbnail", "thumbnail")]

STILL = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".exr")

# docs/quirks — the field is free text with no validation. printf padding, Shake `#` and `@` all occur
# in the wild, so match several notations; assuming %04d would silently mis-read half of them.
SEQ = re.compile(r"%0?(\d*)d|(#+)|(@+)")

# recipe 004 — a LocalStorage root is per platform and a row may define only one, so the other two
# `local_path_*` read null. Only this machine's key can name a file this machine can open.
LOCAL_PATH = {"darwin": "local_path_mac",
              "win32": "local_path_windows"}.get(sys.platform, "local_path_linux")

# What `sequence.describe_colour` wrote into the description at publish time, read back. Recorded,
# never applied: the value is a claim about the frames, and acting on it would be this project making
# an image (DESIGN). Nothing is inferred and nothing defaults to sRGB — silence stays silence.
COLOUR = re.compile(r"^\s*colour space:\s*([^\n(]+)", re.I | re.M)

# A batch is one float32 RGB tensor, so N frames of W×H cost N·W·H·12 bytes to build and that much
# again on the way to VRAM. The cap is here rather than in torch because an allocator's answer to
# "300 frames of 4K" is a stack trace, and this one is a sentence naming the resolution and the
# count. 4 GiB is ~43 frames of 4K, ~340 of HD: a shot's worth of work at working resolution.
BATCH_BUDGET = 4 * 1024 ** 3
# The widget's own ceiling, so an obvious typo is refused by the editor before anything is read.
MAX_FRAMES = 512


def frame_path(pattern, frame):
    m = SEQ.search(pattern or "")
    if not m:
        return pattern
    width = int(m.group(1) or 0) if m.group(1) is not None else len(m.group(2) or m.group(3))
    return pattern[:m.start()] + str(int(frame)).zfill(width) + pattern[m.end():]


def frame_glob(pattern):
    m = SEQ.search(pattern or "")
    return pattern if not m else pattern[:m.start()] + "*" + pattern[m.end():]


def published_files(fpt, version_id):
    """Every PublishedFile on this Version, flattened to what a picker and a loader need.

    recipe 004 — `path` comes back with the LocalStorage join already done, so nothing here reads
    LocalStorage or reassembles a root. A row whose path this platform has no root for reads null,
    and that is the storage row's configuration, not something a reader can fix.

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
                    # A file whose type this site never labelled is still a file. probe 021 met
                    # exactly this on rows nobody had typed.
                    "type": pft.get("name") or "published file",
                    "colour": m.group(1).strip() if m else ""})
    return out


def version(fpt, version_id):
    r = fpt.get(f"/entity/versions/{int(version_id)}", params={"fields": ",".join(FIELDS)})
    if not r.ok:
        raise FPTError(f"Version {version_id}: {r.status_code} {r.text[:200]}")
    d = r.json()["data"]
    # The second call probe 021 named. Folded in here so `sources` and `load` stay pure functions of
    # one Version dict and no caller has to remember to fetch the files separately.
    return {**d.get("attributes", {}), "id": d["id"],
            "published_files": published_files(fpt, version_id)}


def describe(fpt, version_id, statuses=(), colors=None, icons=None):
    """One Version as structured fields, for the editor to render rather than a wall of text."""
    r = fpt.get(f"/entity/versions/{int(version_id)}",
                params={"fields": ",".join(SUMMARY_FIELDS + ["entity", "sg_task",
                                                             "sg_ai_generated_from"])})
    if not r.ok:
        return {"code": f"Version {version_id}", "error": f"{r.status_code}"}
    d = r.json()["data"]
    a, rel = d.get("attributes", {}), d.get("relationships", {})
    code = a.get("sg_status_list")
    ent = (rel.get("entity") or {}).get("data") or {}
    task = (rel.get("sg_task") or {}).get("data") or {}
    facts = []
    for f in SUMMARY_FIELDS:
        if f in ("code", "sg_status_list", "created_at"):
            continue
        v = a.get(f)
        if v not in (None, "", []):
            facts.append({"label": SUMMARY_LABELS.get(f, f), "value": str(v).replace("\n", " ")[:200]})
    src = (rel.get("sg_ai_generated_from") or {}).get("data") or []
    return {
        "id": d["id"], "code": a.get("code") or str(d["id"]),
        "status": {"code": code, "label": {c: l for l, c in statuses}.get(code, code or ""),
                   "rgb": (colors or {}).get(code), "icon": (icons or {}).get(code)},
        "link": f'{ent.get("type", "")} {ent.get("name", "")}'.strip(),
        "task": task.get("name") or "",
        "facts": facts,
        "provenance": provenance_state(a, src),
        "generated_from": [x.get("name", str(x.get("id"))) for x in src],
    }


def summary(fpt, version_id, statuses=()):
    """A few lines describing one Version: what it is, and what made it.

    Absent fields are omitted rather than shown empty — a site with no provenance fields should see a
    short honest summary, not a column of blanks.
    """
    r = fpt.get(f"/entity/versions/{int(version_id)}",
                params={"fields": ",".join(SUMMARY_FIELDS + ["entity", "sg_task",
                                                             "sg_ai_generated_from"])})
    if not r.ok:
        return f"Version {version_id}: {r.status_code}"
    d = r.json()["data"]
    a, rel = d.get("attributes", {}), d.get("relationships", {})
    # site.statuses yields (label, code); an artist reads "Approved", never "apr" (probe 009).
    label = {c: l for l, c in statuses}.get(a.get("sg_status_list"), a.get("sg_status_list") or "")
    head = f'{a.get("code") or version_id}   {label}'.strip()
    lines = [head]
    ent = (rel.get("entity") or {}).get("data") or {}
    task = (rel.get("sg_task") or {}).get("data") or {}
    where = "  ".join(x for x in (f'{ent.get("type","")} {ent.get("name","")}'.strip(),
                                  f'task {task.get("name")}' if task.get("name") else "") if x)
    if where:
        lines.append(where)
    for f in SUMMARY_FIELDS:
        if f in ("code", "sg_status_list", "created_at"):
            continue
        v = a.get(f)
        if v in (None, "", []):
            continue
        text = str(v).replace("\n", " ")
        lines.append(f'{SUMMARY_LABELS.get(f, f)}: {text[:110]}' + ("…" if len(text) > 110 else ""))
    src = (rel.get("sg_ai_generated_from") or {}).get("data") or []
    if src:
        lines.append("generated from: " + ", ".join(x.get("name", str(x.get("id"))) for x in src))
    if provenance_state(a, src) == "unrecorded":
        lines.append("no generation record: this Version does not say how it was made")
    return "\n".join(lines)


def pf_key(pf):
    """What the `source` combo holds for one PublishedFile.

    The type and the filename, because that is how a person tells "the rendered sequence" from "the
    mp4" on a Version that published both. The id is on the end as the tiebreak and never as the
    label: two publishes of one stream differ by nothing else, but nobody picks by id.

    It is also the stored widget value, so it has to survive a save. A file that is later renamed or
    re-typed no longer matches, and the node says so by name rather than loading the wrong file.
    """
    return f'{pf["type"]} · {os.path.basename(pf["path"])} #{pf["id"]}'


PF_ID = re.compile(r"#(\d+)$")


def pf_of(v, key):
    """The PublishedFile a `source` value names, or None if it names a tier."""
    m = PF_ID.search(str(key or ""))
    if not m:
        return None
    return next((p for p in v.get("published_files") or [] if p["id"] == int(m.group(1))), None)


def colour_of(v, key):
    """The colour space this source declares. "" when nothing was declared — never a guess.

    Only a PublishedFile carries one: `sg_path_to_frames` is a path and an upload is bytes, and
    neither has anywhere to say what the pixels claim to be.
    """
    return (pf_of(v, key) or {}).get("colour", "")


def sources(v):
    """(key, label) for every source this Version can actually deliver, best first.

    A path field that is filled but points at nothing is not a source, and neither is a PublishedFile
    on a root this machine has not mounted — that is the whole reason the operator gets a choice
    rather than a guess.
    """
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
        hits = sorted(glob(frame_glob(path)))
        return f"{len(hits)} frames" if hits else ""
    return "1 file" if os.path.exists(path) else ""


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


def pattern_of(v, key):
    """The frame pattern this source reads one file at a time, or "" if it is a single file.

    A sequence is the only source a batch can be *selected* from: everything else is one blob, and a
    movie's frames come out of decoding it rather than off disk.
    """
    pf = pf_of(v, key)
    pat = pf["path"] if pf else (v.get("sg_path_to_frames") or "" if key == "frames" else "")
    return pat if pat and SEQ.search(pat) else ""


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
        return open(p, "rb").read(), os.path.basename(p)
    if key == "uploaded":
        mv = v["sg_uploaded_movie"]
        return _download(mv["url"]), mv.get("name") or "uploaded"
    if key == "thumbnail":
        return _download(v["image"]), f"{v.get('code') or v['id']}_thumb.jpg"
    raise FPTError(f"unknown source {key!r}")


def _at_frame(pattern, frame):
    """(bytes, filename) for one file of a sequence, or for a path with no frame token at all."""
    path = frame_path(pattern, frame)
    if not os.path.exists(path):
        hits = sorted(glob(frame_glob(pattern or "")))
        if not hits:
            raise FPTError(f"no frames match {pattern!r}")
        path = hits[min(max(int(frame) - 1, 0), len(hits) - 1)]
    return open(path, "rb").read(), os.path.basename(path)


def _download(url):
    """probe 021 — the field value IS a presigned S3 URL, so this is an unauthenticated GET. Sending
    the Flow PT bearer token here would leak it to S3."""
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    return r.content


def load_frames(v, key, start=1, count=1):
    """`count` PIL images from `start`. One item is exactly what a single-frame read always was.

    A clip is why this exists: a sequence PublishedFile that comes back one frame at a time is not an
    input to a video graph, and neither is a movie decoded to its first frame.

    Fewer than `count` come back when the source runs out. A short batch is a fact about the media;
    padding it to the number asked for would be this node inventing frames.
    """
    count = max(int(count), 1)
    pat = pattern_of(v, key)
    if pat:
        hits = sorted(glob(frame_glob(pat)))
        if not hits:
            raise FPTError(f"no frames match {pat!r}")
        # `start` is the first frame of the range, never a repurposed "which one frame": the widget
        # kept its meaning when the count was added beside it.
        first = min(max(int(start) - 1, 0), len(hits) - 1)
        chosen = hits[first:first + count]
        # The budget is checked against what is there, not what was asked for: a 6-frame sequence
        # never has to refuse frame_count 500, and a 500-frame one still does.
        return _stack(_stills(chosen), len(chosen),
                      f"{os.path.basename(pat)} has no frame {start}")
    data, filename = load(v, key, start)
    return _stack(_decode(data, filename, start), count, f"{filename} has no frame {start}")


def _stills(paths):
    from PIL import Image
    for p in paths:
        yield Image.open(p).convert("RGB"), os.path.basename(p)


def _decode(data, filename, start=1):
    """Frames out of one blob: a still is itself, a movie is decoded from `start` to its end."""
    from PIL import Image
    import io

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

    Both checks are here rather than at the tensor, because both have an answer a person can act on
    and neither survives the trip: an allocator's reply to 300 frames of 4K is a stack trace, and
    torch's reply to a size change mid-sequence names two shapes and no filename.
    """
    out = []
    for img, name in frames:
        if not out:
            _budget(img.size, count)
        elif img.size != out[0].size:
            w, h = img.size
            w0, h0 = out[0].size
            raise FPTError(
                f"{name} is {w}×{h} but this batch started {w0}×{h0}: frames of different sizes "
                f"cannot stack into one IMAGE. Load the runs separately, or resize before the batch.")
        out.append(img)
        if len(out) >= count:
            break
    if not out:
        raise FPTError(empty)
    return out


def _budget(size, count):
    w, h = size
    need = w * h * 3 * 4 * int(count)     # float32 RGB, which is what an IMAGE tensor holds
    if need > BATCH_BUDGET:
        fits = max(BATCH_BUDGET // (w * h * 3 * 4), 1)
        raise FPTError(
            f"{count} frames of {w}×{h} is {need / 2 ** 30:.1f} GiB as one IMAGE batch, past the "
            f"{BATCH_BUDGET / 2 ** 30:.0f} GiB this node will build. At this resolution "
            f"frame_count tops out at {fits}; read the rest in a second pass from a later `frame`.")
