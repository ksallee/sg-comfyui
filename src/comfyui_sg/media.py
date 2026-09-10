"""Reading media back off a Version: which sources it can deliver, and the frames themselves.

A source is offered only when it resolves to a file this machine can open (probe 021). A
PublishedFile with no path, or a path on a root this machine has not mounted, is absent from the
picker.

PublishedFiles come first. A PublishedFile is the only source that names a type, which tells "the
rendered sequence" from "the mp4" on one Version, and the only one with the colour space the
publisher declared. The fixed tiers follow, best quality first.
"""
import io
import os
import re
import sys
from glob import glob

import requests

from sg_groundtruth.client import FPTError

from . import fields

FIELDS = ["code", "image", "sg_uploaded_movie", "sg_path_to_movie", "sg_path_to_frames",
          "sg_first_frame", "sg_last_frame", "sg_uploaded_movie_frame_rate"]

# When no clip exists anywhere, the frames are wrapped at this rate and the log says so.
DEFAULT_FPS = 24

# Provenance the publish node writes (fields.py), shown on the Load node before a run.
SUMMARY_FIELDS = ["code", "description", "sg_status_list", "created_at", "sg_ai_generator",
                  "sg_ai_model", "sg_ai_prompt", "sg_ai_seed", "sg_ai_sampler", "sg_ai_steps",
                  "sg_ai_cfg"]
SUMMARY_LABELS = {"sg_ai_generator": "made by", "sg_ai_model": "model", "sg_ai_prompt": "prompt",
                  "sg_ai_seed": "seed", "sg_ai_sampler": "sampler", "sg_ai_steps": "steps",
                  "sg_ai_cfg": "cfg", "description": "note"}
# The header shows code, status and date. Everything else is a listed fact.
DETAIL_FIELDS = [f for f in SUMMARY_FIELDS if f not in ("code", "sg_status_list", "created_at")]
# A site without the nine fields records the same facts in the description
# (publish_version._description): the note, a blank line, then one `label: value` line per fact, in
# the labels fields.py writes. Read back here, so a Load reads what a publish recorded.
FACT_LABELS = set(fields.CONCEPT_LABELS.values())
FACT_LINE = re.compile(r"\s*([^:\n]+?)\s*:\s*(.*)$")
LINEAGE_LABEL = fields.CONCEPT_LABELS["generated_from"]
AI_FIELDS = [f for f in SUMMARY_FIELDS if f.startswith("sg_ai_")]
RELATED_FIELDS = ["entity", "sg_task", "sg_ai_generated_from"]

# Best first. `auto` reads this order and takes the first that resolves. These are the tiers a
# Version has at most one of. PublishedFiles are not a fixed set, so they are not here: a Version
# has none, one or several, and each is its own choice (`sources`).
TIERS = [("frames", "path to frames"), ("movie", "path to movie"),
         ("uploaded", "uploaded media"), ("thumbnail", "thumbnail")]

STILL = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".exr")

# The frame-pattern field is free text with no validation. printf padding, Shake `#` and `@` all
# occur.
SEQ = re.compile(r"%0?(\d*)d|(#+)|(@+)")

# recipe 004. A LocalStorage root is per platform and a row may define only one, so the other two
# `local_path_*` read null. Only this machine's key can name a file this machine can open.
LOCAL_PATH = {"darwin": "local_path_mac",
              "win32": "local_path_windows"}.get(sys.platform, "local_path_linux")

# What `sequence.describe_colour` wrote into the description at publish time, read back. Recorded,
# never applied. Nothing is inferred and nothing defaults to sRGB.
COLOUR = re.compile(r"^\s*colour space:\s*([^\n(]+)", re.I | re.M)

