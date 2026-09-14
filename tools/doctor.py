#!/usr/bin/env python3
"""Check what a publish needs on this machine, and say what to fix.

Run it as a file, like instrument.py. `-m` imports the package `__init__`, which imports the nodes
and therefore torch, and this runs on a plain Python. Without `--site` it makes no network request.
"""
import argparse
import os
import sys
import types
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
LOCAL_FILES = ("profile.local.json", "settings.local.json", "session.local.json", ".env.local")
# The route that answers where a running ComfyUI reads the profile from, on ComfyUI's default
# address. Nothing here requests it; the operator does.
PATHS_URL = "http://127.0.0.1:8188/sg/paths"

# The sample a template is rendered on: one Shot, one Roto Task, version 3. `{root_name}` and
# `{version_name}` are the two names a run passes to a path template.
SAMPLE = {"entity": "sh010", "root_name": "sh010_RTO", "version_name": "sh010_RTO_v003",
          "code": "sh010_RTO_v003", "ext": ".png"}


def modules():
    """The package's modules, imported without its `__init__`, which imports torch.

    The stub sets the package directory as `__path__`, so the submodules and their relative imports
    resolve.
    """
    pkg = types.ModuleType("comfyui_sg")
    pkg.__path__ = [str(PACK / "src" / "comfyui_sg")]
    sys.modules.setdefault("comfyui_sg", pkg)
    from comfyui_sg import credentials, naming
    from comfyui_sg import site as sg_site
    return credentials, naming, sg_site


class Report:
    """One line per check, and a non-zero exit for anything that would fail a publish."""

    failed = False

    def ok(self, text):
        print(f"ok    {text}")

    def warn(self, text):
        print(f"warn  {text}")

    def fail(self, text):
        Report.failed = True
        print(f"fail  {text}")


def check_interpreter(r):
    v = ".".join(str(n) for n in sys.version_info[:3])
    if sys.version_info < (3, 11):
        r.fail(f"Python {v} at {sys.executable}. Python 3.11 or newer is required. Run this with "
               f"the interpreter ComfyUI runs on.")
    else:
        r.ok(f"Python {v} at {sys.executable}.")

    for module, name in (("sg_groundtruth", "sg_groundtruth"), ("requests", "requests"),
                         ("PIL", "Pillow")):
        try:
            __import__(module)
            r.ok(f"{name} imports here.")
        except ImportError:
            r.fail(f"{name} does not import here. Install the requirements into this interpreter: "
                   f"{sys.executable} -m pip install -r {PACK / 'requirements.txt'}.")


def check_comfy_interpreter(r):
    comfy = Path(os.environ.get("COMFYUI_PATH", Path.home() / "dev" / "ComfyUI"))
    venv = comfy / "venv"
    python = venv / "bin" / "python"
    # By prefix, not by path: a venv's interpreter resolves to the base Python it was made from, so
    # two environments compare equal once the symlink is followed.
    if not python.exists():
        r.warn(f"No interpreter at {python}. Set COMFYUI_PATH to the ComfyUI this pack is "
               f"installed in, then run this again.")
    elif Path(sys.prefix) == venv:
        r.ok(f"This is the interpreter ComfyUI runs on, {python}.")
    else:
        r.warn(f"This is not the interpreter ComfyUI runs on, {python}. The nodes import in "
               f"ComfyUI's own environment, so install the requirements with that one too.")


def check_paths(r, credentials, sg_site):
    store = credentials.store_dir()
    r.ok(f"The pack is at {PACK}.")
    r.ok(f"The checkout root is {sg_site.ROOT}, which is where .env.local is read from.")
    if store == credentials.ROOT:
        r.ok(f"Settings and the session would be kept at {store}, the checkout root, because "
             f"ComfyUI is not running this.")
        r.ok(f"This run reads the profile from {sg_site.profile_path()}.")
        r.ok(f"ComfyUI reads it from its own protected user directory, which this run cannot see. "
             f"Open {PATHS_URL} on the ComfyUI you publish from for that path, and write the "
             f"profile there.")
    else:
        r.ok(f"Settings and the session are kept at {store}.")
        r.ok(f"ComfyUI and this run both read the profile from {sg_site.profile_path()}.")

    present = [name for name in LOCAL_FILES
               if (credentials.ROOT / name).is_file() or (store / name).is_file()]
    r.ok(f"Local files present: {', '.join(present) or 'none'}.")
    if "profile.local.json" not in present:
        r.warn("No profile.local.json yet. The pickers run on the site's own defaults; run "
               "/inspect-site to record this show's conventions. You do not need it to publish.")
    if ".env.local" not in present:
        r.warn(f"No .env.local in {credentials.ROOT}. The command-line tools read a script key "
               f"from it. ComfyUI itself reads Settings, then SG, instead.")


