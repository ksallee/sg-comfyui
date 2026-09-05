"""Flow PT Publish Version — what the graph made becomes a Version with its provenance.

One run is one Version, because probe 022 found a Version's media single-valued. What that Version
carries is decided by what is wired in, never by a combo asking the operator to say it again: a VIDEO
is the review media, an IMAGE batch on its own is frame 1 as a still, and both wired is the video.

This node records; it does not make images. A VIDEO that is already a file on disk goes up as that
file, byte for byte, and anything else is written by ComfyUI's own encoder (`movie.stage`).

The frames themselves are a PublishedFile, not media — the other half of probe 022's verdict. Tick
`register_files` and the run still produces exactly one Version, plus a PublishedFile per registered
file, copied under a LocalStorage root the site can resolve (recipe 004). See `sequence.py` for what
happens on disk.
"""
import io
import json
import os

from PIL import Image

from .. import fields as fpt_fields
from .. import lineage, movie, naming, provenance, publish, sequence, site

MAX_ID = 2 ** 31 - 1
# The default for an unset keyword, NOT the label a person picks — that is
# site.NO_VALUE, "(none)". Naming both NONE is what produced a combo whose
# declared value the editor could never offer back.
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
    """The profile's default for the tick.

    `published_files.default` held a combo label before this was a checkbox, and `(none)` was that
    combo's way of saying no — so a profile written for the old node reads correctly here rather
    than turning every publish into a deliverable.
    """
    d = pf.get("default")
    return bool(d) and d != site.NO_VALUE


