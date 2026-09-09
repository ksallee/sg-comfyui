"""Frames on disk, and the path under a LocalStorage root that SG can resolve.

A Version's media is single-valued (probe 022), so frames cannot be the media: they are a
PublishedFile, and a PublishedFile's path has to sit under one of the site's LocalStorage roots —
anything else is 400 code 104 (recipe 004).

Frames land in ComfyUI's own output directory and are **copied** into place under the root. Copy,
never move: the run stays where the artist expects it, a publish that fails half way leaves
something to re-publish from, and a second attempt costs a copy rather than a re-render.

Nothing here transcodes and nothing here infers. The frames are written by ComfyUI's own encoder in
the format the node was told, registered under that format's own extension, and the colour space is
recorded exactly as the operator declared it (DESIGN: a colour transform is the most consequential
pixel change there is, and this project does not make images).
"""
import os
import re
import shutil
import sys
import tempfile
from collections import namedtuple
from pathlib import Path

from . import media, naming, site, version_name

# The frame token, wherever the operator put it. `media.SEQ` knows printf, Shake `#` and `@` alike,
# so a path template speaks the same notation `sg_path_to_frames` does.
SEQ = media.SEQ

# Two shapes, because a sequence is many files and earns a folder while a movie is one file and does
# not. Neither repeats the naming scheme: `{root_name}` and `{version_name}` are the two names
# themselves, so a path refers to them rather than spelling them a second time and disagreeing.
# A sequence is many files and gets a folder of its own, named for the version; the movie is one
# file and sits beside that folder in the stream's folder, so no folder holds both.
DEFAULT_SEQUENCE_TEMPLATE = "{entity}/{root_name}/{version_name}/{version_name}.%04d{ext}"
DEFAULT_MOVIE_TEMPLATE = "{entity}/{root_name}/{version_name}{ext}"
DEFAULT_PATH_TEMPLATE = DEFAULT_SEQUENCE_TEMPLATE      # profiles in the wild name this one

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
    """One folder per publish, under ComfyUI's output. The movie lands beside its own frames."""
    return output_dir() / stem


# What each choice on the node's `format` widget is, in ComfyUI's own encoder vocabulary:
# (file format, bit depth, colour space, extension). PNG's colour space does not modify pixels. EXR
# takes "linear", which is the encoder's write-through, so a scene-linear plate goes to disk exactly
# as the graph made it and the operator's declared colour space stays a claim about the pixels
# rather than a transform applied to them.
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
    """The extension the frames of this format actually have."""
    return spec_for(fmt)[3]


def write_frames(images, stem, fmt=DEFAULT_FORMAT):
    """The batch as a sequence in ComfyUI's output directory, one folder per publish.

    ComfyUI's own encoder writes them (`comfy_extras.nodes_images._encode_image`), because bit
    depth, channel count and any colour transform are its business and not this repo's. Imported
    inside the call, so an older install still loads every node and only refuses the write. The
    extension the site records follows these files and is never taken from the path template, which
    would let a template reading `.exr` label 8-bit PNGs as scene-linear EXRs.
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
    """The LocalStorage the profile names. Chosen by code, never by position: one root is not a
    choice, several are, and taking the first would put a show's frames on whichever storage the
    site happens to list first."""
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
    """The platform the Version's path fields are written for: the profile's choice, else this
    machine's where the storage defines it, else the first one it does."""
    have = platforms_of(row)
    if chosen in have:
        return chosen
    return THIS_PLATFORM if THIS_PLATFORM in have else (have[0] if have else THIS_PLATFORM)


def on_platform(path, local_root, row, platform):
    """`path`, written under this machine's root, as the same file under `platform`'s root.

    `sg_path_to_frames` holds one absolute path and cannot resolve on two platforms (probe 021),
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

    recipe 004 — a root is per platform and a row may define only one, so `local_path_windows` and
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

    Same rule as staging the movie first (publish_version): a Version left behind pointing at frames
    nobody wrote is worse than a run that refused.
    """
    if not os.path.isdir(root):
        raise RuntimeError(f"The storage root {root} is not mounted on this machine. Mount it, "
                           f"then run again.")
    if not os.access(root, os.W_OK):
        raise RuntimeError(f"The storage root {root} is not writable by ComfyUI. Give it write "
                           f"access, then run again.")


def swap_ext(path, ext):
    """The extension the files actually have, replacing whatever the template guessed.

    A template that ends in the frame token has no extension to replace — `.%04d` is the frame
    number — so the token is kept and the real extension is appended after it.
    """
    base, dot, tail = str(path).rpartition(".")
    if not dot or "/" in tail or "\\" in tail or SEQ.fullmatch(tail):
        return str(path) + ext
    return base + ext