# A batch is one float32 RGB tensor, so N frames of W×H cost N·W·H·12 bytes to build and that much
# again on the way to VRAM. The cap is here rather than in torch: an allocator answers "300 frames
# of 4K" with a stack trace, and this answers with a sentence naming the resolution and the count.
#
# `batch_budget_gib` in profile.local.json sets the number per machine, and this is the fallback.
# At 4 GiB a batch fits 43 frames of UHD or 172 of HD, short of a shot at 4K. A workstation should
# raise it.
DEFAULT_BUDGET_GIB = 4
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

    The numbers come off disk, not from `sg_first_frame`/`sg_last_frame`, which are a claim a
    publisher made once. A plate is more often 1001-based than 1-based, so the difference is a
    wrong frame.
    """
    m = SEQ.search(pattern or "")
    if not m:
        return []
    # `\d+` rather than the token's own width. A sequence that runs past its padding (`.9999.png`,
    # `.10000.png`) is still that sequence, and reading 4 digits drops the frames needing 5.
    rx = re.compile(re.escape(pattern[:m.start()]) + r"(\d+)" + re.escape(pattern[m.end():]) + r"$")
    return sorted((int(hit.group(1)), p) for p in glob(frame_glob(pattern))
                  if (hit := rx.match(p)))


def frame_range(v, key):
    """(first, last, count) of what this source reads, or None where nothing on disk answers.

    For the panel, so `frame` is a number the operator can read rather than guess. A sequence is
    numbered by its filenames. A movie is numbered from 1, and its length comes off the container
    header, which is one file open and no decode.
    """
    nums = frame_numbers(pattern_of(v, key))
    if nums:
        return (nums[0][0], nums[-1][0], len(nums))
    if kind_of(v, key) == "movie":
        h = _header(_first_file(v, key))
        if h and h["frames"]:
            return (1, h["frames"], h["frames"])
    return None


def frame_size(v, key):
    """(width, height) of this source's first frame, or None where nothing on disk answers.

    Only a sequence answers. A movie's size needs the container opened, which the panel does not do.
    """
    nums = frame_numbers(pattern_of(v, key))
    h = _header(nums[0][1]) if nums else None
    return (h["width"], h["height"]) if h else None


def _header(source):
    """What a file's container header says, or None when it will not open.

    `source` is a path on this machine, or the bytes of a file already fetched. PyAV parses the
    header and stops, so this costs an open rather than a decode.
    """
    import av

    if not source:
        return None
    path = source if isinstance(source, str) else ""
    try:
        with av.open(io.BytesIO(source) if isinstance(source, bytes) else source) as container:
            s = container.streams.video[0]
            fmt = s.format
            comps = list(fmt.components) if fmt else []
            return {"container": (os.path.splitext(path)[1].lstrip(".")
                                  or container.format.name).upper(),
                    "width": s.width, "height": s.height,
                    "bits": max((c.bits for c in comps), default=8),
                    "float": "f32" in (fmt.name if fmt else ""),
                    "channels": len(comps),
                    "alpha": any(c.is_alpha for c in comps),
                    "frames": int(s.frames or 0)}
    except Exception:
        return None


CHANNELS = {1: "greyscale", 3: "RGB", 4: "RGBA"}


def describe_format(v, key):
    """What this source is, in one line: "16-bit PNG, RGBA, 1920x1080, 48 frames."

    Read off the first file's container header, so a sequence costs one file open and nothing is
    decoded. The declared colour space follows as its own sentence when the publisher recorded one.
    """
    line = _format_line(v, key)
    colour = colour_of(v, key)
    return line + (f" Colour space declared {colour}." if line and colour else "")


def _format_line(v, key):
    """The format half of `describe_format`, before the colour space is said."""
    if key == "thumbnail":
        return _thumbnail_format(v)
    pf = pf_of(v, key)
    if pf and pf["link"] == "upload":
        return _upload_format(pf["name"], pf.get("content_type"))
    if key == "uploaded":
        mv = v.get("sg_uploaded_movie") or {}
        return _upload_format(mv.get("name"), mv.get("content_type"))
    nums = frame_numbers(pattern_of(v, key))
    h = _header(nums[0][1] if nums else _first_file(v, key))
    if not h:
        return ""
    # A still image container reports no frame count of its own, and one file is one frame.
    count = len(nums) or h["frames"] or (1 if kind_of(v, key) == "still" else 0)
    parts = [f'{h["bits"]}-bit float {h["container"]}' if h["float"]
             else f'{h["bits"]}-bit {h["container"]}',
             CHANNELS.get(h["channels"], f'{h["channels"]} channels'),
             f'{h["width"]}x{h["height"]}']
    if count:
        parts.append(f"{count} frames" if count > 1 else "1 frame")
    return ", ".join(parts) + "."


def _thumbnail_format(v):
    """The thumbnail's line, which says that it is a preview rather than the media.

    A thumbnail is small enough to fetch for its header; nothing else here is.
    """
    size = ""
    try:
        h = _header(_download(v["image"])) if v.get("image") else None
        size = f', {h["width"]}x{h["height"]}' if h else ""
    except Exception:
        size = ""
    return f"thumbnail{size}, a preview the site made. Publish media to read the original."


def _upload_format(name, content_type=""):
    """An upload's line, read from its name. A clip is never downloaded to be described."""
    kind = content_type or os.path.splitext(name or "")[1].lstrip(".").upper()
    return f'{kind or "uploaded file"} on the site. Size and depth are read at run time.'


