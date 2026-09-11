"""Frames on disk, and the path under a LocalStorage root that SG can resolve.

A Version has one uploaded media file (probe 022), so frames cannot be that file. They are a
PublishedFile, and a PublishedFile's path has to be under one of the site's LocalStorage roots.
Anything else is 400 code 104 (recipe 004).

Frames are written to ComfyUI's own output directory and copied into place under the root. Copy,
never move: the run stays where the artist expects it, and a publish that fails part way leaves
something to re-publish from.

Nothing here transcodes and nothing here infers. The frames are written by ComfyUI's own encoder in
the format the node was told, registered under that format's own extension. The colour space is
recorded as the operator declared it and never applied.
"""
import os
import re
import shutil
import sys
import tempfile
from collections import namedtuple
from pathlib import Path

from . import media, naming, site, version_name

# The frame token, wherever the operator put it. `media.SEQ` matches printf, Shake `#` and `@`, so
# a path template uses the same notation as `sg_path_to_frames`.
SEQ = media.SEQ

# Three shapes. A sequence is many files and gets a folder of its own, named for the version. A
# still and a movie are one file each, written beside that folder, so no folder contains frames and
# a movie together. No template repeats the naming scheme: `{root_name}` and `{version_name}` are
# the two names themselves.
DEFAULT_SEQUENCE_TEMPLATE = "{entity}/{root_name}/{version_name}/{version_name}.%04d{ext}"
DEFAULT_STILL_TEMPLATE = "{entity}/{root_name}/{version_name}{ext}"
DEFAULT_MOVIE_TEMPLATE = "{entity}/{root_name}/{version_name}{ext}"
DEFAULT_PATH_TEMPLATE = DEFAULT_SEQUENCE_TEMPLATE      # existing profiles name this one

# What to ask for, in preference order, against the types the site already has. Never created: a
# PublishedFileType has no `project`, so creating one adds it to every show on the site (recipe 004),
# and an unrecognised extension is better reported than silently minted.
TYPE_CANDIDATES = {
    "frames": ("Rendered Image", "Image"),
    "still": ("Image", "Rendered Image"),
    "movie": ("Movie",),
}


def output_dir():
    """Where ComfyUI writes. Its own output directory, so the frames are where an artist looks."""
    try:
        import folder_paths          # only exists inside a running ComfyUI
        return Path(folder_paths.get_output_directory())
    except Exception:
        return Path(tempfile.gettempdir())


def folder(stem):
    """One folder per publish, under ComfyUI's output. The movie is written beside its frames."""
    return output_dir() / stem


# What each choice on the node's `format` widget is, in ComfyUI's own encoder vocabulary:
# (file format, bit depth, colour space, extension). PNG's colour space does not modify pixels. EXR
# takes "linear", the encoder's write-through, so a scene-linear plate is written as the graph
# made it. The operator's declared colour space is a claim about the pixels, not a transform.
FORMATS = {
    "8-bit PNG":        ("png", "8-bit", "sRGB", ".png"),
    "16-bit PNG":       ("png", "16-bit", "sRGB", ".png"),
    "EXR 32-bit float": ("exr", "32-bit float", "linear", ".exr"),
}
DEFAULT_FORMAT = "8-bit PNG"


def spec_for(fmt):
    """One format's (file format, bit depth, colour space, extension)."""
    return FORMATS.get(fmt or DEFAULT_FORMAT, FORMATS[DEFAULT_FORMAT])


def extension(fmt):
    """The extension the frames of this format have."""
    return spec_for(fmt)[3]


