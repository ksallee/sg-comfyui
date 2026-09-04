"""Frames on disk, and the path under a LocalStorage root that Flow PT can resolve.

A Version's media is single-valued (probe 022), so the frames themselves cannot BE the media: they are
a PublishedFile, and a PublishedFile's path has to sit under one of the site's LocalStorage roots —
anything else is refused with 400 code 104 (recipe 004).

Nothing here asks ComfyUI to write anywhere in particular. The frames land in ComfyUI's own output
directory and are **copied** into place under the root. Copy, never move: the run stays where the
artist expects it, a publish that fails half way leaves something to re-publish from, and a second
attempt costs a copy rather than a re-render.

The format is whatever was written. Bit depth and colour space are the first things a comp supervisor
checks, so nothing here transcodes and nothing here infers: a PNG is registered as a PNG, and the
colour space is recorded exactly as the operator declared it (DESIGN: never build a feature that makes
images — a colour transform is the most consequential one there is).
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
# `{version}` plus whatever literal introduces it — `_v`, `.v`, `-`. Removing it from the TEMPLATE
# rather than from the rendered string is what makes `name` unambiguous: `sbx_0020_depth_v020` has
# two runs of digits and only the template knows which one is the version (recipe 004: `name` is the
# stream, `code` is one version of it).
VERSION_TOKEN = re.compile(r"[._\-]?v?\{version[^{}]*\}", re.I)

DEFAULT_PATH_TEMPLATE = ("{entity.code}/{output}/v{version:03d}/"
                         "{entity.code}_{output}_v{version:03d}.%04d.png")

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


def write_frames(images, stem):
    """The batch as a PNG sequence in ComfyUI's output directory. One folder per publish.

    PNG because that is what Pillow can write from an IMAGE tensor without inventing anything. The
    extension the site records follows these files; it is never taken from the path template, which
    would let a template reading `.exr` label 8-bit PNGs as scene-linear EXRs.
    """
    folder = output_dir() / stem
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for i, frame in enumerate(images, start=1):
        p = folder / f"{stem}.{i:04d}.png"
        Image.fromarray(movie.to_u8(frame)).save(p, format="PNG")
        out.append(p)
    return out


def write_bytes(payload, stem, suffix):
    """The encoded movie beside its frames, so the file registered is the file uploaded."""
    folder = output_dir() / stem
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / f"{stem}{suffix}"
    p.write_bytes(payload)
    return p


def root_for(storages, code=""):
    """(id, root) for the LocalStorage the profile names, on the platform this client runs on.

    recipe 004 — a root is per platform and a row may define only one; `local_path_windows` and
    `local_path_linux` read back null where the row leaves them unset, and that is the storage row's
    configuration, not something a publish can fix. Chosen by code, never by position.
    """
    key = {"darwin": "mac_path", "win32": "windows_path"}.get(sys.platform, "linux_path")
    have = ", ".join(sorted(s["code"] for s in storages)) or "none"
    # One root is not a choice; several are, and taking the first would put a show's frames on
    # whichever storage the site happens to list first. Named in the profile, or unambiguous.
    if not code and len(storages) != 1:
        raise RuntimeError(f"published_files.storage is not set in the profile and this site has "
                           f"{len(storages)} LocalStorage rows ({have})")
    rows = [s for s in storages
            if not code or s["code"].strip().lower() == code.strip().lower()]
    if not rows:
        raise RuntimeError(f"no LocalStorage called {code!r} on this site (have: {have})")
    row = rows[0]
    root = (row.get(key) or "").rstrip("/")
    if not root:
        raise RuntimeError(f"LocalStorage {row['code']!r} has no {key}: this platform has no root "
                           f"under it, so no path here can resolve")
    return row["id"], root


def check_root(root):
    """A root that is not mounted must stop the publish BEFORE the Version exists.

    Same rule as encoding the movie first (publish_version): a Version left behind pointing at frames
    nobody wrote is worse than a run that refused.
    """
    if not os.path.isdir(root):
        raise RuntimeError(f"storage root {root} is not mounted on this machine")
    if not os.access(root, os.W_OK):
        raise RuntimeError(f"storage root {root} is not writable by this process")


def swap_ext(path, ext):
    """The extension the files actually have, replacing whatever the template guessed."""
    base, _, _ = str(path).rpartition(".")
    return (base or str(path)) + ext


# A path template says two numbers at once and they must not be confused. `{version}` is the publish
# revision; `%04d` (or `####`, or `@@@@`) is the frame. `naming.normalise_template` reads ANY printf
# pad as the version — that is right for a code template, where `v%04d` is how a TD spells the
# revision by habit, and wrong here, where it would render frame 3 as `.0003.` and freeze the
# sequence to one frame. So the frame token is lifted out before rendering and put back after.
#
# The consequence, and it is the honest one: in a PATH template the printf form is the frame, and the
# version is `{version:03d}`.
SENTINEL = "\x00"


def _protect(template):
    """(template with the frame token held out, the token). NUL survives `naming.render` untouched:
    it is not a field, not a separator it squashes, and not one it strips from the ends."""
    t = template or ""
    m = SEQ.search(t)
    return (t, "") if not m else (t[:m.start()] + SENTINEL + t[m.end():], m.group(0))


def _clean(path):
    """Forward slashes only, and no empty segment.

    A single backslash is refused by two different errors depending on which key holds it, and in a
    `local_path` it fails as an *unknown storage* rather than as a malformed path (recipe 004). An
    empty segment comes from a template token with no value — `{output}` on a graph with one stream —
    and `//` in a local_path is not the path the server resolves back.
    """
    return re.sub(r"(?<!^)/{2,}", "/", str(path).replace("\\", "/"))


def pattern(root, template, values, version, ext):
    """The absolute destination path, frame token intact, under the storage root."""
    held, token = _protect(template or DEFAULT_PATH_TEMPLATE)
    rel = naming.render(held, values, version).replace(SENTINEL, token)
    return _clean(swap_ext(f"{root}/{rel}", ext))


def stream_name(template, values, ext):
    """The filename with the version dropped: `name`, the publish stream (recipe 004).

    `code` is one version of a stream and `name` is the stream, so the two differ by exactly the
    version token — which is why it is removed from the template and not from the rendered string.
    """
    held, token = _protect(template or DEFAULT_PATH_TEMPLATE)
    bare = VERSION_TOKEN.sub("", naming.normalise_template(held))
    rendered = naming.render(bare, values).replace(SENTINEL, token)
    return os.path.basename(_clean(swap_ext(rendered, ext)))


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
    """What `path_cache` holds. The server fills `path_cache_storage` from the path it resolved but
    leaves `path_cache` null (entity_types/PublishedFile), so a filter on it misses every row
    published over REST unless the client writes it — which is exactly what this is."""
    return str(path)[len(str(root)):].lstrip("/")


def describe_colour(declared):
    """Recorded, never applied. An empty declaration says nothing rather than guessing sRGB."""
    return f"colour space: {declared} (declared by the publisher, not converted)" if declared else ""
