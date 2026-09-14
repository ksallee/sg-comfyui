"""HTTP routes backing the node's pickers.

ComfyUI imports custom nodes between constructing PromptServer and calling add_routes
(main.py:542), so appending to PromptServer.instance.routes here registers normally.

Setup path: these serve the editor and are never touched while publishing.
"""
import json
import re

from . import credentials, resolve, site

# An SG error is a JSON:API envelope. The useful half is one `detail` sentence, or `title` where
# `detail` is null. A refused impersonation returns `title` (probe 027).
_DETAIL = re.compile(r'"detail"\s*:\s*"((?:[^"\\]|\\.)*)"')
_TITLE = re.compile(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"')
# The client's own line for a refused token request: `auth[ as 'x'] <status>: <body>`.
_AUTH = re.compile(r"^auth\b[^:]*?(\d{3}): ", re.S)
# The site's 404 for a missing entity: `Version: 1 not found`. That reads as a field named
# Version, so the sentence restates it in words before quoting it.
_NOT_FOUND = re.compile(r"^(\w+):\s*(\d+)\s+not found\.?$", re.I)

# The largest id any query param accepts.
_MAX_ID = 2 ** 31 - 1


# The token endpoint's refusal of a session the site no longer recognises (probe 052). Its fix is
# a click under Settings, not a value on the node.
_SESSION_DEAD = "Can't authenticate session token"


def _sentence(e):
    """What went wrong, in the site's own words rather than its transport's.

    One truncated sentence, never a traceback.
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
    gone = _NOT_FOUND.match(out)
    if gone:
        return (f"{gone.group(1)} {gone.group(2)} does not exist on this site. Check the id, then "
                f"run again. {out}")
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


def _wired(widgets, name):
    """Whether that input is connected.

    An API-format prompt writes a link as `["node", slot]` and a widget value as a scalar.
    """
    return isinstance(widgets.get(name), list)


def _batch_limit(v, key):
    """{width, height, fits, gib} for this source, or None where the size is not free to read."""
    from . import media

    size = media.frame_size(v, key)
    if not size:
        return None
    budget = media.budget_bytes(site.profile().get("batch_budget_gib", 0))
    return {"width": size[0], "height": size[1],
            "fits": media.frames_that_fit(size, budget), "gib": media.gib(budget)}


def _concept_rows(values, where, schema, names=None):
    """One row per provenance concept: its value, the field it is recorded in, and what is not
    settled until the Run.

    Every concept, not only the ones with a value. The row is named for the field; the concept is
    the label beside it. A field this site has takes the value, everything else is a description
    line.
    """
    from . import fields as sg_fields

    def show(v):
        if isinstance(v, list):     # multi_entity: names, not a dict repr
            return ", ".join((names or {}).get(x.get("id"), str(x.get("id"))) for x in v)
        return str(v)[:160]

    rows = []
    for concept, target in where.items():
        v = values.get(concept)
        has = v not in (None, "", [])
        described = target == sg_fields.DESCRIPTION or (target and target not in schema)
        if target is None:
            note = "Recorded nowhere."
        elif described:
            note = "Into the description."
        else:
            note = "" if has else "Not in this graph."
        # The generator is ComfyUI whoever submits, and the Run adds the client to it. The note
        # is shown beside the value, never instead of it.
        if concept == "generator" and has and not described:
            note = "The client that submits the Run is recorded with it."
        rows.append({
            "name": (target[3:] if target.startswith("sg_") else target)
                    if target and not described else sg_fields.CONCEPT_LABELS[concept],
            "label": sg_fields.CONCEPT_LABELS[concept],
            "value": show(v) if has else "",
            # The field a value is recorded in is the operator's mapping, so a fact in the
            # description says so beside its value.
            "into_description": described,
            "note": note,
        })
    return rows


def _files_preview(widgets, prof, project_id, link_type, target, task_id):
    """(where the files would be written, the sentence that stops them being written).

    Resolved against the storage row. A storage that cannot be resolved refuses the run, so it is
    the panel's alert rather than a line in the fold.
    """
    if not widgets.get("register_files"):
        return [], ""
    from . import publish, sequence, version_name
    # The same resolution the run makes (publish_version.publish). The wires decide which files
    # follow; the profile decides whether the review movie is kept as a file too.
    images, video = _wired(widgets, "images"), _wired(widgets, "video")
    pf = prof.get("published_files") or {}
    want_frames = images
    want_movie = video and (not images or bool(pf.get("register_movie")))
    if not (want_frames or want_movie):
        return [], ""
    try:
        code, version_no = version_name.next_name(widgets.get("code_template", ""), project_id,
                                                  link_type, target, task_id,
                                                  widgets.get("root_name", ""))
        # `sequence.plan` is what the run stages from, so the two cannot render a path differently.
        pl = sequence.plan(prof, publish.storages(site.client()), code, version_no, project_id,
                           link_type, target, task_id, widgets.get("root_name", ""))
        where = []
        if want_frames:
            ext = sequence.extension(widgets.get("format", ""))
            # A batch of one is a still and takes the still template; two or more take the
            # sequence template. The frame count is a run-time fact, so both paths are named.
            where.append({"label": "frames path",
                          "path": sequence.destination(pl, pl.seq_template, ext, version_no)})
            where.append({"label": "still path",
                          "path": sequence.destination(pl, pl.still_template, ext, version_no)})
        # A deliverable is never transformed, so the clip keeps its own extension. That extension
        # is a run-time fact, stated rather than guessed.
        if want_movie:
            ext = ".<the clip's own extension>"
            where.append({"label": "clip path",
                          "path": sequence.destination(pl, pl.movie_template, ext, version_no)})
        # The run's own guard, asked here. A root that is mounted and not writable refuses at
        # staging.
        try:
            sequence.check_root(pl.root)
        except Exception as e:
            return where, str(e)
        return where, ""
    except Exception as e:
        return [], (f"Create Published Files is ticked, but the paths could not be worked out. "
                    f"{_sentence(e)}")


# The profile keys Settings may write, by their dotted path. Anything else stays a file edit.
DEFAULT_KEYS = ("default_project", "code_template", "root_name", "status",
                "published_files.default", "published_files.storage", "published_files.path_platform",
                "published_files.path_template", "published_files.still_path_template",
                "published_files.movie_path_template",
                "published_files.register_movie", "published_files.path_to_frames",
                "published_files.path_to_movie", "published_files.colour_space")

# What a template example is rendered on: one Shot, its Task, version 3.
SAMPLE = {"entity": "sh010", "task": "Roto", "sg_task": "Roto", "step": "Roto", "ext": ".png"}


def _sample_values(template, extra=None):
    """Values for every field a template asks for.

    The project's own fields are resolved from the site. The entity and the Task get sample values.
    """
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
    """`kind` is name, root, sequence, still or movie."""
    from . import naming, sequence, version_name
    p = site.for_project(site.default_project())
    pf = p.get("published_files") or {}
    root_t = ((template if kind == "root" else p.get("root_name"))
              or naming.DEFAULT_ROOT_TEMPLATE).strip()
    root_name = version_name.root_of(root_t, _sample_values(root_t), 3)
    if kind == "root":
        return root_name
    name_t = (template if kind == "name" else p.get("code_template")) or naming.DEFAULT_TEMPLATE
    name = naming.render(name_t, _sample_values(name_t, {"root_name": root_name}), 3)
    if kind == "name":
        return name
    # A path template is relative to the storage root, which the Storage row names.
    extra = {"root_name": root_name, "version_name": name}
    if kind == "sequence":
        t = template or pf.get("path_template") or sequence.DEFAULT_SEQUENCE_TEMPLATE
        return sequence.pattern("/", t, _sample_values(t, extra), 3, ".png").lstrip("/")
    if kind == "still":
        t = template or pf.get("still_path_template") or sequence.DEFAULT_STILL_TEMPLATE
        return sequence.pattern("/", t, _sample_values(t, extra), 3, ".png").lstrip("/")
    if kind == "movie":
        t = template or pf.get("movie_path_template") or sequence.DEFAULT_MOVIE_TEMPLATE
        return sequence.pattern("/", t, _sample_values(t, dict(extra, ext=".mov")), 3, ".mov").lstrip("/")
    return ""


_TYPE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}")


def _entity_type(query):
    """The `type` query param as an entity type. It goes into the schema path, so nothing else."""
    name = (query.get("type") or "").strip()
    if not _TYPE_NAME.fullmatch(name):
        raise ValueError(f"{name or 'That'} is not an entity type.")
    return name


def _token_rows(kind, project, link_type=""):
    """The tokens for one template kind, with the types `{entity}` may descend into.

    `link_type` is the picked link's own type and wins. Without one, the profile's link type, else
    the types this project's Versions link to (probe 005), else Shot.
    """
    from . import naming
    try:
        pid = site.id_for(site.projects(), project) or site.default_project()
    except Exception:
        pid = site.default_project()
    types = [link_type] if link_type else [site.for_project(pid).get("link_type")]
    if not types[0]:
        try:
            types = site.link_types(pid)
        except Exception:
            types = []
    return naming.tokens(kind, types or ["Shot"])


def _in_force(profile):
    """The two name templates Settings has in force for a project, whatever a node's fields read."""
    from . import naming
    return {"root_name": profile.get("root_name") or naming.DEFAULT_ROOT_TEMPLATE,
            "code_template": profile.get("code_template") or naming.DEFAULT_TEMPLATE}


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
        "published_files.still_path_template": pf.get("still_path_template") or "",
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
        "published_files.still_path_template": sequence.DEFAULT_STILL_TEMPLATE,
        "published_files.movie_path_template": sequence.DEFAULT_MOVIE_TEMPLATE,
    }
    return {"values": values, "placeholders": placeholders,
            "projects": [{"label": n, "id": i} for n, i in site.projects()],
            "storages": storages,
            "this_platform": sequence.THIS_PLATFORM,
            "statuses": [{"label": l, "code": c} for l, c in site.statuses(pid)],
            "path": str(site.profile_path())}


