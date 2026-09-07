"""Frames on disk, and the path under a LocalStorage root that Flow PT can resolve.

A Version's media is single-valued (probe 022), so frames cannot be the media: they are a
PublishedFile, and a PublishedFile's path has to sit under one of the site's LocalStorage roots —
anything else is 400 code 104 (recipe 004).

Frames land in ComfyUI's own output directory and are **copied** into place under the root. Copy,
never move: the run stays where the artist expects it, a publish that fails half way leaves
something to re-publish from, and a second attempt costs a copy rather than a re-render.

Nothing here transcodes and nothing here infers. A PNG is registered as a PNG, and the colour space
is recorded exactly as the operator declared it (DESIGN: a colour transform is the most
consequential pixel change there is, and this project does not make images).
"""
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image

from . import media, movie, naming

# The frame token, wherever the operator put it. `media.SEQ` already knows printf, Shake `#` and `@`
# (docs/quirks), so a path template speaks the same notation `sg_path_to_frames` does.
SEQ = media.SEQ

# Two shapes, because a sequence is many files and earns a folder while a movie is one file and does
# not. Neither repeats the naming scheme: `{root_name}` and `{version_name}` are the two names
# themselves, so a path refers to them rather than spelling them a second time and disagreeing.
DEFAULT_SEQUENCE_TEMPLATE = "{entity}/{root_name}/v{version:03d}/{version_name}.%04d{ext}"
DEFAULT_MOVIE_TEMPLATE = "{entity}/{root_name}/v{version:03d}/{version_name}{ext}"
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


def write_frames(images, stem):
    """The batch as a PNG sequence in ComfyUI's output directory, one folder per publish.

    PNG because that is what Pillow can write from an IMAGE tensor without inventing anything. The
    extension the site records follows these files and is never taken from the path template, which
    would let a template reading `.exr` label 8-bit PNGs as scene-linear EXRs.
    """
    into = folder(stem)
    into.mkdir(parents=True, exist_ok=True)
    out = []
    for i, frame in enumerate(images, start=1):
        p = into / f"{stem}.{i:04d}.png"
        Image.fromarray(movie.to_u8(frame)).save(p, format="PNG")
        out.append(p)
    return out


def root_for(storages, code=""):
    """(id, root) for the LocalStorage the profile names, on the platform this client runs on.

    recipe 004 — a root is per platform and a row may define only one, so `local_path_windows` and
    `local_path_linux` read back null where the row leaves them unset. Chosen by code, never by
    position: one root is not a choice, several are, and taking the first would put a show's frames
    on whichever storage the site happens to list first.
    """
    key = {"darwin": "mac_path", "win32": "windows_path"}.get(sys.platform, "linux_path")
    have = ", ".join(sorted(s["code"] for s in storages)) or "none"
    if not code and len(storages) != 1:
        raise RuntimeError(f"published_files.storage is not set in profile.local.json, and this "
                           f"site has {len(storages)} storages to choose from. Set it to one of "
                           f"these: {have}.")
    rows = [s for s in storages
            if not code or s["code"].strip().lower() == code.strip().lower()]
    if not rows:
        raise RuntimeError(f"No storage called {code} on this site. Set published_files.storage "
                           f"in profile.local.json to one of these: {have}.")
    row = rows[0]
    root = (row.get(key) or "").rstrip("/")
    if not root:
        raise RuntimeError(f"The storage {row['code']} has no {key} set, so nothing can be "
                           f"published to it from this machine. Set that path on the storage in "
                           f"Flow PT, or name another storage in profile.local.json.")
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
    """The extension the files actually have, replacing whatever the template guessed."""
    base, _, _ = str(path).rpartition(".")
    return (base or str(path)) + ext


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
                           f"under the root, so fix path_template in profile.local.json.")
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