# A path template says two numbers at once and they must not be confused. `{version}` is the publish
# revision; `%04d` (or `####`, or `@@@@`) is the frame. `naming.normalise_template` reads ANY printf
# pad as the version, which is right for a code template — `v%04d` is how a TD spells the revision by
# habit — and wrong here, where it would render frame 3 as `.0003.` and freeze the sequence to one
# frame. So the frame token is lifted out before rendering and put back after.
#
# The consequence: in a PATH template the printf form is the FRAME, and the version is
# `{version:03d}`.
SENTINEL = "\x00"


def _protect(template):
    """(template with the frame token held out, the token).

    NUL survives `naming.render` untouched: it is not a field, not a separator render squashes, and
    not one it strips from the ends.
    """
    t = template or ""
    m = SEQ.search(t)
    return (t, "") if not m else (t[:m.start()] + SENTINEL + t[m.end():], m.group(0))


def _clean(path):
    """Forward slashes only, and no empty segment.

    A single backslash is refused by two different errors depending on which key holds it, and in a
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

    Field values come from the site, so the result is checked to be inside the root: a path that
    walks out of it would be written outside the storage the site can resolve.
    """
    held, token = _protect(template or DEFAULT_PATH_TEMPLATE)
    rel = naming.render(held, values, version).replace(SENTINEL, token)
    out = _clean(swap_ext(f"{root}/{rel}", ext))
    if not _under(root, out):
        raise RuntimeError(f"{out} is outside the storage root {root}. A published file has to sit "
                           f"under the root. Fix Sequence path or Movie path under Settings, "
                           f"then SG.")
    return out


def single(path):
    """A sequence path with the frame token and its separator removed — for the movie beside it."""
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


Plan = namedtuple("Plan", "root storage_id row platform seq_template movie_template "
                          "values blank name")


def plan(p, storages, code, version_no, project_id, link_type, link_id, task_id, root_name=""):
    """Where this publish's files would land: the root, the two templates and everything filled in.

    Resolves and renders; touches no disk and creates nothing. The panel and the run both answer
    from here, so a path an operator reads before pressing Run is the path the run writes.

    A path template is the language the code template already speaks — dotted SG paths and Python's
    format spec (`naming.render`) — plus the frame token `sg_path_to_frames` uses. A sequence earns
    a folder and a movie does not, which is why there are two templates. Neither repeats the naming
    scheme: `{root_name}` and `{version_name}` are the two names themselves.
    """
    pf = p.get("published_files") or {}
    storage_id, root = root_for(storages, pf.get("storage", ""))
    row = storage_row(storages, pf.get("storage", ""))
    platform = platform_for(row, pf.get("path_platform", ""))
    seq_t = pf.get("path_template") or DEFAULT_SEQUENCE_TEMPLATE
    mov_t = pf.get("movie_path_template") or DEFAULT_MOVIE_TEMPLATE
    root_t = (root_name or p.get("root_name") or naming.DEFAULT_ROOT_TEMPLATE).strip()
    fields = (set(naming.template_fields(seq_t)) | set(naming.template_fields(mov_t))
              | set(naming.template_fields(root_t)))
    vals = site.resolve_paths(fields, project_id, link_type, link_id, task_id)
    # A token nobody could resolve leaves an empty segment that `_clean` swallows, so name them.
    # probe 028: a 200 proves nothing, and neither does a path that rendered.
    # `root_name`, `version_name` and `ext` are filled below rather than looked up, so a template
    # asking for them has not left anything unresolved.
    blank = sorted(k for k in fields - {"root_name", "version_name", "ext"}
                   if not str(vals.get(k, "")).strip())
    name = version_name.root_of(root_t, vals, version_no)
    return Plan(root, storage_id, row, platform, seq_t, mov_t,
                dict(vals, version_name=code, root_name=name), blank, name)


def destination(pl, template, ext, version_no):
    """One rendered absolute path under the plan's root, frame token intact."""
    return pattern(pl.root, template, dict(pl.values, ext=ext), version_no, ext)


def field_path(pl, path):
    """The same file under the root the profile writes the Version's path fields for."""
    return on_platform(path, pl.root, pl.row, pl.platform)


def relative(root, path):
    """What `path_cache` holds.

    The server fills `path_cache_storage` from the path it resolved but leaves `path_cache` null
    after a REST create (entity_types/PublishedFile), so a filter on it misses every row published
    this way unless the client writes it.
    """
    return str(path)[len(str(root)):].lstrip("/")


def describe_colour(declared):
    """Recorded, never applied. An empty declaration says nothing rather than guessing sRGB."""
    return f"colour space: {declared} (declared by the publisher, not converted)" if declared else ""
