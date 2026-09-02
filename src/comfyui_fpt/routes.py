"""HTTP routes backing the node's pickers.

Custom nodes import at main.py:542, between PromptServer construction (536) and add_routes (556), so
appending to PromptServer.instance.routes here is registered normally.

Setup path: these serve the editor and are never touched while publishing.
"""
from . import site


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
        """What the Fetch node WOULD pull, and what that Version is.

        Editor-time, and it calls the node's own resolver, so the preview cannot disagree with the run.
        """
        try:
            from . import media
            from .nodes.fetch_version import FPTFetchVersion
            q = request.rel_url.query
            pin = int(q.get("pin_version_id") or 0)
            if pin:
                vid, code, why = pin, "", "pinned by id"
            else:
                vid, code, why = FPTFetchVersion._resolve(
                    q.get("project", ""), q.get("link_type", ""), q.get("link", ""),
                    q.get("task", ""), q.get("name_contains", ""),
                    [x for x in q.getall("statuses", []) if x], q.get("newest_by", ""))
            if not vid:
                return web.json_response({"id": 0, "why": why, "summary": why, "sources": []})
            fpt = site.client()
            project_id = int(q.get("project_id") or 0) or site.default_project()
            return web.json_response({"id": vid, "code": code, "why": why,
                                      "summary": media.summary(fpt, vid, site.statuses(project_id)),
                                      "sources": [k for k, _ in media.sources(media.version(fpt, vid))]})
        except Exception as e:
            return web.json_response({"id": 0, "summary": str(e)[:200], "sources": []})

    @routes.get("/fpt/statuses")
    async def statuses(request):
        return pairs(site.statuses, int(request.rel_url.query.get("project_id") or 0))

    return True