class FPTPublishVersion:
    @classmethod
    def INPUT_TYPES(cls):
        # Re-evaluated on every /object_info request (server.py:756), so a profile edit or a new Shot
        # reaches the operator on a browser refresh. The JS extension keeps the dependent lists in step
        # while the graph is open; these are only the seed values.
        project_id = site.default_project()
        p = site.for_project(project_id)
        rows = site.links(project_id)
        links = [(l, i) for l, _, i in rows]
        first_type, first_link = (rows[0][1], rows[0][2]) if len(rows) == 1 else ("", 0)
        statuses = site.statuses(project_id)
        status_label = next((l for l, c in statuses if c == p.get("status")), UNSET)

        return {
            # Neither is required and at least one is: what a Version carries is the shape of what
            # was wired, so the node cannot declare one of them the real input. `images` stays the
            # first input and keeps its name — an input slot is addressed by name in a saved graph.
            "required": {},
            # Order is the order they are decided: the pixels, then which show, what they belong to,
            # which task, what state it is in, which stream, and last the note a person writes.
            # Everything below the note is fine print and lives behind ComfyUI's advanced fold.
            #
            # There is no link_type. Version.entity accepts 15 types and a show may use several at
            # once (DESIGN), the link picker searches every type the show uses server-side, and each
            # option carries its own — so a combo whose only job was to shorten a list nobody scrolls
            # any more was one decision to make before the one that mattered.
            "optional": {
                "images": ("IMAGE", {"tooltip": "Frames out of the graph. Alone they publish frame "
                                                "1 as the Version's still; tick Create Published "
                                                "Files to register the sequence itself."}),
                # An input slot is additive and safe where a widget is not, so this is the one part
                # of this change that a saved graph would have survived. `save_to` on it carries the
                # colour space, the bit depth and the audio our own encode never could, and a
                # `VideoFromFile` is a file on disk that is uploaded rather than touched.
                "video": ("VIDEO", {"tooltip": "A clip out of the graph — LoadVideo, CreateVideo, or "
                                               "any of the hosted video models. It becomes the "
                                               "Version's review media, uploaded as the source file "
                                               "itself where the graph did not change it."}),
                "project": (_labels(site.projects()),
                            {"default": site.project_name(project_id),
                             "tooltip": "Project to publish into."}),
                "link": (_labels(links),
                         {"tooltip": "What this Version belongs to. Version.entity accepts many "
                                     "types, so each option carries its own."}),
                "task": (_labels(site.tasks_for(first_type, first_link)),
                         {"tooltip": "Task on that entity. Often empty — probe 005 found sg_task "
                                     "filled on 1% of Versions, so it is optional by design."}),
                "status": (_labels(statuses),
                           {"default": status_label,
                            "tooltip": "Usable statuses for this project (probe 009)."}),
                # Its height belongs to the JS extension (`textRows`): a `customtext` widget is
                # built with an options object of its own and copies nothing from this spec.
                "note": ("STRING", {"multiline": True, "default": "",
                                    "placeholder": "what a person should know about this version",
                                    "tooltip": "Human note, written to description. Provenance is "
                                               "recorded separately and does not belong here."}),
                # A template in Flow PT's own vocabulary: dotted field paths, the same ones filters
                # and ?fields use (probe 003), to any depth the server will traverse. A bare token
                # is the relationship's own name — `{entity}`, `{sg_task}` — the way Flow PT returns
                # it. `{version:03d}` and `v%04d` both work.
                #
                # Advanced: `{root_name}_v{version:03d}` is a house convention, and the name you
                # actually edit per publish is `root name` above.
                "code_template": ("STRING", {
                    "default": p.get("code_template") or naming.DEFAULT_TEMPLATE,
                    "display_name": "version name",
                    "advanced": True,
                    "tooltip": "How a version of the stream is named — almost always "
                               "{root_name}_v{version:03d}. Advanced because the versioning "
                               "convention is the house's and rarely changes; the name you edit is "
                               "`root name` above."}),
                # Lineage the graph already proves is added by itself; this is for a source no
                # upstream Load node can show.
                "source_versions": ("STRING", {"default": "", "advanced": True,
                                    "tooltip": "Comma-separated Version ids this was derived from."}),
                "attach_workflow": ("BOOLEAN", {"default": True, "advanced": True}),
                "link_id": ("INT", {"default": 0, "min": 0, "max": MAX_ID, "advanced": True,
                                    "tooltip": "Overrides `link` when non-zero, for a stale list."}),
                # The one per-publish question left, and it was never about media: is this a
                # deliverable, or only review? WHICH files follow from what is wired, and whether
                # the house also keeps the review movie is `register_movie` in the profile.
                #
                # ComfyUI stores widget values by position, so nothing may be inserted above this
                # once anything outside this repo has saved a graph — DESIGN, "the widget window
                # closes at release".
                "register_files": ("BOOLEAN",
                                   {"default": _wants_files(p.get("published_files") or {}),
                                    "display_name": "Create Published Files",
                                    "tooltip": "Register the files themselves, beside the Version. "
                                               "Frames are copied under the storage root the profile "
                                               "names and registered as a sequence; a movie is "
                                               "registered where it is the deliverable, or where "
                                               "published_files.register_movie says this house "
                                               "keeps its review media too."}),
                # Declared, never inferred and never applied. A colour transform is the most
                # consequential pixel change in a comp, and this node does not make images (DESIGN),
                # so what the operator says is recorded and nothing is converted.
                "colour_space": ("STRING", {
                    "default": (p.get("published_files") or {}).get("colour_space") or "",
                    "advanced": True,
                    "tooltip": "What these pixels ARE — sRGB, ACEScg, linear. Recorded on the "
                               "PublishedFile and in the provenance record. Nothing is converted, "
                               "and nothing is guessed when it is empty."}),
                # APPENDED, never inserted: widgets_values is positional and everything above this
                # is in saved graphs already (CLAUDE.md).
                #
                # Empty is not "no name" — it is "derive one", the filename minus its version, which
                # is what recipe 004 means by `name` being the stream and `code` one version of it.
                # Typing into it locks that answer, so a later filename change cannot silently move
                # a stream someone downstream is already following.
                "root_name": ("STRING", {
                    "default": p.get("root_name") or naming.DEFAULT_ROOT_TEMPLATE,
                    "display_name": "root name",
                    "tooltip": "The stream this publish belongs to, without a version — "
                               "e.g. {entity}_matte. It is the PublishedFile's `name`, the "
                               "folder the files land in, and what `version name` is built from. "
                               "Any dotted Flow PT path works, and a bare token is that link's "
                               "own name."}),
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

        The number comes back because the path template needs the same one: a Version called v003 and
        a sequence written to `v001/` would be two answers to one question.

        `{root_name}` is rendered FIRST and handed to the version template as a value, because that
        template is `{root_name}_v{version:03d}` — the stream composed, then versioned. Resolving it
        the other way round is what left the code as a bare `v001`.
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
        """The code this node would publish next. Shared with /fpt/preview_code so what the panel
        shows is what gets written."""
        return cls.next_name(template, project_id, link_type, link_id, task_id,
                             root_template)[0]

    @classmethod
    def VALIDATE_INPUTS(cls, project=None, link=None, task=None, status=None):
        """Accept what the editor offered, because the editor knows more than INPUT_TYPES did.

        These combos are seeded for the default project and then repopulated per project by the JS
        (`setOptions`), so a value the operator legitimately picked need not be in the list this
        class declared at load time. ComfyUI skips its own membership check for any input named
        here (execution.py:1019), which is the mechanism core nodes use for the same problem
        (comfy_extras/nodes_model_advanced.py:380).

        Nothing is lost: a label that resolves to no entity still fails at run time, naming the
        label and the project, which is the more useful error anyway.
        """
        return True

    @staticmethod
    def _stage(images, media_path, code, version_no, count, colour_space, want_frames, want_movie,
               p, fpt, project_id, link_type, target, task_id, code_template="", root_name=""):
        """Everything that touches disk, done before the Version exists. None when nothing was asked.

        The storage root and the path template are profile data, per project like every other
        site-specific decision (DESIGN: site profile). The template is the language the code template
        already speaks — dotted Flow PT paths and Python's format spec (`naming.render`) — plus the
        frame token `sg_path_to_frames` uses, so nothing here is a second vocabulary.
        """
        if not (want_frames or want_movie):
            return None
        pf = p.get("published_files") or {}
        storage_id, root = sequence.root_for(publish.storages(fpt), pf.get("storage", ""))
        sequence.check_root(root)
        seq_t = pf.get("path_template") or sequence.DEFAULT_SEQUENCE_TEMPLATE
        mov_t = pf.get("movie_path_template") or sequence.DEFAULT_MOVIE_TEMPLATE
        # The two names the templates already decided, handed to the path as `{root_name}` and
        # `{version_name}`. That is what stops a path rewriting the naming scheme a second time, and
        # why `{output}` no longer appears in one: `{root_name}` IS the stream.
        # The stream is RENDERED, not derived by subtraction. `{root_name}` is its own template, so
        # there is no version token to strip back out — which is what used to go wrong when the path
        # template was stripped instead of the name one.
        root_t = root_name or p.get("root_name") or naming.DEFAULT_ROOT_TEMPLATE
        fields = (set(naming.template_fields(seq_t)) | set(naming.template_fields(mov_t))
                  | set(naming.template_fields(root_t)))
        vals = site.resolve_paths(fields, project_id, link_type, target, task_id)
        # A token nobody could resolve leaves an empty segment, and `_clean` swallows it silently —
        # so name them. corpus 028: a 200 proves nothing, and neither does a path that rendered.
        blank = sorted(k for k in fields if not str(vals.get(k, "")).strip())

        # The extension follows the files, never the template: PNG is what Pillow writes from an
        # IMAGE tensor, and a template reading `.exr` must not relabel 8-bit frames as scene-linear.
        out = {"root": root, "storage_id": storage_id, "template": seq_t, "blank_tokens": blank,
               "declared_ext": os.path.splitext(sequence.single(seq_t))[1].lower(),
               "colour": colour_space.strip(), "count": count}
        if want_frames:
            name = naming.render(root_t, vals, version_no)
            v = dict(vals, version_name=code, root_name=name, ext=".png")
            pattern = sequence.pattern(root, seq_t, v, version_no, ".png")
            # ComfyUI's own output directory first. The copy is what puts a file where the site can
            # resolve it; the original stays put so a failed publish is recoverable.
            out["frames"] = sequence.place(sequence.write_frames(images, code), pattern)
            out["frames_pattern"] = pattern
            out["frames_code"] = os.path.basename(pattern)
            out["frames_name"] = name
        if want_movie:
            # The clip's real extension, because a deliverable is never transformed: a `.mov` off
            # LoadVideo is registered as a `.mov`, and only what ComfyUI encoded here is `.mp4`.
            ext = os.path.splitext(media_path)[1].lower() or ".mp4"
            name = naming.render(root_t, vals, version_no)
            v = dict(vals, version_name=code, root_name=name, ext=ext)
            dest = sequence.pattern(root, mov_t, v, version_no, ext)
            out["media"] = sequence.copy_one(media_path, dest)
            out["media_code"] = os.path.basename(dest)
            out["media_name"] = name
        return out

    @staticmethod
    def _register(fpt, staged, project_id, vid, version_no, link_type, target, task_id, count,
                  note, colour_space, src_ids, src_files=None):
        """One PublishedFile per registered file, linked to the Version carrying the review media.

        Returns the lines the panel logs: what was registered, where it landed, and what could not be
        said — an unrecognised type, or ancestors with no files to depend on.

        `upstream_published_files` is the file-level twin of `sg_ai_generated_from`: the same
        ancestors, resolved to the files those Versions published. A tool downstream opens files, not
        Versions, so the dependency is only useful at this level.

        `src_files` is what an upstream Load node actually read (lineage.py). Where it has an answer
        the link is that file; where it does not, the site is asked and the link is every file of
        that ancestor.
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
            # path_cache is null after a REST create even though path resolved, so a filter on it
            # misses every row published this way (entity_types/PublishedFile). It is a plain text
            # field and takes a write, so the client writes what it already knows.
            body["path_cache"] = sequence.relative(staged["root"], path)
            pft = publish.published_file_type(fpt, sequence.TYPE_CANDIDATES[kind])
            if pft:
                body["published_file_type"] = pft
            else:
                notes.append(f"no PublishedFileType on this site for {kind}; registered without one "
                             f"— creating one would add it to every project (recipe 004)")
            pf_id, resolved = publish.create_published_file(fpt, project_id, code, name, path, body)
            # The 201 already carries the resolved path, so this reports what the SERVER stored
            # rather than what was sent — the two differ the moment a root is ambiguous (recipe 004).
            notes.append(f"{what}: {code} -> PublishedFile {pf_id}  "
                         f'{resolved.get("local_path_mac") or path}')
        if staged.get("declared_ext") and staged["declared_ext"] != ".png" and staged.get("frames"):
            notes.append(f'the path template names {staged["declared_ext"]}, but these frames are '
                         f'.png and are registered as .png — nothing was converted')
        if upstream:
            notes.append(f"{len(upstream)} upstream published file(s) linked")
        elif src_ids:
            notes.append("ancestors have no published files, so nothing upstream to link")
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
                "nothing to publish: wire an IMAGE into `images`, a VIDEO into `video`, or both. "
                "This node records what the graph made and never makes it.")
        frames = len(images) if images is not None else 0
        # A sequence cannot BE a Version's media (probe 022) and nothing here is being asked to
        # register it, so frame 1 would go up and the rest would vanish. Loud, never silent
        # (corpus 028) — and refused here, before the site is touched at all.
        if video is None and frames > 1 and not register_files:
            raise ValueError(
                f"{frames} frames on `images` with Create Published Files off: there is nowhere for "
                f"them to go. A Version's media is single-valued (probe 022), so only frame 1 could "
                f"be uploaded and the other {frames - 1} would be dropped. Tick Create Published "
                f"Files to register the sequence, or send the batch through CreateVideo and wire the "
                f"VIDEO into `video`.")
        # The picked project decides, then the profile answers for THAT project — two graphs open in
        # one ComfyUI can target two shows that link Versions differently.
        project_id = _id_for(site.projects(), project) or site.default_project()
        if not project_id:
            raise ValueError("no project: pick one, or set default_project in profile.local.json")
        p = site.for_project(project_id)
        link_field = p.get("link_field", "entity")   # probe 005 — never assume sg_task
        # The type comes from what was picked, not from a profile default: Version.entity accepts 15
        # types and a show may use several at once.
        link, task, status = site.unset(link), site.unset(task), site.unset(status)
        picked_type, picked_name = site.split_link(link)
        # The label carries its own type; the profile answers only for a link picked before it did.
        link_type = picked_type or p.get("link_type", "Shot")

        # Combos carry labels; Flow PT wants ids. Resolve narrowly rather than trusting a cached list.
        target = int(link_id) or (_id_for(site.entities(link_type, project_id, q=picked_name),
                                          picked_name) if link else 0)
        if link and not target:
            raise ValueError(f"no {link_type} named {picked_name!r} in project {project_id}")
        task_id = _id_for(site.tasks_for(link_type, target), task) if (task and target) else 0
        status_code = next((c for l, c in site.statuses(project_id) if l == status), "")

        # unique_id scopes provenance to this node's branch (provenance.ancestors).
        prov = provenance.extract(prompt, extra_pnginfo, node_id=unique_id)
        prov["comfy_usage_source"] = usage_source  # which client submitted this (execution.py:216)
        # Declared, not measured. The attachment is the record, so an operator's statement about the
        # pixels belongs in it — and stays a statement, never a transform.
        if colour_space.strip():
            prov["colour_space"] = colour_space.strip()
        wf = provenance.workflow(extra_pnginfo)

        fpt = site.client()
        # One schema read answers two questions: which provenance fields exist (absent until
        # `python -m comfyui_fpt.fields` has run, so the blob fallback is the honest default, not a
        # bug) and whether this site carries the frame range a movie wants.
        schema = fpt_fields.schema_names(fpt)
        have = set(fpt_fields.names().values()) & schema
        # Typed ids first, then whatever a Load node upstream already proves. The operator can add
        # a source the graph cannot see; they should never have to retype one it can.
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
        # a typo in their profile behind a Version that looks fine (corpus 028, loud and silent).
        missing = sorted(set(routed) - set(have))

        # The template decides the name, rendered from the entity and task it is actually linked
        # to. A real version-number field is authoritative where the site has one (Toolkit sites
        # usually do); the template's own {version} is the fallback for the many sites that do not.
        code, version_no = self.next_name(code_template, project_id, link_type, target, task_id,
                                          root_name)
        vnum_field = p.get("version_number_field", "")
        next_num = (naming.next_number(site.version_numbers(link_type, target, project_id, vnum_field))
                    if vnum_field and target else None)

        # Staged BEFORE the Version exists — an install with no PyAV, or a clip `save_to` refuses,
        # should stop here rather than leave a Version behind holding a still and calling it a clip.
        # The thumbnail is read here too, off the media rather than off `images`, so the still and
        # the clip cannot disagree about what this Version shows — and so a clip that decodes no
        # frames refuses before the Version exists rather than after it.
        media_path = ""
        if video is not None:
            media_path, how = movie.stage(video, sequence.folder(code), code)
            count, media_note = movie.describe(video, how)
            png = movie.poster(media_path)
        else:
            count = frames
            media_note = "frame 1 as a still" if frames > 1 else "the image itself"
            png = _png(images[0])
        # Whether the house ALSO keeps the review movie as a file is a convention, so it lives in
        # the profile; whether this publish is a deliverable at all is the node's tick. A clip
        # published on its own IS the deliverable, so it is registered without the house saying so —
        # a tick that registered nothing would be a silent no-op.
        keeps_movie = bool((p.get("published_files") or {}).get("register_movie"))
        want_frames = bool(register_files and images is not None)
        want_movie = bool(register_files and video is not None and (images is None or keeps_movie))
        # Same rule for the files: the root is resolved, the frames are written and copied into
        # place BEFORE the Version exists, so an unmounted share refuses the run rather than leaving
        # a Version pointing at frames nobody wrote.
        staged = self._stage(images, media_path, code, version_no, count, colour_space,
                             want_frames, want_movie, p, fpt, project_id, link_type, target,
                             task_id, code_template, root_name)

        fields = dict(typed)
        # description is the human note, plus whatever the operator routed into it. The full
        # graph goes up as an attachment either way, so the blob fallback is only for a site
        # that has no provenance fields and asked for nothing in the description.
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
        # probe 022's own verdict: the `%04d` pattern belongs in sg_path_to_frames, with a
        # transcoded movie uploaded for the player. Until now there was no real path to put there.
        # These are tier 2 in probe 021, which is what the Load node reads to pull frames back.
        for field, value in (("sg_path_to_frames", (staged or {}).get("frames_pattern")),
                             ("sg_path_to_movie", (staged or {}).get("media"))):
            if value and field in schema:
                fields[field] = value

        vid = publish.create_version(fpt, project_id, code, fields)
        # Every lookup a name depends on. `find` is the one the template reads; missing it let
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

        published = [f"{code} -> Version {vid}"]
        published.append(f"review media: {media_note}")
        if count > 1:
            skipped = [f for f in movie.FRAME_FIELDS if f not in schema]
            if skipped:
                published.append("no frame range recorded, this site has no " + ", ".join(skipped))
        # Frames wired in that nobody asked to keep are not an error — the clip is the review and
        # carries the same picture — but they are not silent either.
        if images is not None and video is not None and not want_frames:
            published.append(f"{frames} frames wired but not registered; the clip is the media")
        published += file_notes
        # The panel turns these into links. `site_url` comes off the client rather than the profile
        # because the run already authenticated against it — a second source could disagree. Paths
        # are what landed on disk this run, which is the one thing not recoverable from the site.
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

        if attach_workflow and wf is None:
            published.append("no workflow attached: this client sent no EXTRA_PNGINFO")
        if missing:
            published.append("mapped to fields this site does not have: " + ", ".join(missing))
        if not typed and not prov_lines:
            published.append("no provenance fields on this site — run: python -m comfyui_fpt.fields")
        # `text` keeps the plain readout ComfyUI shows anywhere; `published` is what the node's own
        # panel renders — the same run, described rather than printed.
        return {"ui": {"text": published, "published": done}}
