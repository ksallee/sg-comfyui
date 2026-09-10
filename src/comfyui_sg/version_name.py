"""The name a publish takes next, and the pickers that name needs.

Imports `site` and `naming` only. The setup commands `python -m comfyui_sg.fields` and `python -m
comfyui_sg.seed` run on whatever Python is to hand, so nothing on the way to them may reach a node
class and, through it, torch.
"""
from . import naming, site


def templates(template, root_template, project_id):
    """(version-name template, root-name template) in force: the widget, else Settings, else ours.

    An empty widget takes the Settings default, so one edit under Settings reaches every saved
    graph.
    """
    p = site.for_project(project_id)
    return ((template or p.get("code_template") or naming.DEFAULT_TEMPLATE).strip(),
            (root_template or p.get("root_name") or naming.DEFAULT_ROOT_TEMPLATE).strip())


def missing_fields(template, root_template, project_id, link_id, task_id):
    """The pickers a name needs and does not have, by their on-screen names, in order.

    A template renders what it can and drops the rest, so a bare `v004` would come back looking
    finished. Both templates are read, because `{root_name}` hides whatever the root asks for.
    The panel and the run share this, so the alert and the refusal are one sentence.
    """
    name_t, root_t = templates(template, root_template, project_id)
    needs = {f.split(".")[0] for f in
             naming.template_fields(name_t) + naming.template_fields(root_t)}
    return [name for name, filled in (("link", "entity" not in needs or link_id),
                                      ("task", "task" not in needs or task_id)) if not filled]


def root_of(root_template, values, version=None):
    """The stream's name, rendered once and read by the version name, the path and the panel alike.

    A root that carries a `{version}` token is unusual, since the root is what every version of
    this publish shares. It must still render the same wherever it is read, or the Version's code
    and the folder its frames landed in name two different things.
    """
    return naming.render(root_template, values, version)


def next_name(template, project_id, link_type, link_id, task_id, root_template=""):
    """(code, version number) this node would publish next.

    The number comes back because the path template needs the same one: a Version called v003
    and a sequence written to `v001/` would be two answers to one question. `{root_name}` is
    rendered first and handed to the version template as a value, because that template is
    `{root_name}_v{version:03d}`: the stream composed, then versioned.
    """
    name_t, root_t = templates(template, root_template, project_id)
    if not naming.template_fields(name_t) and "{version" not in naming.normalise_template(name_t):
        return name_t, 1       # a literal name, used as-is
    fields = set(naming.template_fields(name_t)) | set(naming.template_fields(root_t))
    vals = site.resolve_paths(fields, project_id, link_type, link_id, task_id)
    # Two passes, because the number is counted from codes the root is pinned in and the root may
    # itself ask for that number. The count uses the root without one; the name uses the root with.
    vals["root_name"] = root_of(root_t, vals)
    codes = [c for c, _, _ in site.find_versions(project_id, link_type, link_id)]
    n = naming.next_version(codes, name_t, vals)
    vals["root_name"] = root_of(root_t, vals, n)
    return naming.render(name_t, vals, n), n


def next_code(template, project_id, link_type, link_id, task_id, root_template=""):
    """The code this node would publish next. Shared with /sg/preview_code and `seed.py`."""
    return next_name(template, project_id, link_type, link_id, task_id, root_template)[0]
