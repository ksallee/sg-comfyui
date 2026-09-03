"""Flow PT Publish Version — an image out of the graph becomes a Version with its provenance."""
import io
import json

import numpy as np
from PIL import Image

from .. import fields as fpt_fields
from .. import lineage, naming, provenance, publish, site

MAX_ID = 2 ** 31 - 1
# The default for an unset keyword, NOT the label a person picks — that is
# site.NO_VALUE, "(none)". Naming both NONE is what produced a combo whose
# declared value the editor could never offer back.
UNSET = ""


def _png(frame):
    """One frame of a ComfyUI IMAGE batch ([H,W,C] float 0-1) as PNG bytes."""
    a = (frame.cpu().numpy() * 255.0).round().clip(0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(a).save(buf, format="PNG")
    return buf.getvalue()


def _labels(pairs):
    """Choices with a visible "no value" first — an empty string cannot be selected back."""
    return [site.NO_VALUE] + [label for label, _ in pairs]


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
        rows = site.links(project_id)
        links = [(l, i) for l, _, i in rows]
        first_type, first_link = (rows[0][1], rows[0][2]) if len(rows) == 1 else ("", 0)
        statuses = site.statuses(project_id)
        status_label = next((l for l, c in statuses if c == p.get("status")), UNSET)

        return {
            "required": {
                "images": ("IMAGE",),
                # A template in Flow PT's own vocabulary: dotted field paths, the same ones filters
                # and ?fields use (probe 003). `{version:03d}` and `v%04d` both work. The panel shows
                # what it renders to before anything is published.
                "code_template": ("STRING", {
                    "default": p.get("code_template") or naming.DEFAULT_TEMPLATE,
                    "display_name": "name template",
                    "tooltip": "e.g. {entity.Shot.code}_{task.Task.content}_v%04d — "
                               "`entity` is what the Version hangs off, `task` its Task, `output` "
                               "the pass below. Leave a literal name to use it as-is."}),
            },
            "optional": {
                "project": (_labels(site.projects()),
                            {"default": site.project_name(project_id),
                             "tooltip": "Project to publish into."}),
                # Narrowing lives here, not in a search box beside the combo: the editor's own
                # dropdown already searches, and a second one behaves differently.
                "link_type": (site.link_type_choices(project_id),
                              {"tooltip": "Restrict the list to one type. Empty means every type "
                                          "this project uses."}),
                "link": (_labels(links),
                         {"tooltip": "What this Version belongs to. Version.entity accepts many "
                                     "types, so each option carries its own."}),
                "task": (_labels(site.tasks_for(first_type, first_link)),
                         {"tooltip": "Task on that entity. Often empty — probe 005 found sg_task "
                                     "filled on 1% of Versions, so it is optional by design."}),
                "status": (_labels(statuses),
                           {"default": status_label,
                            "tooltip": "Usable statuses for this project (probe 009)."}),
                "output_name": ("STRING", {"default": "",
                                "tooltip": "What this stream is — depth, normals, mask. Fills "
                                           "{output} in the template."}),
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

    @classmethod
    def next_code(cls, template, project_id, link_type, link_id, task_id, output_name):
        """The code this node would publish next. Shared with /fpt/preview_code so what the panel
        shows is what gets written."""
        template = (template or naming.DEFAULT_TEMPLATE).strip()
        if not naming.template_fields(template) and "{version" not in naming.normalise_template(template):
            return template          # a literal name, used as-is
        vals = site.resolve_paths(naming.template_fields(template), project_id, link_type, link_id,
                                  task_id, {"output": output_name})
        codes = [c for c, _, _ in site.find_versions(project_id, link_type, link_id)]
        return naming.render(template, vals, naming.next_version(codes, template, vals))

    @classmethod
    def VALIDATE_INPUTS(cls, project=None, link_type=None, link=None, task=None, status=None):
        """Accept what the editor offered, because the editor knows more than INPUT_TYPES did.

        These combos are seeded for the default project and then repopulated per project by the JS
        (`setOptions`), so a value the operator legitimately picked need not be in the list this
        class declared at load time. ComfyUI skips its own membership check for any input named
        here (execution.py:1019), which is the mechanism core nodes use for the same problem
        (comfy_extras/nodes_model_advanced.py:380).

        Nothing is lost: a label that resolves to no entity still fails at run time, naming the
        label and the project, which is the more useful error anyway.
        """
        return True

    RETURN_TYPES = ()
    FUNCTION = "publish"
    CATEGORY = "Flow Production Tracking"
    OUTPUT_NODE = True
    DESCRIPTION = "Create a Flow PT Version from this image, carrying the graph that made it."

    def publish(self, images, code_template=UNSET, project=UNSET, link_type=UNSET, link=UNSET, task=UNSET,
                status=UNSET, output_name="", note="",
                source_versions="", attach_workflow=True, link_id=0,
                prompt=None, extra_pnginfo=None, usage_source=None, unique_id=None):
        # The picked project decides, then the profile answers for THAT project — two graphs open in
        # one ComfyUI can target two shows that link Versions differently.
        project_id = _id_for(site.projects(), project) or site.default_project()
        if not project_id:
            raise ValueError("no project: pick one, or set default_project in profile.local.json")
        p = site.for_project(project_id)
        link_field = p.get("link_field", "entity")   # probe 005 — never assume sg_task
        # The type comes from what was picked, not from a profile default: Version.entity accepts 15
        # types and a show may use several at once.
        link, task, status = site.unset(link), site.unset(task), site.unset(status)
        picked_type, picked_name = site.split_link(link)
        # The label's own type wins; the filter is only a way to shorten the list.
        link_type = (picked_type or (site.chosen_types(link_type, project_id) or [""])[0]
                     or p.get("link_type", "Shot"))

        # Combos carry labels; Flow PT wants ids. Resolve narrowly rather than trusting a cached list.
        target = int(link_id) or (_id_for(site.entities(link_type, project_id, q=picked_name),
                                          picked_name) if link else 0)
        if link and not target:
            raise ValueError(f"no {link_type} named {picked_name!r} in project {project_id}")
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
        # Typed ids first, then whatever a Load node upstream already proves. The operator can add
        # a source the graph cannot see; they should never have to retype one it can.
        src_ids = [int(x) for x in source_versions.replace(",", " ").split() if x.strip().isdigit()]
        # Widget-pinned ids come from the graph; resolved ones only exist at run time (lineage).
        upstream = provenance.ancestors(prompt or {}, unique_id) if prompt else set()
        for vid in (provenance.loaded_versions(prompt or {}, unique_id)
                    + lineage.for_nodes(upstream)):
            if vid not in src_ids:
                src_ids.append(vid)
        # Where each concept lands is the operator's mapping, not this file's business (DESIGN).
        mapping, prov_mode = site.provenance_map(project_id)
        routed, prov_lines = fpt_fields.route(prov, src_ids, mapping, prov_mode)
        typed = {k: v for k, v in routed.items() if k in have}
        # A target the operator named that this site does not have. Dropping it silently would hide
        # a typo in their profile behind a Version that looks fine (corpus 028, loud and silent).
        missing = sorted(set(routed) - set(have))

        # The template decides the name, rendered from the entity and task it is actually linked
        # to. A real version-number field is authoritative where the site has one (Toolkit sites
        # usually do); the template's own {version} is the fallback for the many sites that do not.
        code = self.next_code(code_template, project_id, link_type, target, task_id, output_name)
        vnum_field = p.get("version_number_field", "")
        next_num = (naming.next_number(site.version_numbers(link_type, target, project_id, vnum_field))
                    if vnum_field and target else None)

        published, done = [], []
        for i, frame in enumerate(images):
            name = code if len(images) == 1 else f"{code}_{i + 1:02d}"
            fields = dict(typed)
            # description is the human note, plus whatever the operator routed into it. The full
            # graph goes up as an attachment either way, so the blob fallback is only for a site
            # that has no provenance fields and asked for nothing in the description.
            if prov_lines:
                fields["description"] = "\n".join(([note] if note else []) + prov_lines)
            elif typed:
                fields["description"] = note
            else:
                fields["description"] = json.dumps({"note": note, "provenance": prov}, indent=2)
            if status_code:
                fields["sg_status_list"] = status_code
            if target:
                fields[link_field] = {"type": link_type, "id": target}
            if task_id:
                fields["sg_task"] = {"type": "Task", "id": task_id}
            if next_num is not None:
                fields[vnum_field] = next_num + i

            vid = publish.create_version(fpt, project_id, name, fields)
            # Every lookup a name depends on. `find` is the one the template reads; missing it let
            # two publish nodes in one run propose the same version again.
            site.forget("find", "versions_on", "vnums", "paths")
            png = _png(frame)
            publish.upload(fpt, vid, png, f"{name}.png", field="image")
            publish.upload(fpt, vid, png, f"{name}.png", field="sg_uploaded_movie")
            publish.attach_json(fpt, vid, prov, f"{name}.provenance.json")
            if attach_workflow and wf is not None:
                publish.attach_json(fpt, vid, wf, f"{name}.workflow.json")
            published.append(f"{name} -> Version {vid}")
            done.append({"code": name, "id": vid, "link": f"{link_type} {picked_name}".strip(),
                         "status": status_code, "outputs": sorted(typed)})

        if attach_workflow and wf is None:
            published.append("no workflow attached: this client sent no EXTRA_PNGINFO")
        if missing:
            published.append("mapped to fields this site does not have: " + ", ".join(missing))
        if not typed and not prov_lines:
            published.append("no provenance fields on this site — run: python -m comfyui_fpt.fields")
        # `text` keeps the plain readout ComfyUI shows anywhere; `published` is what the node's own
        # panel renders — the same run, described rather than printed.
        return {"ui": {"text": published, "published": done}}
