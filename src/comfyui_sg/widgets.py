"""The widget table both nodes are declared from: order, kind, label and copy, stated once.

ComfyUI stores widget values positionally, so the order of each tuple below IS the saved-graph
format. Append only: never insert, remove or rename once a graph outside this repo has been saved.

`instrument.py`, `tools/smoke.py` and the editor extension all read these lists rather than
repeating them, so there is one order and nothing to keep in step by hand.

Pure data. Nothing here imports the rest of the package, which is what lets `instrument.py` read it
on a machine with no torch and no route to the site.
"""
from dataclasses import dataclass

# What a `kind` becomes in ComfyUI's own vocabulary. A combo is a list of labels, not a type name.
KINDS = {"text": "STRING", "multiline": "STRING", "int": "INT", "bool": "BOOLEAN"}


@dataclass(frozen=True)
class Field:
    """One widget: what it is called, what it holds, and how it is shown."""

    name: str
    kind: str
    tooltip: str = ""
    label: str = ""          # display_name, where it differs from the name
    advanced: bool = False
    default: object = None
    choices: tuple = ()      # a fixed combo's values
    dynamic: bool = False    # a combo whose values the node supplies per project
    minimum: int = 0
    maximum: int = 0
    placeholder: str = ""


# Decided in the order they are decided: which show, what it belongs to, which task, what state it
# is in, what it is called, whether it is a deliverable, and last the note a person writes. The
# fold holds what a house sets once.
PUBLISH_FIELDS = (
    Field("project", "combo", dynamic=True,
          tooltip="Project to publish into."),
    Field("link", "combo", dynamic=True,
          tooltip="The Shot, Asset or other entity this Version belongs to."),
    Field("task", "combo", dynamic=True,
          tooltip="Task this Version is for, if there is one."),
    Field("status", "combo", dynamic=True,
          tooltip="Status to set on the new Version."),
    # Above `code_template` and out of the fold: the stream is what changes between runs when
    # someone is exploring variations, and the version name usually just builds on it.
    Field("root_name", "text", label="root name",
          tooltip="The name shared by all versions of this publish, without a version number, for "
                  "example {entity}_matte. It names the folder the files land in, and version "
                  "name can build on it with {root_name}. A token with no value drops out with "
                  "its separator. Empty uses the default under Settings, then SG."),
    Field("code_template", "text", label="version name",
          tooltip="The name given to the new Version, for example "
                  "{entity}_plate_v{version:03d}. Use {root_name} to build on the root name, and "
                  "{version:03d} or v%04d to pad the number. Empty uses the default under "
                  "Settings, then SG."),
    Field("register_files", "bool", label="Create Published Files", default=False,
          tooltip="Publish the files themselves beside the Version, copied to the storage root "
                  "this project's profile names."),
    # Its height belongs to the JS extension (`textRows`): a `customtext` widget is built with an
    # options object of its own and copies nothing from this spec.
    Field("note", "multiline", default="",
          placeholder="What someone should know about this version.",
          tooltip="A note for the people who will read this Version, written to its description."),
    Field("colour_space", "text", advanced=True, default="",
          tooltip="The colour space these pixels are already in, for example sRGB or ACEScg. It is "
                  "recorded with the Version, never applied to the pixels."),
    Field("source_versions", "text", advanced=True, default="",
          tooltip="Version ids this was made from, separated by commas, for example 1042, 1043."),
    Field("link_id", "int", advanced=True, default=0,
          tooltip="The id to link this Version to, used instead of the link picker when it is "
                  "not 0."),
    Field("attach_workflow", "bool", advanced=True, default=True,
          tooltip="Attach the graph that made this Version, so the run can be opened again."),
    Field("format", "combo", advanced=True, label="format", default="8-bit PNG",
          choices=("8-bit PNG", "16-bit PNG", "EXR 32-bit float"),
          tooltip="What the published frames are written as, for example EXR 32-bit float for a "
                  "scene-linear plate. The review still stays 8-bit PNG."),
)