def _first_file(v, key):
    """The one file this source's format can be read off, or "" when nothing local answers."""
    pf = pf_of(v, key)
    if pf:
        return pf["path"]
    return v.get("sg_path_to_movie") or "" if key == "movie" else ""


def _frames_on_disk(pattern):
    """"N frames" for a sequence pattern that matches files, "" when it matches none."""
    hits = glob(frame_glob(pattern)) if pattern else []
    return f"{len(hits)} frames" if len(hits) > 1 else "1 frame" if hits else ""


# --- one Version ---------------------------------------------------------------------------------

def published_files(sg, version_id):
    """Every readable PublishedFile on this Version, as a plain list for a picker.

    What stopped a read is dropped here and kept by `version`, which is the caller that has to
    explain an empty picker.
    """
    return _published_files(sg, version_id)[0]


def _published_files(sg, version_id):
    """(rows, why): the read, and what stopped it.

    recipe 004. A `local` path comes back with the LocalStorage join already done, so nothing here
    reads LocalStorage or reassembles a root. A row whose path this platform has no root for reads
    null, which is the storage row's configuration and not something a reader can fix.

    field_types/url. Read `link_type` first. A `local` value has no `url` key at all and an `upload`
    one (probe 013, the three-call flow) has no local path, so a reader that indexes one shape drops
    every row of the other. A `web` row is skipped: it names a file on another machine.

    Never raises. A Version whose files cannot be read still offers its path fields and its upload.
    `why` is what stopped the read, so a caller says that rather than blaming the storage.
    """
    from .site import ARRAY_JSON
    try:
        r = sg.post("/entity/published_files/_search", headers=ARRAY_JSON, json={
            "filters": [["version", "is", {"type": "Version", "id": int(version_id)}]],
            "fields": ["path", "description", "published_file_type"], "page": {"size": 200}})
    except Exception as e:
        return [], (f"The published files could not be read. Check the connection in "
                    f"Settings, then run again. {e}")
    if not r.ok:
        return [], (f"The published files could not be read. Try again. The site answered "
                    f"{r.status_code}. {r.text[:200]}")
    try:
        rows = r.json().get("data", [])
    except ValueError:
        return [], ("The published files could not be read. Try again. The site's answer was "
                    "not JSON.")
    out = []
    for d in rows:
        a = d.get("attributes") or {}
        path = a.get("path") or {}
        link = path.get("link_type") or "local"
        if link == "web":
            continue
        pft = ((d.get("relationships") or {}).get("published_file_type") or {}).get("data") or {}
        m = COLOUR.search(a.get("description") or "")
        local = path.get(LOCAL_PATH) or "" if link == "local" else ""
        out.append({"id": d["id"], "link": link, "path": local,
                    "url": path.get("url") or "" if link == "upload" else "",
                    # What an upload can be described by without fetching it (probe 013).
                    "content_type": path.get("content_type") or "" if link == "upload" else "",
                    # The stored `source` value is built from this. A local row is named by its file
                    # on disk, an uploaded one by the name the site records.
                    "name": os.path.basename(local) if link == "local" else path.get("name") or "",
                    # A file whose type this site never labelled is still a file (probe 021).
                    "type": pft.get("name") or "published file",
                    "colour": m.group(1).strip() if m else ""})
    return out, ""


