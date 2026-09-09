"""SG Load — a Version's media comes back into the graph, and the link is recorded.

The pixels are half of it. A Version loaded here is remembered as an ancestor (`lineage`), so
anything published downstream records what it came from without the operator typing an id.

The inputs are a rule an artist would say out loud — *the newest approved depth on this shot* —
rather than a Version id. `pin_version_id` is the escape hatch and overrides everything above it.
"""
import json

import torch

from .. import lineage, media, resolve, site, widgets

MAX_ID = 2 ** 31 - 1
# The default for an unset keyword. It is NOT the label a person picks — that is site.NO_VALUE,
# "(none)" — and the two must stay distinct, or a combo declares a value the editor cannot offer.
UNSET = ""
AUTO = "auto"


def _labels(pairs):
    """Choices with a visible "no value" first — an empty string cannot be selected back."""
    return [site.NO_VALUE] + [label for label, _ in pairs]


def _id_for(pairs, label):
    return next((i for l, i in pairs if l == label), 0)


# shotgun_api3 spells the same filter tree differently (probe 030), and a TD reaching for a filter
# will type the Python spelling. Accept it and translate rather than 400 on a reasonable guess.
_PY_KEYS = {"filter_operator": "logical_operator", "filters": "conditions"}
_PY_OPS = {"any": "or", "all": "and"}


def _as_rest_filter(v):
    """A filter group in REST's spelling, from either REST's or shotgun_api3's."""
    if isinstance(v, list):
        return [_as_rest_filter(x) for x in v] if v and isinstance(v[0], (list, dict)) else v
    if not isinstance(v, dict):
        return v
    out = {_PY_KEYS.get(k, k): val for k, val in v.items()}
    if "logical_operator" in out:
        out["logical_operator"] = _PY_OPS.get(str(out["logical_operator"]).lower(),
                                              str(out["logical_operator"]).lower())
    if "conditions" in out:
        out["conditions"] = [_as_rest_filter(c) for c in out["conditions"]]
    return out


def _as_list(v):
    """The multi-select arrives as a list; a hand-edited graph may hold a comma-separated string."""
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v if x]
    return [x.strip() for x in str(v or "").split(",") if x.strip()]


