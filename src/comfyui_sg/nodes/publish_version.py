"""SG Publish — what the graph made becomes a Version carrying its provenance.

One run is one Version, because a Version's media is single-valued (probe 022). What that Version
carries follows from what is wired in, never from a combo asking the operator to say it again: a
VIDEO is the review media, an IMAGE batch on its own is frame 1 as a still, and both wired is the
video.

This node records; it does not make images. A VIDEO that is already a file on disk goes up as that
file, byte for byte, and anything else is written by ComfyUI's own encoder (`movie.stage`).

The frames themselves are a PublishedFile, not media — the other half of probe 022's verdict. Tick
`register_files` and the run still produces exactly one Version, plus a PublishedFile per registered
file, copied under a LocalStorage root the site can resolve (recipe 004). `sequence.py` is what
happens on disk.
"""
import io
import os

from PIL import Image

from .. import fields as sg_fields
from .. import (lineage, movie, naming, provenance, publish, sequence, site,
                version_name, widgets)

MAX_ID = 2 ** 31 - 1
# The default for an unset keyword. It is NOT the label a person picks — that is site.NO_VALUE,
# "(none)" — and the two must stay distinct, or a combo declares a value the editor cannot offer.
UNSET = ""


def _png(frame):
    """One frame of a ComfyUI IMAGE batch ([H,W,C] float 0-1) as PNG bytes."""
    buf = io.BytesIO()
    Image.fromarray(movie.to_u8(frame)).save(buf, format="PNG")
    return buf.getvalue()


def _as_line(concept, value):
    """One concept as a line of the description. Only `generated_from` is not already a scalar."""
    if concept == "generated_from":
        return ", ".join(f'Version {v["id"]}' for v in value)
    return str(value)


def _split(values, where, absent_targets):
    """({field: value}, [line]) — each concept typed where this site has the field, else a line.

    The operator's mapping decides the target; the schema decides only whether that target can hold
    a value. A concept whose field is absent is written out in full — the whole prompt, every source
    Version — because a fact recorded nowhere is the one thing this project exists to prevent.
    """
    fields, lines = {}, []
    for concept, value in values.items():
        target = where.get(concept)
        if not target:
            continue
        if target == sg_fields.DESCRIPTION or target in absent_targets:
            lines.append(f"{sg_fields.CONCEPT_LABELS[concept]}: {_as_line(concept, value)}")
        else:
            fields[target] = value
    return fields, lines


def _description(note, lines):
    """The note, a blank line, then one line per fact. Either half alone is that half."""
    return "\n".join([x for x in (note,) if x] + ([""] if note and lines else []) + lines)


def _labels(pairs):
    """Choices with a visible "no value" first — an empty string cannot be selected back."""
    return [site.NO_VALUE] + [label for label, _ in pairs]


def _id_for(pairs, label):
    return next((i for l, i in pairs if l == label), 0)


def _wants_files(pf):
    """The profile's default for the tick. `published_files.default` of `(none)` means no."""
    d = pf.get("default")
    return bool(d) and d != site.NO_VALUE


def settings_defaults(project_id):
    """The values a publish node takes from Settings, as widget values: the templates written out."""
    p = site.for_project(project_id)
    pf = p.get("published_files") or {}
    statuses = site.statuses(project_id)
    return {
        "root_name": p.get("root_name") or naming.DEFAULT_ROOT_TEMPLATE,
        "code_template": p.get("code_template") or naming.DEFAULT_TEMPLATE,
        "status": next((l for l, c in statuses if c == p.get("status")), site.NO_VALUE),
        "register_files": _wants_files(pf),
        "colour_space": pf.get("colour_space") or "",
    }


