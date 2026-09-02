"""Flow PT Fetch Version — a Version's media comes back into the graph, and the link is recorded.

The point is not only the pixels. A Version fetched here is remembered as an ancestor, so anything
published downstream records what it came from without the operator typing an id. A plate becomes a
previs; several Versions become one output; the chain is in Flow PT, not in someone's memory.

The inputs are a rule an artist would say out loud — *the newest approved depth on this shot* — not a
Version id. An id is the escape hatch, not the interface: `pin_version_id` overrides everything when
you need one exact Version and nothing else will do.
"""
import json

import numpy as np
import torch

from .. import lineage, media, resolve, site

MAX_ID = 2 ** 31 - 1
NONE = ""
AUTO = "auto"


def _labels(pairs):
    return [NONE] + [label for label, _ in pairs]


def _id_for(pairs, label):
    return next((i for l, i in pairs if l == label), 0)


# shotgun_api3 spells the same tree differently (probe 030), and a TD reaching for a filter will
# type the Python spelling. Accept it and translate rather than 400 on a reasonable guess.
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
    """The multi-select arrives as a list; a hand-edited graph may hold a string."""
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v if x]
    return [x.strip() for x in str(v or "").split(",") if x.strip()]


class FPTFetchVersion:
    @classmethod
    def INPUT_TYPES(cls):
        project_id = site.default_project()
        statuses = site.statuses(project_id)
        return {
            "required": {
                "project": (_labels(site.projects()),
                            {"default": site.project_name(project_id)}),
                "link_type": (site.link_type_choices(project_id),
                              {"tooltip": "Restrict the list below to one type."}),
                "link": (_labels([(l, i) for l, _, i in site.links(project_id)]),
                         {"tooltip": "What to read from. Empty searches the whole project."}),
            },
            "optional": {
                "task": ([NONE], {"tooltip": "Narrow to one Task on that entity. Optional — probe "
                                             "005 found sg_task filled on 1% of Versions."}),
                "name_contains": ("STRING", {"default": "",
                                  "tooltip": "Words that must ALL appear in the Version name, as in "
                                             "the Flow PT UI: `depth v0` matches both."}),
                # Several statuses, any of which will do. There is no "approved" concept in Flow PT —
                # the codes differ per project (probe 009), so the operator names this project's.
                #
                # A plain text field, not ComfyUI's MultiCombo. That widget renders at 16px in a slot
                # the node reserves from the widget spec rather than from the DOM, so CSS shrinks the
                # control to 33px and leaves it floating in 82px of gap. One ordinary row that works
                # on every frontend beats a prettier control that looks broken; the tooltip carries
                # the choices and `resolves to` says at once when nothing matches.
                "statuses": ("STRING", {"default": "",
                             "tooltip": "Any of these will do; empty means any status. Comma "
                                        "separated. This project allows: "
                                        + ", ".join(l for l, _ in statuses)}),
                # The API's own language, for when the fields above cannot say it. Empty means the
                # fields decide; the panel shows what they add up to, so this starts as a copy of
                # something that already works rather than a blank page.
                "filters": ("STRING", {"default": "", "multiline": True,
                            "display_name": "SG Filters",
                            "tooltip": "The Flow PT filter the fields above add up to, shown as you "
                                       "change them. Edit it and it takes over. An array is an "
                                       "implicit AND; for OR use a group: {\"logical_operator\": "
                                       "\"or\", \"conditions\": [...]} (probe 030)."}),
                "newest_by": (resolve.ORDERS, {"default": resolve.BY_VERSION,
                              "tooltip": "What 'newest' means. A re-published v002 is newer by id "
                                         "but older by intent."}),
                "pin_version_id": ("INT", {"default": 0, "min": 0, "max": MAX_ID,
                                   "tooltip": "Escape hatch: this exact Version, ignoring the rule. "
                                              "0 means resolve by the rule above."}),
                "source": ([AUTO], {"default": AUTO,
                                    "tooltip": "Which media to pull. `auto` takes the best this "
                                               "Version can actually deliver."}),
                "frame": ("INT", {"default": 1, "min": 1, "max": 1048576,
                                  "tooltip": "Frame to read from a sequence or a movie."}),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("IMAGE", "INT", "STRING")
    RETURN_NAMES = ("image", "version_id", "code")
    FUNCTION = "fetch"
    CATEGORY = "Flow PT"
    DESCRIPTION = "Read a Flow PT Version's media into the graph, recording it as a source."

    @classmethod
    def _context(cls, project, link_type, link, task):
        """(project_id, link_type, link_id, task_id) — the 'where', without the 'which'."""
        project_id = _id_for(site.projects(), project) or site.default_project()
        picked_type, picked_name = site.split_link(link)
        lt = picked_type or (site.chosen_types(link_type, project_id) or [""])[0]
        target = _id_for(site.entities(lt, project_id, q=picked_name), picked_name) if link else 0
        task_id = _id_for(site.tasks_for(lt, target), task) if (task and target) else 0
        return project_id, lt, target, task_id

    @staticmethod
    def _filters(raw):
        """Parsed override, or None. A broken filter must say so, not silently fall back."""
        raw = (raw or "").strip()
        if not raw:
            return None
        try:
            v = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"filters is not valid JSON: {e}")
        # Both shapes, because Flow PT takes both — under different Content-Types (probe 030).
        # An array is a flat implicit `and`; a dict is {"logical_operator", "conditions"} and is the
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
        """The rule, applied. Shared by execution and IS_CHANGED so the two cannot disagree."""
        project_id, lt, target, task_id = cls._context(project, link_type, link, task)
        p = site.for_project(project_id)
        codes, unknown = site.resolve_statuses(project_id, _as_list(statuses))
        if unknown:
            allowed = ", ".join(l for l, _ in site.statuses(project_id))
            return 0, "", (f"no status called {', '.join(repr(u) for u in unknown)} on this project. "
                           f"It allows: {allowed}")
        return resolve.pick(project_id, lt, target, task_id, name_contains, codes,
                            newest_by, p.get("code_regex", ""), cls._filters(filters))

    @classmethod
    def IS_CHANGED(cls, project=NONE, link_type=NONE, link=NONE, task=NONE, name_contains="",
                   statuses=(), filters="", newest_by=resolve.BY_VERSION, pin_version_id=0,
                   source=AUTO, frame=1, **kw):
        """Re-resolve at queue time, so the graph sees what has been published since.

        Without this ComfyUI caches on unchanged widgets and a re-run costs 0.00s without asking the
        site — the read node keeps serving v001 after v002 lands, which defeats resolving by rule.
        Returns the id it WOULD fetch, so it re-executes when that changes and only then.
        """
        if int(pin_version_id):
            return f"{int(pin_version_id)}:{source}:{frame}"
        try:
            site.forget("find", "versions_on")   # a status flipped a moment ago must be visible
            vid, _, _ = cls._resolve(project, link_type, link, task, name_contains, statuses,
                                     newest_by, filters)
            return f"{vid}:{source}:{frame}"
        except Exception:
            return float("nan")   # unreachable site: re-run rather than serve something stale

    def fetch(self, project=NONE, link_type=NONE, link=NONE, task=NONE, name_contains="",
              statuses=(), filters="", newest_by=resolve.BY_VERSION, pin_version_id=0, source=AUTO,
              frame=1, unique_id=None):
        if int(pin_version_id):
            vid, why = int(pin_version_id), "pinned by id"
        else:
            vid, code, why = self._resolve(project, link_type, link, task, name_contains, statuses,
                                           newest_by, filters)
            if not vid:
                # Failing at run time is exactly when you need to see what IS on that link, so the
                # error carries it rather than only the rule that missed.
                project_id, lt, target, task_id = self._context(project, link_type, link, task)
                near = site.find_versions(project_id, lt, target, task_id)[:8]
                labels = {c: l for l, c in site.statuses(project_id)}   # 'pndvs' means nothing
                listing = "\n  ".join(f"{c}  [{labels.get(st, st)}]" for c, st, _ in near)
                raise ValueError(why + (f"\nwhat is there:\n  {listing}" if near
                                        else "\nthere are no Versions there at all"))
            why = f"{code} ({why})"
        # Recorded so a publish downstream can credit what was actually resolved — a rule-resolved
        # Version is not in the prompt graph, only the rule is.
        lineage.record(unique_id, vid)

        fpt = site.client()
        v = media.version(fpt, vid)
        available = media.sources(v)
        if not available:
            raise ValueError(
                f"Version {vid} ({v.get('code')}) has no media this node can read. probe 021: "
                f"published files are not a source yet, and its path fields point at nothing here.")

        key = available[0][0] if source in (AUTO, NONE) else source.split(" — ")[0].strip()
        if key not in [k for k, _ in available]:
            raise ValueError(f"Version {vid} cannot deliver {key!r}; it has: "
                             f"{', '.join(k for k, _ in available)}")

        data, filename = media.load(v, key, frame)
        img = media.to_image(data, filename, frame)
        a = np.array(img, dtype=np.float32) / 255.0
        print(f"[Flow PT] fetched Version {vid}: {why}; source={key}")
        return (torch.from_numpy(a)[None, ...], vid, v.get("code") or "")