def with_alpha(images, mask):
    """The batch with the mask as a fourth channel, alpha `1 - mask`, ComfyUI's own convention.

    One mask applies to every frame. A batch of masks has one mask per frame. A mask of another
    size, or another count, is refused. Nothing here resamples a mask onto the frames.
    """
    import torch

    m = mask.reshape(1, *mask.shape) if mask.ndim == 2 else mask
    n, h, w = images.shape[0], images.shape[1], images.shape[2]
    if (m.shape[1], m.shape[2]) != (h, w):
        raise ValueError(f"The mask is {m.shape[2]}x{m.shape[1]} and the frames are {w}x{h}. Wire "
                         f"a mask the size of the frames, or unplug it.")
    if m.shape[0] not in (1, n):
        raise ValueError(f"There are {m.shape[0]} masks and {n} frames. Wire one mask for the "
                         f"batch, or one mask per frame.")
    if m.shape[0] == 1 and n > 1:
        m = m[[0] * n]
    alpha = (1.0 - m.to(images)).clip(0.0, 1.0)
    return torch.cat((images[..., :3], alpha[..., None]), dim=-1)


def write_frames(images, stem, fmt=DEFAULT_FORMAT):
    """The batch as a sequence in ComfyUI's output directory, one folder per publish.

    ComfyUI's own encoder writes them (`comfy_extras.nodes_images._encode_image`). Imported inside
    the call, so an older install still loads every node and only refuses the write. The extension
    the site records comes from these files, never from the path template, which would let a
    template reading `.exr` label 8-bit PNGs as scene-linear EXRs.
    """
    try:
        from comfy_extras.nodes_images import _encode_image
    except ImportError:
        raise RuntimeError(f"Writing {fmt} needs ComfyUI 0.34.0 or newer. Update ComfyUI, or pick "
                           f"8-bit PNG.")
    file_format, bit_depth, colorspace, ext = spec_for(fmt)
    into = folder(stem)
    into.mkdir(parents=True, exist_ok=True)
    out = []
    for i, frame in enumerate(images, start=1):
        p = into / f"{stem}.{i:04d}{ext}"
        p.write_bytes(_encode_image(frame, file_format, bit_depth, colorspace))
        out.append(p)
    return out


# A LocalStorage row defines one root per platform (recipe 004), under these keys.
PLATFORM_KEY = {"mac": "mac_path", "linux": "linux_path", "windows": "windows_path"}
THIS_PLATFORM = {"darwin": "mac", "win32": "windows"}.get(sys.platform, "linux")


def storage_row(storages, code=""):
    """The LocalStorage the profile names, chosen by code and never by position."""
    have = ", ".join(sorted(s["code"] for s in storages))
    if not storages:
        raise RuntimeError("This site has no Local File Storage, so nothing can be published to "
                           "it. Add one in Flow Production Tracking, under Site Preferences then "
                           "File Management.")
    if not code and len(storages) != 1:
        raise RuntimeError(f"No storage is chosen, and this site has {len(storages)} to choose "
                           f"from. Pick Storage under Settings, then SG: {have}.")
    rows = [s for s in storages
            if not code or s["code"].strip().lower() == code.strip().lower()]
    if not rows:
        raise RuntimeError(f"No storage called {code} on this site. Pick Storage under Settings, "
                           f"then SG: {have}.")
    return rows[0]


def platforms_of(row):
    """The platforms this storage defines a root for, in the order mac, linux, windows."""
    return [p for p, k in PLATFORM_KEY.items() if (row or {}).get(k)]


def platform_for(row, chosen=""):
    """The platform the Version's path fields are written for.

    The profile's choice, else this machine's where the storage defines a root for it, else the
    first platform the storage does define one for.
    """
    have = platforms_of(row)
    if chosen in have:
        return chosen
    return THIS_PLATFORM if THIS_PLATFORM in have else (have[0] if have else THIS_PLATFORM)


def on_platform(path, local_root, row, platform):
    """`path`, written under this machine's root, as the same file under `platform`'s root.

    `sg_path_to_frames` is one absolute path and cannot resolve on two platforms (probe 021),
    so a studio picks the one it is written for. A Windows root takes backslashes after it, which
    is reasoned from how SG spells `windows_path` and not measured against a Windows client.
    """
    here, base = _clean(path), _clean(local_root).rstrip("/")
    # Both cleaned: a path is written forward-slashed and a Windows root is not, so comparing them
    # raw finds no match on a Windows publisher and the swap silently never happens.
    if platform == THIS_PLATFORM or not here.startswith(base):
        return path
    root = ((row or {}).get(PLATFORM_KEY.get(platform, "")) or "").rstrip("/").rstrip("\\")
    if not root:
        return path
    rel = here[len(base):]
    return root + (rel.replace("/", "\\") if platform == "windows" else rel)


