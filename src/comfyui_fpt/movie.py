"""The clip a Version reviews, and the file it publishes. probe 022.

A Version's media is single-valued, so a run is ONE Version carrying ONE piece of review media. Where
that is a ComfyUI `VIDEO`, this file's job is to touch it as little as it can: a `VideoFromFile` is
already a file on disk and a deliverable is never transformed (DESIGN), and anything else is written
by `VideoInput.save_to()`, which is ComfyUI's own encoder and carries the clip's colour space, bit
depth and audio. Nothing here encodes.

`sg_uploaded_movie_mp4`, `_frame_rate` and `_transcoding_status` are deliberately absent from
FRAME_FIELDS. probe 022 measured the server filling them itself, and measured `_mp4` still serving a
transcode of a replaced file while status read 1; writing them ourselves manufactures that same
desync in a player that trusts them.

PyAV is imported inside `poster` rather than at module scope (DESIGN), so an install without it still
loads every node.
"""
import io
import os

import numpy as np

# Frame metadata that IS ours to write, confirmed present on Version (probe 022).
FRAME_FIELDS = ("sg_first_frame", "sg_last_frame", "frame_count", "frame_range")


def frame_fields(count):
    """The clip's own range, one-based — what a frame_range reads as everywhere else."""
    return {"sg_first_frame": 1, "sg_last_frame": int(count),
            "frame_count": int(count), "frame_range": f"1-{int(count)}"}


def to_u8(frame):
    """One frame of a ComfyUI IMAGE batch ([H,W,C] float 0-1) as uint8 RGB."""
    return (frame.cpu().numpy() * 255.0).round().clip(0, 255).astype(np.uint8)


def source_file(video):
    """The path this VIDEO already is, or "" when uploading that path would be a lie.

    `VideoFromFile.get_stream_source()` returns the source path even after `as_trimmed` or
    `as_cropped`, both of which answer with a new `VideoFromFile` over that same file with the window
    kept beside it. Trusting the class alone would file a ten-second plate as the two-second
    selection a supervisor asked for, and would do it silently (corpus 028). So the test is whether
    the object and the file are the same video — same size, same length as a plain `VideoFromFile`
    over that path. Both are container metadata reads; neither decodes.
    """
    try:
        from comfy_api.input_impl import VideoFromFile
    except ImportError:      # a ComfyUI too old to have the VIDEO type has no such clip to preserve
        return ""
    if not isinstance(video, VideoFromFile):
        return ""
    src = video.get_stream_source()
    # A clip held in memory has no file to leave untouched, so it takes the encode path and loses
    # nothing by it.
    if not isinstance(src, str) or not os.path.isfile(src):
        return ""
    plain = VideoFromFile(src)
    if video.get_dimensions() != plain.get_dimensions():
        return ""
    if abs(video.get_duration() - plain.get_duration()) > 1e-3:
        return ""
    return src


def stage(video, folder, stem):
    """(the file to publish, how it got there) — never a transform where a file already exists.

    `save_to` replaced a hardcoded libx264/yuv420p encode of our own that had no crf, dropped the
    audio and said nothing about colour. It carries sRGB as BT.709, HDR as BT.2020/HLG and HDR PQ as
    BT.2020/PQ, at the clip's own bit depth.
    """
    src = source_file(video)
    if src:
        return src, f"source file uploaded untouched — {os.path.basename(src)}"
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"{stem}.mp4"
    video.save_to(str(dest))
    return str(dest), "encoded by ComfyUI — VideoInput.save_to"


def poster(path):
    """Frame 1 of the file about to be uploaded, as PNG bytes.

    The site derives its own thumbnail from a movie, but only once the transcode lands, and a Version
    with no picture until then is worse. Decoded from the file rather than through `get_components()`,
    which materialises every frame as float32 — 300 frames of 4K is 27.8 GiB of thumbnail.
    """
    try:
        import av   # ships with ComfyUI for its video nodes; see DESIGN
    except ImportError:
        raise RuntimeError("reading a thumbnail off a movie needs PyAV, which ComfyUI ships; "
                           "this install has no `av`")
    with av.open(path) as container:
        frame = next(container.decode(container.streams.video[0]), None)
    if frame is None:
        raise RuntimeError(f"{os.path.basename(path)} decoded no frames, so there is no thumbnail "
                           f"and nothing to review")
    buf = io.BytesIO()
    frame.to_image().convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def describe(video, how):
    """One sentence naming the clip and which of the two paths it took. The panel reads it back.

    The rate is measured off the container (`VideoInput.get_frame_rate`), never guessed: the node's
    own `fps` widget is gone because a VIDEO states its own and `CreateVideo` is where a person sets
    one.
    """
    count = int(video.get_frame_count())
    rate = float(video.get_frame_rate())
    return count, f"{count} frames at {rate:g} fps — {how}"
