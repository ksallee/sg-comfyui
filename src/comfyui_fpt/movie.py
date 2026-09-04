"""An IMAGE batch out of the graph becomes one movie. probe 022.

A Version's media is single-valued and a sequence cannot be media, so a batch publishes ONE Version
carrying ONE movie — never one Version per frame, which is what this file replaced.

`sg_uploaded_movie_mp4`, `_frame_rate` and `_transcoding_status` are deliberately absent from
FRAME_FIELDS. probe 022 measured the server filling them itself, and measured `_mp4` still serving a
transcode of a replaced file while status read 1; writing them ourselves manufactures that same
desync in a player that trusts them.

PyAV is imported inside `encode` rather than at module scope (DESIGN), so an install without it still
loads every node and fails only when someone actually publishes a batch.
"""
import io
from fractions import Fraction

import numpy as np

from . import provenance

DEFAULT_FPS = 24.0

# Frame metadata that IS ours to write, confirmed present on Version (probe 022).
FRAME_FIELDS = ("sg_first_frame", "sg_last_frame", "frame_count", "frame_range")


def frame_fields(count):
    """The batch's own range, one-based — what a frame_range reads as everywhere else."""
    return {"sg_first_frame": 1, "sg_last_frame": int(count),
            "frame_count": int(count), "frame_range": f"1-{int(count)}"}


def rate(prompt, node_id, chosen=0.0):
    """(fps, how it was decided) — the second half is shown, never dropped.

    A frame rate decides whether a supervisor reads real timing off the player, so an invented 24
    must never look like a measured one. Three sources in order: this node's own widget, a frame
    rate the graph states, and only then the default, which says that it is the default.
    """
    if chosen and float(chosen) > 0:
        return float(chosen), f"{float(chosen):g} fps, set on this node"
    found, why = provenance.frame_rate(prompt, node_id)
    if found:
        return found, f"{found:g} fps, from {why}"
    return DEFAULT_FPS, f"{DEFAULT_FPS:g} fps by default — {why}"


def to_u8(frame):
    """One frame of a ComfyUI IMAGE batch ([H,W,C] float 0-1) as uint8 RGB."""
    return (frame.cpu().numpy() * 255.0).round().clip(0, 255).astype(np.uint8)


def encode(frames, fps):
    """h264 in an mp4 container, as bytes, from a ComfyUI IMAGE batch."""
    try:
        import av   # ships with ComfyUI for its video nodes; see DESIGN
    except ImportError:
        raise RuntimeError("publishing a batch as a movie needs PyAV, which ComfyUI ships; "
                           "this install has no `av`")
    arrays = [to_u8(f) for f in frames]
    h, w = arrays[0].shape[:2]
    # yuv420p halves both axes, so libx264 refuses an odd dimension. Cropping the last row or column
    # loses one line; rescaling every pixel to dodge it would change every one of them.
    h, w = h - h % 2, w - w % 2
    buf = io.BytesIO()
    with av.open(buf, mode="w", format="mp4") as container:
        # A Fraction, not the float: PyAV wants an exact rate, and 23.976 as a float carries a
        # denominator in the billions.
        stream = container.add_stream("libx264", rate=Fraction(fps).limit_denominator(1000))
        stream.width, stream.height, stream.pix_fmt = w, h, "yuv420p"
        for a in arrays:
            picture = av.VideoFrame.from_ndarray(np.ascontiguousarray(a[:h, :w]), format="rgb24")
            for packet in stream.encode(picture):
                container.mux(packet)
        for packet in stream.encode():   # flush: the last GOP is still inside the encoder
            container.mux(packet)
    return buf.getvalue()