def root_for(storages, code=""):
    """(id, root) for the LocalStorage the profile names, on the platform this client runs on.

    recipe 004: a root is per platform and a row may define only one, so `local_path_windows` and
    `local_path_linux` read back null where the row leaves them unset.
    """
    key = PLATFORM_KEY[THIS_PLATFORM]
    row = storage_row(storages, code)
    root = (row.get(key) or "").rstrip("/")
    if not root:
        raise RuntimeError(f"The storage {row['code']} has no {key} set, so nothing can be "
                           f"published to it from this machine. Set that path on the storage in "
                           f"Flow Production Tracking, or pick another Storage under Settings, "
                           f"then SG.")
    return row["id"], root


def check_root(root):
    """A root that is not mounted or not writable stops the publish before the Version exists.

    Same rule as staging the movie first (publish_version). A Version pointing at frames nobody
    wrote is worse than a run that refused.

    Both refusals are measured against a volume mounted read-only and then detached. Each is on the
    panel before the Run and stops it, and neither leaves a Version or a file behind.
    """
    if not os.path.isdir(root):
        raise RuntimeError(f"The storage root {root} is not mounted on this machine. Mount it, "
                           f"then run again.")
    if not os.access(root, os.W_OK):
        raise RuntimeError(f"The storage root {root} is not writable by ComfyUI. Give it write "
                           f"access, then run again.")


def swap_ext(path, ext):
    """The extension the files have, replacing whatever the template guessed.

    A template that ends in the frame token has no extension to replace, because `.%04d` is the
    frame number. The token is kept and the files' extension is appended after it.
    """
    base, dot, tail = str(path).rpartition(".")
    if not dot or "/" in tail or "\\" in tail or SEQ.fullmatch(tail):
        return str(path) + ext
    return base + ext


# A path template says two numbers at once. `{version}` is the publish revision. `%04d`, `####` and
# `@@@@` are the frame. `naming.normalise_template` reads any printf pad as the version, which is
# right for a code template and wrong here: it would render frame 3 as `.0003.` and freeze the
# sequence to one frame. The frame token is lifted out before rendering and put back after.
#
# In a path template the printf form is the frame, and the version is `{version:03d}`.
SENTINEL = "\x00"


def _protect(template):
    """(template with the frame token swapped for the sentinel, the token).

    NUL survives `naming.render` untouched: it is not a field, not a separator render squashes, and
    not one it strips from the ends.
    """
    t = template or ""
    m = SEQ.search(t)
    return (t, "") if not m else (t[:m.start()] + SENTINEL + t[m.end():], m.group(0))


def _clean(path):
    """Forward slashes only, and no empty segment.

    A single backslash is refused by two different errors depending on which key it is in, and in a
    `local_path` it fails as an *unknown storage* rather than as a malformed path (recipe 004). An
    empty segment comes from a template token with no value, and `//` in a local_path is not the
    path the server resolves back.
    """
    return re.sub(r"(?<!^)/{2,}", "/", str(path).replace("\\", "/"))


def _under(root, path):
    """Whether a rendered path lies inside the storage root."""
    r, p = os.path.normpath(str(root)), os.path.normpath(str(path))
    return p == r or p.startswith(r + os.sep)


def pattern(root, template, values, version, ext):
    """The absolute destination path, frame token intact, under the storage root.

    Field values come from the site, so the result is checked to be inside the root. A rendered
    path outside it would be written where the site cannot resolve it.
    """
    held, token = _protect(template or DEFAULT_PATH_TEMPLATE)
    rel = naming.render(held, values, version).replace(SENTINEL, token)
    out = _clean(swap_ext(f"{root}/{rel}", ext))
    if not _under(root, out):
        raise RuntimeError(f"{out} is outside the storage root {root}. A published file has to be "
                           f"under the root. Fix Sequence path, Still path or Movie path under "
                           f"Settings, then SG.")
    return out