def version(sg, version_id):
    """One Version's media fields plus its PublishedFiles.

    The files are folded in here (the second call probe 021 named), so `sources` and `load` stay
    pure functions of one dict.
    """
    r = sg.get(f"/entity/versions/{int(version_id)}", params={"fields": ",".join(FIELDS)})
    if not r.ok:
        raise FPTError(f"Could not read Version {version_id} from Flow Production Tracking. Check that "
                       f"it still exists, then run again. The site answered {r.status_code}. "
                       f"{r.text[:200]}")
    d = r.json()["data"]
    files, why = _published_files(sg, version_id)
    return {**d.get("attributes", {}), "id": d["id"],
            "published_files": files, "published_files_error": why}


def split_description(text):
    """(note, facts): the operator's note, and the facts publish wrote under it.

    Only the run of `label: value` lines at the end, in the labels fields.py writes, is facts.
    Everything above it is the note, colons and all.
    """
    lines = (text or "").rstrip().splitlines()
    facts = []
    while lines:
        m = FACT_LINE.match(lines[-1])
        if not m or m.group(1) not in FACT_LABELS:
            break
        facts.insert(0, {"label": m.group(1), "value": m.group(2).strip()})
        lines.pop()
    return "\n".join(lines).strip(), facts


def provenance_state(attrs, sources):
    """Whether this Version says how it was made: "generated", "derived" or "unrecorded".

    A Version with no AI fields may have come from a tool that records nothing, from ComfyUI
    without this node, or from a camera. Absence is the absence of a record, never "not AI
    generated".

    The description counts for as much as the typed fields. On a site without the nine fields a
    publish wrote every fact there, and reading only the fields would call its own record absent.
    """
    facts = split_description(attrs.get("description"))[1]
    made = [f for f in facts if f["label"] != LINEAGE_LABEL]
    if made or any(attrs.get(f) not in (None, "", []) for f in AI_FIELDS):
        return "generated"
    return "derived" if (sources or facts) else "unrecorded"


def describe(sg, version_id, statuses=(), colors=None, icons=None):
    """One Version as structured fields, for the editor to render rather than a wall of text.

    Absent fields are omitted rather than shown empty. A site with no provenance fields gets a short
    summary, not a column of blanks.
    """
    r = sg.get(f"/entity/versions/{int(version_id)}",
                params={"fields": ",".join(SUMMARY_FIELDS + RELATED_FIELDS)})
    if not r.ok:
        return {"code": f"Version {version_id}",
                "error": f"Could not read this Version from Flow Production Tracking. Check that it "
                         f"still exists. The site answered {r.status_code}."}
    d = r.json()["data"]
    a, rel = d.get("attributes", {}), d.get("relationships", {})
    code = a.get("sg_status_list")
    ent = (rel.get("entity") or {}).get("data") or {}
    task = (rel.get("sg_task") or {}).get("data") or {}
    src = (rel.get("sg_ai_generated_from") or {}).get("data") or []
    note, written = split_description(a.get("description"))
    facts = []
    for f in DETAIL_FIELDS:
        # The note fact is the note. The facts publish wrote under it are facts of their own, so a
        # site without the nine fields reads the same as one that has them.
        value = note if f == "description" else a.get(f)
        if value not in (None, "", []):
            facts.append({"label": SUMMARY_LABELS.get(f, f),
                          "value": str(value).replace("\n", " ")[:200]})
    # A typed field wins over the same fact in the description: it is the queryable one.
    seen = {x["label"] for x in facts}
    facts += [x for x in written if x["label"] not in seen]
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
    """What the `source` combo shows for one PublishedFile: type, filename, then id.

    The type and the filename tell "the rendered sequence" from "the mp4" on a Version that
    published both. The id is the tiebreak two publishes of one stream differ by, never the label.
    It is also the stored widget value, so a file later renamed or re-typed stops matching and the
    node says so by name rather than loading the wrong file.
    """
    return f'{pf["type"]} · {pf["name"]} #{pf["id"]}'


