#!/usr/bin/env python3
"""Create the demo's entities, idempotently.

    PYTHONPATH=src python tools/demo_setup.py            # print what it would do
    PYTHONPATH=src python tools/demo_setup.py --write    # create it

`ensure()`, not create: a Shot's `code` is optional and not unique (entity_types/Shot), so a second
run without a read would duplicate the rows. Each write here reads first and keys on `id`, which is
probe 019's precedent for idempotency.

A Task is named by `content`, not `code` (entity_types/Task). Steps are site-wide and partitioned by
`entity_type` (entity_types/Step), so a Step is matched by name against what the site has and left
off where nothing matches. A Task with only `content` is legal, and a Step created here would appear
on all the projects on the site.

Credentials reach the site through `site.client()` and are not printed: this logs entity names and
ids. `seed.py` writes Versions; nothing here does.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from comfyui_sg import site                      # noqa: E402
from comfyui_sg.site import ARRAY_JSON           # noqa: E402

# The demo's structure. `step` is a name to look for, not an id: another site has different ids and
# may not have the Step.
SHOTS = {
    "sh010": [("Plate", None), ("Roto", "Roto"), ("Prep", None),
              ("Paint", None), ("Comp", "Comp"), ("Delivery", "Online")],
}
ASSETS = {
    "mp_skyline": [("Concept", "Art")],
}


def search(sg, kind, filters, fields, size):
    """The rows matching these filters, or none where the read is refused."""
    r = sg.post(f"/entity/{kind}/_search", headers=ARRAY_JSON,
                 json={"filters": filters, "fields": fields, "page": {"size": size}})
    return r.json().get("data", []) if r.ok else []


def by_name(rows, field):
    """{name: id}, lowered. Text matching is case-insensitive on this API (field_types/text)."""
    return {(d["attributes"].get(field) or "").strip().lower(): d["id"] for d in rows}


def find(sg, kind, project_id, code):
    """The id of the row with this code on this project, or 0."""
    rows = search(sg, kind, [["project", "is", {"type": "Project", "id": project_id}],
                              ["code", "is", code]], "code", 10)
    return rows[0]["id"] if rows else 0


def steps_for(sg, entity_type):
    """The site's Steps for this entity type, by name."""
    return by_name(search(sg, "steps", [["entity_type", "is", entity_type]], "code", 100), "code")


def tasks_on(sg, entity_type, entity_id, project_id):
    """The tasks already on this entity, by content."""
    rows = search(sg, "tasks", [["project", "is", {"type": "Project", "id": project_id}],
                                 ["entity", "is", {"type": entity_type, "id": entity_id}]],
                  "content", 200)
    return by_name(rows, "content")


def create(sg, kind, body, write):
    """The new row's id, or -1 on a dry run."""
    if not write:
        return -1
    r = sg.post(f"/entity/{kind}", json=body)
    if not r.ok:
        raise RuntimeError(f"create {kind} {r.status_code}: {r.text[:200]}")
    return r.json()["data"]["id"]


def ensure(sg, kind, entity_type, project_id, code, tasks, write, log):
    """The entity and its tasks, created where the project does not already have them."""
    eid = find(sg, kind, project_id, code)
    if eid:
        log.append(f"  {entity_type} {code}: exists ({eid})")
    else:
        eid = create(sg, kind, {"project": {"type": "Project", "id": project_id}, "code": code},
                     write)
        log.append(f"  {entity_type} {code}: CREATED ({eid if write else 'dry run'})")
    # A dry run that would have created the entity has no id to attach tasks to, so it counts them.
    if not write and eid == -1:
        log.append(f"    would add {len(tasks)} task(s): " + ", ".join(t for t, _ in tasks))
        return
    have = tasks_on(sg, entity_type, eid, project_id)
    steps = steps_for(sg, entity_type)
    for content, step_name in tasks:
        if content.lower() in have:
            log.append(f"    task {content}: exists ({have[content.lower()]})")
            continue
        body = {"project": {"type": "Project", "id": project_id},
                "entity": {"type": entity_type, "id": eid}, "content": content}
        sid = steps.get((step_name or "").lower())
        if sid:
            body["step"] = {"type": "Step", "id": sid}
        tid = create(sg, "tasks", body, write)
        where = f" on Step {step_name}" if sid else " (no Step on this site)"
        log.append(f"    task {content}: CREATED ({tid if write else 'dry run'}){where}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="create the rows; default is a dry run")
    ap.add_argument("--project", type=int, default=0, help="project id (default: the profile's)")
    a = ap.parse_args()
    sg = site.client()
    project_id = a.project or site.default_project()
    if not project_id:
        print("no project: pass --project or set default_project in profile.local.json")
        return 1
    log = [f"project {project_id}" + ("" if a.write else "   DRY RUN — nothing is written")]
    for code, tasks in SHOTS.items():
        ensure(sg, "shots", "Shot", project_id, code, tasks, a.write, log)
    for code, tasks in ASSETS.items():
        ensure(sg, "assets", "Asset", project_id, code, tasks, a.write, log)
    print("\n".join(log))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