def single(path):
    """A sequence path with the frame token and its separator removed, for the movie beside it."""
    m = SEQ.search(path or "")
    if not m:
        return path
    start = m.start() - 1 if m.start() and path[m.start() - 1] in "._-" else m.start()
    return path[:start] + path[m.end():]


def place(sources, dest_pattern, first=1):
    """Copy each staged frame to its numbered destination. Returns what was written.

    `media.frame_path` decides the numbering, so a path template and `sg_path_to_frames` read the
    same notation and a `####` template is not silently treated as literal text.
    """
    Path(dest_pattern).parent.mkdir(parents=True, exist_ok=True)
    out = []
    for i, src in enumerate(sources, start=int(first)):
        dst = media.frame_path(dest_pattern, i)
        shutil.copyfile(src, dst)          # copy, never move: see the module docstring
        out.append(dst)
    return out


def copy_one(source, dest):
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    return dest


Plan = namedtuple("Plan", "root storage_id row platform seq_template still_template "
                          "movie_template values blank name")


def plan(p, storages, code, version_no, project_id, link_type, link_id, task_id, root_name=""):
    """Where this publish's files would be written: the root, the two templates and the values.

    Resolves and renders; touches no disk and creates nothing. The panel and the run both answer
    from here, so a path an operator reads before pressing Run is the path the run writes.

    A path template uses the language of the code template, dotted SG paths and Python's format
    spec (`naming.render`), plus the frame token `sg_path_to_frames` uses. There are three
    templates because a sequence gets a folder and a single file does not. None of them repeats the
    naming scheme: `{root_name}` and `{version_name}` are the two names themselves.
    """
    pf = p.get("published_files") or {}
    storage_id, root = root_for(storages, pf.get("storage", ""))
    row = storage_row(storages, pf.get("storage", ""))
    platform = platform_for(row, pf.get("path_platform", ""))
    seq_t = pf.get("path_template") or DEFAULT_SEQUENCE_TEMPLATE
    still_t = pf.get("still_path_template") or DEFAULT_STILL_TEMPLATE
    mov_t = pf.get("movie_path_template") or DEFAULT_MOVIE_TEMPLATE
    root_t = (root_name or p.get("root_name") or naming.DEFAULT_ROOT_TEMPLATE).strip()
    fields = (set(naming.template_fields(seq_t)) | set(naming.template_fields(still_t))
              | set(naming.template_fields(mov_t)) | set(naming.template_fields(root_t)))
    vals = site.resolve_paths(fields, project_id, link_type, link_id, task_id)
    # A token nobody could resolve leaves an empty segment that `_clean` removes, so name them.
    # probe 028: a 200 proves nothing, and neither does a path that rendered.
    # `root_name`, `version_name` and `ext` are filled below rather than looked up, so a template
    # asking for them has not left anything unresolved.
    blank = sorted(k for k in fields - {"root_name", "version_name", "ext"}
                   if not str(vals.get(k, "")).strip())
    name = version_name.root_of(root_t, vals, version_no)
    return Plan(root, storage_id, row, platform, seq_t, still_t, mov_t,
                dict(vals, version_name=code, root_name=name), blank, name)


def destination(pl, template, ext, version_no):
    """One rendered absolute path under the plan's root, frame token intact."""
    return pattern(pl.root, template, dict(pl.values, ext=ext), version_no, ext)


def field_path(pl, path):
    """The same file under the root the profile writes the Version's path fields for."""
    return on_platform(path, pl.root, pl.row, pl.platform)


def relative(root, path):
    """The value `path_cache` is set to.

    The server fills `path_cache_storage` from the path it resolved but leaves `path_cache` null
    after a REST create (entity_types/PublishedFile), so a filter on it misses every row published
    this way unless the client writes it.
    """
    return str(path)[len(str(root)):].lstrip("/")


def describe_colour(declared):
    """Recorded, never applied. An empty declaration says nothing rather than guessing sRGB."""
    return f"colour space: {declared} (declared by the publisher, not converted)" if declared else ""