class SGLoadVersion:
    @classmethod
    def INPUT_TYPES(cls):
        project_id = site.default_project()
        statuses = site.statuses(project_id)
        return {
            # Order, labels and copy come from `widgets.LOAD_FIELDS`, shared with instrument.py,
            # smoke.py and the editor extension. ComfyUI's required/optional split is presentation:
            # the positional array spans both sections in declared order.
            "required": widgets.declare(
                [f for f in widgets.LOAD_FIELDS if f.name in widgets.LOAD_REQUIRED],
                choices={
                    "project": _labels(site.projects()),
                    "link": _labels([(l, i) for l, _, i in site.links(project_id)]),
                },
                overrides={"project": {"default": site.project_name(project_id)}}),
            "optional": widgets.declare(
                [f for f in widgets.LOAD_FIELDS if f.name not in widgets.LOAD_REQUIRED],
                choices={
                    # site.NO_VALUE, not "": a label a person picks, and declaring "" while the
                    # editor offers "(none)" makes ComfyUI refuse to run the graph.
                    "task": [site.NO_VALUE],
                    "source": [AUTO],
                    "newest_by": resolve.ORDERS,
                },
                overrides={
                    **widgets.folding(widgets.LOAD_FIELDS,
                                      (site.for_project(project_id).get("widgets") or {}).get("load")),
                    "source": {"default": AUTO},
                    "newest_by": {"default": resolve.BY_VERSION},
                    "pin_version_id": {"max": MAX_ID},
                    "frame_count": {"max": media.MAX_FRAMES},
                    "statuses": {"tooltip": widgets.field(widgets.LOAD_FIELDS, "statuses").tooltip
                                 + " This project allows: "
                                 + ", ".join(l for l, _ in statuses)},
                }),
            "hidden": {"unique_id": "UNIQUE_ID", "prompt": "PROMPT"},
        }

    @classmethod
    def VALIDATE_INPUTS(cls, project=None, link_type=None, link=None, task=None, source=None):
        """Accept what the editor offered, because the editor knows more than INPUT_TYPES did.

        These combos are seeded for the default project and then repopulated per project by the JS
        (`setOptions`), so a value the operator legitimately picked need not be in the list this
        class declared at load time. ComfyUI skips its own membership check for any input named here
        (execution.py:1019), the mechanism core nodes use for the same problem
        (comfy_extras/nodes_model_advanced.py:380). A label that resolves to no entity still fails
        at run time, naming the label and the project.
        """
        return True

    # | output | what it carries |
    # |---|---|
    # | image | the frames read, float32 [N,H,W,3] |
    # | version_id | the Version resolved, for a node downstream to name |
    # | code | that Version's name |
    # | colour_space | what the publisher declared, "" when nothing was |
    # | video | the clip, or the frames wrapped at a stated rate |
    # | mask | 1 - alpha, or a zero mask where the source has no alpha |
    #
    # `colour_space` is an output rather than a log line because an artist about to comp acts on it:
    # it feeds the publish node's own colour_space widget, so a claim made once upstream travels
    # with the pixels. Empty when nothing was declared — recorded, never applied, never inferred.
    #
    # `mask` is appended last, after `video`, because an output slot is additive: a graph saved
    # before it existed keeps every link it had.
    RETURN_TYPES = ("IMAGE", "INT", "STRING", "STRING", "VIDEO", "MASK")
    RETURN_NAMES = ("image", "version_id", "code", "colour_space", "video", "mask")
    FUNCTION = "load"
    CATEGORY = "Flow Production Tracking"
    DESCRIPTION = ("Read a Flow Production Tracking Version's media into the graph, recording it "
                   "as a source.")

    @classmethod
    def _context(cls, project, link_type, link, task):
        """(project_id, link_type, link_id, task_id) — the 'where', without the 'which'."""
        link, task = site.unset(link), site.unset(task)
        project_id = _id_for(site.projects(), project) or site.default_project()
        picked_type, picked_name = site.split_link(link)
        lt = picked_type or (site.chosen_types(link_type, project_id) or [""])[0]
        target = _id_for(site.entities(lt, project_id, q=picked_name), picked_name) if link else 0
        task_id = _id_for(site.tasks_for(lt, target), task) if (task and target) else 0
        return project_id, lt, target, task_id

    @staticmethod
    def _filters(raw):
        """The parsed `filters` override, or None. A broken filter raises rather than falling back."""
        raw = (raw or "").strip()
        if not raw:
            return None
        try:
            v = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Extra filters is not valid JSON. {e}")
        # Both shapes, because SG takes both under different Content-Types (probe 030). An
        # array is a flat implicit `and`; a dict is {"logical_operator", "conditions"} and is the
        # only way to express `or`, nested up to 265 groups deep.
        if isinstance(v, dict):
            return _as_rest_filter(v)
        if not isinstance(v, list):
            raise ValueError('Extra filters must be an array of conditions, for example '
                             '[["sg_status_list", "in", ["apr"]]], or one group: '
                             '{"logical_operator": "or", "conditions": [...]}.')
        return v

    @classmethod
    def _resolve(cls, project, link_type, link, task, name_contains, statuses, newest_by,
                 filters=""):
        """(version_id, code, why) for the rule. Shared by execution, IS_CHANGED and the panel."""
        project_id, lt, target, task_id = cls._context(project, link_type, link, task)
        p = site.for_project(project_id)
        codes, unknown = site.resolve_statuses(project_id, _as_list(statuses))
        if unknown:
            allowed = ", ".join(l for l, _ in site.statuses(project_id))
            return 0, "", (f"No status called {', '.join(unknown)} on this project. Use one of: "
                           f"{allowed}.")
        return resolve.pick(project_id, lt, target, task_id, name_contains, codes,
                            newest_by, p.get("code_regex", ""), cls._filters(filters),
                            where=site.unset(link) or "", template=p.get("code_template", ""))

    @classmethod
    def IS_CHANGED(cls, project=UNSET, link_type=UNSET, link=UNSET, task=UNSET, name_contains="",
                   statuses=(), filters="", newest_by=resolve.BY_VERSION, pin_version_id=0,
                   source=AUTO, frame=0, frame_count=0, **kw):
        """The id this node WOULD load, so it re-executes when that changes and only then.

        ComfyUI otherwise caches on unchanged widgets, and a node resolving by rule keeps serving
        v001 after v002 lands.
        """
        if int(pin_version_id):
            return f"{int(pin_version_id)}:{source}:{frame}:{frame_count}"
        try:
            site.forget("find", "versions")   # a status flipped a moment ago must be visible
            vid, _, _ = cls._resolve(project, link_type, link, task, name_contains, statuses,
                                     newest_by, filters)
            return f"{vid}:{source}:{frame}:{frame_count}"
        except Exception:
            return float("nan")   # unreachable site: re-run rather than serve something stale

    def load(self, project=UNSET, link_type=UNSET, link=UNSET, task=UNSET, name_contains="",
              statuses=(), filters="", newest_by=resolve.BY_VERSION, pin_version_id=0, source=AUTO,
              frame=0, frame_count=0, unique_id=None, prompt=None):
        if int(pin_version_id):
            vid, why = int(pin_version_id), "pinned by id"
        else:
            vid, code, why = self._resolve(project, link_type, link, task, name_contains, statuses,
                                           newest_by, filters)
            if not vid:
                # A rule that matches nothing is when you most need to see what IS on that link, so
                # the error carries it rather than only the rule that missed.
                project_id, lt, target, task_id = self._context(project, link_type, link, task)
                near = site.find_versions(project_id, lt, target, task_id)[:8]
                labels = {c: l for l, c in site.statuses(project_id)}   # 'pndvs' means nothing
                listing = "\n  ".join(f"{c}  [{labels.get(st, st)}]" for c, st, _ in near)
                raise ValueError(why + (f"\nVersions on this link:\n  {listing}" if near
                                        else "\nThere are no Versions on this link."))
            why = f"{code} ({why})"

        sg = site.client()
        v = media.version(sg, vid)
        available = media.sources(v)
        if not available:
            raise ValueError(media.no_media(v))

        # Each output takes its own best; a picked source makes both read that one file.
        if source in (AUTO, UNSET):
            key, clip_key = media.best(v, "image", available), media.best(v, "video", available)
        else:
            key = source.split(" — ")[0].strip()
            if key not in [k for k, _ in available]:
                # The labels, not the keys: a PublishedFile that has been renamed or re-typed no
                # longer matches the saved value, and the listing is what tells you which.
                raise ValueError(f"Version {vid} has no {key} to read. Pick one of these "
                                 f"instead:\n  " + "\n  ".join(label for _, label in available))
            clip_key = key if media.kind_of(v, key) == "movie" else ""

        # Recorded so a publish downstream can credit what was actually resolved — a rule-resolved
        # Version is not in the prompt graph, only the rule is. The file goes with it: a read that
        # came off a PublishedFile makes the downstream dependency that one file rather than every
        # file the ancestor ever published.
        pf = media.pf_of(v, key)
        lineage.record(unique_id, vid, (pf or {}).get("id", 0), prompt)

        images, alpha = media.load_frames(v, key, frame, frame_count,
                                          site.profile().get("batch_budget_gib", 0))
        n = int(images.shape[0])
        # ComfyUI's own convention (nodes.LoadImage): the mask is the inverse of the alpha channel,
        # and a source carrying none gets a 64×64 zero mask rather than a shape every node
        # downstream has to special-case.
        mask = 1.0 - alpha[..., -1] if alpha is not None else torch.zeros((n, 64, 64))
        colour = media.colour_of(v, key)
        # The frame the read STARTED at: `frame` 0 means "wherever this source begins", and a log
        # line saying "from 0" would name a frame that does not exist.
        rng = media.frame_range(v, key)
        at = (rng[0] if rng else 1) if int(frame) <= 0 else int(frame)
        got = f"{n} frames from {at}" if n > 1 else f"frame {at}"
        # A batch that came back short is a fact about the media, said out loud rather than left for
        # the graph downstream to discover as a wrong frame count.
        short = f", short of the {frame_count} asked for" if n < int(frame_count) else ""
        # The clip is fetched only when something reads it: a download nobody asked for is a cost,
        # and the frames wrapped at a stated rate are a video too.
        if clip_key and _wired(prompt, unique_id, 4):
            video, clip_why = media.clip(v, clip_key), f"the file, {clip_key}"
        else:
            fps, fps_why = media.frame_rate(v)
            video, clip_why = _wrap(images, fps), f"the frames at {fps:g} fps, {fps_why}"
        print(f"[SG] Loaded Version {vid}: {why}. Source {key}, {got}{short}. Video: {clip_why}."
              + (f" Colour space declared {colour}, recorded but not applied." if colour else ""))
        return (images, vid, v.get("code") or "", colour, video, mask)


def _wired(prompt, node_id, slot):
    """Whether any node in the prompt reads this node's output `slot`."""
    for node in (prompt or {}).values():
        for val in (node.get("inputs") or {}).values():
            if isinstance(val, list) and len(val) == 2 and str(val[0]) == str(node_id) \
                    and int(val[1]) == slot:
                return True
    return False


def _wrap(images, fps):
    """An IMAGE batch as ComfyUI's own VIDEO object. Nothing is encoded until a node saves it."""
    from fractions import Fraction

    from comfy_api.input_impl import VideoFromComponents
    from comfy_api.util import VideoComponents
    return VideoFromComponents(VideoComponents(images=images, frame_rate=Fraction(fps)))
