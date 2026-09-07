"""HTTP routes backing the node's pickers.

ComfyUI imports custom nodes between constructing PromptServer and calling add_routes
(main.py:542), so appending to PromptServer.instance.routes here registers normally.

Setup path: these serve the editor and are never touched while publishing.
"""
import json
import os
import re

from . import resolve, site

# Flow PT answers an error as a JSON:API envelope whose useful half is one `detail` sentence.
_DETAIL = re.compile(r'"detail"\s*:\s*"((?:[^"\\]|\\.)*)"')

# The widest id any query param may carry.
_MAX_ID = 2 ** 31 - 1


def _sentence(e):
    """What went wrong, in the site's own words rather than its transport's.

    One truncated sentence, never a traceback: this is read in the editor and by an artist.
    """
    text = str(e)
    m = _DETAIL.search(text)
    if not m:
        return text[:200]
    try:
        return json.loads(f'"{m.group(1)}"')[:200]   # the capture is still JSON-escaped
    except ValueError:
        return m.group(1)[:200]


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


def _files_preview(widgets, prof, project_id, link_type, target, task_id):
    """Where the files would land, resolved against the real storage row.

    A publish that copies a sequence onto a shared volume is what an operator reads back before
    pressing Run, and an unmounted root belongs here rather than at the end of a render.
    """
    if not widgets.get("register_files"):
        return []
    from . import naming, publish, sequence
    from .nodes.publish_version import FPTPublishVersion as PV
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

    @routes.get("/fpt/projects")
    async def projects(request):
        """label and id as everywhere else, plus what a picker row draws: code and thumbnail."""
        return items(lambda: [
            {"label": p["name"], "id": p["id"], "code": p["code"], "image": p["image"]}
            for p in site.project_cards()])

    @routes.get("/fpt/link_types")
    async def link_types(request):
        """Entity types this project links Versions to. Empty choice means all of them."""
        q = request.rel_url.query
        return items(lambda: [{"label": t, "id": t}
                              for t in site.link_type_choices(_int(q, "project_id"))])

    @routes.get("/fpt/entities")
    async def entities(request):
        """Every type this project links Versions to, not one. Version.entity accepts 15 types."""
        q = request.rel_url.query

        def rows():
            # probe 017 — `contains` filters server-side, so the list is never fetched whole.
            pid = _int(q, "project_id")
            found = site.links(pid, q.get("q", ""), site.chosen_types(q.get("type", ""), pid))
            return [{"label": l, "type": t, "id": i} for l, t, i in found]
        return items(rows)

    @routes.get("/fpt/tasks")
    async def tasks(request):
        q = request.rel_url.query
        return pairs(lambda: site.tasks_for(q.get("type", ""), _int(q, "id")))

    @routes.get("/fpt/profile")
    async def profile(request):
        """What the profile says for ONE project. `link_type` decides which entity type the link
        picker searches, and it is per project, not per site."""
        q = request.rel_url.query

        def read():
            p = site.for_project(_int(q, "project_id"))
            return {k: p.get(k) for k in ("link_type", "link_field", "code_prefix", "status")}
        return answer(read, {})

    @routes.get("/fpt/versions")
    async def versions(request):
        q = request.rel_url.query
        return pairs(lambda: site.versions(_int(q, "project_id"), q.get("type", ""),
                                           _int(q, "link_id"), q.get("q", "")))

    @routes.get("/fpt/version_sources")
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

    @routes.get("/fpt/resolve")
    async def resolve_one(request):
        """What the Load node WOULD pull, and what that Version is.

        Editor-time, and it calls the node's own resolver, so the preview cannot disagree with the
        run.
        """
        q = request.rel_url.query

        def read():
            from . import media
            from .nodes.load_version import FPTLoadVersion
            pin = _int(q, "pin_version_id")
            typed = [t.strip() for x in q.getall("statuses", [])
                     for t in x.split(",") if t.strip()]
            # `filters` holds EXTRA conditions only, ANDed onto the fields.
            raw = q.get("filters", "")
            pid, lt, target, task_id = FPTLoadVersion._context(
                q.get("project", ""), q.get("link_type", ""), q.get("link", ""), q.get("task", ""))
            codes, _ = site.resolve_statuses(pid, typed)
            terms = [t for t in (q.get("name_contains", "") or "").split() if t]
            if pin:
                vid, code, why = pin, "", "pinned by id"
            else:
                vid, code, why = FPTLoadVersion._resolve(
                    q.get("project", ""), q.get("link_type", ""), q.get("link", ""),
                    q.get("task", ""), q.get("name_contains", ""), typed,
                    q.get("newest_by", ""), raw)
            # The whole query in the API's own language — the fields plus whatever was added — so
            # the panel shows what is actually being asked rather than half of it.
            built = resolve.combine(
                site.version_filters(pid, lt, target, task_id, terms, codes),
                FPTLoadVersion._filters(raw))

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

            fpt = site.client()
            project_id = _int(q, "project_id") or pid
            desc = media.describe(fpt, vid, site.statuses(project_id), site.status_colors(),
                                  site.status_icons())
            v = media.version(fpt, vid)
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
                "colour_space": media.colour_of(v, key)}
        return answer(read, {"id": 0, "media": []})

    @routes.get("/fpt/preview_code")
    async def preview_code(request):
        """The name this publish node would write next. The node's own renderer, so the panel cannot
        promise something the run does not deliver."""
        q = request.rel_url.query

        def read():
            from . import naming
            from .nodes.publish_version import FPTPublishVersion as PV
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
            return {"code": code, "link": f"{lt} {picked_name}".strip(),
                    "task": q.get("task", ""), "alert": alert, "latest": latest}
        return answer(read, {"code": ""})

    @routes.post("/fpt/preview_publish")
    async def preview_publish(request):
        """Everything this publish node would write, from the graph as it stands.

        Provenance comes from the executing graph, so the editor hands it over in the shape the
        frontend already builds for Run (`graphToPrompt`). Nothing is written.
        """
        try:
            from . import fields as fpt_fields, provenance
            from .nodes.load_version import FPTLoadVersion as FV
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
                if node.get("class_type") != "FPTLoadVersion":
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
            # sampler is information. The row is named for where the value LANDS, because that is
            # the operator's decision; the concept is the label beside it.
            for concept, target in where.items():
                v = values.get(concept)
                has = v not in (None, "", [])
                if target is None:
                    note = "not mapped to a field"
                elif target == fpt_fields.DESCRIPTION:
                    note = "into the description"
                elif target in have:
                    note = "" if has else "not in this graph"
                else:
                    note = "this site has no such field"
                rows.append({
                    "name": (target[3:] if target.startswith("sg_") else target) if target
                            else fpt_fields.CONCEPT_LABELS[concept],
                    "label": fpt_fields.CONCEPT_LABELS[concept],
                    "value": show(v) if has else "",
                    "present": target is None or target == fpt_fields.DESCRIPTION or target in have,
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
                                          if t and t != fpt_fields.DESCRIPTION and t not in have}),
            })
        except Exception as e:
            return web.json_response({"error": _sentence(e), "fields": [], "sources": []})

    @routes.get("/fpt/statuses")
    async def statuses(request):
        """Labels, codes and how to draw each one. The picker shows what the Flow PT UI shows."""
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
