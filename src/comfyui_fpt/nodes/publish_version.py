"""Flow PT Publish Version — an image out of the graph becomes a Version with its provenance."""
import io
import json

import numpy as np
from PIL import Image

from .. import fields as fpt_fields
from .. import lineage, naming, provenance, publish, site

MAX_ID = 2 ** 31 - 1
NONE = ""


def _png(frame):
    """One frame of a ComfyUI IMAGE batch ([H,W,C] float 0-1) as PNG bytes."""
    a = (frame.cpu().numpy() * 255.0).round().clip(0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(a).save(buf, format="PNG")
    return buf.getvalue()


def _labels(pairs):
    return [NONE] + [label for label, _ in pairs]


def _id_for(pairs, label):
    return next((i for l, i in pairs if l == label), 0)


class FPTPublishVersion:
    @classmethod
    def INPUT_TYPES(cls):
        # Re-evaluated on every /object_info request (server.py:756), so a profile edit or a new Shot
        # reaches the operator on a browser refresh. The JS extension keeps the dependent lists in step
        # while the graph is open; these are only the seed values.
        project_id = site.default_project()
        p = site.for_project(project_id)
        link_type = p.get("link_type", "Shot")
        links = site.entities(link_type, project_id)
        first_link = links[0][1] if len(links) == 1 else 0
        statuses = site.statuses(project_id)
        status_label = next((l for l, c in statuses if c == p.get("status")), NONE)

        return {
            "required": {
                "images": ("IMAGE",),
                "code": ("STRING", {"default": p.get("code_prefix", "comfy_v001"),
                         "tooltip": "Leave as `auto` to follow this show's naming convention."}),
            },
            "optional": {
                "project": (_labels(site.projects()),
                            {"default": site.project_name(project_id),
                             "tooltip": "Project to publish into."}),
                "link": (_labels(links),
                         {"tooltip": f"{link_type} this Version belongs to."}),
                "task": (_labels(site.tasks_for(link_type, first_link)),
                         {"tooltip": "Task on that entity. Often empty — probe 005 found sg_task "
                                     "filled on 1% of Versions, so it is optional by design."}),
                "status": (_labels(statuses),
                           {"default": status_label,
                            "tooltip": "Usable statuses for this project (probe 009)."}),
                "note": ("STRING", {"multiline": True, "default": "",
                                    "tooltip": "Human note. Provenance is recorded separately."}),
                "source_versions": ("STRING", {"default": "",
                                    "tooltip": "Comma-separated Version ids this was derived from."}),
                "attach_workflow": ("BOOLEAN", {"default": True}),
                "link_id": ("INT", {"default": 0, "min": 0, "max": MAX_ID,
                                    "tooltip": "Overrides `link` when non-zero, for a stale list."}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "usage_source": "COMFY_USAGE_SOURCE",
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "publish"
    CATEGORY = "Flow PT"
    OUTPUT_NODE = True
    DESCRIPTION = "Create a Flow PT Version from this image, carrying the graph that made it."

    def publish(self, images, code, project=NONE, link=NONE, task=NONE, status=NONE, note="",
                source_versions="", attach_workflow=True, link_id=0,
                prompt=None, extra_pnginfo=None, usage_source=None, unique_id=None):
        # The picked project decides, then the profile answers for THAT project — two graphs open in
        # one ComfyUI can target two shows that link Versions differently.
        project_id = _id_for(site.projects(), project) or site.default_project()
        if not project_id:
            raise ValueError("no project: pick one, or set default_project in profile.local.json")
        p = site.for_project(project_id)
        link_type = p.get("link_type", "Shot")
        link_field = p.get("link_field", "entity")   # probe 005 — never assume sg_task

        # Combos carry labels; Flow PT wants ids. Resolve narrowly rather than trusting a cached list.
        target = int(link_id) or (_id_for(site.entities(link_type, project_id, q=link), link) if link else 0)
        if link and not target:
            raise ValueError(f"no {link_type} named {link!r} in project {project_id}")
        task_id = _id_for(site.tasks_for(link_type, target), task) if (task and target) else 0
        status_code = next((c for l, c in site.statuses(project_id) if l == status), "")

        # unique_id scopes provenance to this node's branch (provenance.ancestors).
        prov = provenance.extract(prompt, extra_pnginfo, node_id=unique_id)
        prov["comfy_usage_source"] = usage_source  # which client submitted this (execution.py:216)
        wf = provenance.workflow(extra_pnginfo)

        fpt = site.client()
        # Which typed fields this site actually has. Absent until `python -m comfyui_fpt.fields` has
        # run, so the blob fallback is the honest default, not a bug.
        have = fpt_fields.available(fpt)
        # Typed ids first, then whatever a Fetch node upstream already proves. The operator can add
        # a source the graph cannot see; they should never have to retype one it can.
        src_ids = [int(x) for x in source_versions.replace(",", " ").split() if x.strip().isdigit()]
        # Widget-pinned ids come from the graph; resolved ones only exist at run time (lineage).
        upstream = provenance.ancestors(prompt or {}, unique_id) if prompt else set()
        for vid in (provenance.fetched_versions(prompt or {}, unique_id)
                    + lineage.for_nodes(upstream)):
            if vid not in src_ids:
                src_ids.append(vid)
        typed = {k: v for k, v in fpt_fields.values_for(prov, src_ids).items() if k in have}

        # `auto` means: follow the convention this show already uses, numbering per link. There is no
        # version-number field on Version (it lives in `code`), so the convention is the only source.
        # A real version-number field is authoritative where the site has one (Toolkit sites usually
        # do); the code convention is the fallback for the many sites that do not.
        vnum_field = p.get("version_number_field", "")
        next_num = None
        if code.strip().lower() == "auto":
            existing = [c for c, _, _ in site.versions_on(link_type, target, project_id)]
            rx, tpl = p.get("code_regex", ""), p.get("code_template", "")
            if not (rx and tpl):
                raise ValueError("code=auto needs code_regex and code_template in the profile — "
                                 "run /inspect-site, which infers them and reports their coverage")
            task_token = (naming.parse(existing[0], rx) or {}).get("task", "") if existing else ""
            code = naming.next_code(tpl, rx, existing, link or "", task_token)
        if vnum_field and target:
            next_num = naming.next_number(site.version_numbers(link_type, target, project_id, vnum_field))

        published = []
        for i, frame in enumerate(images):
            name = code if len(images) == 1 else f"{code}_{i + 1:02d}"
            fields = dict(typed)
            # description is the human note. The full graph goes up as an attachment, so it stays
            # readable; only a site with no provenance fields falls back to a blob here.
            fields["description"] = note if typed else json.dumps(
                {"note": note, "provenance": prov}, indent=2)
            if status_code:
                fields["sg_status_list"] = status_code
            if target:
                fields[link_field] = {"type": link_type, "id": target}
            if task_id:
                fields["sg_task"] = {"type": "Task", "id": task_id}
            if next_num is not None:
                fields[vnum_field] = next_num + i

            vid = publish.create_version(fpt, project_id, name, fields)
            png = _png(frame)
            publish.upload(fpt, vid, png, f"{name}.png", field="image")
            publish.upload(fpt, vid, png, f"{name}.png", field="sg_uploaded_movie")
            publish.attach_json(fpt, vid, prov, f"{name}.provenance.json")
            if attach_workflow and wf is not None:
                publish.attach_json(fpt, vid, wf, f"{name}.workflow.json")
            published.append(f"{name} -> Version {vid}")

        if attach_workflow and wf is None:
            published.append("no workflow attached: this client sent no EXTRA_PNGINFO")
        if not typed:
            published.append("no provenance fields on this site — run: python -m comfyui_fpt.fields")
        return {"ui": {"text": published}}
