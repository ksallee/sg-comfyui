"""Publish a file that is already on disk as a Version.

Setup path. A chain has to start somewhere: a graph that reads its plate from ComfyUI's `input/`
cannot be pointed at SG until that plate is *in* SG, so `/track-workflow` offers this
before it replaces a loader.

Naming, link, task and version-number resolution are the publish node's own — `version_name` is
called here rather than reimplemented, so a seeded Version follows the show's convention like any
other.

It writes no AI fields by design: a file on disk does not say how it was made, so the Version reads
as `unrecorded` (media.provenance_state) rather than claiming a provenance nobody measured.
"""
import argparse
from pathlib import Path

from . import naming, publish, site, version_name


def seed(path, project="", link="", task="", code="", template="", status="", note="",
         root_name=""):
    """Create one Version from a local file. Returns (version_id, code)."""
    data = Path(path).read_bytes()
    sg = site.client()

    # The node's own resolution, so a seeded Version links the way every other one does: the label
    # carries its own type — `sh010 (Shot)` — and a bare name falls back to the project's default
    # rather than assuming one (probe 005).
    ctx = site.context(project, link, task, status)
    project_id, p, link_type = ctx.project_id, ctx.profile, ctx.link_type
    target, task_id, status_code = ctx.link_id, ctx.task_id, ctx.status_code
    if not project_id:
        raise ValueError("No project chosen. Pass --project, or set the default project under "
                         "Settings, then SG.")
    if link and not target:
        raise ValueError(f"No {link_type} named {ctx.link_name} on project {project_id}. Check the "
                         f"spelling, and use the name as it appears in Flow Production Tracking.")

    name = code or version_name.next_code(
        template, project_id, link_type, target, task_id,
        root_name or Path(path).stem)

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
    site.forget("find", "versions", "vnums", "paths")
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
                                                   "Version name under Settings, then SG.")
    ap.add_argument("--status", default="")
    ap.add_argument("--note", default="", help="a note for the Version description. Say what "
                                               "this file is a stand-in for.")
    ap.add_argument("--root-name", default="", dest="root_name",
                    help="the name every version of this publish shares, as a template or a plain "
                         'word, for example "{entity}_depth" or "depth". Leave it out to use the '
                         "file's own name.")
    a = ap.parse_args(argv)
    for path in a.path:
        vid, name = seed(path, a.project, a.link, a.task, a.code, a.template, a.status, a.note,
                         a.root_name)
        print(f"  {Path(path).name} -> Version {vid}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
