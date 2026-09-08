"""HTTP routes backing the node's pickers.

ComfyUI imports custom nodes between constructing PromptServer and calling add_routes
(main.py:542), so appending to PromptServer.instance.routes here registers normally.

Setup path: these serve the editor and are never touched while publishing.
"""
import json
import os
import re

from . import credentials, resolve, site

# SG answers an error as a JSON:API envelope whose useful half is one `detail` sentence, or
# `title` where `detail` is null, which is what a refused impersonation carries (probe 027).
_DETAIL = re.compile(r'"detail"\s*:\s*"((?:[^"\\]|\\.)*)"')
_TITLE = re.compile(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"')
# The client's own line for a refused token request: `auth[ as 'x'] <status>: <body>`.
_AUTH = re.compile(r"^auth\b[^:]*?(\d{3}): ", re.S)

# The widest id any query param may carry.
_MAX_ID = 2 ** 31 - 1


# The token endpoint's refusal of a session the site no longer holds (probe 052). It is the one
# error whose fix is a click under Settings rather than a value on the node.
_SESSION_DEAD = "Can't authenticate session token"


def _sentence(e):
    """What went wrong, in the site's own words rather than its transport's.

    One truncated sentence, never a traceback: this is read in the editor and by an artist.
    """
    text = str(e)
    if _SESSION_DEAD in text:
        return ("Your Flow Production Tracking login has expired. Open Settings, then SG, and log in "
                "again.")
    m = _DETAIL.search(text) or _TITLE.search(text)
    if not m:
        # A token request that never reached the API: a wrong address answers with a web page.
        auth = _AUTH.match(text)
        if auth and '"errors"' not in text:
            return (f"The site answered {auth.group(1)} instead of signing in. Check the site "
                    f"address, then the script name and key, under Settings, then SG.")
        return text[:200]
    try:
        out = json.loads(f'"{m.group(1)}"')[:200]   # the capture is still JSON-escaped
    except ValueError:
        out = m.group(1)[:200]
    if "'sudo'" in out:
        out = f"{out.rstrip('.')}. Check Publish as under Settings, then SG."
    elif "authenticate script" in out:
        out = f"{out.rstrip('.')}. Check the script name and key under Settings, then SG."
    return out


def _int(query, name):
    """One query param as an id: absent reads 0, anything but a whole number in range is refused."""
    raw = (query.get(name) or "").strip()
    if not raw:
        return 0
    if not raw.isdigit() or int(raw) > _MAX_ID:
        raise ValueError(f"{name} must be a whole number between 0 and {_MAX_ID}.")
    return int(raw)


def _id_for(pairs, label):
    return next((i for l, i in pairs if l == label), 0)


def _wired(widgets, name):
    """Whether that input is connected. An API-format prompt writes a link as ["node", slot] and a
    widget value as a scalar, so the shape of the entry is the answer."""
    return isinstance(widgets.get(name), list)


def _batch_limit(v, key):
    """{width, height, fits, gib} for this source, or None where the size is not free to read."""
    from . import media

    size = media.frame_size(v, key)
    if not size:
        return None
    budget = media.budget_bytes(site.profile().get("batch_budget_gib", 0))
    return {"width": size[0], "height": size[1],
            "fits": media.frames_that_fit(size, budget), "gib": round(budget / 2 ** 30, 1)}


def _files_preview(widgets, prof, project_id, link_type, target, task_id):
    """Where the files would land, resolved against the real storage row.

    A publish that copies a sequence onto a shared volume is what an operator reads back before
    pressing Run, and an unmounted root belongs here rather than at the end of a render.
    """
    if not widgets.get("register_files"):
        return []
    from . import naming, publish, sequence
    from .nodes.publish_version import SGPublishVersion as PV
    # The same resolution the run makes (publish_version.publish): the wires decide which files
    # follow, and the profile decides whether the house also keeps its review movie.
    images, video = _wired(widgets, "images"), _wired(widgets, "video")
    pf = prof.get("published_files") or {}
    want_frames = images
    want_movie = video and (not images or bool(pf.get("register_movie")))
    if not (want_frames or want_movie):
        return []
    try:
        _, root = sequence.root_for(publish.storages(site.client()), pf.get("storage", ""))
        # Two templates, the pair `publish_version._stage` picks: a sequence earns a folder and a
        # movie does not.
        seq_t = pf.get("path_template") or sequence.DEFAULT_SEQUENCE_TEMPLATE
        mov_t = pf.get("movie_path_template") or sequence.DEFAULT_MOVIE_TEMPLATE
        root_t = (widgets.get("root_name", "") or prof.get("root_name")
                  or naming.DEFAULT_ROOT_TEMPLATE)
        code, version_no = PV.next_name(widgets.get("code_template", ""), project_id, link_type,
                                        target, task_id, root_t)
        # `{root_name}` and `{version_name}` are rendered here, never looked up: resolve_paths knows
        # neither, and the run hands the path these same two names (publish_version._stage).
        fields = (set(naming.template_fields(seq_t)) | set(naming.template_fields(mov_t))
                  | set(naming.template_fields(root_t)))
        vals = site.resolve_paths(fields, project_id, link_type, target, task_id)
        vals["root_name"] = naming.render(root_t, vals, version_no)
        vals["version_name"] = code
        where = []
        if want_frames:
            where.append(sequence.pattern(root, seq_t, dict(vals, ext=".png"), version_no, ".png"))
        # A deliverable is never transformed, so the clip keeps its own extension — a run-time fact
        # this states rather than guesses.
        if want_movie:
            ext = ".<the clip's own extension>"
            where.append(sequence.pattern(root, mov_t, dict(vals, ext=ext), version_no, ext))
        if not os.path.isdir(root):
            where.append(f"{root} is not mounted. Mount it before you Run.")
        return where
    except Exception as e:
        return [f"Create Published Files is ticked, but the paths could not be worked out. "
                f"{_sentence(e)}"]


# The profile keys Settings may write, by their dotted path. Anything else stays a file edit.
DEFAULT_KEYS = ("default_project", "code_template", "root_name", "status",
                "published_files.default", "published_files.storage", "published_files.path_platform",
                "published_files.path_template", "published_files.movie_path_template",
                "published_files.register_movie", "published_files.path_to_frames",
                "published_files.path_to_movie", "published_files.colour_space")

# What a template example is rendered on: one Shot, one Task, one output, version 3.
SAMPLE = {"entity": "sh010", "task": "Roto", "sg_task": "Roto", "output": "roto",
          "step": "Roto", "ext": ".png"}


def _sample_values(template, extra=None):
    """Values for every field a template asks for: the project's own fields resolved from the
    site, since the project is known, and sample values for the entity and Task, which are not."""
    from . import naming
    vals = dict(extra or {})
    fields = [f for f in naming.template_fields(template) if f not in vals]
    vals.update(site.resolve_paths([f for f in fields if f.split(".")[0] == "project"],
                                   site.default_project()))
    for f in fields:
        if f in vals:
            continue
        if f.endswith("short_name"):
            vals[f] = "RTO"                 # a Step's short name, the way the sandbox spells Roto
        else:
            vals[f] = SAMPLE.get(f.split(".")[0], "")
    return vals


def _example(kind, template):
    """`kind` is name, root, sequence or movie."""
    from . import naming, sequence
    p = site.for_project(site.default_project())
    pf = p.get("published_files") or {}
    root_t = (template if kind == "root" else p.get("root_name")) or naming.DEFAULT_ROOT_TEMPLATE
    root_name = naming.render(root_t, _sample_values(root_t), 3)
    if kind == "root":
        return root_name
    name_t = (template if kind == "name" else p.get("code_template")) or naming.DEFAULT_TEMPLATE
    name = naming.render(name_t, _sample_values(name_t, {"root_name": root_name}), 3)
    if kind == "name":
        return name
    # Relative to the storage root, which is what a path template is; the Storage row names the root.
    extra = {"root_name": root_name, "version_name": name}
    if kind == "sequence":
        t = template or pf.get("path_template") or sequence.DEFAULT_SEQUENCE_TEMPLATE
        return sequence.pattern("/", t, _sample_values(t, extra), 3, ".png").lstrip("/")
    if kind == "movie":
        t = template or pf.get("movie_path_template") or sequence.DEFAULT_MOVIE_TEMPLATE
        return sequence.pattern("/", t, _sample_values(t, dict(extra, ext=".mov")), 3, ".mov").lstrip("/")
    return ""


def _defaults():
    """What Settings shows: the effective values for the project the nodes open on, plus the
    choices the site offers for the pickers. Storages and statuses fail soft to empty lists."""
    from . import naming, sequence
    pid = site.default_project()
    p = site.for_project(pid)
    pf = p.get("published_files") or {}
    try:
        from . import publish
        storages = [{"code": s["code"], **{k: s.get(v) or "" for k, v in sequence.PLATFORM_KEY.items()}}
                    for s in publish.storages(site.client())]
    except Exception:
        storages = []
    values = {
        "default_project": pid,
        "code_template": p.get("code_template") or "",
        "root_name": p.get("root_name") or "",
        "status": p.get("status") or "",
        "published_files.default": bool(pf.get("default")) and pf.get("default") != site.NO_VALUE,
        "published_files.storage": pf.get("storage") or "",
        "published_files.path_template": pf.get("path_template") or "",
        "published_files.movie_path_template": pf.get("movie_path_template") or "",
        "published_files.register_movie": bool(pf.get("register_movie")),
        "published_files.path_platform": pf.get("path_platform") or "",
        "published_files.path_to_frames": bool(pf.get("path_to_frames", True)),
        "published_files.path_to_movie": bool(pf.get("path_to_movie", True)),
        "published_files.colour_space": pf.get("colour_space") or "",
    }
    placeholders = {
        "code_template": naming.DEFAULT_TEMPLATE,
        "root_name": naming.DEFAULT_ROOT_TEMPLATE,
        "published_files.path_template": sequence.DEFAULT_SEQUENCE_TEMPLATE,
        "published_files.movie_path_template": sequence.DEFAULT_MOVIE_TEMPLATE,
    }
    return {"values": values, "placeholders": placeholders,
            "projects": [{"label": n, "id": i} for n, i in site.projects()],
            "storages": storages,
            "this_platform": sequence.THIS_PLATFORM,
            "statuses": [{"label": l, "code": c} for l, c in site.statuses(pid)],
            "path": str(site.profile_path())}


def register():
    try:
        from server import PromptServer  # only exists inside a running ComfyUI
    except ImportError:
        return False

    from aiohttp import web

    routes = PromptServer.instance.routes

    def answer(fn, empty):
        """One route's body, or `empty` plus one sentence. Never 500 into the editor: an
        unreachable site must degrade to an empty picker."""
        try:
            return web.json_response(fn())
        except Exception as e:
            return web.json_response(dict(empty, error=_sentence(e)))

    def items(fn):
        """The `items` envelope every picker reads."""
        return answer(lambda: {"items": fn()}, {"items": []})

    def pairs(fn):
        """`items` built from (label, id) pairs."""
        return items(lambda: [{"label": l, "id": i} for l, i in fn()])

    @routes.get("/sg/session")
    async def session(request):
        """Who this ComfyUI talks to SG as, and whether the site still agrees."""
        return answer(credentials.status, {"how": "none", "alive": False})

    @routes.post("/sg/settings")
    async def save_settings(request):
        """The Settings dialog wrote a value. The key is written, never echoed."""
        body = await request.json()

        def out():
            credentials.save_settings(body if isinstance(body, dict) else {})
            site.forget_all()
            return credentials.status()
        return answer(out, {"how": "none", "alive": False})

    @routes.post("/sg/test")
    async def test(request):
        """One round trip as whoever the nodes would publish as, so a wrong key or a refused login
        is read in Settings rather than on the first Run."""
        return answer(credentials.test, {"ok": False})

    @routes.get("/sg/defaults")
    async def defaults(request):
        """The publish defaults Settings edits, for the project the nodes open on."""
        return answer(_defaults, {"values": {}, "projects": []})

    @routes.post("/sg/defaults")
    async def save_default(request):
        """One profile value from Settings: {key, value}, dotted keys into nested blocks."""
        body = await request.json()

        def out():
            key = str(body.get("key") or "")
            if key not in DEFAULT_KEYS:
                raise ValueError(f"{key} is not a setting.")
            site.set_default(site.default_project(), key, body.get("value"))
            return _defaults()
        return answer(out, {"values": {}, "projects": []})

    @routes.get("/sg/preview_template")
    async def preview_template(request):
        """A template rendered on sample values, so a setting shows what it produces."""
        q = request.rel_url.query
        return answer(lambda: {"example": _example(q.get("kind", ""), q.get("template", ""))},
                      {"example": ""})

    @routes.post("/sg/login")
    async def login(request):
        """Start a sign-in: the site issues an approval page for the person's browser."""
        body = await request.json()
        return answer(lambda: credentials.begin(body.get("site", "")), {})

    @routes.get("/sg/login")
    async def login_poll(request):
        """Has the person approved yet. `approved` has already written the session."""
        rid = request.rel_url.query.get("request_id", "")
        return answer(lambda: credentials.finish(rid), {"state": "gone"})

    @routes.post("/sg/logout")
    async def logout(request):
        def out():
            credentials.clear_session()
            site.forget_all()
            return {"how": "none"}
        return answer(out, {})

    @routes.get("/sg/projects")
    async def projects(request):
        """label and id as everywhere else, plus what a picker row draws: code and thumbnail, and
        the project a graph that picked none opens on."""
        return answer(lambda: {
            "items": [{"label": p["name"], "id": p["id"], "code": p["code"], "image": p["image"]}
                      for p in site.project_cards()],
            "default": site.default_project()}, {"items": []})

    @routes.get("/sg/link_types")
    async def link_types(request):
        """Entity types this project links Versions to. Empty choice means all of them."""
        q = request.rel_url.query
        return items(lambda: [{"label": t, "id": t}
                              for t in site.link_type_choices(_int(q, "project_id"))])

    @routes.get("/sg/entities")
    async def entities(request):
        """Every type this project links Versions to, not one. Version.entity accepts 15 types."""
        q = request.rel_url.query

        def rows():
            # probe 017 — `contains` filters server-side, so the list is never fetched whole.
            pid = _int(q, "project_id")
            found = site.links(pid, q.get("q", ""), site.chosen_types(q.get("type", ""), pid))
            return [{"label": l, "type": t, "id": i} for l, t, i in found]
        return items(rows)

    @routes.get("/sg/tasks")
    async def tasks(request):
        q = request.rel_url.query
        return pairs(lambda: site.tasks_for(q.get("type", ""), _int(q, "id")))

    @routes.get("/sg/profile")
    async def profile(request):
        """What the profile says for ONE project. `link_type` decides which entity type the link
        picker searches, and it is per project, not per site."""
        q = request.rel_url.query

        def read():
            p = site.for_project(_int(q, "project_id"))
            return {k: p.get(k) for k in ("link_type", "link_field", "code_prefix", "status")}
        return answer(read, {})

    @routes.get("/sg/versions")
    async def versions(request):
        q = request.rel_url.query
        return pairs(lambda: site.versions(_int(q, "project_id"), q.get("type", ""),
                                           _int(q, "link_id"), q.get("q", "")))

    @routes.get("/sg/version_sources")
    async def version_sources(request):
        """What THIS Version can actually deliver (probe 021). A filled path field is not a file on
        disk, and neither is a PublishedFile on a root this machine has not mounted.

        `colour` belongs to the file rather than to the Version: two PublishedFiles on one Version
        can declare different colour spaces, and the picker is where that is chosen.
        """
        q = request.rel_url.query

        def rows():
            from . import media
            v = media.version(site.client(), _int(q, "version_id"))
            return [{"label": label, "id": key, "colour": media.colour_of(v, key)}
                    for key, label in media.sources(v)]
        return items(rows)

    @routes.get("/sg/resolve")
    async def resolve_one(request):
        """What the Load node WOULD pull, and what that Version is.

        Editor-time, and it calls the node's own resolver, so the preview cannot disagree with the
        run.
        """
        q = request.rel_url.query

        def read():
            from . import media
            from .nodes.load_version import SGLoadVersion
            site.client()     # nothing resolves until someone is connected: the sentence names Settings
            pin = _int(q, "pin_version_id")
            typed = [t.strip() for x in q.getall("statuses", [])
                     for t in x.split(",") if t.strip()]
            # `filters` holds EXTRA conditions only, ANDed onto the fields.
            raw = q.get("filters", "")
            pid, lt, target, task_id = SGLoadVersion._context(
                q.get("project", ""), q.get("link_type", ""), q.get("link", ""), q.get("task", ""))
            codes, _ = site.resolve_statuses(pid, typed)
            terms = [t for t in (q.get("name_contains", "") or "").split() if t]
            if pin:
                vid, code, why = pin, "", "pinned by id"
            else:
                vid, code, why = SGLoadVersion._resolve(
                    q.get("project", ""), q.get("link_type", ""), q.get("link", ""),
                    q.get("task", ""), q.get("name_contains", ""), typed,
                    q.get("newest_by", ""), raw)
            # The whole query in the API's own language — the fields plus whatever was added — so
            # the panel shows what is actually being asked rather than half of it.
            built = resolve.combine(
                site.version_filters(pid, lt, target, task_id, terms, codes),
                SGLoadVersion._filters(raw))

            if not vid:
                # A rule that matches nothing is the moment what IS there matters most, so the same
                # link and task are listed with their statuses and the filters dropped. With the
                # icon, because a status is drawn the same way everywhere it appears (recipe 010).
                colors = site.status_colors()
                labels = {c: l for l, c in site.statuses(pid)}
                icons = site.status_icons()
                near = [{"code": c, "status": {"code": st, "label": labels.get(st, st),
                                               "rgb": colors.get(st), "icon": icons.get(st)}, "id": i}
                        for c, st, i in site.find_versions(pid, lt, target, task_id)[:12]]
                return {"id": 0, "why": why, "media": [], "candidates": near, "filters": built}

            sg = site.client()
            project_id = _int(q, "project_id") or pid
            desc = media.describe(sg, vid, site.statuses(project_id), site.status_colors(),
                                  site.status_icons())
            v = media.version(sg, vid)
            available = media.sources(v)
            # What the node itself would pick: `auto` is a rule, and only the site knows what it
            # lands on.
            picked = q.get("source", "") or "auto"
            key = available[0][0] if (picked in ("auto", "") and available) \
                else picked.split(" — ")[0].strip()
            # `media`, not `sources`: the publish panel spends `sources` on the Versions a publish
            # came from.
            return {
                **desc, "why": why, "filters": built,
                "media": [k for k, _ in available],
                # The label of what will actually be read: the type, the file and the count that the
                # bare key cannot say.
                "source_label": next((l for k, l in available if k == key), ""),
                # The frame numbers this source has, so `frame` is read off the panel rather than
                # guessed. Only a sequence has them; a movie carries no numbering.
                "frames": (lambda r: {"first": r[0], "last": r[1], "count": r[2]} if r else None)(
                    media.frame_range(v, key)),
                # What this machine will spend on one batch, so the panel can say a plate is too
                # big to read in one go before the Run rather than after it. Only a sequence
                # answers: a movie's size would cost a decode.
                "batch": _batch_limit(v, key),
                "colour_space": media.colour_of(v, key)}
        return answer(read, {"id": 0, "media": []})

    @routes.get("/sg/preview_code")
    async def preview_code(request):
        """The name this publish node would write next. The node's own renderer, so the panel cannot
        promise something the run does not deliver."""
        q = request.rel_url.query

        def read():
            from . import naming
            from .nodes.publish_version import SGPublishVersion as PV
            site.client()     # nothing to preview until someone is connected: the sentence names Settings
            project_id = _id_for(site.projects(), q.get("project", "")) or site.default_project()
            p = site.for_project(project_id)
            picked_type, picked_name = site.split_link(q.get("link", ""))
            lt = picked_type or (site.chosen_types(q.get("link_type", ""), project_id) or [""])[0] \
                or p.get("link_type", "Shot")
            target = _id_for(site.entities(lt, project_id, q=picked_name), picked_name) \
                if q.get("link") else 0
            task_id = _id_for(site.tasks_for(lt, target), q.get("task", "")) \
                if (q.get("task") and target) else 0
            root_t = q.get("root_name", "")            # the ROOT template, not the version's name
            code = PV.next_code(q.get("code_template", ""), project_id, lt, target, task_id, root_t)
            # A template renders what it can and drops the rest, so `corridor_depth_v004` and a bare
            # `v004` come back looking equally finished. Both templates are read, because
            # `{root_name}` hides whatever the root template asks for.
            needs = {f.split(".")[0] for f in
                     naming.template_fields(q.get("code_template", "") or naming.DEFAULT_TEMPLATE)
                     + naming.template_fields(root_t or naming.DEFAULT_ROOT_TEMPLATE)}
            # Name the fields to fill in, never the consequence of leaving them empty.
            missing = [name for name, filled in
                       (("link", "entity" not in needs or target), ("task", "task" not in needs or task_id))
                       if not filled]
            if q.get("link") and not target:
                alert = f"No {lt} named {picked_name} on this project. Pick one from the list."
            elif missing:
                alert = f"Fill in the required fields ({', '.join(missing)})."
            else:
                alert = ""
            # What is already there, not only what comes next. `versions_on` is the same cached read
            # `next_name` used to pick the number, and the files are cached against the Version, so
            # scrubbing the pickers costs nothing.
            latest = {}
            rows = site.versions_on(lt, target, project_id) if target else []
            if rows:
                lcode, _lstatus, lid = rows[0]
                latest = {"id": lid, "code": lcode, "site_url": site.client().site, "files": []}
                try:
                    latest["files"] = [{"kind": f.get("type") or "file", "path": f["path"]}
                                       for f in site.cached_published_files(lid) if f.get("path")]
                except Exception:
                    pass                      # a Version whose files cannot be read still has a link
            # An empty field on the node means Settings names it, and the panel is where that
            # shows: the template in force, tagged with where it came from.
            templates = [{"label": label, "value": value, "source": "Settings"}
                         for label, own, value in
                         (("root name", root_t, p.get("root_name") or naming.DEFAULT_ROOT_TEMPLATE),
                          ("version name", q.get("code_template", ""),
                           p.get("code_template") or naming.DEFAULT_TEMPLATE))
                         if not own.strip()]
            return {"code": code, "link": f"{lt} {picked_name}".strip(),
                    "task": q.get("task", ""), "alert": alert, "latest": latest,
                    "templates": templates}
        return answer(read, {"code": ""})

    @routes.get("/sg/node_defaults")
    async def node_defaults(request):
        """What a publish node copies in from Settings, for the picked project."""
        q = request.rel_url.query

        def read():
            from .nodes.publish_version import settings_defaults
            site.client()
            pid = _id_for(site.projects(), q.get("project", "")) or site.default_project()
            return settings_defaults(pid)
        return answer(read, {})

    @routes.post("/sg/preview_publish")
    async def preview_publish(request):
        """Everything this publish node would write, from the graph as it stands.

        Provenance comes from the executing graph, so the editor hands it over in the shape the
        frontend already builds for Run (`graphToPrompt`). Nothing is written.
        """
        try:
            from . import fields as sg_fields, provenance
            from .nodes.load_version import SGLoadVersion as FV
            body = await request.json()
            prompt, node_id = body.get("prompt") or {}, str(body.get("node_id") or "")
            prov = provenance.extract(prompt, None, node_id=node_id)

            # Typed ids first, then upstream Load nodes — the order the node itself uses.
            own = (prompt.get(node_id) or {}).get("inputs") or {}
            sources = [{"id": int(x), "code": "", "why": "typed on this node"}
                       for x in str(own.get("source_versions") or "").replace(",", " ").split()
                       if x.strip().isdigit()]
            # A pinned Load node is in the graph; a rule-driven one is resolved the same way the
            # node will resolve it at run time.
            scope = provenance.ancestors(prompt, node_id)
            for nid in sorted(scope, key=lambda n: (0, int(n)) if str(n).isdigit() else (1, str(n))):
                node = prompt.get(nid) or {}
                if node.get("class_type") != "SGLoadVersion":
                    continue
                i = node.get("inputs") or {}
                pinned = i.get("pin_version_id") or i.get("version_id") or 0
                if pinned:
                    if not any(x["id"] == int(pinned) for x in sources):
                        sources.append({"id": int(pinned), "code": "", "why": "pinned"})
                    continue
                vid, code, why = FV._resolve(i.get("project", ""), i.get("link_type", ""),
                                             i.get("link", ""), i.get("task", ""),
                                             i.get("name_contains", ""), i.get("statuses", ""),
                                             i.get("newest_by", ""), i.get("filters", ""))
                if not any(x["id"] == vid for x in sources):
                    sources.append({"id": vid, "code": code, "why": why})

            sg = site.client()
            have = sg_fields.available(sg)
            by_id = {x["id"]: (x.get("code") or f'Version {x["id"]}') for x in sources}
            w = (prompt.get(node_id) or {}).get("inputs") or {}
            pid = next((n for l, n in site.projects() if l == w.get("project")), 0) \
                or site.default_project()
            where = sg_fields.targets(*site.provenance_map(pid))
            values = sg_fields.concepts(prov, [x["id"] for x in sources if x["id"]])

            def show(v):
                if isinstance(v, list):     # multi_entity: names, not a dict repr
                    return ", ".join(by_id.get(x.get("id"), str(x.get("id"))) for x in v)
                return str(v)[:160]

            rows = []
            # Every concept, not only the ones with a value: an empty seed on a graph with no
            # sampler is information. The row is named for where the value LANDS, because that is
            # the operator's decision; the concept is the label beside it.
            for concept, target in where.items():
                v = values.get(concept)
                has = v not in (None, "", [])
                if target is None:
                    note = "not mapped to a field"
                elif target == sg_fields.DESCRIPTION:
                    note = "into the description"
                elif target in have:
                    note = "" if has else "not in this graph"
                else:
                    note = "this site has no such field"
                rows.append({
                    "name": (target[3:] if target.startswith("sg_") else target) if target
                            else sg_fields.CONCEPT_LABELS[concept],
                    "label": sg_fields.CONCEPT_LABELS[concept],
                    "value": show(v) if has else "",
                    "present": target is None or target == sg_fields.DESCRIPTION or target in have,
                    "note": note,
                })
            # The rest of the Version: not provenance, but still what gets written. Resolved the way
            # the RUN resolves it rather than the way the picker displays it — the link field takes
            # {"type", "id"}, the status takes a code, and the field name is the profile's
            # (probe 005). `site.unset()` drops "(none)" and "(all types)", which are labels for the
            # operator and never values for the site.
            status, link, task = (site.unset(w.get(k)) for k in ("status", "link", "task"))
            prof = site.for_project(pid)
            link_field = prof.get("link_field", "entity")
            picked_type, picked_name = site.split_link(link)
            link_type = picked_type or prof.get("link_type", "Shot")
            target = int(w.get("link_id") or 0) or (
                _id_for(site.entities(link_type, pid, q=picked_name), picked_name) if link else 0)
            task_id = _id_for(site.tasks_for(link_type, target), task) if (task and target) else 0
            status_code = next((c for l, c in site.statuses(pid) if l == status), "") if status else ""
            plain = [("description", w.get("note") or "", "from the note field"),
                     ("sg_status_list", status_code, "" if status_code else "no status picked"),
                     (link_field, f"{link_type} {target}" if target else "",
                      "" if target else
                      (f"no {link_type} named {picked_name} on this project" if link
                       else "no link picked")),
                     ("sg_task", f"Task {task_id}" if task_id else "",
                      "" if task_id else "no task picked")]
            for name, val, note in plain:
                rows.append({"name": name, "value": str(val)[:160], "present": True, "note": note})

            # Uploads are not fields, and a copy onto a shared volume is not an upload, so each is
            # its own list of what lands.
            uploads = ["image (the thumbnail)", "sg_uploaded_movie (the review movie)",
                       "<version name>.provenance.json"]
            if w.get("attach_workflow", True):
                uploads.append("<version name>.workflow.json")
            writes = _files_preview(w, prof, pid, link_type, target, task_id)
            # Which row of the truth table this node is on. The frame count and the frame rate are
            # run-time facts, so the panel states the rule and names the path the run will take.
            if _wired(w, "video"):
                media = "the clip"
                if _wired(w, "images"):
                    media += ". The frames become Published Files."
            elif _wired(w, "images") and w.get("register_files"):
                media = "frame 1, as a still. Every frame becomes a Published File."
            elif _wired(w, "images"):
                media = "frame 1, as a still. Tick Create Published Files to publish all frames."
            else:
                media = "nothing. Wire an image or a video into this node."
            return web.json_response({
                "fields": rows,
                "uploads": uploads,
                "writes": writes,
                "media": media,
                "sources": sources,
                "missing_fields": sorted({t for t in where.values()
                                          if t and t != sg_fields.DESCRIPTION and t not in have}),
            })
        except Exception as e:
            return web.json_response({"error": _sentence(e), "fields": [], "sources": []})

    @routes.get("/sg/statuses")
    async def statuses(request):
        """Labels, codes and how to draw each one. The picker shows what the SG UI shows."""
        q = request.rel_url.query

        def rows():
            colors, icons = site.status_colors(), site.status_icons()
            # Most-used first (probe 020). A picker sorted by the schema makes an artist hunt for
            # the two codes their show actually uses among the twenty it merely allows.
            pid = _int(q, "project_id")
            used = site.status_usage(pid)
            ordered = sorted(enumerate(site.statuses(pid)),
                             key=lambda r: (-used.get(r[1][1], 0), r[0]))
            return [{"label": l, "id": c, "code": c, "rgb": colors.get(c), "icon": icons.get(c),
                     "used": used.get(c, 0)}
                    for _, (l, c) in ordered]
        return items(rows)

    site.warm()   # prime the setup caches now, not on the operator's first page load
    return True