# Which show, what to read from, which task, which of its media, and which frames. The fold holds
# the rule for choosing between candidates, which a graph settles once and rarely reopens.
LOAD_FIELDS = (
    Field("project", "combo", dynamic=True,
          tooltip="Project to read from."),
    Field("link", "combo", dynamic=True,
          tooltip="The Shot, Asset or other entity to read from. Leave it empty to search the "
                  "whole project."),
    # Optional by design: probe 005 found sg_task set on 1% of Versions.
    Field("task", "combo", dynamic=True,
          tooltip="Narrow the search to one Task on that entity."),
    # Text, not ComfyUI's MultiCombo: that widget reserves its slot from the widget spec rather
    # than the DOM, so CSS shrinks the control to 33px inside an 82px gap. The node appends this
    # project's own codes to the tooltip, because SG has no "approved" concept and the codes
    # differ per project (probe 009).
    Field("statuses", "text", default="",
          tooltip="The statuses to accept, separated by commas; empty accepts any."),
    Field("name_contains", "text", default="",
          tooltip="Words that must all appear in the Version name, for example depth v0."),
    # An override: each output takes its own best on auto, and a picked file feeds both.
    Field("source", "combo", dynamic=True, advanced=True,
          tooltip="Read both outputs from this one file. Auto takes the best for each: the frames "
                  "on the storage for image, the movie for video."),
    Field("frame", "int", advanced=True, default=0, minimum=0, maximum=1048576,
          tooltip="The frame to start at, by the number in the filename: 1003 means "
                  "plate.1003.exr. 0 starts wherever the sequence starts, so a plate running "
                  "1001-1048 needs no typing. A movie has no frame numbers inside it, so there "
                  "the count starts at 1."),
    # 0, so the node reads the whole plate without being told to. Both frame widgets sit in the
    # fold on the strength of that default: a batch past the size budget is refused with the count
    # that fits, and the panel names the range before a run.
    Field("frame_count", "int", advanced=True, default=0, minimum=0,
          tooltip="How many frames to read as one batch, starting at the frame above. 0 is all "
                  "frames to the end of the sequence or the movie, and 1 is a single image. A "
                  "batch too large to hold is refused, and the error says how many fit."),
    Field("newest_by", "combo", advanced=True,
          tooltip="What newest means when several Versions match."),
    # `advanced` is ComfyUI's own fold, used by 246 core nodes. A hand-rolled toggle ends up
    # appended at the bottom, nowhere near the widget it controls, and cannot be moved next to it.
    Field("filters", "multiline", label="extra filters", advanced=True, default="",
          tooltip="Extra conditions in Flow Production Tracking's filter syntax, added to the fields above with "
                  "AND, for example [[\"sg_ai_model\", \"contains\", \"flux\"]]. For OR, use one "
                  "group: {\"logical_operator\": \"or\", \"conditions\": [...]}. Leave it empty "
                  "to let the fields above decide."),
    Field("pin_version_id", "int", advanced=True, default=0, minimum=0,
          tooltip="Load this exact Version by id, ignoring all the fields above. 0 loads whatever "
                  "those fields find."),
)

# The load node's first two are ComfyUI-required; everything else on both nodes is optional. The
# positional array spans both sections in declared order, so this split changes nothing about it.
LOAD_REQUIRED = ("project", "link")


def names(fields):
    """The declared widget names, in order. This is the saved-graph layout."""
    return [f.name for f in fields]


def field(fields, name):
    """The Field called `name`."""
    return next(f for f in fields if f.name == name)


def spec(f, choices=(), override=None):
    """One field as ComfyUI's `(type, options)` pair.

    `choices` fills a dynamic combo; `override` supplies what only the node knows, such as a
    default read from the site profile or a bound held elsewhere as a constant.
    """
    options = {"tooltip": f.tooltip} if f.tooltip else {}
    if f.label:
        options["display_name"] = f.label
    if f.advanced:
        options["advanced"] = True
    if f.kind == "multiline":
        options["multiline"] = True
    if f.placeholder:
        options["placeholder"] = f.placeholder
    if f.kind == "int":
        options["min"], options["max"] = f.minimum, f.maximum
    if f.default is not None:
        options["default"] = f.default
    options.update(override or {})
    # An override may put a field back in the normal set, and ComfyUI reads the key's presence
    # rather than its value, so a False has to be removed instead of written.
    if options.get("advanced") is False:
        options.pop("advanced")
    kind = list(choices or f.choices) if f.kind == "combo" else KINDS[f.kind]
    return (kind, options)


def folding(fields, block):
    """Per-field `advanced` overrides from a profile block naming `normal` and `advanced` fields.

    Which fields a house wants in front of it is a house decision, not this file's, so the split
    below is a default rather than a rule. A name in neither list keeps the declared setting.
    """
    normal = set((block or {}).get("normal") or ())
    advanced = set((block or {}).get("advanced") or ())
    out = {}
    for f in fields:
        if f.name in advanced:
            out[f.name] = {"advanced": True}
        elif f.name in normal:
            out[f.name] = {"advanced": False}
    return out


def declare(fields, choices=None, overrides=None):
    """`{name: spec}` for every field, in declared order."""
    choices, overrides = choices or {}, overrides or {}
    return {f.name: spec(f, choices.get(f.name, ()), overrides.get(f.name))
            for f in fields}
