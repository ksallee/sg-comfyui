"""Flow PT Load Version — a Version's media comes back into the graph, and the link is recorded.

The pixels are half of it. A Version loaded here is remembered as an ancestor (`lineage`), so
anything published downstream records what it came from without the operator typing an id.

The inputs are a rule an artist would say out loud — *the newest approved depth on this shot* —
rather than a Version id. `pin_version_id` is the escape hatch and overrides everything above it.
"""
import json

import numpy as np
import torch

from .. import lineage, media, resolve, site

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


class FPTLoadVersion:
    @classmethod
    def INPUT_TYPES(cls):
        project_id = site.default_project()
        statuses = site.statuses(project_id)
        return {
            # Order is the order they are read: which show, which thing, which task, which state.
            # Everything else is the rule's fine print and lives behind ComfyUI's advanced fold.
            #
            # WIDGET ORDER IS FROZEN. widgets_values is positional, so a key inserted, removed or
            # renamed here displaces every value below it in every graph already saved. Append only,
            # and move instrument.LOAD_WIDGETS, web/fpt_entity_picker.js DECLARED and every *.json
            # under example_workflows/ and tools/workflows/ in the same commit.
            "required": {
                "project": (_labels(site.projects()),
                            {"default": site.project_name(project_id)}),
                "link": (_labels([(l, i) for l, _, i in site.links(project_id)]),
                         {"tooltip": "What to read from. Empty searches the whole project."}),
            },
            "optional": {
                # site.NO_VALUE, not UNSET: this is a label a person picks, and declaring "" while
                # the editor offers "(none)" makes ComfyUI refuse to run the graph.
                "task": ([site.NO_VALUE], {"tooltip": "Narrow to one Task on that entity. Optional — probe "
                                             "005 found sg_task filled on 1% of Versions."}),
                # Several statuses, any of which will do. Flow PT has no "approved" concept and the
                # codes differ per project (probe 009), so the operator names this project's.
                #
                # A plain text field, not ComfyUI's MultiCombo: that widget reserves its slot from
                # the widget spec rather than the DOM, so CSS shrinks the control to 33px inside an
                # 82px gap. The tooltip carries the choices instead.
                "statuses": ("STRING", {"default": "",
                             "tooltip": "Any of these will do; empty means any status. Comma "
                                        "separated. This project allows: "
                                        + ", ".join(l for l, _ in statuses)}),
                "name_contains": ("STRING", {"default": "",
                                  "tooltip": "Words that must ALL appear in the Version name, as in "
                                             "the Flow PT UI: `depth v0` matches both."}),
                "newest_by": (resolve.ORDERS, {"default": resolve.BY_VERSION,
                              "tooltip": "What 'newest' means. A re-published v002 is newer by id "
                                         "but older by intent.", "advanced": True}),
                "pin_version_id": ("INT", {"default": 0, "min": 0, "max": MAX_ID,
                                   "tooltip": "REPLACES every field above — this exact Version by "
                                              "id, whatever the rule says.\n\n"
                                              "0 is off, and the rule resolves normally. Non-zero "
                                              "and the panel says in amber that it is pinned, "
                                              "because nothing else on this node is being read.\n\n"
                                              "For when you want THIS version and not whatever is "
                                              "newest or approved right now.", "advanced": True}),
                "source": ([AUTO], {"default": AUTO,
                                    "tooltip": "Which media to pull. `auto` takes the best this "
                                               "Version can actually deliver.", "advanced": True}),
                "frame": ("INT", {"default": 0, "min": 0, "max": 1048576, "advanced": True,
                          "tooltip": "Which frame to start at, BY THE NUMBER IN THE FILENAME — 1003 "
                                     "means `plate.1003.exr`, not the 1003rd file in the folder. It "
                                     "is the number Flow PT shows you.\n\n0 is 'whatever this "
                                     "source starts at', which is the right answer nearly always and "
                                     "why this can be left alone: a plate that runs 1001-1048 needs "
                                     "no typing. Ask for a frame the sequence does not have and it "
                                     "is refused, and the error names the range it does have.\n\n"
                                     "A movie has no numbers inside it, so there this counts decoded "
                                     "frames from 1 and 0 means the same as 1."}),
                # The API's own language, for what the fields above cannot say. Empty means the
                # fields decide, and the panel shows what they add up to.
                #
                # Its height belongs to the JS extension (`textRows`): a `customtext` widget is
                # built with an options object of its own and copies nothing from this spec.
                "filters": ("STRING", {"default": "", "multiline": True,
                            "display_name": "extra filters",
                            # ComfyUI's own fold for advanced inputs — 246 core nodes use it. A
                            # hand-rolled toggle button ends up appended at the bottom, nowhere near
                            # the widget it controls, and widgets_values is positional so it cannot
                            # be moved next to it.
                            "advanced": True,
                            "tooltip": "ADDED to the fields above with AND — it narrows, it never "
                                       "replaces. Every field on this node keeps meaning what it "
                                       "says.\n\nEmpty is the normal case. Put conditions here "
                                       "for what the fields cannot express, in Flow PT's own filter "
                                       "syntax: [[\"sg_ai_model\", \"contains\", \"flux\"]]. "
                                       "An array is an implicit AND (probe 004); for OR use one "
                                       "group: {\"logical_operator\": \"or\", \"conditions\": "
                                       "[...]} (probe 030).\n\nThe panel shows the whole query "
                                       "this adds up to."}),
                # LAST, appended after the multiline box it has no business sitting under, because
                # widgets_values is positional and a widget added above an existing one displaces
                # every value in every graph already saved. A row in the wrong place is cosmetic;
                # a silently shifted value is not.
                #
                # Default 1 for the same reason: a widget's declared default is what a graph saved
                # before the widget existed loads, and such a graph asks for one image.
                "frame_count": ("INT", {"default": 1, "min": 0, "max": media.MAX_FRAMES,
                                "advanced": True,
                                "tooltip": "How many frames to read as one batch, starting at "
                                           "`frame`. 1 is a single image; 0 is all of them, to the "
                                           "end of the sequence or the movie. A sequence or a movie can "
                                           "give more; a still cannot. Large batches are refused by "
                                           "size, not by count — the error says what fits at this "
                                           "resolution."}),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
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

    # `colour_space` is an output rather than a log line because an artist about to comp acts on it:
    # it feeds the publish node's own colour_space widget, so a claim made once upstream travels
    # with the pixels. Empty when nothing was declared — recorded, never applied, never inferred.
    RETURN_TYPES = ("IMAGE", "INT", "STRING", "STRING")
    RETURN_NAMES = ("image", "version_id", "code", "colour_space")
    FUNCTION = "load"
    CATEGORY = "Flow Production Tracking"
    DESCRIPTION = "Read a Flow PT Version's media into the graph, recording it as a source."

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
            raise ValueError(f"filters is not valid JSON: {e}")
        # Both shapes, because Flow PT takes both under different Content-Types (probe 030). An
        # array is a flat implicit `and`; a dict is {"logical_operator", "conditions"} and is the
        # only way to express `or`, nested up to 265 groups deep.
        if isinstance(v, dict):
            return _as_rest_filter(v)
        if not isinstance(v, list):
            raise ValueError('SG Filters must be an array of conditions, e.g. '
                             '[["sg_status_list", "in", ["apr"]]], or a group object '
                             '{"logical_operator": "or", "conditions": [...]}')
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
            return 0, "", (f"no status called {', '.join(repr(u) for u in unknown)} on this project. "
                           f"It allows: {allowed}")
        return resolve.pick(project_id, lt, target, task_id, name_contains, codes,
                            newest_by, p.get("code_regex", ""), cls._filters(filters),
                            where=site.unset(link) or "")

    @classmethod
    def IS_CHANGED(cls, project=UNSET, link_type=UNSET, link=UNSET, task=UNSET, name_contains="",
                   statuses=(), filters="", newest_by=resolve.BY_VERSION, pin_version_id=0,
                   source=AUTO, frame=0, frame_count=1, **kw):
        """The id this node WOULD load, so it re-executes when that changes and only then.

        ComfyUI otherwise caches on unchanged widgets, and a node resolving by rule keeps serving
        v001 after v002 lands.
        """
        if int(pin_version_id):
            return f"{int(pin_version_id)}:{source}:{frame}:{frame_count}"
        try:
            site.forget("find", "versions_on")   # a status flipped a moment ago must be visible
            vid, _, _ = cls._resolve(project, link_type, link, task, name_contains, statuses,
                                     newest_by, filters)
            return f"{vid}:{source}:{frame}:{frame_count}"
        except Exception:
            return float("nan")   # unreachable site: re-run rather than serve something stale

    def load(self, project=UNSET, link_type=UNSET, link=UNSET, task=UNSET, name_contains="",
              statuses=(), filters="", newest_by=resolve.BY_VERSION, pin_version_id=0, source=AUTO,
              frame=0, frame_count=1, unique_id=None):
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
                raise ValueError(why + (f"\nwhat is there:\n  {listing}" if near
                                        else "\nthere are no Versions there at all"))
            why = f"{code} ({why})"

        fpt = site.client()
        v = media.version(fpt, vid)
        available = media.sources(v)
        if not available:
            raise ValueError(
                f"Version {vid} ({v.get('code')}) has no media this node can read: its published "
                f"files carry no path this machine has a root for, and its path fields point at "
                f"nothing here.")

        key = available[0][0] if source in (AUTO, UNSET) else source.split(" — ")[0].strip()
        if key not in [k for k, _ in available]:
            # The labels, not the keys: a PublishedFile that has been renamed or re-typed no longer
            # matches the saved value, and the listing is what tells you which.
            raise ValueError(f"Version {vid} cannot deliver {key!r}; it has:\n  "
                             + "\n  ".join(label for _, label in available))

        # Recorded so a publish downstream can credit what was actually resolved — a rule-resolved
        # Version is not in the prompt graph, only the rule is. The file goes with it: a read that
        # came off a PublishedFile makes the downstream dependency that one file rather than every
        # file the ancestor ever published.
        pf = media.pf_of(v, key)
        lineage.record(unique_id, vid, (pf or {}).get("id", 0))

        frames = media.load_frames(v, key, frame, frame_count)
        a = np.stack([np.array(img, dtype=np.float32) / 255.0 for img in frames])
        colour = media.colour_of(v, key)
        # The frame the read STARTED at: `frame` 0 means "wherever this source begins", and a log
        # line saying "from 0" would name a frame that does not exist.
        rng = media.frame_range(v, key)
        at = (rng[0] if rng else 1) if int(frame) <= 0 else int(frame)
        got = f"{len(frames)} frames from {at}" if len(frames) > 1 else f"frame {at}"
        # A batch that came back short is a fact about the media, said out loud rather than left for
        # the graph downstream to discover as a wrong frame count.
        short = f" (asked for {frame_count})" if len(frames) < int(frame_count) else ""
        print(f"[Flow PT] loaded Version {vid}: {why}; source={key}; {got}{short}"
              + (f"; colour space declared {colour} — recorded, not applied" if colour else ""))
        return (torch.from_numpy(a), vid, v.get("code") or "", colour)
