"""Publish a file that is already on disk as a Version.

Setup path. A chain has to start somewhere: a graph that reads its plate from ComfyUI's `input/`
cannot be pointed at SG until that plate is *in* SG, so `/track-workflow` offers this
before it replaces a loader.

Naming, link, task and version-number resolution are the publish node's own — `next_code` is called
here rather than reimplemented, so a seeded Version follows the show's convention like any other.

It writes no AI fields by design: a file on disk does not say how it was made, so the Version reads
as `unrecorded` (media.provenance_state) rather than claiming a provenance nobody measured.
"""
import argparse
from pathlib import Path

from . import naming, publish, site
from .nodes.publish_version import SGPublishVersion


def _pick(pairs, label):
    """The id whose label matches exactly, or 0."""
    return next((i for name, i in pairs if name == label), 0)


def seed(path, project="", link="", task="", code="", template="", status="", note="", output=""):
    """Create one Version from a local file. Returns (version_id, code)."""
    data = Path(path).read_bytes()
    sg = site.client()

    project_id = (int(project) if str(project).isdigit() else _pick(site.projects(), project)) \
        or site.default_project()
    if not project_id:
        raise ValueError("No project chosen. Pass --project, or set default_project in "
                         "profile.local.json.")
    p = site.for_project(project_id)

    # The label carries its own type — `sh010 (Shot)` — and that wins, exactly as in the node:
    # Version.entity accepts 15 types and a show may use several at once, so a bare name falls back
    # to the project's default rather than assuming one (probe 005).
    picked_type, picked_name = site.split_link(link)
    link_type = picked_type or p.get("link_type", "Shot")
    target = _pick(site.entities(link_type, project_id, q=picked_name), picked_name) if link else 0
    if link and not target:
        raise ValueError(f"No {link_type} named {picked_name} on project {project_id}. Check the "
                         f"spelling, and use the name as it appears in Flow Production Tracking.")
    task_id = _pick(site.tasks_for(link_type, target), task) if (task and target) else 0
    status_code = next((c for label, c in site.statuses(project_id) if label == status), "")

    name = code or SGPublishVersion.next_code(
        template or p.get("code_template", ""), project_id, link_type, target, task_id,
        output or Path(path).stem)

    fields = {}
    if note:
        fields["description"] = note
    if status_code:
        fields["sg_status_list"] = status_code
    if target:
        fields[p.get("link_field", "entity")] = {"type": link_type, "id": target}
    if task_id:
        fields["sg_task"] = {"type": "Task", "id": task_id}
    vnum_field = p.get("version_number_field", "")
    if vnum_field and target:
        fields[vnum_field] = naming.next_number(
            site.version_numbers(link_type, target, project_id, vnum_field))

    vid = publish.create_version(sg, project_id, name, fields)
    filename = f"{name}{Path(path).suffix or '.png'}"
    publish.upload(sg, vid, data, filename, field="image")
    publish.upload(sg, vid, data, filename, field="sg_uploaded_movie")
    # Seeding several files in one run must re-read the codes it just wrote, or every one numbers v001.
    site.forget("find", "versions_on", "vnums", "paths")
    return vid, name


def _cli(argv=None):
    ap = argparse.ArgumentParser(prog="comfyui_sg.seed", description=__doc__.split("\n")[0])
    ap.add_argument("path", nargs="+", help="the image files to publish, in order")
    ap.add_argument("--project", default="",
                    help="the project id or name. Leave it out to use default_project.")
    ap.add_argument("--link", default="",
                    help='what this belongs to, for example "sh010 (Shot)". A bare name uses '
                         'the project default type.')
    ap.add_argument("--task", default="")
    ap.add_argument("--code", default="",
                    help="the exact name to use. Leave it out to follow the show's convention.")
    ap.add_argument("--template", default="", help="a name template to use instead of the "
                                                   "project's code_template.")
    ap.add_argument("--status", default="")
    ap.add_argument("--note", default="", help="a note for the Version description. Say what "
                                               "this file is a stand-in for.")
    ap.add_argument("--output", default="", help="what this file is, for example depth or matte. "
                                                 "It fills {output} in the name template.")
    a = ap.parse_args(argv)
    for path in a.path:
        vid, name = seed(path, a.project, a.link, a.task, a.code, a.template, a.status, a.note,
                         a.output)
        print(f"  {Path(path).name} -> Version {vid}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
