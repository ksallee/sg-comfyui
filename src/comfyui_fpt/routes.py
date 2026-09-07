"""HTTP routes backing the node's pickers.

Custom nodes import at main.py:542, between PromptServer construction (536) and add_routes (556), so
appending to PromptServer.instance.routes here is registered normally.

Setup path: these serve the editor and are never touched while publishing.
"""
import json
import os
import re

from . import resolve, site

# Flow PT answers an error as a JSON:API envelope, and the useful part is one `detail` sentence
# inside it. Four wrapped lines of `{"errors":[{"id":"0dc12...","status":404,...}]}` in a readout an
# artist glances at is the same as saying nothing.
_DETAIL = re.compile(r'"detail"\s*:\s*"((?:[^"\\]|\\.)*)"')


def _sentence(e):
    """What went wrong, in the site's own words rather than its transport's."""
    text = str(e)
    m = _DETAIL.search(text)
    if not m:
        return text[:200]
    try:
        return json.loads(f'"{m.group(1)}"')[:200]   # the capture is still JSON-escaped
    except ValueError:
        return m.group(1)[:200]


def _id_for(pairs, label):
    return next((i for l, i in pairs if l == label), 0)


def _wired(widgets, name):
    """Whether that input is connected. An API-format prompt writes a link as ["node", slot] and a
    widget value as a scalar, so the shape of the entry is the answer."""
    return isinstance(widgets.get(name), list)


