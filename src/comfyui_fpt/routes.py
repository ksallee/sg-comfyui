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

    @routes.get("/fpt/entities")
    async def entities(request):
        q = request.rel_url.query
        # probe 017 — `contains` filters server-side, so the list never has to be fetched whole.
        return pairs(site.entities, q.get("type", ""), int(q.get("project_id") or 0), q.get("q", ""))

    @routes.get("/fpt/tasks")
    async def tasks(request):
        q = request.rel_url.query
        return pairs(site.tasks_for, q.get("type", ""), int(q.get("id") or 0))

    @routes.get("/fpt/statuses")
    async def statuses(request):
        return pairs(site.statuses, int(request.rel_url.query.get("project_id") or 0))

    return True