def sample_for(field):
    """A stand-in value for one template token, or "" where there is nothing to stand in for."""
    if field in SAMPLE:
        return SAMPLE[field]
    if field.endswith("short_name"):
        return "RTO"                       # a Step's short name, as a Roto step spells it
    head = field.split(".")[0]
    return {"entity": "sh010", "sg_task": "Roto", "project": "Demo"}.get(head, "")


def templates(profile):
    """(where, key, template) for each name and path template in the profile."""
    blocks = [("The site block", {k: v for k, v in profile.items() if k != "projects"})]
    blocks += [(f"Project {pid}", b) for pid, b in (profile.get("projects") or {}).items()]
    for where, block in blocks:
        files = block.get("published_files") or {}
        for key in ("root_name", "code_template"):
            if block.get(key):
                yield where, key, block[key]
        for key in ("path_template", "still_path_template", "movie_path_template"):
            if files.get(key):
                yield where, f"published_files.{key}", files[key]


def check_profile(r, naming, sg_site):
    path = sg_site.profile_path()
    if not path.is_file():
        return
    try:
        profile = sg_site.profile()
    except Exception as e:
        r.fail(f"{path} is not valid JSON. Fix the file, then run this again. {e}")
        return
    r.ok(f"{path.name} parses, and holds {len(profile.get('projects') or {})} project block(s).")

    for where, key, template in templates(profile):
        values, empty = {}, []
        for field in naming.template_fields(template):
            value = sample_for(field)
            values[field] = value
            if not value:
                empty.append(field)
        rendered = naming.render(template, values, 3)
        if not rendered:
            r.fail(f"{where} {key} renders nothing on a sample publish. Rewrite it around tokens "
                   f"the node fills, for example {{entity}}_v{{version:03d}}. Nothing was found "
                   f"for {', '.join(empty)}.")
        elif empty:
            r.warn(f"{where} {key} renders {rendered}, and nothing was found for "
                   f"{', '.join(empty)}. Check those names against the fields on Version.")
        else:
            r.ok(f"{where} {key} renders {rendered}.")


def check_site(r, credentials, sg_site):
    try:
        who = credentials.test()["who"]
        r.ok(f"The site answered, as {who}.")
    except Exception as e:
        r.fail(f"The site refused the connection. Open Settings, then SG, and log in or enter a "
               f"script name and application key. {e}")
        return
    client = credentials.client()

    from comfyui_sg import fields
    have, names = fields.available(client), fields.names()
    absent = [display for display, name in names.items() if name not in have]
    if absent:
        r.warn(f"{len(have)} of {len(names)} provenance fields exist on this site. Press Create "
               f"under Settings, then SG, SG Site Setup, or run the command in INSTALL.md with a "
               f"script key that can create fields. Missing: {', '.join(absent)}. You do not need "
               f"this to publish.")
    else:
        r.ok(f"All {len(names)} provenance fields exist on this site.")

    project_id = sg_site.default_project()
    if not project_id:
        r.warn("No project is set. Open Settings, then SG, and pick the project the nodes open on.")
        return
    r.ok(f"The nodes open on {sg_site.project_name(project_id) or project_id}, and link Versions to "
         f"{', '.join(sg_site.link_types(project_id)) or 'nothing yet'}.")

    check_storage(r, sg_site, client, project_id)


def check_storage(r, sg_site, client, project_id):
    try:
        from comfyui_sg import publish, sequence
    except ImportError as e:
        r.warn(f"The storage roots were not checked: {e}. Run this with the interpreter ComfyUI "
               f"runs on.")
        return
    files = sg_site.for_project(project_id).get("published_files") or {}
    rows = publish.storages(client)
    r.ok(f"Local File Storages on this site: {', '.join(s['code'] for s in rows) or 'none'}.")
    if not rows:
        return
    try:
        _, root = sequence.root_for(rows, files.get("storage", ""))
        sequence.check_root(root)
        r.ok(f"The storage root {root} is mounted here and writable.")
    except Exception as e:
        message = f"{e}"
        (r.warn if not files else r.fail)(
            f"{message} Publishing files needs it; publishing review media does not.")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tools/doctor.py", description=__doc__.split("\n")[0])
    ap.add_argument("--site", action="store_true",
                    help="also ask the site what it has: the connection, the provenance fields, "
                         "the storage roots and the link types.")
    args = ap.parse_args(argv)

    report = Report()
    check_interpreter(report)
    check_comfy_interpreter(report)
    try:
        credentials, naming, sg_site = modules()
    except ImportError as e:
        report.fail(f"The pack does not import here. Install the requirements into this "
                    f"interpreter, then run this again. {e}")
        return 1
    check_paths(report, credentials, sg_site)
    check_profile(report, naming, sg_site)
    if args.site:
        check_site(report, credentials, sg_site)
    return 1 if Report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