class SGPublishVersion:
    @classmethod
    def INPUT_TYPES(cls):
        # Re-evaluated on every /object_info request (server.py:756), so a profile edit or a new Shot
        # reaches the operator on a browser refresh. The JS extension keeps the dependent lists in
        # step while the graph is open; these are only the seed values.
        project_id = site.default_project()
        p = site.for_project(project_id)
        rows = site.links(project_id)
        links = [(l, i) for l, _, i in rows]
        first_type, first_link = (rows[0][1], rows[0][2]) if len(rows) == 1 else ("", 0)
        statuses = site.statuses(project_id)
        status_label = next((l for l, c in statuses if c == p.get("status")), UNSET)

        return {
            # Neither input is required and at least one is: what a Version carries is the shape of
            # what was wired, so the node cannot declare one of them the real input.
            "required": {},
            # Order, labels and copy come from `widgets.PUBLISH_FIELDS`, which instrument.py,
            # smoke.py and the editor extension read as well. An input slot is additive and stays
            # outside that table; a widget is positional and does not.
            #
            # There is no link_type. Version.entity accepts 15 types and a show may use several at
            # once (DESIGN); the link picker searches every type the show uses, server-side, and
            # each option carries its own type.
            "optional": {
                "images": ("IMAGE", {"tooltip": "The frames out of the graph to publish."}),
                "video": ("VIDEO", {"tooltip": "The clip out of the graph to publish, from "
                                               "LoadVideo, CreateVideo or a video model."}),
                **widgets.declare(
                    widgets.PUBLISH_FIELDS,
                    choices={
                        "project": _labels(site.projects()),
                        "link": _labels(links),
                        "task": _labels(site.tasks_for(first_type, first_link)),
                        "status": _labels(statuses),
                    },
                    overrides={
                        # A house decides which fields it wants in front of it; the table's own
                        # `advanced` flags are only the default (DESIGN: site profile).
                        **widgets.folding(widgets.PUBLISH_FIELDS,
                                          (p.get("widgets") or {}).get("publish")),
                        "project": {"default": site.project_name(project_id)},
                        "status": {"default": status_label},
                        # Empty means the Settings default names it, so a Settings change reaches
                        # every saved graph. `settings_defaults` is what a node copies in on request.
                        "code_template": {"default": ""},
                        "root_name": {"default": ""},
                        "colour_space": {"default": (p.get("published_files") or {})
                                         .get("colour_space") or ""},
                        "register_files": {"default": _wants_files(p.get("published_files") or {})},
                        "link_id": {"max": MAX_ID},
                    }),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "usage_source": "COMFY_USAGE_SOURCE",
                "unique_id": "UNIQUE_ID",
            },
        }

    @classmethod
    def VALIDATE_INPUTS(cls, project=None, link=None, task=None, status=None):
        """Accept what the editor offered, because the editor knows more than INPUT_TYPES did.

        These combos are seeded for the default project and then repopulated per project by the JS
        (`setOptions`), so a value the operator legitimately picked need not be in the list this
        class declared at load time. ComfyUI skips its own membership check for any input named here
        (execution.py:1019), the mechanism core nodes use for the same problem
        (comfy_extras/nodes_model_advanced.py:380). A label that resolves to no entity still fails
        at run time, naming the label and the project.
        """
        return True

    @staticmethod
    def _stage(images, media_path, code, version_no, count, colour_space, want_frames, want_movie,
               p, sg, project_id, link_type, target, task_id, root_name="", frame_format=""):
        """Everything that touches disk, done before the Version exists. None when nothing was asked.

        The storage root and the path templates are profile data, per project like every other
        site-specific decision (DESIGN). A path template is the language the code template already
        speaks — dotted SG paths and Python's format spec (`naming.render`) — plus the frame
        token `sg_path_to_frames` uses. A sequence earns a folder and a movie does not, which is why
        there are two templates.
        """
        if not (want_frames or want_movie):
            return None
        pf = p.get("published_files") or {}
        storages = publish.storages(sg)
        storage_id, root = sequence.root_for(storages, pf.get("storage", ""))
        sequence.check_root(root)
        # The Version's path fields hold one absolute path each, written for the platform the
        # profile picks; the files themselves are written under this machine's root.
        row = sequence.storage_row(storages, pf.get("storage", ""))
        platform = sequence.platform_for(row, pf.get("path_platform", ""))
        field_path = lambda path: sequence.on_platform(path, root, row, platform)
        seq_t = pf.get("path_template") or sequence.DEFAULT_SEQUENCE_TEMPLATE
        mov_t = pf.get("movie_path_template") or sequence.DEFAULT_MOVIE_TEMPLATE
        # The stream is RENDERED from its own template, never derived by subtracting a version token
        # from a longer one. A path refers to `{root_name}` and `{version_name}` rather than
        # spelling the naming scheme a second time, so the two cannot disagree.
        root_t = (root_name or p.get("root_name") or naming.DEFAULT_ROOT_TEMPLATE).strip()
        fields = (set(naming.template_fields(seq_t)) | set(naming.template_fields(mov_t))
                  | set(naming.template_fields(root_t)))
        vals = site.resolve_paths(fields, project_id, link_type, target, task_id)
        # A token nobody could resolve leaves an empty segment that `_clean` swallows, so name them.
        # probe 028: a 200 proves nothing, and neither does a path that rendered.
        blank = sorted(k for k in fields if not str(vals.get(k, "")).strip())
        # `version_name.root_of`, so the folder is the same stream name the code was built on.
        name = version_name.root_of(root_t, vals)

        def path_for(template, ext):
            return sequence.pattern(root, template,
                                    dict(vals, version_name=code, root_name=name, ext=ext),
                                    version_no, ext)

        # The extension follows the files, never the template: it is the one the node's `format`
        # widget names, and a template reading `.exr` must not relabel 8-bit frames as scene-linear.
        ext = sequence.extension(frame_format)
        out = {"root": root, "storage_id": storage_id, "template": seq_t, "blank_tokens": blank,
               "declared_ext": os.path.splitext(sequence.single(seq_t))[1].lower(), "ext": ext,
               "colour": colour_space.strip(), "count": count}
        if want_frames:
            pattern = path_for(seq_t, ext)
            # Written to ComfyUI's own output directory first. The copy is what puts a file where
            # the site can resolve it; the original stays put so a failed publish is recoverable.
            out["frames"] = sequence.place(sequence.write_frames(images, code, frame_format),
                                           pattern)
            out["frames_pattern"] = pattern
            out["frames_code"] = os.path.basename(pattern)
            out["frames_name"] = name
            if pf.get("path_to_frames", True):
                out["frames_field"] = field_path(pattern)
        if want_movie:
            # The clip's real extension, because a deliverable is never transformed: a `.mov` off
            # LoadVideo is registered as a `.mov`, and only what ComfyUI encoded here is `.mp4`.
            ext = os.path.splitext(media_path)[1].lower() or ".mp4"
            dest = path_for(mov_t, ext)
            out["media"] = sequence.copy_one(media_path, dest)
            out["media_code"] = os.path.basename(dest)
            out["media_name"] = name
            if pf.get("path_to_movie", True):
                out["media_field"] = field_path(out["media"])
        return out

    @staticmethod
    def _register(sg, staged, project_id, vid, version_no, link_type, target, task_id, count,
                  note, colour_space, src_ids, src_files=None):
        """One PublishedFile per registered file, linked to the Version carrying the review media.

        Returns the lines the panel logs: what was registered, where it landed, and what could not
        be said — an unrecognised type, or ancestors with no files to depend on.

        `upstream_published_files` is the file-level twin of `sg_ai_generated_from`: the same
        ancestors, resolved to the files those Versions published, because a tool downstream opens
        files rather than Versions. `src_files` is what an upstream Load node actually read
        (lineage.py); where it has an answer the link is that one file, where it does not the site
        is asked and the link is every file of that ancestor.
        """
        if not staged:
            return []
        upstream, upstream_problem = publish.published_files_of(sg, src_ids, src_files)
        common = {"version": {"type": "Version", "id": int(vid)}, "version_number": int(version_no)}
        if target:
            common["entity"] = {"type": link_type, "id": int(target)}
        if task_id:
            common["task"] = {"type": "Task", "id": int(task_id)}
        if upstream:
            common["upstream_published_files"] = upstream
        # sg_status_list is deliberately absent. PublishedFile carries its own status list — `wtg`,
        # `ip`, `cmpt` here — and the Version's codes are a different set entirely (probe 009), so
        # copying one across writes a code this field never allowed. The field's default applies.
        common["description"] = "\n".join(x for x in (
            note, sequence.describe_colour(colour_space.strip()),
            f"frames 1-{count}" if count > 1 else "") if x)

        jobs = []
        if staged.get("frames"):
            n = len(staged["frames"])
            jobs.append(("frames" if n > 1 else "still", staged["frames_code"],
                         staged["frames_name"], staged["frames_pattern"],
                         f"{n} frames" if n > 1 else "1 frame"))
        if staged.get("media"):
            jobs.append(("movie", staged["media_code"], staged["media_name"], staged["media"],
                         "the clip"))

        # One type read per kind, before anything is written: it is a site-wide list and does not
        # change between two files of one publish.
        types = {kind: publish.published_file_type(sg, sequence.TYPE_CANDIDATES[kind])
                 for kind in {j[0] for j in jobs}}

        notes = []
        for kind, code, name, path, what in jobs:
            body = dict(common)
            # path_cache is null after a REST create even though the path resolved, so a filter on
            # it misses every row published this way (entity_types/PublishedFile). It is a plain
            # text field and takes a write, so the client writes what it already knows.
            body["path_cache"] = sequence.relative(staged["root"], path)
            pft, problem = types.get(kind, (None, ""))
            if pft:
                body["published_file_type"] = pft
            elif problem:
                notes.append(problem)
            else:
                notes.append(f"This site has no Published File Type for {kind}, so the file was "
                             f"registered without one. Creating one would add it to all projects.")
            try:
                pf_id, resolved = publish.create_published_file(sg, project_id, code, name, path,
                                                                body)
            except Exception as e:
                # One file of two failing must not take the other's line with it: the Version and
                # whatever already registered are on the site, and the operator needs to read both.
                notes.append(f"{what.capitalize()} could not be registered as {code}. Run again to "
                             f"register it. {e}")
                continue
            # The 201 already carries the resolved path, so this reports what the SERVER stored
            # rather than what was sent — the two differ the moment a root is ambiguous (recipe 004).
            notes.append(f"Registered {what} as {code}, PublishedFile {pf_id}. "
                         f'{resolved.get("local_path_mac") or path}')
        if staged.get("declared_ext") and staged["declared_ext"] != staged.get("ext") \
                and staged.get("frames"):
            notes.append(f'These frames were registered as {staged["ext"]}. The path template '
                         f'names {staged["declared_ext"]}, and nothing was converted.')
        if upstream:
            notes.append(f"Linked {len(upstream)} upstream published file(s).")
        elif upstream_problem:
            notes.append(upstream_problem)
        elif src_ids:
            notes.append("The source versions have no published files, so nothing upstream was "
                         "linked.")
        return notes

    RETURN_TYPES = ()
    FUNCTION = "publish"
    CATEGORY = "Flow Production Tracking"
    OUTPUT_NODE = True
    DESCRIPTION = ("Create a Flow Production Tracking Version from this image or video, carrying "
                   "the graph that made it.")

    def publish(self, images=None, video=None, project=UNSET, link=UNSET, task=UNSET, status=UNSET,
                note="", code_template=UNSET,
                source_versions="", attach_workflow=True, link_id=0,
                register_files=False, colour_space="", root_name="",
                format=sequence.DEFAULT_FORMAT,
                prompt=None, extra_pnginfo=None, usage_source=None, unique_id=None):
        if images is None and video is None:
            raise ValueError(
                "Nothing is wired into this node. Connect an image to images, a video to video, or "
                "both.")
        frames = len(images) if images is not None else 0
        if images is not None and frames == 0:
            raise ValueError("The image batch is empty, so there is nothing to publish. Check the "
                             "node feeding images, then run again.")
        # A sequence cannot BE a Version's media (probe 022) and nothing here is being asked to
        # register it, so frame 1 would go up and the rest would vanish. Refused loudly, and refused
        # before the site is touched at all.
        if video is None and frames > 1 and not register_files:
            raise ValueError(
                f"Only frame 1 would be published, and the other {frames - 1} frames would be lost. "
                f"Tick Create Published Files to publish all {frames}, or send the batch through "
                f"CreateVideo and wire the video into this node.")
        # The picked project decides, then the profile answers for THAT project — two graphs open in
        # one ComfyUI can target two shows that link Versions differently.
        project_id = _id_for(site.projects(), project) or site.default_project()
        if not project_id:
            raise ValueError("No project is selected. Pick one from the list, or set "
                             "default_project in profile.local.json.")
        p = site.for_project(project_id)
        link_field = p.get("link_field", "entity")   # probe 005 — never assume sg_task
        link, task, status = site.unset(link), site.unset(task), site.unset(status)
        # The label carries its own type: Version.entity accepts 15 types and a show may use several
        # at once. The profile answers only for a link picked before labels carried a type.
        picked_type, picked_name = site.split_link(link)
        link_type = picked_type or p.get("link_type", "Shot")

        # Combos carry labels; SG wants ids. Resolve narrowly rather than trusting a cached list.
        target = int(link_id) or (_id_for(site.entities(link_type, project_id, q=picked_name),
                                          picked_name) if link else 0)
        if link and not target:
            raise ValueError(f"No {link_type} named {picked_name} on this project. Pick one from "
                             f"the list.")
        task_id = _id_for(site.tasks_for(link_type, target), task) if (task and target) else 0
        # The same sentence the panel shows, refused before the site is written to.
        missing = version_name.missing_fields(code_template, root_name, project_id, target,
                                              task_id)
        if missing:
            raise ValueError(f"Fill in the required fields ({', '.join(missing)}).")
        status_code = next((c for l, c in site.statuses(project_id) if l == status), "")

        # unique_id scopes provenance to this node's branch (provenance.ancestors).
        prov = provenance.extract(prompt, extra_pnginfo, node_id=unique_id)
        prov["comfy_usage_source"] = usage_source  # which client submitted this (execution.py:216)
        # Declared, not measured: an operator's statement about the pixels belongs in the record and
        # stays a statement, never a transform.
        if colour_space.strip():
            prov["colour_space"] = colour_space.strip()
        wf = provenance.workflow(extra_pnginfo)

        sg = site.client()
        # One schema read answers two questions: which of the operator's targets this site actually
        # has, and whether it carries the frame range a movie wants.
        schema = sg_fields.schema_names(sg)
        # Typed ids first, then whatever a Load node upstream already proves. The operator can add a
        # source the graph cannot see; they never have to retype one it can.
        src_ids = [int(x) for x in source_versions.replace(",", " ").split() if x.strip().isdigit()]
        # Widget-pinned ids come from the graph; resolved ones only exist at run time (lineage).
        upstream = provenance.ancestors(prompt or {}, unique_id) if prompt else set()
        for vid in (provenance.loaded_versions(prompt or {}, unique_id)
                    + lineage.for_nodes(upstream)):
            if vid not in src_ids:
                src_ids.append(vid)
        # Where each concept lands is the operator's mapping, not this file's business (DESIGN).
        # The schema decides only whether that target can be written, per concept: a field this site
        # has takes the value, and everything else — a target mapped to the description, and a target
        # this site does not have — becomes a line of the description instead. Nothing is dropped and
        # nothing is a JSON blob, so the same nine facts are readable either way.
        mapping, prov_mode = site.provenance_map(project_id)
        where = sg_fields.targets(mapping, prov_mode)
        absent_targets = {t for t in where.values()
                          if t and t != sg_fields.DESCRIPTION and t not in schema}
        typed, prov_lines = _split(sg_fields.concepts(prov, src_ids), where, absent_targets)

        # The template decides the name, rendered from the entity and task it is actually linked to.
        # A real version-number field is authoritative where the site has one (Toolkit sites usually
        # do); the template's own {version} is the fallback for the many sites that do not.
        code, version_no = version_name.next_name(code_template, project_id, link_type, target,
                                                  task_id, root_name)
        vnum_field = p.get("version_number_field", "")
        next_num = (naming.next_number(site.version_numbers(link_type, target, project_id, vnum_field))
                    if vnum_field and target else None)

        # Staged BEFORE the Version exists — an install with no PyAV, or a clip `save_to` refuses,
        # stops here rather than leaving a Version behind holding a still and calling it a clip. The
        # thumbnail is read off the media rather than off `images`, so the still and the clip cannot
        # disagree about what this Version shows.
        media_path = ""
        if video is not None:
            media_path, how = movie.stage(video, sequence.folder(code), code)
            count, media_note = movie.describe(video, how)
            png = movie.poster(media_path)
        else:
            count = frames
            media_note = "frame 1 as a still" if frames > 1 else "the image itself"
            png = _png(images[0])
        # Whether the house ALSO keeps the review movie as a file is a convention and lives in the
        # profile; whether this publish is a deliverable at all is the node's tick. A clip published
        # on its own IS the deliverable, so it is registered without the house saying so — a tick
        # that registered nothing would be a silent no-op.
        keeps_movie = bool((p.get("published_files") or {}).get("register_movie"))
        want_frames = bool(register_files and images is not None)
        want_movie = bool(register_files and video is not None and (images is None or keeps_movie))
        # Same rule for the files: the root is resolved, the frames are written and copied into
        # place BEFORE the Version exists, so an unmounted share refuses the run rather than leaving
        # a Version pointing at frames nobody wrote.
        staged = self._stage(images, media_path, code, version_no, count, colour_space,
                             want_frames, want_movie, p, sg, project_id, link_type, target,
                             task_id, root_name, format)

        fields = dict(typed)
        # The note first, then a blank line, then one line per fact this site has no field for. The
        # full graph and the full provenance go up as attachments either way.
        fields["description"] = _description(note, prov_lines)
        if status_code:
            fields["sg_status_list"] = status_code
        if target:
            fields[link_field] = {"type": link_type, "id": target}
        if task_id:
            fields["sg_task"] = {"type": "Task", "id": task_id}
        if next_num is not None:
            fields[vnum_field] = next_num
        # The range is ours; everything derived from the media is the transcoder's (probe 022).
        if count > 1:
            fields.update({k: v for k, v in movie.frame_fields(count).items() if k in schema})
        # probe 022's verdict: the `%04d` pattern belongs in sg_path_to_frames, with a transcoded
        # movie uploaded for the player. These are tier 2 in probe 021, which is what the Load node
        # reads to pull frames back. Each is written for the platform the profile picks, and only
        # when the profile wants the field at all (_stage).
        skipped_paths = []
        for field, value in (("sg_path_to_frames", (staged or {}).get("frames_field")),
                             ("sg_path_to_movie", (staged or {}).get("media_field"))):
            if not value:
                continue
            if field in schema:
                fields[field] = value
            else:
                skipped_paths.append(field)

        # Staging copied files onto the storage and the create puts a Version on the site. Neither
        # is recoverable from a traceback, so from here a failure carries both in its own sentence.
        written = [x for x in ((staged or {}).get("frames_pattern"), (staged or {}).get("media"))
                   if x]
        vid = 0
        try:
            vid = publish.create_version(sg, project_id, code, fields)
            # Every lookup a name depends on. `find` is the one the template reads, and a stale one
            # lets two publish nodes in one run propose the same version again.
            site.forget("find", "versions", "vnums", "paths")
            # Frame 1 is the thumbnail whichever way this went: the site derives one from a movie
            # too, but not until the transcode lands, and no picture until then is worse.
            publish.upload(sg, vid, png, f"{code}.png", field="image")
            if media_path:
                # Streamed off disk. A clip is the one payload here with no ceiling, and the file
                # that goes up is the file that was registered.
                publish.upload_file(sg, vid, media_path,
                                    f"{code}{os.path.splitext(media_path)[1].lower() or '.mp4'}",
                                    field="sg_uploaded_movie")
            else:
                publish.upload(sg, vid, png, f"{code}.png", field="sg_uploaded_movie")
            publish.attach_json(sg, vid, prov, f"{code}.provenance.json")
            if attach_workflow and wf is not None:
                publish.attach_json(sg, vid, wf, f"{code}.workflow.json")

            file_notes = self._register(sg, staged, project_id, vid, version_no, link_type, target,
                                        task_id, count, note, colour_space, src_ids,
                                        lineage.files_for_nodes(upstream))
        except Exception as e:
            raise RuntimeError(" ".join(x for x in (
                str(e),
                f"Files were already written to: {', '.join(written)}." if written else "",
                f"Version {vid} was created and is incomplete. Delete it in Flow Production "
                f"Tracking, then run again." if vid else "") if x)) from e

        published = [f"Published {code} as Version {vid}.", f"Review media: {media_note}"]
        # A stock field this site does not have. The files are still registered and still carry the
        # path, so this is one line about the Version's own path column, never a refusal.
        if skipped_paths:
            published.append(f"This site has no {', '.join(skipped_paths)}. Ask an admin to add "
                             f"them, so the files open from the Version.")
        if count > 1:
            skipped = [f for f in movie.FRAME_FIELDS if f not in schema]
            if skipped:
                published.append(f"This site has no {', '.join(skipped)}. Ask an admin to add "
                                 f"them, so the frame range reads on the Version.")
        # Frames wired in that nobody asked to keep are not an error — the clip is the review and
        # carries the same picture — but they are not silent either.
        if images is not None and video is not None and not want_frames:
            published.append(f"The {frames} frames were not published, only the clip. Tick Create "
                             f"Published Files to publish them too.")
        published += file_notes
        if attach_workflow and wf is None:
            published.append("No workflow was attached. This client did not send one with the run.")

        # The panel turns these into links. `site_url` comes off the client rather than the profile
        # because the run already authenticated against it — a second source could disagree. Paths
        # are what landed on disk this run, the one thing not recoverable from the site.
        staged_files = []
        if staged:
            if staged.get("frames_pattern"):
                staged_files.append({"kind": "frames", "path": staged["frames_pattern"],
                                     "count": len(staged.get("frames") or [])})
            if staged.get("media"):
                staged_files.append({"kind": "movie", "path": staged["media"], "count": 1})
        done = [{"code": code, "id": vid, "link": f"{link_type} {picked_name}".strip(),
                 "status": status_code, "outputs": sorted(typed), "media": media_note,
                 "site_url": sg.site, "files": staged_files}]
        # `text` is the plain readout ComfyUI shows anywhere; `published` is what the node's own
        # panel renders — the same run, described rather than printed.
        return {"ui": {"text": published, "published": done}}