def pf_of(v, key):
    """The PublishedFile a `source` value names, or None if it names a tier."""
    m = PF_ID.search(str(key or ""))
    if not m:
        return None
    return next((p for p in v.get("published_files") or [] if p["id"] == int(m.group(1))), None)


def colour_of(v, key):
    """The colour space this source declares, or "" when nothing was declared. Never a guess.

    Only a PublishedFile has one. `sg_path_to_frames` is a path and an upload is bytes, and
    neither has anywhere to say what the pixels claim to be.
    """
    return (pf_of(v, key) or {}).get("colour", "")


def sources(v):
    """(key, label) for every source this Version can deliver, best first."""
    out = []
    for pf in v.get("published_files") or []:
        detail = _pf_detail(pf)
        if detail:
            out.append((pf_key(pf), f'{pf["type"]} — {pf["name"]}, {detail}'))
    for key, label in TIERS:
        detail = _resolve(v, key)
        if detail:
            out.append((key, f"{label} — {detail}"))
    return out


def no_media(v):
    """Why this Version cannot be read here, said to the person who has to fix it.

    A Version nothing was published to is a different problem from one whose files are on a root
    this machine has not mounted. A read the site answered with an error says nothing about the
    storage, so the storage is not blamed for it.
    """
    who = f'Version {v["id"]} ({v.get("code") or v["id"]})'
    if v.get("published_files_error"):
        return f'{who} has no media this node can read. {v["published_files_error"]}'
    if v.get("published_files") or v.get("sg_path_to_frames") or v.get("sg_path_to_movie"):
        return (f"{who} has no media this node can read. Check that the storage holding its files "
                f"is mounted on this machine.")
    return f"{who} has no media. Publish media to it, or pick another Version."


def kind_of(v, key):
    """"sequence", "still", "movie" or "zip": the shape of what one source delivers.

    Only "zip" cannot be read. It is still offered, so a sequence published as one upload is named
    rather than missing.
    """
    pf = pf_of(v, key)
    if pf and pf["link"] != "local":
        # An uploaded sequence is one zip, so a frame pattern in the name means nothing here.
        name = pf["name"].lower()
        return "zip" if name.endswith(".zip") else "still" if name.endswith(STILL) else "movie"
    if pf:
        name = pf["path"]
    elif key == "frames":
        name = v.get("sg_path_to_frames") or ""
    elif key == "movie":
        name = v.get("sg_path_to_movie") or ""
    elif key == "uploaded":
        name = (v.get("sg_uploaded_movie") or {}).get("name") or ""
    else:
        return "still"
    if SEQ.search(name):
        return "sequence"
    return "still" if name.lower().endswith(STILL) else "movie"


# The Published File types a site publishes its deliverable as lead, then the rest by shape.
_FRAMES_ORDER = ("sequence", "movie", "still")


def best(v, want, available=None):
    """The source the `image` or the `video` output takes on its own, or "" when nothing serves.

    `image` takes frames from a sequence first, then a clip decoded, then a still, then the
    thumbnail. `video` takes a clip only: a Movie Published File, the movie on the storage, the
    uploaded mp4. A Published File beats a path field of the same shape because it names a type,
    per-platform paths and the declared colour space. The site's own transcode is never offered: it
    is derived from the upload, lags it, and can describe a file that was replaced (probe 022).
    """
    keys = [k for k, _ in (available if available is not None else sources(v))]
    if want == "video":
        return next((k for k in keys if kind_of(v, k) == "movie"), "")
    for shape in _FRAMES_ORDER:
        for k in keys:
            if k != "thumbnail" and kind_of(v, k) == shape:
                return k
    return "thumbnail" if "thumbnail" in keys else ""


