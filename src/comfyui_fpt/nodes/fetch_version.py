"""Flow PT Fetch Version — a Version's media comes back into the graph, and the link is recorded.

The point is not only the pixels. A Version fetched here is remembered as an ancestor, so anything
published downstream records what it came from without the operator typing an id. A plate becomes a
previs; several Versions become one output; the chain is in Flow PT, not in someone's memory.
"""
import numpy as np
import torch

from .. import lineage, media, naming, resolve, site

MAX_ID = 2 ** 31 - 1
NONE = ""
AUTO = "auto"


class FPTFetchVersion:
    @classmethod
    def INPUT_TYPES(cls):
        project_id = site.default_project()
        p = site.for_project(project_id)
        link_type = p.get("link_type", "Shot")
        return {
            "required": {
                # Authoritative, and the only thing downstream provenance reads — a label would have
                # to be re-resolved against a site that may have moved on.
                "version_id": ("INT", {"default": 0, "min": 0, "max": MAX_ID,
                                       "tooltip": "Used when select is 'pinned id'; the picker sets it."}),
                "select": (resolve.MODES, {"default": resolve.LATEST,
                           "tooltip": "Resolve at run time, so a graph re-run picks up whatever was "
                                      "published since. 'pinned id' freezes one Version."}),
            },
            "optional": {
                "project": (_labels(site.projects()),
                            {"default": site.project_name(project_id)}),
                "link": (_labels(site.entities(link_type, project_id)),
                         {"tooltip": f"Narrow to one {link_type}."}),
                "version": ([NONE], {"tooltip": "Versions in that project, newest first."}),
                # Populated per Version by the editor: only tiers this Version can actually deliver
                # are offered (probe 021), because a filled path field is not the same as a file.
                "source": ([AUTO], {"default": AUTO,
                                    "tooltip": "Which media to pull. `auto` takes the best available."}),
                "match": ("STRING", {"default": "",
                          "tooltip": "Substring the code must contain, e.g. 'comp'. Empty means any."}),
                "frame": ("INT", {"default": 1, "min": 1, "max": 1048576,
                                  "tooltip": "Frame to read from a sequence or a movie."}),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("IMAGE", "INT", "STRING")
    RETURN_NAMES = ("image", "version_id", "code")
    FUNCTION = "fetch"
    CATEGORY = "Flow PT"
    DESCRIPTION = "Pull a Flow PT Version's media into the graph, recording it as a source."

    def fetch(self, version_id, select=resolve.LATEST, project=NONE, link=NONE, version=NONE,
              source=AUTO, match="", frame=1, unique_id=None):
        project_id = _id_for(site.projects(), project) or site.default_project()
        p = site.for_project(project_id)
        link_type = p.get("link_type", "Shot")

        if select == resolve.PINNED:
            vid, why = int(version_id), "pinned"
        else:
            target = _id_for(site.entities(link_type, project_id, q=link), link) if link else 0
            if not target:
                raise ValueError(f"select={select!r} resolves against a {link_type}; pick one in `link`")
            vid, code, why = resolve.pick(select, link_type, target, project_id, match,
                                          p.get("approved_status", ""), p.get("code_regex", ""))
            if not vid:
                raise ValueError(why)
            why = f"{code} ({why})"
        if not vid:
            raise ValueError("no Version: pick one, or set version_id directly")
        # Recorded so a publish downstream can credit what was actually resolved — the prompt graph
        # only carries the widget, which is 0 for every mode but 'pinned id'.
        lineage.record(unique_id, vid)

        fpt = site.client()
        v = media.version(fpt, vid)
        available = media.sources(v)
        if not available:
            raise ValueError(
                f"Version {vid} ({v.get('code')}) has no media this node can read. probe 021: "
                f"published files are not a source yet, and its path fields point at nothing here.")

        key = available[0][0] if source in (AUTO, NONE) else source.split(" — ")[0].strip()
        keys = [k for k, _ in available]
        if key not in keys:
            raise ValueError(f"Version {vid} cannot deliver {key!r}; it has: {', '.join(keys)}")

        data, filename = media.load(v, key, frame)
        img = media.to_image(data, filename, frame)
        a = np.array(img, dtype=np.float32) / 255.0
        print(f"[Flow PT] fetched Version {vid}: {why}; source={key}")
        return (torch.from_numpy(a)[None, ...], vid, v.get("code") or "")


def _labels(pairs):
    return [NONE] + [label for label, _ in pairs]


def _id_for(pairs, label):
    return next((i for l, i in pairs if l == label), 0)