# Appended to a site's own refusal to create the provenance fields.
FIELDS_REFUSED = ("Ask an admin to press this button, or run the command in INSTALL.md with a "
                  "script key that can create fields.")


def _fields_survey():
    """Which provenance fields this site already has, by display and programmatic name."""
    from . import fields as sg_fields
    return sg_fields.survey(credentials.client())


def _fields_create():
    """Create whatever is missing: one row per field, the counts, and who to ask on a refusal."""
    from . import fields as sg_fields
    present, created, failed = sg_fields.ensure(credentials.client())
    out = {"rows": sg_fields.outcome(present, created, failed), "present": len(present),
           "created": len(created), "failed": len(failed), "total": len(sg_fields.FIELDS)}
    if failed:
        out["advice"] = FIELDS_REFUSED
    return out


def _fields_error(e):
    """One sentence for a survey or a create that never started, plus who to ask on a refusal."""
    from . import fields as sg_fields
    sentence = _sentence(e)
    if isinstance(e, sg_fields.Refused) and e.status in (401, 403):
        return f"{sentence} {FIELDS_REFUSED}"
    return sentence


def register():
    try:
        from server import PromptServer  # only exists inside a running ComfyUI
    except ImportError:
        return False

    from aiohttp import web

    routes = PromptServer.instance.routes

    def answer(fn, empty):
        """One route's body, or `empty` plus one sentence.

        Never 500 into the editor. An unreachable site degrades to an empty picker.
        """
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

    @routes.get("/sg/tokens")
    async def template_tokens(request):
        """The tokens a template may use, for the completion in the editor."""
        q = request.rel_url.query
        return items(lambda: _token_rows(q.get("kind", ""), q.get("project", ""),
                                         q.get("link_type", "")))

    @routes.get("/sg/schema_fields")
    async def schema_fields(request):
        """The fields of one type, for the dotted path the completion builds hop by hop."""
        return items(lambda: site.schema_fields(_entity_type(request.rel_url.query)))

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
            # probe 017: `contains` filters server-side, so the list is never fetched in full.
            pid = _int(q, "project_id")
            found = site.links(pid, q.get("q", ""), site.chosen_types(q.get("type", ""), pid))
            return [{"label": l, "type": t, "id": i} for l, t, i in found]
        return items(rows)

    @routes.get("/sg/tasks")
    async def tasks(request):
        """label and id as everywhere else, plus the pipeline step where the Task has one."""
        q = request.rel_url.query

        def rows():
            found = site.task_rows(q.get("type", ""), _int(q, "id"))
            return [{"label": content, "id": i, "step": step} for content, i, step in found]
        return items(rows)

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
        """What THIS Version can deliver (probe 021). A filled path field is not a file on disk,
        and neither is a PublishedFile on a root this machine has not mounted.

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
            # `filters` is EXTRA conditions only, ANDed onto the fields.
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
            # The full query in the API's own language, the fields plus whatever was added, so
            # the panel shows what is asked rather than half of it.
            built = resolve.combine(
                site.version_filters(pid, lt, target, task_id, terms, codes),
                SGLoadVersion._filters(raw))

            if not vid:
                # A rule that matches nothing lists what is there: the same link and task, with
                # their statuses, and the filters dropped. A status is drawn the same way
                # everywhere it appears (recipe 010).
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
            # resolves to.
            picked = q.get("source", "") or "auto"
            if picked == "auto":
                key, clip_key = media.best(v, "image", available), media.best(v, "video", available)
            else:
                key = picked.split(" · ")[0].strip()
                clip_key = key if media.kind_of(v, key) == "movie" else ""
            label = dict(available)
            fps, fps_why = media.frame_rate(v)
            # `media`, not `sources`: the publish panel spends `sources` on the Versions a publish
            # came from. The thumbnail is a fallback, never a choice.
            return {
                **desc, "why": why, "filters": built,
                "media": [k for k, _ in available if k != "thumbnail"],
                # What each output will take: the type, the file and the count that the bare key
                # cannot say.
                "image_label": label.get(key, ""),
                "video_label": label.get(clip_key) if clip_key
                else f"the frames at {fps:g} fps, {fps_why}",
                # The frame numbers this source has, so `frame` is read off the panel rather than
                # guessed. Only a sequence has them; a movie has no numbering.
                "frames": (lambda r: {"first": r[0], "last": r[1], "count": r[2]} if r else None)(
                    media.frame_range(v, key)),
                # What this machine will spend on one batch, so the panel names an oversized plate
                # before the Run. Only a sequence answers; a movie's size would cost a decode.
                "batch": _batch_limit(v, key),
                # What the `image` output will read, off the first file's header. Bit depth and
                # channels tell a plate from a preview, and neither is visible in a filename.
                "format": media.describe_format(v, key),
                "colour_space": media.colour_of(v, key)}
        return answer(read, {"id": 0, "media": []})

    @routes.get("/sg/preview_code")
    async def preview_code(request):
        """The name this publish node would write next. The node's own renderer, so the panel cannot
        promise something the run does not deliver."""
        q = request.rel_url.query

        def read():
            from . import version_name
            site.client()     # nothing to preview until someone is connected: the sentence names Settings
            ctx = site.context(q.get("project", ""), q.get("link", ""), q.get("task", ""),
                               link_type=q.get("link_type", ""))
            project_id, p, lt = ctx.project_id, ctx.profile, ctx.link_type
            target, task_id, picked_name = ctx.link_id, ctx.task_id, ctx.link_name
            root_t = q.get("root_name", "")            # the ROOT template, not the version's name
            code = version_name.next_code(q.get("code_template", ""), project_id, lt, target,
                                          task_id, root_t)
            # Name the fields to fill in, never the consequence of leaving them empty. The run
            # refuses on the same list.
            missing = version_name.missing_fields(q.get("code_template", ""), root_t, project_id,
                                                  target, task_id)
            if q.get("link") and not target:
                alert = f"No {lt} named {picked_name} on this project. Pick one from the list."
            elif missing:
                alert = f"Fill in the required fields ({', '.join(missing)})."
            else:
                alert = ""
            # What is already there, not only what comes next. `versions_on` is the same cached
            # read `next_name` picks the number from, so scrubbing the pickers costs nothing.
            latest = {}
            rows = site.versions_on(lt, target, project_id) if target else []
            if rows:
                lcode, _lstatus, lid = rows[0]
                # Its link only. Drawing its files here would read as the files this publish
                # writes.
                latest = {"id": lid, "code": lcode, "site_url": site.client().site}
            # The two templates Settings has in force, whatever the node's own fields read. The
            # editor draws one inside an empty field as its placeholder, and lists it as the
            # completion's Default row whether the field is empty or not.
            return {"code": code, "link": f"{lt} {picked_name}".strip(),
                    "task": q.get("task", ""), "alert": alert, "latest": latest,
                    "settings": _in_force(p)}
        return answer(read, {"code": ""})

    @routes.post("/sg/sync")
    async def sync(request):
        """Drop every cached site read. Sync from SG calls this first, so a Task or Step edited on
        the site is read again rather than served from the 600 second cache."""
        site.forget()
        return web.json_response({})

    @routes.post("/sg/preview_publish")
    async def preview_publish(request):
        """Everything this publish node would write, from the graph as it stands.

        Provenance comes from the executing graph, so the editor hands it over in the shape the
        frontend already builds for Run (`graphToPrompt`). Nothing is written.
        """
        try:
            from . import fields as sg_fields, provenance, sequence
            from .nodes.load_version import SGLoadVersion as FV
            body = await request.json()
            prompt, node_id = body.get("prompt") or {}, str(body.get("node_id") or "")
            prov = provenance.extract(prompt, None, node_id=node_id)

            # Typed ids first, then upstream Load nodes. That is the order the node itself uses.
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
            # The full schema, not the nine this repo declares. A mapping may point at a field
            # the studio already has.
            schema = sg_fields.schema_names(sg)
            by_id = {x["id"]: (x.get("code") or f'Version {x["id"]}') for x in sources}
            w = (prompt.get(node_id) or {}).get("inputs") or {}
            ctx = site.context(w.get("project", ""), w.get("link", ""), w.get("task", ""),
                               w.get("status", ""), w.get("link_id") or 0)
            pid = ctx.project_id
            where = sg_fields.targets(*site.provenance_map(pid))
            values = sg_fields.concepts(prov, [x["id"] for x in sources if x["id"]])
            # The Version records "ComfyUI (<client>)". The client is whoever POSTs /prompt
            # (execution.py:224): the frontend, a farm, the `comfy` CLI, an MCP server. This route
            # is not that call, so the panel names what it knows.
            values["generator"] = prov.get("generator") or "ComfyUI"
            rows = _concept_rows(values, where, schema, by_id)
            # The rest of the Version: not provenance, but still what gets written. Resolved the
            # way the run resolves it, not the way the picker displays it. The link field takes
            # {"type", "id"}, the status takes a code, and the field name is the profile's
            # (probe 005). `site.unset()` drops "(none)" and "(all types)", which are labels for the
            # operator and never values for the site.
            link = site.unset(w.get("link"))
            prof, link_type, picked_name = ctx.profile, ctx.link_type, ctx.link_name
            link_field = prof.get("link_field", "entity")
            target, task_id, status_code = ctx.link_id, ctx.task_id, ctx.status_code
            plain = [("description", w.get("note") or "",
                      "" if w.get("note") else "From the note field."),
                     ("sg_status_list", status_code, "" if status_code else "No status picked."),
                     (link_field, f"{link_type} {target}" if target else "",
                      "" if target else
                      (f"No {link_type} named {picked_name} on this project." if link
                       else "No link picked.")),
                     ("sg_task", f"Task {task_id}" if task_id else "",
                      "" if task_id else "No task picked.")]
            for name, val, note in plain:
                rows.append({"name": name, "value": str(val)[:160], "note": note})

            # Uploads are not fields, and a copy onto a shared volume is not an upload. Each gets
            # its own list of what is written.
            uploads = ["image (the thumbnail)", "sg_uploaded_movie (the review movie)",
                       "<version name>.provenance.json"]
            if w.get("attach_workflow", True):
                uploads.append("<version name>.workflow.json")
            paths, files_alert = _files_preview(w, prof, pid, link_type, target, task_id)
            # What this node will publish, from what is wired into it: the review media on the
            # Version, and the files written when Create Published Files is ticked. The frame count
            # and the frame rate are run-time facts, so the sentences state the rule.
            images, video = _wired(w, "images"), _wired(w, "video")
            fmt = w.get("format") or sequence.DEFAULT_FORMAT
            keeps_movie = bool((prof.get("published_files") or {}).get("register_movie"))
            if video:
                review = "The clip, 8-bit."
            elif images:
                review = "Frame 1 as a still, 8-bit PNG."
            else:
                review = "Nothing. Wire an image or a video into this node."
            if not (images or video):
                files = ""
            elif not w.get("register_files"):
                files = ("None. Tick Create Published Files to keep the frames as files."
                         if images else "None. Tick Create Published Files to keep the clip as a file.")
            elif images and video:
                files = (f"Every frame as {fmt}, and the clip as it is." if keeps_movie
                         else f"Every frame as {fmt}. The clip is review only.")
            elif images:
                files = f"Every frame as {fmt}."
            else:
                files = "The clip as it is, never re-encoded."
            return web.json_response({
                "fields": rows,
                "uploads": uploads,
                "paths": paths,
                # A publish that cannot resolve its storage is not valid, whatever the name reads.
                "alert": files_alert,
                "review": review,
                "files": files,
                "sources": sources,
            })
        except Exception as e:
            return web.json_response({"error": _sentence(e), "fields": [], "sources": []})

    @routes.get("/sg/statuses")
    async def statuses(request):
        """Labels, codes and how to draw each one. The picker shows what the SG UI shows."""
        q = request.rel_url.query

        def rows():
            colors, icons = site.status_colors(), site.status_icons()
            # Most-used first (probe 020). A schema-ordered picker buries the two codes a show
            # uses among the twenty it allows.
            pid = _int(q, "project_id")
            used = site.status_usage(pid)
            ordered = sorted(enumerate(site.statuses(pid)),
                             key=lambda r: (-used.get(r[1][1], 0), r[0]))
            return [{"label": l, "id": c, "code": c, "rgb": colors.get(c), "icon": icons.get(c),
                     "used": used.get(c, 0)}
                    for _, (l, c) in ordered]
        return items(rows)

    @routes.get("/sg/fields")
    async def fields_survey(request):
        """How many of the provenance fields exist on this site, and which are missing."""
        from . import fields as sg_fields
        try:
            return web.json_response(_fields_survey())
        except Exception as e:
            return web.json_response({"present": [], "missing": [],
                                      "total": len(sg_fields.FIELDS), "error": _fields_error(e)})

    @routes.post("/sg/fields")
    async def fields_create(request):
        """Create the provenance fields this site is missing, as whoever Settings is connected as."""
        from . import fields as sg_fields
        try:
            return web.json_response(_fields_create())
        except Exception as e:
            return web.json_response({"rows": [], "present": 0, "created": 0, "failed": 0,
                                      "total": len(sg_fields.FIELDS), "error": _fields_error(e)})

    site.warm()   # prime the setup caches now, not on the operator's first page load
    return True