def clip(v, key):
    """This source as ComfyUI's VIDEO, the file untouched. A path stays a path; an upload is read
    into memory. Only a movie source answers; a sequence or a still is wrapped by the caller."""
    import io

    from comfy_api.latest._input_impl.video_types import VideoFromFile
    pf = pf_of(v, key)
    if pf and pf["link"] == "upload":
        return VideoFromFile(io.BytesIO(_download(pf["url"])))
    path = pf["path"] if pf else v.get("sg_path_to_movie") if key == "movie" else ""
    if path:
        return VideoFromFile(path)
    if key == "uploaded":
        return VideoFromFile(io.BytesIO(_download(v["sg_uploaded_movie"]["url"])))
    raise FPTError(f"{key} is not a clip. Pick a movie source.")


def frame_rate(v):
    """(fps, why) for wrapping frames: the rate the site measured on an uploaded clip, else 24."""
    fps = v.get("sg_uploaded_movie_frame_rate")
    if fps and kind_of(v, "uploaded") == "movie":
        return float(fps), "the uploaded clip's rate"
    return float(DEFAULT_FPS), "the Version records no frame rate"


def _pf_detail(pf):
    """What one PublishedFile would deliver, by kind, or "" if it would deliver nothing here."""
    if pf["link"] == "upload":
        # Bytes on the site: nothing local can say how many frames are inside.
        return "zip on the site" if pf["name"].lower().endswith(".zip") else "uploaded file"
    path = pf["path"]
    if not path:
        return ""            # probe 021: a PublishedFile need not have a path at all
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
        # probe 013: an unfinished transcode serves a placeholder from this path, not the media.
        img = v.get("image")
        return ("a preview the site made"
                if isinstance(img, str) and "/images/status/transient/" not in img else "")
    return ""