def _files_preview(widgets, prof, project_id, link_type, target, task_id):
    """Where the files would land, resolved against the real storage row.

    The panel must not understate what the run will write: a publish that copies a sequence onto a
    shared volume is the one thing an operator wants to read back before pressing Run, and a storage
    root that is not mounted should be visible here rather than at the end of a render.
    """
    if not widgets.get("register_files"):
        return []
    from . import naming, publish, sequence
    from .nodes.publish_version import FPTPublishVersion as PV
    # Which files follow from what is wired, and whether the house also keeps its review movie is
    # the profile's call — the same resolution the run makes (publish_version.publish).
    images, video = _wired(widgets, "images"), _wired(widgets, "video")
    pf = prof.get("published_files") or {}
    want_frames = images
    want_movie = video and (not images or bool(pf.get("register_movie")))
    if not (want_frames or want_movie):
        return []
    try:
        _, root = sequence.root_for(publish.storages(site.client()), pf.get("storage", ""))
        # Two templates, because a sequence earns a folder and a movie does not — the same pair
        # `publish_version._stage` picks. One template for both put the movie among its own frames.
        seq_t = pf.get("path_template") or sequence.DEFAULT_SEQUENCE_TEMPLATE
        mov_t = pf.get("movie_path_template") or sequence.DEFAULT_MOVIE_TEMPLATE
        root_t = (widgets.get("root_name", "") or prof.get("root_name")
                  or naming.DEFAULT_ROOT_TEMPLATE)
        code, version_no = PV.next_name(widgets.get("code_template", ""), project_id, link_type,
                                        target, task_id, root_t)
        # `{root_name}` and `{version_name}` are RENDERED, not looked up — resolve_paths has never
        # heard of either. Leaving them out is what wrote `/<root>/<entity>/v001/.png`: the stream
        # folder and the whole filename collapsed to nothing and `swap_ext` pasted `.png` onto the
        # empty stem. The run hands the path the two names its templates already decided
        # (publish_version._stage), so the preview has to hand it the same two.
        fields = (set(naming.template_fields(seq_t)) | set(naming.template_fields(mov_t))
                  | set(naming.template_fields(root_t)))
        vals = site.resolve_paths(fields, project_id, link_type, target, task_id)
        vals["root_name"] = naming.render(root_t, vals, version_no)
        vals["version_name"] = code
        where = []
        if want_frames:
            where.append(sequence.pattern(root, seq_t, dict(vals, ext=".png"), version_no, ".png"))
        # The clip's real extension is a run-time fact — a deliverable is never transformed, so a
        # `.mov` off LoadVideo stays a `.mov` — and this states that rather than guessing one.
        if want_movie:
            ext = ".<the clip's own extension>"
            where.append(sequence.pattern(root, mov_t, dict(vals, ext=ext), version_no, ext))
        if not os.path.isdir(root):
            where.append(f"{root} is NOT mounted — the run will stop")
        return where
    except Exception as e:
        return [f"published files asked for, but: {_sentence(e)}"]


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
            return web.json_response({"items": [], "error": _sentence(e)})

    @routes.get("/fpt/projects")
    async def projects(request):
        """label and id as everywhere else, plus what a picker row draws: code and thumbnail."""
        try:
            return web.json_response({"items": [
                {"label": p["name"], "id": p["id"], "code": p["code"], "image": p["image"]}
                for p in site.project_cards()]})
        except Exception as e:
            return web.json_response({"items": [], "error": _sentence(e)})

    @routes.get("/fpt/link_types")
    async def link_types(request):
        """Entity types this project links Versions to. Empty choice means all of them."""
        try:
            ts = site.link_type_choices(int(request.rel_url.query.get("project_id") or 0))
            return web.json_response({"items": [{"label": t, "id": t} for t in ts]})
        except Exception as e:
            return web.json_response({"items": [], "error": _sentence(e)})

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
            return web.json_response({"items": [], "error": _sentence(e)})

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
            return web.json_response({"error": _sentence(e)})

    @routes.get("/fpt/versions")
    async def versions(request):
        q = request.rel_url.query
        return pairs(site.versions, int(q.get("project_id") or 0), q.get("type", ""),
                     int(q.get("link_id") or 0), q.get("q", ""))

    @routes.get("/fpt/version_sources")
    async def version_sources(request):
        """What THIS Version can actually deliver (probe 021). A filled path field is not the same as
        a file on disk, and neither is a PublishedFile on a root this machine has not mounted, so the
        editor asks per Version rather than offering a fixed list.

        `colour` rides along because it belongs to the file, not to the Version: two PublishedFiles
        on one Version can declare different colour spaces, and the picker is where that is chosen.
        """
        try:
            from . import media
            v = media.version(site.client(), int(request.rel_url.query.get("version_id") or 0))
            return web.json_response({"items": [
                {"label": label, "id": key, "colour": media.colour_of(v, key)}
                for key, label in media.sources(v)]})
        except Exception as e:
            return web.json_response({"items": [], "error": _sentence(e)})

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
            # Read once, before the branch. `typed`, `raw` and `same` were bound only where the rule
            # ran, and the pinned path used them anyway: every pin raised UnboundLocalError, which
            # the panel drew as "nothing resolved yet". Once, above, is also the whole context —
            # _context was being asked the same question three times per request.
            typed = [t.strip() for x in q.getall("statuses", [])
                     for t in x.split(",") if t.strip()]
            raw = q.get("filters", "")
            pid, lt, target, task_id = FPTLoadVersion._context(
                q.get("project", ""), q.get("link_type", ""), q.get("link", ""), q.get("task", ""))
            codes, _ = site.resolve_statuses(pid, typed)
            terms = [t for t in (q.get("name_contains", "") or "").split() if t]
            # No mirror to detect any more. `raw` holds EXTRA conditions only, ANDed onto the
            # fields, so there is no state where the box might or might not be the node's own
            # writing — which is what used to go stale and silently take over the whole query.
            if pin:
                vid, code, why = pin, "", "pinned by id"
            else:
                vid, code, why = FPTLoadVersion._resolve(
                    q.get("project", ""), q.get("link_type", ""), q.get("link", ""),
                    q.get("task", ""), q.get("name_contains", ""), typed,
                    q.get("newest_by", ""), raw)
            # The WHOLE query in the API's own language — fields plus whatever was added — so the
            # panel can show what is actually being asked rather than half of it.
            built = resolve.combine(
                site.version_filters(pid, lt, target, task_id, terms, codes),
                FPTLoadVersion._filters(raw))

            if not vid:
                # A rule that matches nothing is the moment you most need to see what IS there, so
                # the same link and task are listed with their statuses and the filters dropped.
                colors, labels = site.status_colors(), dict(
                    (c, l) for l, c in site.statuses(pid))
                # `icon` too, not just the colour: a status is drawn the same way everywhere it
                # appears (recipe 010), and without this the candidate list rendered a bare pill
                # while every other status on the node carried its icon.
                icons = site.status_icons()
                near = [{"code": c, "status": {"code": st, "label": labels.get(st, st),
                                               "rgb": colors.get(st), "icon": icons.get(st)}, "id": i}
                        for c, st, i in site.find_versions(pid, lt, target, task_id)[:12]]
                return web.json_response({"id": 0, "why": why, "media": [],
                                          "candidates": near, "filters": built})
            fpt = site.client()
            project_id = int(q.get("project_id") or 0) or pid
            desc = media.describe(fpt, vid, site.statuses(project_id), site.status_colors(),
                                  site.status_icons())
            # One read, not two. `version` now carries a second call for the published files
            # (probe 021), so asking for the same Version twice in one request doubled it.
            v = media.version(fpt, vid)
            available = media.sources(v)
            # What the node itself would pick, so the readout answers for the run rather than for
            # the widget: `auto` is a rule, and only the site knows what it lands on.
            picked = q.get("source", "") or "auto"
            key = available[0][0] if (picked in ("auto", "") and available) \
                else picked.split(" — ")[0].strip()
            # `media`, not `sources`: the publish panel uses `sources` for the Versions a publish
            # came from, and one word meaning two things rendered "Version undefined" in the other.
            return web.json_response({
                **desc, "why": why, "filters": built,
                "media": [k for k, _ in available],
                # The label of what will actually be read — "Rendered Image — foo.%04d.png, 6
                # frames" says the type, the file and the count that the bare key cannot.
                "source_label": next((l for k, l in available if k == key), ""),
                # The frame numbers this source actually has, so `frame` is read off the panel
                # instead of guessed. Only a sequence has them: a movie carries no numbering, and
                # saying nothing is the honest answer there.
                "frames": (lambda r: {"first": r[0], "last": r[1], "count": r[2]} if r else None)(
                    media.frame_range(v, key)),
                "colour_space": media.colour_of(v, key)})
        except Exception as e:
            # `error`, not `summary`: nothing read `summary`, so a pin pointing at a Version that is
            # not there rendered as "nothing resolved yet" and the reason was thrown away.
            return web.json_response({"id": 0, "error": _sentence(e), "media": []})

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
            # `root_name`, not the `output_name` widget that was deleted: this argument is the ROOT
            # template, and sending a name no widget has answered since meant the panel rendered
            # `{root_name}` as empty. A stream called `{entity}_plate` previewed as a bare `v001`
            # while the run wrote `sh010_plate_v001` — the readout promising less than it delivers.
            root_t = q.get("root_name", "")
            code = PV.next_code(q.get("code_template", ""), project_id, lt, target, task_id, root_t)
            # A template renders what it can and drops the rest, so `corridor_depth_v004` and a bare
            # `v004` come back looking equally finished. Say which fields the name is missing and
            # why, because the name is the one thing the operator checks before a Run.
            from . import naming
            # Both templates, because `{root_name}` hides whatever the root one asks for: a code of
            # `{root_name}_v{version:03d}` over a root of `{entity}_plate` still needs a link, and
            # reading only the code template said it needed nothing.
            needs = {f.split(".")[0] for f in
                     naming.template_fields(q.get("code_template", "") or naming.DEFAULT_TEMPLATE)
                     + naming.template_fields(root_t or naming.DEFAULT_ROOT_TEMPLATE)}
            if q.get("link") and not target:
                alert = f"no {lt} named {picked_name!r} on this project — the run will stop here"
            elif "entity" in needs and not target:
                alert = "nothing is linked, so the name has no shot or asset in it"
            elif "task" in needs and not task_id:
                alert = "no task picked, so the name has no task in it"
            else:
                alert = ""
            # What is already there, not just what comes next. `versions_on` is the same cached read
            # `next_name` used to pick the number, so the id costs nothing; only the files are a
            # second call, and it is cached against the Version so scrubbing the pickers does not
            # re-ask. Shown before anything is published, which is when it is most useful.
            latest = {}
            rows = site.versions_on(lt, target, project_id) if target else []
            if rows:
                lcode, _lstatus, lid = rows[0]
                latest = {"id": lid, "code": lcode, "site_url": site.client().site, "files": []}
                try:
                    from . import media
                    latest["files"] = [{"kind": f.get("type") or "file", "path": f["path"]}
                                       for f in site.cached_published_files(lid) if f.get("path")]
                except Exception:
                    pass                      # a Version whose files cannot be read still has a link
            return web.json_response({"code": code, "link": f"{lt} {picked_name}".strip(),
                                      "task": q.get("task", ""), "alert": alert, "latest": latest})
        except Exception as e:
            return web.json_response({"code": "", "error": _sentence(e)})

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

            # Typed ids first, then upstream Load nodes — the order the node itself uses. Reading
            # only the Load nodes made the panel say "nothing in this graph" for lineage the run
            # would go on to write, which is the one direction a preview must never be wrong in.
            own = (prompt.get(node_id) or {}).get("inputs") or {}
            sources = [{"id": int(x), "code": "", "why": "typed on this node"}
                       for x in str(own.get("source_versions") or "").replace(",", " ").split()
                       if x.strip().isdigit()]
            # Upstream Load nodes: a pinned one is in the graph, a rule-driven one has to be
            # resolved the same way the node will resolve it at run time.
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
            # site.unset(): "(none)" and "(all types)" are labels for the operator, and printing one
            # as a value made the readout say `sg_status_list (none)` where it means "left unset".
            #
            # Resolved the way the RUN resolves it, not the way the picker displays it. This block
            # is headed "what gets written", and it was printing `sbx_0020 (Shot)` — a label built
            # for a dropdown — into a field that takes {"type", "id"}. Same for the status, which
            # takes a code, and the field name itself, which the profile decides (probe 005).
            status, link, task = (site.unset(w.get(k)) for k in ("status", "link", "task"))
            prof = site.for_project(pid)
            link_field = prof.get("link_field", "entity")
            picked_type, picked_name = site.split_link(link)
            link_type = picked_type or prof.get("link_type", "Shot")
            target = int(w.get("link_id") or 0) or (
                _id_for(site.entities(link_type, pid, q=picked_name), picked_name) if link else 0)
            task_id = _id_for(site.tasks_for(link_type, target), task) if (task and target) else 0
            status_code = next((c for l, c in site.statuses(pid) if l == status), "") if status else ""
            plain = [("description", w.get("note") or "", "the note below"),
                     ("sg_status_list", status_code, "" if status_code else "left unset"),
                     (link_field, f"{link_type} {target}" if target else "",
                      "" if target else
                      (f"no {link_type} named {picked_name!r} here" if link else "not linked")),
                     ("sg_task", f"Task {task_id}" if task_id else "",
                      "" if task_id else "no task")]
            for name, val, note in plain:
                rows.append({"name": name, "value": str(val)[:160], "present": True, "note": note})

            # Media and attachments are uploads, not fields, but they are part of "what gets saved".
            # A list of what lands, not a paragraph about it: the rule that decides WHICH of these
            # the media is stated once, in `media` below, rather than again on every row.
            uploads = ["image  (thumbnail)", "sg_uploaded_movie", "<version name>.provenance.json"]
            if w.get("attach_workflow", True):
                uploads.append("<version name>.workflow.json")
            # A copied file is not an upload, so it gets its own list. A publish that writes onto a
            # shared volume is the line an operator most wants to read before a Run.
            writes = _files_preview(w, prof, pid, link_type, target, task_id)
            # Which row of the truth table this node is on. The frame count and the frame rate are
            # run-time facts, so the panel states the rule and names the path the run will take —
            # which is the half an operator cannot see from the wires alone.
            if _wired(w, "video"):
                media = "the clip, uploaded as its own file unless the graph re-encoded it"
                if _wired(w, "images"):
                    media += ". The frames can only be Published Files, never media"
            elif _wired(w, "images"):
                media = ("frame 1, as a still. For every frame, tick Create Published Files or "
                         "wire a VIDEO — a Version holds one piece of media")
            else:
                media = "nothing — neither images nor video is wired, so this run will refuse"
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
        try:
            pid = int(request.rel_url.query.get("project_id") or 0)
            colors, icons = site.status_colors(), site.status_icons()
            # Most-used first (probe 020). A picker sorted by the schema makes an artist hunt for
            # the two codes their show actually uses among the twenty it merely allows.
            used = site.status_usage(pid)
            rows = list(enumerate(site.statuses(pid)))
            rows.sort(key=lambda r: (-used.get(r[1][1], 0), r[0]))
            return web.json_response({"items": [
                {"label": l, "id": c, "code": c, "rgb": colors.get(c), "icon": icons.get(c),
                 "used": used.get(c, 0)}
                for _, (l, c) in rows]})
        except Exception as e:
            return web.json_response({"items": [], "error": _sentence(e)})

    site.warm()   # prime the setup caches now, not on the operator's first page load
    return True
