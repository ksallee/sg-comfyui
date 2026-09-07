"""Flow PT Publish Version — what the graph made becomes a Version carrying its provenance.

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
import json
import os

from PIL import Image

from .. import fields as fpt_fields
from .. import lineage, movie, naming, provenance, publish, sequence, site

MAX_ID = 2 ** 31 - 1
# The default for an unset keyword. It is NOT the label a person picks — that is site.NO_VALUE,
# "(none)" — and the two must stay distinct, or a combo declares a value the editor cannot offer.
UNSET = ""


def _png(frame):
    """One frame of a ComfyUI IMAGE batch ([H,W,C] float 0-1) as PNG bytes."""
    buf = io.BytesIO()
    Image.fromarray(movie.to_u8(frame)).save(buf, format="PNG")
    return buf.getvalue()


def _labels(pairs):
    """Choices with a visible "no value" first — an empty string cannot be selected back."""
    return [site.NO_VALUE] + [label for label, _ in pairs]


def _id_for(pairs, label):
    return next((i for l, i in pairs if l == label), 0)


def _wants_files(pf):
    """The profile's default for the tick. `published_files.default` of `(none)` means no."""
    d = pf.get("default")
    return bool(d) and d != site.NO_VALUE


class FPTPublishVersion:
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
            # what was wired, so the node cannot declare one of them the real input. `images` stays
            # first and keeps its name — an input slot is addressed by name in a saved graph.
            "required": {},
            # Order is the order they are decided: the pixels, then which show, what they belong to,
            # which task, what state it is in, which stream, and last the note a person writes.
            # Everything below the note is fine print and lives behind ComfyUI's advanced fold.
            #
            # There is no link_type. Version.entity accepts 15 types and a show may use several at
            # once (DESIGN); the link picker searches every type the show uses, server-side, and
            # each option carries its own type.
            #
            # WIDGET ORDER IS FROZEN. widgets_values is positional, so a key inserted, removed or
            # renamed here displaces every value below it in every graph already saved. Append only,
            # and move instrument.PUBLISH_WIDGETS, web/fpt_entity_picker.js DECLARED and every
            # *.json under example_workflows/ and tools/workflows/ in the same commit.
            "optional": {
                "images": ("IMAGE", {"tooltip": "The frames out of the graph to publish."}),
                # An input slot is additive: adding one does not move widgets_values.
                "video": ("VIDEO", {"tooltip": "The clip out of the graph to publish, from "
                                               "LoadVideo, CreateVideo or a video model."}),
                "project": (_labels(site.projects()),
                            {"default": site.project_name(project_id),
                             "tooltip": "Project to publish into."}),
                "link": (_labels(links),
                         {"tooltip": "The Shot, Asset or other entity this Version belongs to."}),
                "task": (_labels(site.tasks_for(first_type, first_link)),
                         {"tooltip": "Task this Version is for, if there is one."}),
                "status": (_labels(statuses),
                           {"default": status_label,
                            "tooltip": "Status to set on the new Version."}),
                # Its height belongs to the JS extension (`textRows`): a `customtext` widget is
                # built with an options object of its own and copies nothing from this spec.
                "note": ("STRING", {"multiline": True, "default": "",
                                    "placeholder": "What someone should know about this version.",
                                    "tooltip": "A note for the people who will read this Version, "
                                               "written to its description."}),
                # A template in Flow PT's own vocabulary: dotted field paths, the same ones filters
                # and ?fields use (probe 003), to any depth the server will traverse. A bare token is
                # the relationship's own name — `{entity}`, `{sg_task}`. `{version:03d}` and `v%04d`
                # both pad.
                #
                # Not advanced: this is the name that ends up on the Version, so it is what an
                # operator checks against the readout before pressing Run.
                "code_template": ("STRING", {
                    "default": p.get("code_template") or naming.DEFAULT_TEMPLATE,
                    "display_name": "version name",
                    "tooltip": "The name given to the new Version, for example "
                               "{entity}_plate_v{version:03d}. Use {root_name} to build on the root "
                               "name, and {version:03d} or v%04d to pad the number."}),
                # Lineage the graph already proves is added by itself; this is for a source no
                # upstream Load node can show.
                "source_versions": ("STRING", {"default": "", "advanced": True,
                                    "tooltip": "Version ids this was made from, separated by "
                                               "commas, for example 1042, 1043."}),
                "attach_workflow": ("BOOLEAN", {"default": True, "advanced": True}),
                "link_id": ("INT", {"default": 0, "min": 0, "max": MAX_ID, "advanced": True,
                                    "tooltip": "The id to link this Version to, used instead of the "
                                               "link picker when it is not 0."}),
                # The one per-publish question, and it is not about media: is this a deliverable, or
                # only review? WHICH files follow from what is wired, and whether the house also
                # keeps the review movie is `register_movie` in the profile.
                "register_files": ("BOOLEAN",
                                   {"default": _wants_files(p.get("published_files") or {}),
                                    "display_name": "Create Published Files",
                                    "tooltip": "Publish the files themselves beside the Version, "
                                               "copied to the storage root this project's profile "
                                               "names."}),
                # Declared, never inferred and never applied. A colour transform is the most
                # consequential pixel change in a comp, and this node does not make images (DESIGN).
                "colour_space": ("STRING", {
                    "default": (p.get("published_files") or {}).get("colour_space") or "",
                    "advanced": True,
                    "tooltip": "The colour space these pixels are already in, for example sRGB or "
                               "ACEScg. It is recorded with the Version, never applied to the "
                               "pixels."}),
                # APPENDED, never inserted: everything above this is in saved graphs already.
                #
                # recipe 004: `name` is the stream and `code` is one version of it. Empty derives
                # the stream from the profile; typing one locks it, so a later filename change
                # cannot silently move a stream someone downstream is following.
                "root_name": ("STRING", {
                    "default": p.get("root_name") or naming.DEFAULT_ROOT_TEMPLATE,
                    "display_name": "root name",
                    "advanced": True,
                    "tooltip": "The name shared by all versions of this publish, without a version "
                               "number, for example {entity}_matte. It names the folder the files "
                               "land in, and version name can build on it with {root_name}."}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "usage_source": "COMFY_USAGE_SOURCE",
                "unique_id": "UNIQUE_ID",
            },
        }

    @classmethod
    def next_name(cls, template, project_id, link_type, link_id, task_id, root_template=""):
        """(code, version number) this node would publish next.

        The number comes back because the path template needs the same one: a Version called v003
        and a sequence written to `v001/` would be two answers to one question. `{root_name}` is
        rendered first and handed to the version template as a value, because that template is
        `{root_name}_v{version:03d}` — the stream composed, then versioned.
        """
        template = (template or naming.DEFAULT_TEMPLATE).strip()
        if not naming.template_fields(template) and "{version" not in naming.normalise_template(template):
            return template, 1       # a literal name, used as-is
        root_t = (root_template or naming.DEFAULT_ROOT_TEMPLATE).strip()
        fields = set(naming.template_fields(template)) | set(naming.template_fields(root_t))
        vals = site.resolve_paths(fields, project_id, link_type, link_id, task_id)
        vals["root_name"] = naming.render(root_t, vals)
        codes = [c for c, _, _ in site.find_versions(project_id, link_type, link_id)]
        n = naming.next_version(codes, template, vals)
        return naming.render(template, vals, n), n

    @classmethod
    def next_code(cls, template, project_id, link_type, link_id, task_id, root_template=""):
        """The code this node would publish next. Shared with /fpt/preview_code and `seed.py`."""
        return cls.next_name(template, project_id, link_type, link_id, task_id,
                             root_template)[0]

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
               p, fpt, project_id, link_type, target, task_id, root_name=""):
        """Everything that touches disk, done before the Version exists. None when nothing was asked.

        The storage root and the path templates are profile data, per project like every other
        site-specific decision (DESIGN). A path template is the language the code template already
        speaks — dotted Flow PT paths and Python's format spec (`naming.render`) — plus the frame
        token `sg_path_to_frames` uses. A sequence earns a folder and a movie does not, which is why
        there are two templates.
        """
        if not (want_frames or want_movie):
            return None
        pf = p.get("published_files") or {}
        storage_id, root = sequence.root_for(publish.storages(fpt), pf.get("storage", ""))
        sequence.check_root(root)
        seq_t = pf.get("path_template") or sequence.DEFAULT_SEQUENCE_TEMPLATE
        mov_t = pf.get("movie_path_template") or sequence.DEFAULT_MOVIE_TEMPLATE
        # The stream is RENDERED from its own template, never derived by subtracting a version token
        # from a longer one. A path refers to `{root_name}` and `{version_name}` rather than
        # spelling the naming scheme a second time, so the two cannot disagree.
        root_t = root_name or p.get("root_name") or naming.DEFAULT_ROOT_TEMPLATE
        fields = (set(naming.template_fields(seq_t)) | set(naming.template_fields(mov_t))
                  | set(naming.template_fields(root_t)))
        vals = site.resolve_paths(fields, project_id, link_type, target, task_id)
        # A token nobody could resolve leaves an empty segment that `_clean` swallows, so name them.
        # corpus 028: a 200 proves nothing, and neither does a path that rendered.
        blank = sorted(k for k in fields if not str(vals.get(k, "")).strip())
        name = naming.render(root_t, vals, version_no)

        def path_for(template, ext):
            return sequence.pattern(root, template,
                                    dict(vals, version_name=code, root_name=name, ext=ext),
                                    version_no, ext)

        # The extension follows the files, never the template: PNG is what Pillow writes from an
        # IMAGE tensor, and a template reading `.exr` must not relabel 8-bit frames as scene-linear.
        out = {"root": root, "storage_id": storage_id, "template": seq_t, "blank_tokens": blank,
               "declared_ext": os.path.splitext(sequence.single(seq_t))[1].lower(),
               "colour": colour_space.strip(), "count": count}
        if want_frames:
            pattern = path_for(seq_t, ".png")
            # Written to ComfyUI's own output directory first. The copy is what puts a file where
            # the site can resolve it; the original stays put so a failed publish is recoverable.
            out["frames"] = sequence.place(sequence.write_frames(images, code), pattern)
            out["frames_pattern"] = pattern
            out["frames_code"] = os.path.basename(pattern)
            out["frames_name"] = name
        if want_movie:
            # The clip's real extension, because a deliverable is never transformed: a `.mov` off
            # LoadVideo is registered as a `.mov`, and only what ComfyUI encoded here is `.mp4`.
            ext = os.path.splitext(media_path)[1].lower() or ".mp4"
            dest = path_for(mov_t, ext)
            out["media"] = sequence.copy_one(media_path, dest)
            out["media_code"] = os.path.basename(dest)
            out["media_name"] = name
        return out

    @staticmethod
    def _register(fpt, staged, project_id, vid, version_no, link_type, target, task_id, count,
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
        upstream = publish.published_files_of(fpt, src_ids, src_files)
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
                         staged["frames_name"], staged["frames_pattern"], f"{n} frames"))
        if staged.get("media"):
            jobs.append(("movie", staged["media_code"], staged["media_name"], staged["media"],
                         "the clip"))

        notes = []
        for kind, code, name, path, what in jobs:
            body = dict(common)
            # path_cache is null after a REST create even though the path resolved, so a filter on
            # it misses every row published this way (entity_types/PublishedFile). It is a plain
            # text field and takes a write, so the client writes what it already knows.
            body["path_cache"] = sequence.relative(staged["root"], path)
            pft = publish.published_file_type(fpt, sequence.TYPE_CANDIDATES[kind])
            if pft:
                body["published_file_type"] = pft
            else:
                notes.append(f"This site has no Published File Type for {kind}, so the file was "
                             f"registered without one. Creating one would add it to all projects.")
            pf_id, resolved = publish.create_published_file(fpt, project_id, code, name, path, body)
            # The 201 already carries the resolved path, so this reports what the SERVER stored
            # rather than what was sent — the two differ the moment a root is ambiguous (recipe 004).
            notes.append(f"Registered {what} as {code}, PublishedFile {pf_id}. "
                         f'{resolved.get("local_path_mac") or path}')
        if staged.get("declared_ext") and staged["declared_ext"] != ".png" and staged.get("frames"):
            notes.append(f'These frames were registered as .png. The path template names '
                         f'{staged["declared_ext"]}, and nothing was converted.')
        if upstream:
            notes.append(f"Linked {len(upstream)} upstream published file(s).")
        elif src_ids:
            notes.append("The source versions have no published files, so nothing upstream was "
                         "linked.")
        return notes

    RETURN_TYPES = ()
    FUNCTION = "publish"
    CATEGORY = "Flow Production Tracking"
    OUTPUT_NODE = True
    DESCRIPTION = ("Create a Flow PT Version from this image or video, carrying the graph that "
                   "made it.")

    def publish(self, images=None, video=None, project=UNSET, link=UNSET, task=UNSET, status=UNSET,
                note="", code_template=UNSET,
                source_versions="", attach_workflow=True, link_id=0,
                register_files=False, colour_space="", root_name="",
                prompt=None, extra_pnginfo=None, usage_source=None, unique_id=None):
        if images is None and video is None:
            raise ValueError(
                "Nothing is wired into this node. Connect an image to images, a video to video, or "
                "both.")
        frames = len(images) if images is not None else 0
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

        # Combos carry labels; Flow PT wants ids. Resolve narrowly rather than trusting a cached list.
        target = int(link_id) or (_id_for(site.entities(link_type, project_id, q=picked_name),
                                          picked_name) if link else 0)
        if link and not target:
            raise ValueError(f"No {link_type} named {picked_name} on this project. Pick one from "
                             f"the list.")
        task_id = _id_for(site.tasks_for(link_type, target), task) if (task and target) else 0
        status_code = next((c for l, c in site.statuses(project_id) if l == status), "")

        # unique_id scopes provenance to this node's branch (provenance.ancestors).
        prov = provenance.extract(prompt, extra_pnginfo, node_id=unique_id)
        prov["comfy_usage_source"] = usage_source  # which client submitted this (execution.py:216)
        # Declared, not measured: an operator's statement about the pixels belongs in the record and
        # stays a statement, never a transform.
        if colour_space.strip():
            prov["colour_space"] = colour_space.strip()
        wf = provenance.workflow(extra_pnginfo)

        fpt = site.client()
        # One schema read answers two questions: which provenance fields exist (absent until
        # `python -m comfyui_fpt.fields` has run, so the blob fallback is the honest default) and
        # whether this site carries the frame range a movie wants.
        schema = fpt_fields.schema_names(fpt)
        have = set(fpt_fields.names().values()) & schema
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
        mapping, prov_mode = site.provenance_map(project_id)
        routed, prov_lines = fpt_fields.route(prov, src_ids, mapping, prov_mode)
        typed = {k: v for k, v in routed.items() if k in have}
        # A target the operator named that this site does not have. Dropping it silently would hide
        # a typo in their profile behind a Version that looks fine (corpus 028: loud, never silent).
        missing = sorted(set(routed) - set(have))

        # The template decides the name, rendered from the entity and task it is actually linked to.
        # A real version-number field is authoritative where the site has one (Toolkit sites usually
        # do); the template's own {version} is the fallback for the many sites that do not.
        code, version_no = self.next_name(code_template, project_id, link_type, target, task_id,
                                          root_name)
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
                             want_frames, want_movie, p, fpt, project_id, link_type, target,
                             task_id, root_name)

        fields = dict(typed)
        # description is the human note, plus whatever the operator routed into it. The full graph
        # goes up as an attachment either way, so the blob fallback is only for a site that has no
        # provenance fields and asked for nothing in the description.
        if prov_lines:
            fields["description"] = "\n".join(([note] if note else []) + prov_lines)
        elif typed:
            fields["description"] = note
        else:
            fields["description"] = json.dumps({"note": note, "provenance": prov}, indent=2)
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
        # reads to pull frames back.
        for field, value in (("sg_path_to_frames", (staged or {}).get("frames_pattern")),
                             ("sg_path_to_movie", (staged or {}).get("media"))):
            if value and field in schema:
                fields[field] = value

        vid = publish.create_version(fpt, project_id, code, fields)
        # Every lookup a name depends on. `find` is the one the template reads, and a stale one lets
        # two publish nodes in one run propose the same version again.
        site.forget("find", "versions_on", "vnums", "paths")
        # Frame 1 is the thumbnail whichever way this went: the site derives one from a movie too,
        # but not until the transcode lands, and a Version with no picture until then is worse.
        publish.upload(fpt, vid, png, f"{code}.png", field="image")
        if media_path:
            # Streamed off disk. A clip is the one payload here with no ceiling, and the file that
            # goes up is the file that was registered.
            publish.upload_file(fpt, vid, media_path,
                                f"{code}{os.path.splitext(media_path)[1].lower() or '.mp4'}",
                                field="sg_uploaded_movie")
        else:
            publish.upload(fpt, vid, png, f"{code}.png", field="sg_uploaded_movie")
        publish.attach_json(fpt, vid, prov, f"{code}.provenance.json")
        if attach_workflow and wf is not None:
            publish.attach_json(fpt, vid, wf, f"{code}.workflow.json")

        file_notes = self._register(fpt, staged, project_id, vid, version_no, link_type, target,
                                    task_id, count, note, colour_space, src_ids,
                                    lineage.files_for_nodes(upstream))

        published = [f"Published {code} as Version {vid}.", f"Review media: {media_note}"]
        if count > 1:
            skipped = [f for f in movie.FRAME_FIELDS if f not in schema]
            if skipped:
                published.append("No frame range was recorded. This site has no "
                                 + ", ".join(skipped) + ".")
        # Frames wired in that nobody asked to keep are not an error — the clip is the review and
        # carries the same picture — but they are not silent either.
        if images is not None and video is not None and not want_frames:
            published.append(f"The {frames} frames were not published, only the clip. Tick Create "
                             f"Published Files to publish them too.")
        published += file_notes
        if attach_workflow and wf is None:
            published.append("No workflow was attached. This client did not send one with the run.")
        if missing:
            published.append("This site has no fields called " + ", ".join(missing)
                             + ". Check the provenance mapping in profile.local.json.")
        if not typed and not prov_lines:
            published.append("This site has no provenance fields yet. Run "
                             "python -m comfyui_fpt.fields to create them.")

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
                 "site_url": fpt.site, "files": staged_files}]
        # `text` is the plain readout ComfyUI shows anywhere; `published` is what the node's own
        # panel renders — the same run, described rather than printed.
        return {"ui": {"text": published, "published": done}}