def pattern_of(v, key):
    """The frame pattern this source reads one file at a time, or "" if it is a single file.

    A sequence is the only source a batch can be selected from. Everything else is one blob, and a
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
        if pf["link"] == "upload":
            if pf["name"].lower().endswith(".zip"):
                raise FPTError("This file is a zip and cannot be read yet. Pick another source.")
            return _download(pf["url"]), pf["name"]
        if not pf["path"]:
            raise FPTError(f'Published File {pf["id"]} has no path this machine can open. Pick '
                           f'another source, or set this platform\'s path on the storage in SG. '
                           f'The empty field is {LOCAL_PATH}.')
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
    raise FPTError(f"This Version has no source called {key}. Pick one from the source list.")


def _read(path):
    with open(path, "rb") as fh:
        return fh.read()


def _at_frame(pattern, frame):
    """(bytes, filename) for one file of a sequence, or for a path with no frame token at all.

    `frame` is the number in the filename. A frame the sequence does not have is refused with the
    range it does have. A frame other than the one asked for is never returned.
    """
    path = frame_path(pattern, frame)
    if os.path.exists(path):
        return _read(path), os.path.basename(path)
    nums = frame_numbers(pattern)
    if not nums:
        raise FPTError(f"No files match the frame pattern {pattern}. Check that the sequence is "
                       f"on this machine, and that the path on the Version is right.")
    raise FPTError(f"{os.path.basename(pattern)} has no frame {frame}. Pick a frame between "
                   f"{nums[0][0]} and {nums[-1][0]}. The sequence has {len(nums)} frames.")


def _download(url):
    """An unauthenticated GET. The field value is itself a presigned S3 URL (probe 021), and
    sending the SG bearer token here would leak it to S3."""
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    return r.content


def load_frames(v, key, start=0, count=1, budget=0):
    """(images, alpha) for `count` frames from frame `start`, as ComfyUI's own decoder returns them.

    `images` is float32 [N,H,W,3]; `alpha` is [N,H,W,1] or None where the source has none.

    `start` is the frame NUMBER, the one in the filename and the one SG shows, not a position in
    the list. `start` 0 is the first frame the source has, and `count` 0 is every frame
    from there to the end.

    Fewer than `count` come back when the source runs out. A short batch is a fact about the media,
    and padding it to the number asked for would invent frames.
    """
    count, start = int(count), int(start)
    pat = pattern_of(v, key)
    if pat:
        nums = frame_numbers(pat)
        if not nums:
            raise FPTError(f"No files match the frame pattern {pat}. Check that the sequence is "
                           f"on this machine, and that the path on the Version is right.")
        first = nums[0][0] if start <= 0 else start
        at = next((i for i, (n, _) in enumerate(nums) if n == first), None)
        if at is None:
            raise FPTError(
                f"{os.path.basename(pat)} has no frame {first}. Pick a frame between "
                f"{nums[0][0]} and {nums[-1][0]}. The sequence has {len(nums)} frames. Frame is "
                f"the number in the filename, not a position in the list, and 0 means whatever "
                f"the sequence itself starts at.")
        chosen = [path for _, path in (nums[at:] if count <= 0 else nums[at:at + count])]
        # The budget is checked against what is there, not what was asked for. A 6-frame sequence
        # never refuses frame_count 500, and a 500-frame one still does. The first file's header
        # gives the size, so a batch too big is refused before one frame is decoded.
        head = _header(chosen[0])
        if head:
            _budget((head["width"], head["height"]), len(chosen), budget_bytes(budget))
        return _batch(_stack(
            _stills(chosen), len(chosen),
            f"{os.path.basename(pat)} has no frame {first}. Pick a frame the sequence has.",
            budget_bytes(budget)))
    # Not a sequence: one blob, and a movie's frames come out of decoding it. A container has no
    # frame numbers, so `start` counts decoded frames from 1 and 0 means the same as 1.
    at = max(start, 1)
    data, filename = load(v, key, at)
    return _batch(_stack(_decode(data, filename, at), count,
                         f"{filename} has no frame {at}. Pick a lower frame number.",
                         budget_bytes(budget)))


def _components(source, filename):
    """(images, alpha) out of one image file or blob, through ComfyUI's own decoder.

    `VideoFromFile(...).get_components()` is the call core Load Image makes. Frames come back float32
    [N,H,W,3] with the alpha channel separate, so a 16-bit PNG keeps its levels and a 32-bit float
    EXR keeps its range and its values above 1. Pillow is off this path: it reads the first as two
    levels and cannot open the second at all.

    One image at a time. It reads a whole container into memory, so a movie goes through
    `_frames_of`.
    """
    from comfy_api.latest._input_impl.video_types import VideoFromFile

    try:
        got = VideoFromFile(source).get_components()
    except Exception as e:
        raise FPTError(f"{filename} could not be decoded. Check that the file is complete, then run "
                       f"again. {e}")
    if got.images.shape[0] == 0:
        raise FPTError(f"{filename} has no image this node can read. Pick another source.")
    return got.images, got.alpha


def _stills(paths):
    """(image, alpha, name) for each file of a sequence, one frame per file."""
    for p in paths:
        name = os.path.basename(p)
        images, alpha = _components(p, name)
        yield images[0], None if alpha is None else alpha[0], name


# The pixel formats ComfyUI's decoder reads as 8-bit and scales, rather than converting to planar
# float (video_types.get_components_internal).
EIGHT_BIT = ("yuvj420p", "yuvj422p", "yuvj444p", "rgb24", "rgba", "pal8")


def _decode(data, filename, start=1):
    """(image, alpha, name) out of one blob: a still is itself, a movie is every frame from `start`.

    A still is read whole: one file is one image. A movie is decoded frame by frame, so the ceiling
    below refuses a long plate before all of it is in memory.
    """
    import io

    if filename.lower().endswith(STILL):
        images, alpha = _components(io.BytesIO(data), filename)
        single = images.shape[0] == 1
        for i in range(int(start) - 1, images.shape[0]):
            yield images[i], None if alpha is None else alpha[i], \
                filename if single else f"{filename} frame {i + 1}"
        return
    yield from _frames_of(io.BytesIO(data), filename, int(start))


def _frames_of(blob, filename, start=1):
    """(image, alpha, name) for every frame of a container from `start`, one decode at a time.

    The pixel format is the one ComfyUI's decoder picks for that stream. An 8-bit RGB or full-range
    JPEG stream converts to `rgb24`/`rgba` and scales by 255. Everything else converts straight to
    planar float, which keeps a 10-bit or float stream at its own precision. The alpha channel comes
    off the same conversion and is handed back separately, as core hands it back.

    Core pads a frame whose width is not a multiple of 32 before converting, against an ffmpeg
    alignment artefact at the right and bottom edge. Nothing here does, and an h264 stream at such a
    width reads identically either way.
    """
    import av
    import torch

    fmt = alpha_channel = eight_bit = None
    with av.open(blob) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        for n, frame in enumerate(container.decode(stream), start=1):
            if fmt is None:
                alpha_channel = frame.format.name == "pal8" or \
                    any(c.is_alpha for c in frame.format.components)
                eight_bit = frame.format.name in EIGHT_BIT
                fmt = ("rgba" if alpha_channel else "rgb24") if eight_bit else \
                      ("gbrapf32le" if alpha_channel else "gbrpf32le")
            if n < start:
                continue
            a = torch.from_numpy(frame.to_ndarray(format=fmt))
            if eight_bit:
                a = a.float() / 255.0
            yield (a[..., :-1], a[..., -1:], f"{filename} frame {n}") if alpha_channel \
                else (a, None, f"{filename} frame {n}")


def _size(image):
    """(width, height) of one decoded frame, which arrives height first."""
    return int(image.shape[1]), int(image.shape[0])


def _stack(frames, count, empty, budget):
    """The frames that will become one IMAGE batch, refused before torch has to refuse them.

    Both checks are here rather than at the tensor, because both have an answer a person can act on.
    An allocator answers 300 frames of 4K with a stack trace, and torch answers a size change
    mid-sequence with two shapes and no filename.
    """
    out = []
    for img, alpha, name in frames:
        if not out:
            _budget(_size(img), max(count, 1), budget)
        elif _size(img) != _size(out[0][0]):
            w, h = _size(img)
            w0, h0 = _size(out[0][0])
            raise FPTError(
                f"{name} is {w}×{h} but this batch started {w0}×{h0}. Frames of different sizes "
                f"cannot go into one IMAGE. Load the runs separately, or resize before the batch.")
        out.append((img, alpha))
        # `count` 0 is everything there is. A sequence has its own count before it reads anything
        # and arrives here with a number. A movie does not, so the budget is checked against what
        # has accumulated.
        if count <= 0:
            _budget(_size(out[0][0]), len(out), budget)
        elif len(out) >= count:
            break
    if not out:
        raise FPTError(empty)
    return out


def _batch(frames):
    """(images, alpha) as two tensors. A batch mixing files with and without an alpha channel has no
    single alpha, and returns None for it."""
    import torch

    images = torch.stack([img for img, _ in frames])
    alpha = None if any(a is None for _, a in frames) else torch.stack([a for _, a in frames])
    return images, alpha


def budget_bytes(gib=0):
    """Bytes one IMAGE batch may cost. Anything that is not a positive number is the fallback.

    A negative budget refuses every batch there is, naming a negative ceiling.
    """
    try:
        gib = float(gib or 0)
    except (TypeError, ValueError):
        gib = 0
    return int((gib if gib > 0 else DEFAULT_BUDGET_GIB) * 2 ** 30)


def gib(n):
    """Bytes as GiB. Three significant digits, so a budget under a tenth of a GiB still reads."""
    return f"{float(f'{n / 2 ** 30:.3g}'):g}"


def frames_that_fit(size, budget):
    """How many frames of this size fit in one batch."""
    w, h = size
    return max(int(budget) // (w * h * 3 * 4), 1)


def _budget(size, count, budget):
    """Refuse a batch past `budget`: what to set, then the numbers that say why."""
    w, h = size
    need = w * h * 3 * 4 * int(count)     # float32 RGB, the layout of an IMAGE tensor
    if need > budget:
        raise FPTError(
            f"Set frame_count to {frames_that_fit(size, budget)} or less at this resolution. "
            f"{count} frames of {w}×{h} would need {gib(need)} GiB as one batch; the limit is "
            f"{gib(budget)} GiB, batch_budget_gib in profile.local.json.")
