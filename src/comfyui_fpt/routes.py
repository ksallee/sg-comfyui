"""HTTP routes backing the node's pickers.

Custom nodes import at main.py:542, between PromptServer construction (536) and add_routes (556), so
appending to PromptServer.instance.routes here is registered normally.

Setup path: these serve the editor and are never touched while publishing.
"""
import json

from . import site


def _id_for(pairs, label):
    return next((i for l, i in pairs if l == label), 0)


def register():
    try:
        from server import PromptServer  # only exists inside a running ComfyUI
    except ImportError:
        return False

    from aiohttp import web

    routes = PromptServer.instance.routes

    def pairs(fn, *a, **kw):
        try:
            return web.json_response({"items": [{"label": l, "id": i} for l, i in fn(*a, **kw)]})
        except Exception as e:
            # Never 500 into the editor: an unreachable site must degrade to an empty picker.
            return web.json_response({"items": [], "error": str(e)[:200]})

    @routes.get("/fpt/projects")
    async def projects(request):
        return pairs(site.projects)

    @routes.get("/fpt/link_types")
    async def link_types(request):
        """Entity types this project links Versions to. Empty choice means all of them."""
        try:
            ts = site.link_type_choices(int(request.rel_url.query.get("project_id") or 0))
            return web.json_response({"items": [{"label": t, "id": t} for t in ts]})
        except Exception as e:
            return web.json_response({"items": [], "error": str(e)[:200]})

    @routes.get("/fpt/entities")
    async def entities(request):
        """Every type this project links Versions to, not one. Version.entity accepts 15 types."""
        q = request.rel_url.query
        try:
            # probe 017 — `contains` filters server-side, so the list is never fetched whole.
            pid = int(q.get("project_id") or 0)
            rows = site.links(pid, q.get("q", ""), site.chosen_types(q.get("type", ""), pid))
            return web.json_response({"items": [{"label": l, "type": t, "id": i} for l, t, i in rows]})
        except Exception as e:
            return web.json_response({"items": [], "error": str(e)[:200]})

    @routes.get("/fpt/tasks")
    async def tasks(request):
        q = request.rel_url.query
        return pairs(site.tasks_for, q.get("type", ""), int(q.get("id") or 0))

    @routes.get("/fpt/profile")
    async def profile(request):
        """What the profile says for ONE project. The editor needs this because link_type decides
        which entity type the link picker searches, and it is per project, not per site."""
        try:
            p = site.for_project(int(request.rel_url.query.get("project_id") or 0))
            return web.json_response({k: p.get(k) for k in
                                      ("link_type", "link_field", "code_prefix", "status")})
        except Exception as e:
            return web.json_response({"error": str(e)[:200]})

    @routes.get("/fpt/versions")
    async def versions(request):
        q = request.rel_url.query
        return pairs(site.versions, int(q.get("project_id") or 0), q.get("type", ""),
                     int(q.get("link_id") or 0), q.get("q", ""))

    @routes.get("/fpt/version_sources")
    async def version_sources(request):
        """Which tiers THIS Version can actually deliver (probe 021). A filled path field is not the
        same as a file on disk, so the editor asks per Version rather than offering a fixed list."""
        try:
            from . import media
            v = media.version(site.client(), int(request.rel_url.query.get("version_id") or 0))
            return web.json_response({"items": [{"label": label, "id": key}
                                                for key, label in media.sources(v)]})
        except Exception as e:
            return web.json_response({"items": [], "error": str(e)[:200]})

    @routes.get("/fpt/resolve")
    async def resolve_one(request):
        """What the Load node WOULD pull, and what that Version is.

        Editor-time, and it calls the node's own resolver, so the preview cannot disagree with the run.
        """
        try:
            from . import media
            from .nodes.load_version import FPTLoadVersion
            q = request.rel_url.query
            pin = int(q.get("pin_version_id") or 0)
            if pin:
                vid, code, why = pin, "", "pinned by id"
            else:
                typed = [t.strip() for x in q.getall("statuses", [])
                         for t in x.split(",") if t.strip()]
                # The widget mirrors the fields until someone edits it, so a filter identical to the
                # generated one is not an override — treating it as one would lose the friendlier
                # explanations and the "what is there" listing.
                raw = q.get("filters", "")
                pid0, lt0, tgt0, tsk0 = FPTLoadVersion._context(
                    q.get("project", ""), q.get("link_type", ""), q.get("link", ""), q.get("task", ""))
                codes0, _ = site.resolve_statuses(pid0, typed)
                same = json.dumps(FPTLoadVersion._filters(raw), sort_keys=True) == json.dumps(
                    site.version_filters(pid0, lt0, tgt0, tsk0,
                                         [t for t in (q.get("name_contains", "") or "").split() if t],
                                         codes0), sort_keys=True)
                vid, code, why = FPTLoadVersion._resolve(
                    q.get("project", ""), q.get("link_type", ""), q.get("link", ""),
                    q.get("task", ""), q.get("name_contains", ""), typed,
                    q.get("newest_by", ""), "" if same else raw)
            # What the fields add up to, in the API's own language — shown so an override can start
            # from something that already works.
            pid, lt2, tgt2, tsk2 = FPTLoadVersion._context(
                q.get("project", ""), q.get("link_type", ""), q.get("link", ""), q.get("task", ""))
            codes2, _ = site.resolve_statuses(pid, typed)
            built = (None if same else FPTLoadVersion._filters(raw)) or site.version_filters(
                pid, lt2, tgt2, tsk2,
                [t for t in (q.get("name_contains", "") or "").split() if t], codes2)

            if not vid:
                # A rule that matches nothing is the moment you most need to see what IS there, so
                # the same link and task are listed with their statuses and the filters dropped.
                project_id, lt, target, task_id = FPTLoadVersion._context(
                    q.get("project", ""), q.get("link_type", ""), q.get("link", ""), q.get("task", ""))
                colors, labels = site.status_colors(), dict(
                    (c, l) for l, c in site.statuses(project_id))
                near = [{"code": c, "status": {"code": st, "label": labels.get(st, st),
                                               "rgb": colors.get(st)}, "id": i}
                        for c, st, i in site.find_versions(project_id, lt, target, task_id)[:12]]
                return web.json_response({"id": 0, "why": why, "media": [],
                                          "candidates": near, "filters": built})
            fpt = site.client()
            project_id = int(q.get("project_id") or 0) or site.default_project()
            desc = media.describe(fpt, vid, site.statuses(project_id), site.status_colors(),
                                  site.status_icons())
            # `media`, not `sources`: the publish panel uses `sources` for the Versions a publish
            # came from, and one word meaning two things rendered "Version undefined" in the other.
            return web.json_response({**desc, "why": why, "filters": built,
                                      "media": [k for k, _ in media.sources(media.version(fpt, vid))]})
        except Exception as e:
            return web.json_response({"id": 0, "summary": str(e)[:200], "media": []})

    @routes.get("/fpt/preview_code")
    async def preview_code(request):
        """The name this publish node would write next. The node's own renderer, so the panel cannot
        promise something the run does not deliver."""
        try:
            from .nodes.publish_version import FPTPublishVersion as PV
            q = request.rel_url.query
            project_id = _id_for(site.projects(), q.get("project", "")) or site.default_project()
            p = site.for_project(project_id)
            picked_type, picked_name = site.split_link(q.get("link", ""))
            lt = picked_type or (site.chosen_types(q.get("link_type", ""), project_id) or [""])[0] \
                or p.get("link_type", "Shot")
            target = _id_for(site.entities(lt, project_id, q=picked_name), picked_name) \
                if q.get("link") else 0
            task_id = _id_for(site.tasks_for(lt, target), q.get("task", "")) \
                if (q.get("task") and target) else 0
            code = PV.next_code(q.get("code_template", ""), project_id, lt, target, task_id,
                                q.get("output_name", ""))
            return web.json_response({"code": code, "link": f"{lt} {picked_name}".strip(),
                                      "task": q.get("task", "")})
        except Exception as e:
            return web.json_response({"code": "", "error": str(e)[:200]})

    @routes.post("/fpt/preview_publish")
    async def preview_publish(request):
        """Everything this publish node would write, from the graph as it stands.

        Provenance comes from the executing graph, so the editor has to hand it over — the frontend
        already builds exactly this shape for Run (`graphToPrompt`), which is why the preview and the
        run agree. Nothing is written.
        """
        try:
            from . import fields as fpt_fields, provenance
            from .nodes.load_version import FPTLoadVersion as FV
            body = await request.json()
            prompt, node_id = body.get("prompt") or {}, str(body.get("node_id") or "")
            prov = provenance.extract(prompt, None, node_id=node_id)

            # Upstream Load nodes: a pinned one is in the graph, a rule-driven one has to be
            # resolved the same way the node will resolve it at run time.
            scope = provenance.ancestors(prompt, node_id)
            sources = []
            for nid in sorted(scope, key=lambda n: (0, int(n)) if str(n).isdigit() else (1, str(n))):
                node = prompt.get(nid) or {}
                if node.get("class_type") != "FPTLoadVersion":
                    continue
                i = node.get("inputs") or {}
                pinned = i.get("pin_version_id") or i.get("version_id") or 0
                if pinned:
                    sources.append({"id": int(pinned), "code": "", "why": "pinned"})
                    continue
                vid, code, why = FV._resolve(i.get("project", ""), i.get("link_type", ""),
                                             i.get("link", ""), i.get("task", ""),
                                             i.get("name_contains", ""), i.get("statuses", ""),
                                             i.get("newest_by", ""), i.get("filters", ""))
                sources.append({"id": vid, "code": code, "why": why})

            fpt = site.client()
            have = fpt_fields.available(fpt)
            by_id = {x["id"]: (x.get("code") or f'Version {x["id"]}') for x in sources}
            w = (prompt.get(node_id) or {}).get("inputs") or {}
            pid = next((n for l, n in site.projects() if l == w.get("project")), 0) \
                or site.default_project()
            where = fpt_fields.targets(*site.provenance_map(pid))
            values = fpt_fields.concepts(prov, [x["id"] for x in sources if x["id"]])

            def show(v):
                if isinstance(v, list):     # multi_entity: names, not a dict repr
                    return ", ".join(by_id.get(x.get("id"), str(x.get("id"))) for x in v)
                return str(v)[:160]

            rows = []
            # Every concept, not only the ones with a value: an empty seed on a graph with no
            # sampler is information, and hiding it makes the list look arbitrary. The row is named
            # for where the value LANDS, because that is the operator's decision and the thing they
            # are checking — the concept is the label beside it.
            for concept, target in where.items():
                v = values.get(concept)
                has = v not in (None, "", [])
                if target is None:
                    note = "not recorded"
                elif target == fpt_fields.DESCRIPTION:
                    note = "into the description"
                elif target in have:
                    note = "" if has else "nothing in this graph"
                else:
                    note = "field missing on this site"
                rows.append({
                    "name": (target[3:] if target.startswith("sg_") else target) if target
                            else fpt_fields.CONCEPT_LABELS[concept],
                    "label": fpt_fields.CONCEPT_LABELS[concept],
                    "value": show(v) if has else "",
                    "present": target is None or target == fpt_fields.DESCRIPTION or target in have,
                    "note": note,
                })
            # The rest of the Version, which is not provenance but is still what gets written.
            plain = [("description", w.get("note") or "", "the note below"),
                     ("sg_status_list", w.get("status") or "", "" if w.get("status") else "left unset"),
                     ("entity", w.get("link") or "", "" if w.get("link") else "not linked"),
                     ("sg_task", w.get("task") or "", "" if w.get("task") else "no task")]
            for name, val, note in plain:
                rows.append({"name": name, "value": str(val)[:160], "present": True, "note": note})

            # Media and attachments are uploads, not fields, but they are part of "what gets saved".
            uploads = ["image (thumbnail)", "sg_uploaded_movie", "<name>.provenance.json"]
            if w.get("attach_workflow", True):
                uploads.append("<name>.workflow.json — only if this client sends EXTRA_PNGINFO")
            return web.json_response({
                "fields": rows,
                "uploads": uploads,
                "sources": sources,
                "missing_fields": sorted({t for t in where.values()
                                          if t and t != fpt_fields.DESCRIPTION and t not in have}),
            })
        except Exception as e:
            return web.json_response({"error": str(e)[:300], "fields": [], "sources": []})

    @routes.get("/fpt/statuses")
    async def statuses(request):
        return pairs(site.statuses, int(request.rel_url.query.get("project_id") or 0))

    site.warm()   # prime the setup caches now, not on the operator's first page load
    return True
