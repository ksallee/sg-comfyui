# Design

## Thesis

Studios generate in ComfyUI. Output lands in Slack and Dropbox with no version history, no review, no record of model, prompt, seed, or source. Clients are starting to require AI disclosure and nobody can answer.

This is not a generation tool. It is the provenance and review path for generation that already happens.

Consequence: never pitch or build a feature that makes images. Build the trail.

## Local first, agent operable

The tool runs on the operator's machine against their own site. No service, no account, no telemetry.

The operator is not expected to read the code. They fork, point an agent at the repo, and change the node or the design. That is the product, equally with the node itself.

Requirements this imposes:
- Every convention discoverable from `CLAUDE.md` alone
- Slash commands in `.claude/commands/` for the recurring jobs: `/inspect-site` measures a project and
  writes the profile, `/track-workflow` puts the nodes into a graph, `/task` does a job against the API
- Probes runnable by an agent to learn the API before editing
- No framework, no plugin system, no dynamic dispatch

## Architecture

    __init__.py      re-exports the mappings; ComfyUI reads this file and no other
    src/comfyui_fpt/
      site.py        .env.local, profile.local.json, a connected client
      publish.py     create Version, three-step upload, attach, register PublishedFile
      sequence.py    frames on disk: written to ComfyUI's output, copied under a LocalStorage root
      provenance.py  extract model/prompt/seed/graph from the ComfyUI prompt object
      nodes/         one file per node
      __init__.py    NODE_CLASS_MAPPINGS

Site access goes through `sg_groundtruth`, the sibling corpus repo's client. This repo holds node code only.

The root `__init__.py` is not optional and not decoration: ComfyUI imports `custom_nodes/<dir>/__init__.py`
directly (`nodes.py:2263`) and a `src/` layout is invisible to it. Any module importing `sg_groundtruth` must
import `_deps` first — import order inside the package decides whether the path is set up yet.

### Two paths

**Publish path** — the node at runtime. REST and `requests` only, no exceptions. A ComfyUI node ships into
someone else's Python env; every dependency is a support burden, and `shotgun_api3` is heavyweight.

**Setup path** — schema cache, inspector, field creation. Runs on the operator's machine at configuration time
with an agent present, so it may use the Python API where that is genuinely better. If REST cannot create
schema fields but `shotgun_api3` can, provenance-as-typed-fields survives as a setup step.

Same line as "LLM at configuration time, never in the publish path".

Probes exercise REST, always — their job is to prove the *node's* behaviour, and the two APIs differ in filter
syntax, return shape and upload flow. Findings carry a Python equivalent where the mapping is non-obvious; TDs
read Python, and REST-and-Python-side-by-side-both-verified does not exist anywhere else.

### Cheap index, expensive body

The pattern repeats, and it is deliberate: `probes/findings/INDEX.md` over the findings, the schema digest over
the raw schema. An agent reads the index, then opens only what it needs. An agent that must read the corpus to
answer one question burns its context on the first call and is useless for the rest of the session.

Findings are therefore tagged, and a verdict is one actionable sentence — often the only thing read.

## Schema cache

The schema is the only source of truth for what a site calls things: which `CustomEntityNN` are enabled and
their display names, which fields exist, their types, per-project status lists. It changes when anyone adds a
field, so it is cached and refreshable, never assumed.

Two layers, because a real studio site has hundreds of entity types by hundreds of fields:

- **raw** — full JSON, per site and per project, on disk, timestamped, gitignored. Refresh explicitly; the node
  never refreshes on the publish path.
- **digest** — compact, generated from raw: entity types actually in use, display name to programmatic name,
  fields with type and mandatory flag.

"Consultable by the LLM" means a query CLI over the cache, not a blob in context. It lives in the corpus repo
with the client — `python -m sg_groundtruth.schema field Version sg_task`, `python -m sg_groundtruth.schema entities
--custom`. An agent that has to read the raw dump to answer one question will burn its context on the first
call and be useless for the rest of the session.

Per site *and* per project: some field configuration and every status list is project-scoped.

## Site profile

Every site is different: custom fields, custom entity types, different mandatory fields, different status lists,
and no agreement on whether a Version hangs off a Task, a Shot, an Asset or a playlist. Integrations here fail
because they hardcode one studio's conventions, or expose every field and become unusable.

Instead the operator's agent inspects their site and writes a profile the node consumes.

The schema cache says what *exists*. The profile says what is *practiced* and what to expose.
Different lifetimes: the cache refreshes when the schema changes, the profile is inference plus
operator edits layered on top.

- Schema says what is *possible*; recent Versions say what is *practiced*. Rank fields by fill rate over the
  project's last N Versions, not by what the schema permits — sites carry hundreds of dead legacy fields.
- Keyed per project, not per site. One studio runs shows with different conventions.

`Version.entity` is not one type. The schema lists **15** valid ones — Asset, Level, MocapTake, Reel,
ShootDay, Shot, Sequence, Delivery, Launch, Camera, Slate, SourceClip and three `CustomEntity` slots —
identical on every project. So a single `link_type` was never Flow PT's model: one show hangs Versions
off Shots, another off Assets, and plenty use several at once (the reference show links 99 Shots and 1
Asset; another links Assets, Shots and Sequences).

The picker therefore offers **every type the show actually uses**, each option carrying its own type
(`bunny_030_0090 (Shot)`), and the type written to the Version comes from what was picked rather than
from a default. Which types to search is observed from recent Versions, because searching all 15 would
be slow and mostly empty — with Shot, Asset and Sequence added regardless, since observation alone is
circular: a brand new Asset cannot be picked while no Version points at one. `link_types` in the
profile overrides the lot.

Top-level keys are the site default; a `projects` block overrides them per show. Nothing is global that a
show can disagree about:

    {
      "default_project": 1180,
      "projects": {
        "1180": {"name": "sandbox",   "link_type": "Shot",  "link_field": "entity", "code_prefix": "corridor_v001"},
        "91":   {"name": "Kids Room", "link_type": "Asset", "link_field": "entity", "code_prefix": "comfy_v001"}
      }
    }

This is what lets two graphs open in one ComfyUI publish into two shows that link Versions differently. The
node resolves `link_type` from the project the operator picked on that node, and `/fpt/profile` tells the
editor the same thing so the link picker searches the right entity type. One ComfyUI, one profile, many shows.
- Plain JSON, human-editable, regenerable. Operator edits win over inference.
- Gitignored. Field naming and pipeline conventions are potentially confidential — unlike `probes/findings/`,
  which document the API itself and are safe to publish.

**The LLM runs at configuration time, never in the publish path.** It probes, then writes data. Publishing is
deterministic, offline, and costs no tokens.

## Nodes (v0)

- `Flow PT Publish Version` — an image or a video in, Version created, media uploaded, provenance attached.
  Inputs are built from the site profile: link target and exposed fields are resolved, not hardcoded.
- `Flow PT Load Version` — a Version's media back into the graph, and the link recorded

`av` (PyAV) joins `requests` and `Pillow` as a dependency ComfyUI already ships — it backs ComfyUI's own
video nodes. Imported lazily wherever a frame has to be decoded — `media.py` reading a Version's movie back,
`movie.py` taking a poster frame off the clip it is about to upload — so an install without it still loads
every node and fails only when someone asks for a movie frame. Nothing here encodes any more and nothing
shells out to ffmpeg: `VideoInput.save_to()` is ComfyUI's own encoder and owns that side.

## The node records; ComfyUI makes the media

A run is one Version. What that Version carries is decided by what is wired into the node, not by a combo
asking the operator to state again what the graph already states:

    images    video    the Version's media       what a tick registers as files
    —         wired    that video                the movie
    wired     —        frame 1, as a still       the frames
    wired     wired    the video                 the frames, plus the movie where the house keeps it
    —         —        nothing to publish — the run refuses, loudly

ComfyUI has had a first-class `VIDEO` since its video nodes landed, and this node ignored it. A video graph
had to go `VIDEO → GetVideoComponents → IMAGE →` our own hardcoded `libx264`/`yuv420p` encode: a file that
already existed on disk was decoded to float32 and re-encoded at a rate we had to guess, with no crf, no
audio and no colour properties. Over 120 classes on a stock install emit `VIDEO` — `LoadVideo`,
`CreateVideo`, `SaveVideo`, and every hosted model from Kling to Veo to Sora to Runway to Wan — so most of
the video work a studio does was running through the one part of this repo that made pixels.

**Review media is derived and may be transcoded; a deliverable file is never transformed.** That was already
the rule for frames — PNG in, PNG registered, a template claiming `.exr` overruled — and it is structural
now rather than a habit. `movie.encode` is gone. Where a `VIDEO` is a file on disk, that file is what goes
up, byte for byte. Where it is not — `CreateVideo` assembling a batch, a hosted model answering with frames —
`VideoInput.save_to()` writes it, which is ComfyUI's own encoder and knows what ours never did: sRGB is
BT.709, HDR is BT.2020/HLG, HDR PQ is BT.2020/PQ, the bit depth is the clip's, and the audio comes with it.

`sg_first_frame`, `sg_last_frame`, `frame_count` and `frame_range` are still ours, written where the site
has them. `sg_uploaded_movie_mp4`, `_frame_rate` and `_transcoding_status` are still the transcoder's and
still never written: probe 022 measured `_mp4` serving a transcode of a replaced file while status read 1,
and writing them ourselves manufactures that desync in any player that trusts them.

Image sequences stay supported as *input*: the Load node's `frames` tier is untouched.

### The file on disk is the file only when nothing has happened to it

`VideoFromFile.get_stream_source()` hands back the source path — and hands back the *whole* source path
even where the graph trimmed or cropped the clip, because `as_trimmed` and `as_cropped` return a new
`VideoFromFile` over that same file with a window recorded beside it. Uploading the source on the strength
of the class alone would file a ten-second plate as the two-second selection a supervisor asked for, and
would do it silently, which is corpus 028's failure mode exactly.

So the test is not the class, it is whether the object and the file are the same video: same duration and
same dimensions as a plain `VideoFromFile` over that path. Both are container metadata reads, neither
decodes, and a clip that fails is encoded rather than copied. Which of the two happened is on the panel,
because it is the thing an operator wants to read back.

A `VIDEO` whose source is a `BytesIO` has no file to preserve and takes the encode path. Nothing is lost:
there was never a file to leave untouched.

### `fps` and `published_files` are answers the graph already gave

The node's own `fps` widget existed because a batch of frames carries no rate and an invented 24 must not
read as a measured one. A `VIDEO` carries its rate, `CreateVideo` is where a person sets one, and a rate
read off the media beats a rate inferred from a sibling node. The widget goes, and with it the walk that
guessed for it and the three-source sentence that explained the guess.

`published_files` was a four-way combo — `(none)`, `frames`, `movie`, `frames and movie` — because the node
could not tell a sequence from the frames of a movie: one IMAGE batch, two intentions. Two inputs tell them
apart by themselves. Frames arrive as `images`, a movie arrives as `video`, the combo's four rows are the
truth table's four rows, and the operator decides by wiring rather than by agreeing with a menu afterwards.

What is left is one genuinely per-publish question, and it is not about media at all: **is this a
deliverable, or only review?** `register_files` — "Create Published Files" — is that question and nothing
else.

### `register_movie` is the house's, `register_files` is the publish's

Whether a studio *also* keeps the review movie as a `PublishedFile` beside the sequence is a convention, not
something anyone decides twice a day, so it sits in the profile with `storage`, `path_template` and
`colour_space`:

    "published_files": {
      "storage":        "primary",
      "path_template":  "{entity.code}/{output}/v{version:03d}/{entity.code}_{output}_v{version:03d}.%04d.png",
      "colour_space":   "sRGB",
      "register_movie": false
    }

The two compose in one place. `register_files` off registers nothing. On, it registers the frames wherever
`images` is wired, and the movie where `video` is wired and either the house keeps it or there are no frames
— a movie published on its own IS the deliverable, and a tick that registered nothing would be a silent
no-op.

### The impossible ask is a run-time error, not a greyed-out box

`images` alone, more than one frame, `register_files` off. The frames cannot be the media, because a
Version's media is single-valued (probe 022), and they are not being registered as files, so the only
container left is frame 1 and the other twenty-three are dropped. The node refuses, naming the count and the
two ways out: tick the box, or send the batch through `CreateVideo` and wire the `VIDEO`.

The frontend must not pre-empt this by disabling the checkbox. A batch size does not exist until execution —
it is a tensor the graph has not produced yet — so the browser could only guess, and a box greyed out on a
guess is worse than an error that knows.

### The widget window closes at release

`widgets_values` is positional, so removing `fps` and `published_files` and adding `register_files` shifts
every value below them in every saved graph. That is normally forbidden here, and it is done once, now, on
purpose: at 0.1.0 with an empty `PublisherId` and nothing published, the only graphs in the world carrying
these widgets are the ones in this repo, and they move in the same commit. After the first Registry release
the rule is the old one — append, never insert, never remove.

## The frames are files, not media

The other half of probe 022's verdict. A movie is what a supervisor reviews; the frames are what the next
department opens, and a Version cannot hold them — media is single-valued and Attachments are storage rather
than review. So the frames are a `PublishedFile`, and asking for them changes nothing about the Version: one
run is still one Version carrying one piece of review media.

    video wired            one Version, the movie uploaded. A PublishedFile where the house keeps one
    images wired           one Version carrying frame 1 for review, PLUS a PublishedFile per frame
    images and video       the movie for review, the frames as files
    a single image, no tick  unchanged: PNG to `image` and `sg_uploaded_movie`, no file, no storage root

### We copy; ComfyUI writes wherever it writes

A PublishedFile's path has to sit under one of the site's LocalStorage roots — anything else is 400 code 104
(recipe 004). That could have been a constraint on ComfyUI's output directory. It is not: the frames land in
ComfyUI's own output directory, and the node **copies** them to `<root>/<path rendered from the template>`.

Copy, never move. The run stays where the artist expects it, a publish that fails half way leaves something to
re-publish from, and a second attempt costs a copy rather than a re-render.

Everything that touches disk happens *before* the Version is created — root resolved, frames written, copies
made — for the same reason the movie is encoded first: a Version pointing at frames nobody wrote is worse than
a run that refused. An unmounted share stops the publish, and `/fpt/preview_publish` says so before the Run.

### The path template is the template language that already exists

The storage root and the path template are profile data, per project like every other site-specific decision:

    "published_files": {
      "storage":       "primary",
      "path_template": "{entity.code}/{output}/v{version:03d}/{entity.code}_{output}_v{version:03d}.%04d.png",
      "colour_space":  "sRGB"
    }

`naming.render` already speaks Flow PT's dotted field paths and Python's whole format spec, so a path template
is the same language as a code template and no second vocabulary was invented. Two things are particular to a
path:

- **`{version}` is the publish, `%04d` is the frame.** They are different numbers and a code template cannot
  tell them apart — `naming.normalise_template` reads *any* printf pad as the version, which is right where a
  TD writes `v%04d` by habit and catastrophic here, since it would freeze a sequence to one frame. So the
  frame token is lifted out before rendering and put back after (`sequence._protect`), and in a path template
  the printf form means the frame. `####` and `@@@@` work too, because `sg_path_to_frames` accepts all three
  (`media.SEQ`) and a template that disagreed with the field it fills would be its own bug.
- **The extension follows the files, not the template.** PNG is what Pillow writes from an IMAGE tensor. A
  template reading `.exr` does not make 8-bit frames scene-linear, so the real extension wins and the panel
  says the template was overruled.

The version number is the Version's own, so `pf_seq_depth_v001` and `.../v001/` cannot disagree.

### Colour space is recorded, never converted

A colour transform is the most consequential pixel change in a comp, and this project does not make images. So
`colour_space` is a widget the operator fills in — declared, never inferred from the tensor, and never applied.

Where it lands took an argument. This site's `PublishedFile` has 33 fields and none of them is a colour space,
and probe 019's rule is that a name spent is spent site-wide forever — so no field is created for it. It goes
in `PublishedFile.description`, which is a real field this type already has and the place a person reads, and
into the `.provenance.json` attachment, which is the record. A studio whose site *does* carry a colour space
field points at it the same way every other concept is pointed at, in the profile.

It is a per-node widget rather than a profile value alone because two outputs of one graph can differ — a
depth pass is not the beauty — with the show's usual answer seeded from the profile.

### Dependencies are linked at the file level

`upstream_published_files` is the PublishedFile-level twin of `sg_ai_generated_from`. The publish node already
knows which Versions this one came from; where those Versions published files, those files are what a
downstream tool actually opens, so the link is only useful at this level. It is written from the same ancestor
set, resolved with one `_search`, and left empty — reported, not invented — when the ancestors published
nothing.

`sg_status_list` is deliberately *not* copied from the Version. PublishedFile carries its own status list —
`wtg`, `ip`, `cmpt` here — and the Version's codes are a different set entirely (probe 009). The field's own
default applies.

`path_cache` is written by hand. The server fills `path_cache_storage` from the path it resolved but leaves
`path_cache` null after a REST create, so a filter on it misses every row published this way
(`entity_types/PublishedFile`). It is a plain text field, it takes a write, and the client already knows the
answer.

### Where someone else wrote the files, we register them

`write_frames` is the one place this node makes a picture, and what it makes is an 8-bit PNG. That is the
honest answer for an `IMAGE` batch, which is a tensor and has no file. It is the wrong answer the moment a
colour-managed graph is in play, where `OCIO Write` has already written 32-bit EXR in a known space: writing
8-bit PNGs of scene-linear data under a truthful `colour_space` label would be worse than refusing.

So a third input, `files`, and the rule the other two already follow — `images` and `video` are the review
side and may be derived; `files` is the deliverable side and is never touched:

    images  wired    review media, plus PNGs written from the tensor when the box is ticked
    video   wired    review media; a file on disk is uploaded untouched
    files   wired    the deliverable, registered where it already lies. No PNG is written at all

**It is a socket, not a widget**, so this lands without moving `widgets_values`. `OCIOWrite` declares
`RETURN_TYPES = ("STRING",)` and `RETURN_NAMES = ("path",)` alongside `OUTPUT_NODE = True`, so the path is
already on a wire and nobody has to type one. Adding an input slot is additive; adding a widget is not.

**What comes down that wire is one concrete path, not a pattern.** `OCIOWrite` returns the written file for
a still and for a movie, and `paths[0]` — the *first frame* — for a sequence: `<folder>/<name>.0086.exr`,
four-digit, re-based to its own `start_number`. Everything here speaks the other notation (`media.SEQ`:
`%04d`, `####`, `@@@@`), so the first job is `sequence.discover(first)` — same folder, same stem, same
extension, digits in the frame slot and nothing else — giving back the pattern, the frames and the real
range. Anchored on all four, because a loose glob in a render folder collects the neighbours.

**The folder holds more than pictures.** `write_sidecar` defaults on, so `<name>.json` sits beside the
frames, and a sequence carrying audio gets a `.wav` as well. Only the pictures are registered. The sidecar
is named in the description, because an artist who cannot find a tag needs to know the file is there, and it
gets no PublishedFile of its own: this site has no type for it, and a type is never created — a
PublishedFileType has no `project`, so minting one adds it to every show on the site (recipe 004), which is
probe 019's rule again.

**The copy becomes conditional.** "We copy; ComfyUI writes wherever it writes" was written when the frames
always began in ComfyUI's output directory. An operator who points `output_folder` straight at the storage
root has already put the file where the site can resolve it, and copying it beside itself would duplicate a
4K EXR sequence for nothing. So: already under the root, register in place; anywhere else, copy as before.
`sequence.relative` answers `path_cache` either way.

**Colour space stops being a claim.** `colour_space` is a widget the operator types precisely because this
node cannot know what a tensor is. It *can* know what an EXR is: `output_colorspace` is a value on the
`OCIO Write` that made the file, sitting in the graph this node already reads whole for provenance
(`provenance.extract`). Where the wire leads back to a Write we can identify, that value wins and the panel
says where it came from; the widget stays for everything else, and for when identification fails. Two
sources for one field is worth it because one of them is measured and the other is a promise — but they are
never blended, and the record always names which it was. Nothing is converted either way.

**`register_files` does not gate it.** A tick that registered nothing would be a silent no-op, which is the
same argument that already registers a clip published on its own: someone who wired a Write's output into a
publish node has said what this is. `files` wired means registered.

**The residual risk is `partial_execution_targets`, and it is not closed.** Both nodes are `OUTPUT_NODE`s,
and ComfyUI's front end can send a list naming which output nodes to run — every output node not in it is
dropped before execution starts. A selective run can therefore execute this node while `OCIO Write` never
fires, leaving `files` pointing at whatever was on disk from last time. A missing file refuses loudly. A
*stale* one cannot be refused: a cached Write that legitimately did not re-run returns the same path with
the same mtime, so treating that as an error would break the normal case. The panel reports the path, the
frame count and the mtime of what it registered, and the operator sees the date. Closing it properly needs
a probe of what the front end actually sends on a selective run. That probe does not exist.

## Media comes back the same way it went out

A fetched Version is an ancestor, not just pixels. `version_id` is a plain widget, so it is already in the
prompt graph — the branch walk that scopes provenance answers "what did this come from" for free, and the
operator never types an id. A plate becomes a previs; several Versions become one output; the chain lives in
Flow PT.

Which media a Version can deliver is a property of that Version, not of the site (probe 021), so the editor
asks per pick and offers only sources that resolve to a real file.

Published files **were** not a tier, and the reason is worth keeping rather than deleting: on the only site
available, the types a graph wants carried no path at all. That was recorded as unproven, not as absent.
What closed it is this repo writing them. A publish registers a PublishedFile per file and the server
resolves the path in the 201 itself (recipe 004), so there are now real files to read, and they come
**first**: a PublishedFile is the only source that names a *type*, which is what makes "the rendered
sequence" and "the mp4" on one Version distinguishable, and the only one carrying the colour space the
publisher declared.

Which is why the `source` combo holds a *type and a filename* — `Rendered Image · sh010_comp_v003.%04d.png
#6843` — with the id last, as the tiebreak two publishes of one stream differ by. Nobody picks by id. It is
also the stored widget value, so a file later renamed or re-typed stops matching and the node lists what the
Version does have, by label, rather than loading a plausible neighbour.

The rule that made this design good did not change: a source is offered only when it can actually deliver.
A PublishedFile with no path, or a path on a root this machine has not mounted, is absent from the picker
rather than a run that fails at the end. Still unproven, and the same shape of gap: a path resolved for a
platform other than the one publishing — the only LocalStorage row here defines `mac_path` and leaves the
other two null, so `local_path_windows` and `local_path_linux` read null on every row written — and a site
whose PublishedFiles a real publisher wrote rather than this node.

Tier 2 also resolves on anything this node published: a sequence publish writes the real `%04d` pattern into
`sg_path_to_frames`, and a registered movie into `sg_path_to_movie`. probe 021 found `sg_path_to_frames`
filled on 0 of 53 Versions and probe 022's verdict was to put the pattern there; until there was a shared
root to point at, there was nothing to write.

### A clip, not a frame

A sequence that comes back one frame at a time is not an input to a video graph, so a source can deliver a
**batch of N frames** — a sequence off disk, or a movie decoded. `frame` is the first frame of the range and
kept that meaning; `frame_count` beside it says how many.

`frame_count` defaults to **1**, which is exactly what the node always returned. A batch is opted into, never
handed over: a graph saved before the widget existed asks for one image and must keep getting one. The widget
is also *appended*, last, after the multiline filter box it has no business sitting under — `widgets_values`
is positional, so a widget inserted above an existing one displaces every value in every graph already saved,
including graphs this repo will never see. A row in the wrong place is cosmetic; a silently shifted value is
not.

The batch has to be bounded, because 300 frames of 4K is 27.8 GiB of float32 and an allocator's answer to
that is a stack trace. So the ceiling is a **size**, not a count: `media.BATCH_BUDGET` is 4 GiB, checked
against the real resolution after the first frame is read, and the refusal names the resolution, the total,
and how many frames do fit at it. `MAX_FRAMES` (512) is only the widget's own guard against a typo. A short
read comes back short and says so — padding a batch to the number asked for would be this node inventing
frames — and frames whose size changes mid-sequence are refused by filename rather than by two shapes in a
torch traceback, because they cannot stack and no resize belongs here.

### Colour space travels with the pixels

Publish records a declared colour space on the PublishedFile description and in the `.provenance.json`. The
Load node reads it back onto the panel and out of a fourth output, so a claim made once upstream reaches the
artist about to comp instead of being retyped. **Recorded, never applied**: nothing converts, nothing infers,
and a Version that declared nothing says nothing rather than defaulting to sRGB.

### The upstream link is exact where it can be

`upstream_published_files` was every PublishedFile of every ancestor Version — right, and approximate: on a
Version carrying both a sequence and its mp4 it claims a dependency on both when the graph read one. The Load
node now records the file it actually opened (`lineage.py`, beside the Version id it resolved), and the
publish node links that one file. Ancestors that were read through a path field or an upload opened no
PublishedFile, so they still get the search — approximate is the honest answer where nothing narrower is
known, and the two cases are decided per ancestor rather than per run.

## Where the version number lives is site-specific

A Toolkit-driven site usually carries a real numeric field on Version — `sg_version_number` or
similar — and that is authoritative when present, so `version_number_field` names it in the profile
and the node writes it. Many sites have none (this one has none; `PublishedFile.version_number` is a
different entity), and then the version lives inside `code` as a freeform convention that differs per
show. Both paths are supported and neither is assumed.

So the convention is inferred from the codes a show already uses, shown to the operator with its
coverage, and stored in the profile as data:

    "code_template":   "{entity.code}_{output}_v{version:03d}",
    "code_regex":      "^(?P<entity>.+)_(?P<output>[A-Za-z]+)_v(?P<version>\\d+)$",
    "approved_status": "apr"

Measured on three real projects: the reference show scores 100/100, this sandbox 2/3, and a project of
ad-hoc test names 0/53. **The coverage number is the point** — 0% is the honest answer, and the
operator sees it rather than getting a confident wrong guess.

There is deliberately **no "approved" concept**. Flow PT has no such thing — approved is one status
code among many, the codes differ per project (probe 009), and a show may care about `rev`, `ip`, a
custom code, or none. So a Load node takes a status the operator picks from that project's real list,
and empty means any. An earlier version of this hardcoded "latest approved", which was this project
inventing vocabulary the API does not have.

### Which makes two nodes a pipeline

`code = auto` numbers per link. `select = newest matching` resolves at run time using Flow PT's own
rule — order newest-first (`id` or `created_at`), optionally require a status, optionally require a
substring in the code. Ordering by the convention's version number is offered as a third option,
because a re-published v002 is newer by id but older by intent. So step N publishes and step N+1
consumes it, with no id copied between graphs, and the lineage field records the join by itself.

A Version resolved at run time is not in the prompt graph, so `lineage.py` records what each Load node
actually resolved and the publish node reads back only its own ancestors' entries.

## Provenance

Captured per publish:

| field | source |
|---|---|
| model, seed, sampler | ComfyUI prompt graph |
| prompt | text that reached a conditioning input in this branch — see below; not "text near a seed" |
| workflow JSON | attachment — best effort, see below |
| submitting client | whoever POSTed `/prompt` said so — see below |
| input Version ids | upstream `Flow PT Load Version` nodes, or typed by hand |
| user, timestamp | client |

### The workflow attachment is best effort

`PROMPT` is guaranteed — execution cannot happen without it. `EXTRA_PNGINFO` is not: it is whatever the
client put in `extra_data`, and `None` otherwise (`execution.py:199`). The standard frontend sends it; the
`comfy` CLI, the ComfyUI MCP server, and every wrapper UI that builds its own API-format prompt do not.

So a publish must never depend on the workflow, and must say when it is missing rather than quietly
omitting it. Which client submitted the prompt is exactly the information needed to explain an
absent workflow later, and that is what the generator field carries.

This is also the reason the demo drives ComfyUI over plain HTTP rather than through its MCP server:
an MCP-submitted prompt exercises the degraded provenance path.

### The submitting client names itself; nothing else names it

`COMFY_USAGE_SOURCE` is the hidden-input spelling and it reads like an environment variable. It is
not one. ComfyUI hands the node `extra_data.get("comfy_usage_source")` from the submitted prompt
(`execution.py:224`) — a string chosen by whoever POSTed `/prompt`, never read from the environment
of the running server. A `Comfy-Usage-Source` header is copied into `extra_data` only when the body
omitted the key (`server.py:1120`), so the body always wins.

The standard frontend does set it: `comfyui-frontend`, hardcoded in the body of every Run, confirmed
by driving a browser and reading the request off the wire. So a Version reading
`ComfyUI (unknown client)` was not published by a person clicking Run — it was published by a script
that POSTed a prompt and said nothing about itself. That is the whole value of the field, and it
survives only if our own harnesses fill it in: `tools/qa_node.py` rewrites the body of every
`/prompt` it drives so a QA run is not filed as an artist at a keyboard.

### Where each piece lands is the operator's, not ours

The nine fields are a default, not a schema. A studio that already records seeds in `sg_render_seed`,
or that wants nothing but a readable paragraph, should not have to fork the node — so the mapping is
data, per project, beside every other per-show decision:

    "provenance": {
      "mode": "fields",
      "map": {
        "seed":   "sg_render_seed",
        "prompt": "description",
        "cfg":    null
      }
    }

`mode` is the fallback for concepts the map does not name: `fields` uses the defaults, `description`
folds everything into the note. That is the difference between one word and nine null entries, and
"put it all in the description" is a real request.

The concepts — generator, model, prompt, negative_prompt, seed, sampler, steps, cfg,
generated_from — are what the graph knows. `fields.concepts` produces them, `fields.targets`
resolves the operator's decision once, and both the publish path and `/fpt/preview_publish` read
that same resolution, so the panel shows where a value will actually land rather than where this
repo would have put it.

A target the site does not have is **reported, not dropped**: a typo in a profile would otherwise
hide behind a Version that looks fine.

Pointing at a field the studio already has is the preferred move, and cheaper than it looks —
`fields.ensure` only creates what `FIELDS` names, and every name it spends is spent site-wide
forever (probe 019).

### Typed fields, not a JSON blob

`fields.py` defines nine fields on Version and creates them idempotently (`python -m comfyui_fpt.fields`).
`description` is then the operator's note, and the complete structure still rides up as a
`.provenance.json` attachment — the fields are the queryable summary, the attachment is the record.

Three constraints came out of probe 019 and are not negotiable:

- **Seed is `text`.** A `number` field takes 2**31-1 but 400s at 2**63; ComfyUI seeds reach 2**64-1.
- **`ensure()` reads `/schema` first.** Re-POSTing an existing display name does not error, it silently
  creates `<name>_1`, so a POST-and-hope ensure quietly multiplies fields on every run.
- **Field names are permanent.** DELETE frees the field but never its name, and trashed fields cannot be
  enumerated, so the collision is invisible. Adding to `FIELDS` spends a name site-wide, forever.

Lineage is `sg_ai_generated_from`, a `multi_entity` of Version — probe 019 confirms multi_entity
round-trips `{type, id}` hashes and takes exactly one `valid_types` element.

Not "source versions": the sources need not be AI, and a scanned plate feeding a previs is the ordinary
case. The `AI` describes this Version's generation, not its inputs. Display and programmatic names are
kept in step — a TD reading `sg_ai_generated_from` should find "AI Generated From" in the UI — so a
rename means a new field, never a relabel.

## Provenance is per branch, not per graph

One graph holds several independent branches — three lookdev variants off a shared depth pass. The
publish node takes `UNIQUE_ID` and walks back through its own inputs (`provenance.ancestors`), so each
Version describes only what produced *its* image. Without it every Version carries every other variant's
prompt and seed, and a depth AOV claims sampler settings it never used.

Tracing conditioning respects the input it started from: `ControlNetApplyAdvanced` takes both `positive`
and `negative`, so following every link merges the two prompts into one.

C2PA where the writer supports it; custom fields plus attachment otherwise. Field names are decided by probe, not by the docs.

## A prompt is text that reached a conditioning input, not text near a seed

Half the graphs a VFX shop runs never sample. A segmentation graph is the sharp case: `SAM3_Detect`
takes a text prompt that decides *what gets cut out* — "the actor" — and there is no seed anywhere in
it. Looking for text by walking back from a node that carries a seed is a diffusion-shaped assumption,
and under it the single most important creative input in a roto graph was recorded nowhere queryable.

So the rule is the one the graph itself uses. **Text becomes a prompt when an encoder turns it into
CONDITIONING and a node consumes it** (`provenance.directing_text`). A sampler consuming conditioning
and `SAM3_Detect` consuming conditioning are the same event; the seed was never what made it a prompt.
The same walk also picks up modern custom-sampler graphs, where the seed sits on `RandomNoise` and the
conditioning on a `CFGGuider`, and which therefore recorded no prompt either.

That consumption test is also the whole of the conservatism. The alternative — scrape every string
widget — puts `filename_prefix`, `ckpt_name` and a format enum into `sg_ai_prompt` and makes the field
useless. None of those reaches a conditioning input. Neither does `TextOverlay`'s caption or
`SaveText`'s payload, which is why the loose `text` key is safe here and would not be on its own.

Roles: `positive` and `negative` name one, a bare `conditioning` input does not. Text found with no
role reads as positive **unless a roled walk already claimed it**, so a `FluxGuidance` sitting on a
sampler's negative cannot smuggle the negative prompt into the positive one.

One exception to "must be conditioning": a widget named `prompt` or `negative_prompt`. Every cloud
generator node (Kling, Veo, Runway, Bria, the Qwen edit encoders — 147 core classes) takes its words
that way and encodes nothing. All 147 declare it multiline and none of them ever names a file, so the
name alone is enough. That is the only widget name trusted without the conditioning test.

### One node, several tokenisers

`CLIPTextEncodeSDXL` takes `text_g` and `text_l`, `CLIPTextEncodeFlux` takes `clip_l` and `t5xxl`,
and SD3, HiDream, HunyuanDiT, Kandinsky5 and Lumina2 each spell it differently again. Only `text`
was read, so every SDXL and Flux graph published an empty `sg_ai_prompt` — with a sampler present,
which is what made this a second hole rather than the seedless one. `ENCODER_TEXT_KEYS` names all
eleven spellings. Across the 908 core classes each name but `text` occurs on exactly one class,
always a multiline STRING on a node returning CONDITIONING, so the name alone identifies it.

**Two encoders that disagree are two texts, not one sentence.** They usually hold the same line and
dedupe to one. When they differ — a scene in `text_g` and a style in `text_l`, keywords for `clip_l`
and a paragraph for `t5xxl` — both are kept, separately. Concatenating would put a sentence nobody
typed into the field a supervisor searches; picking one would silently drop the other. The list
already carries several texts wherever a graph has several encoders, and `fields.concepts` joins
them with " | " like any other.

**`ConditioningZeroOut` is a wall.** It erases what it is handed, so text behind it reached nothing.
A Flux or SD3 negative is conventionally the positive encoder zeroed out, so without the wall these
keys would report every such graph's positive prompt as its negative one too. 31 publish points in
the corpus were already doing exactly that through plain `CLIPTextEncode`; the wall is what fixes
them, and it is the larger half of this change.

Deliberately **not** captured, and each for a reason:

- **A click instead of a prompt.** `SAM3_Detect.positive_coords` is a JSON point list. The role prefix
  would otherwise catch it, so `_coords` is excluded by name.
- **`WanTrackToVideo.tracks`**, a multiline STRING of motion paths on a node that does return
  CONDITIONING — the `positive_coords` case with a different name; and `MakeTrainingDataset.texts`,
  a file list.
- **`tags`, `lyrics` and `caption`** on the AceStep and MiniMax music encoders. They are conditioning
  and they are words, but an audio graph publishes no image, and a lyric sheet is a document rather
  than a direction.
- **A `prompt` input wired from a string node** rather than typed. The words are then in a
  `PrimitiveString`'s `value`, which is a generic string widget again.
- **Text assembled by third-party concat nodes**, as in the ZHO gallery graphs. Nothing readable
  reaches the encoder, so nothing is recorded — the right answer, not a guess.

### It stays in `sg_ai_prompt`; no new field

"What did you tell it to cut?" and "what did you tell it to generate?" are one question — the words the
artist gave the model — and a supervisor filtering Versions should type them in one box. A second field
would split that query in half and spend a name site-wide forever (probe 019), and would force every
operator to map two concepts for one idea in `site.provenance_map`.

Which node the text actually reached is not lost: `provenance.extract` records `prompts` alongside
`samplers`, and the whole structure rides up as the `.provenance.json` attachment. Fields are the
queryable summary, the attachment is the record — the same split as everywhere else here.

A graph that genuinely has nothing to say still records nothing. `07_retime` fills `generator`, `model`
and `generated_from` and leaves `prompt`, `seed` and `sampler` empty, and that is correct.

## Coverage, measured

"Works on any workflow" is a claim, so it is measured rather than asserted. The corpus is 680 real
graphs: the 629 ComfyUI template workflows every user sees in the template browser, plus the three
most-starred public collections (ZHO, Yolain, `comfyanonymous/ComfyUI_examples`).

Re-measured 2026-09-03, after `instrument.py` learned to see through subgraphs:

                                    before   after
    analysed without error         680/680  680/680
    finds a publishable stream     509/680  546/680   75% → 80%
    finds a loader to replace      428/680  430/680
    publishable streams, in total      977     1419

**The count is the small half of it.** 246 of the 680 graphs put their work inside a subgraph, and of
those, 200 already reported *something* — the instance's own output slot, or a plate feeding it. What
they reported was the wrong thing. 297 streams moved from a subgraph instance's output onto the node
that actually makes the picture, which is where the name lives: `video_ltx2_i2v` used to offer
`scale_dimensions`, a node feeding the block, and now offers the `VAEDecode` inside it;
`3d_moge_perspective_to_mesh` now offers `normal_opengl` and `normal_directx` by those names, which
existed only inside. 215 graphs have a stream that exists nowhere else. So a TD opening a current
template and running `/track-workflow` is no longer told there is nothing to do on a graph full of
work.

29 old addresses are gone rather than moved, and all 29 were wrong: 27 were an IMAGE feeding a
subgraph that only *looked* like a video sink because the instance declares a VIDEO output — the
input plate reported as an output — and 2 were an instance output slot nothing inside ever fed. **No
graph that used to find a stream finds none now.**

14 of the 37 newly-covered graphs came from a second, smaller correction in the same pass: a save
node is an end even when it also hands the picture on. `SaveImage` feeding an `ImageCompare` so the
operator can see before and after is the shape, and it hid every SeedVR2 int8 upscaler.

Instrumenting is measured too, not just analysis: all 586 corpus graphs that have anything to
instrument were tapped and had their loader replaced, and all 586 came out with unique node and link
ids across the document, no dangling endpoint, every instance's output count matching its
definition's, and the publish node fed by exactly the stream that was asked for.

The 134 that still find nothing are mostly 3D, audio and text graphs with no image output at all,
correctly out of scope.

Before the sink rule learned that frames assembled into another medium end an image stream too
(`instrument._is_sink`) the number was 57%. That one fix moved 124 workflows, nearly all of them
video. Those graphs end in a `VIDEO`, which is now what the publish node takes — see "The node records;
ComfyUI makes the media".

### Subgraphs

`instrument.py` analyses a flattened view (`_flatten`), because a subgraph instance is a relay rather
than a node: what the definition's `inputNode` hands on is whatever the instance's input was fed, and
what its `outputNode` receives is what the instance's output emits. Splicing those pairs gives the
graph ComfyUI itself executes — confirmed against `graphToPrompt`, which addresses the same interior
node as `306:296` where this addresses it `306/296`. Nesting comes out for free and does occur: 76
places in the corpus instantiate a definition inside another, one level deep, never more.

Tapping crosses the boundary at the instance's output: the stream is **promoted** to an output slot,
exactly as dragging an interior output onto the subgraph's output panel does in the editor, so the
publish node itself stays at the top level with its pickers rather than being buried a level down. If
the stream already leaves through an output — as a template's own `depth` pass does — that slot is
reused and nothing is added at all.

Promotion is additive and safe. The reverse is not: a definition's interior is shared by every
instance of it, so rewiring an interior input to feed it from outside would break the other
instances. A loader inside a subgraph is therefore replaced *inside* that same subgraph. Only 3
corpus graphs have one, and no corpus graph instantiates a definition twice — but the file is
someone else's, so the rule is the rule and not the measurement.

The naming rule is unchanged in spirit and needed one addition: what a stream is called still comes
from what the graph already says, and inside a subgraph the graph says one more thing — the
subgraph's own name. Its useful half is the *opposite* half from a sink label's. "Preview Image
(normal_opengl)" says what the stream is inside the brackets; "Depth Estimation (Depth Anything 3)"
says it before them and names a model inside. So the trailing bracket is dropped, and the name is
tried only after everything nearer the stream.

## Non-goals

Charts, dashboards, reports, webhooks, automations — see `CLAUDE.md`. Video and OTIO. Inpainting UI. three.js. Browser extension.

## Later

React review surface showing iteration lineage, extracted into an MIT component registry. Not in this repo.

## Node anatomy

A custom node is a Python class registered from `__init__.py`. Verified against docs.comfy.org, 2026-09-02.

    class FPTPublishVersion:
        @classmethod
        def INPUT_TYPES(cls):
            return {
                "required": {"images": ("IMAGE", {})},
                "optional": {"description": ("STRING", {"multiline": True})},
                "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
            }
        RETURN_TYPES = ()          # trailing comma matters when there is one
        FUNCTION = "publish"
        CATEGORY = "Flow Production Tracking"
        OUTPUT_NODE = True         # terminal node: always executes

    NODE_CLASS_MAPPINGS = {"FPTPublishVersion": FPTPublishVersion}
    NODE_DISPLAY_NAME_MAPPINGS = {"FPTPublishVersion": "Flow PT Publish Version"}

`INPUT_TYPES` is a classmethod evaluated at load, which is what lets the mapping drive the inputs.

There is a second, newer schema — `io.ComfyNode` with `define_schema()` returning an `io.Schema`, which is
how the stock `comfy_extras/*` nodes are now written; `execution.py` branches on `is_v3`. Both are live and
v1 is not deprecated. **This repo targets v1**, because a registry node should load on the older ComfyUI a
studio actually has installed, and because the dict form is the one a forker's agent can read without
learning a second vocabulary. The cost is that v1 hidden inputs are raw dict lookups, where v3's
`HiddenHolder` returns `None` for anything absent (`_io.py:1545`) — so we handle the `None` cases ourselves.

### Where provenance comes from

The hidden inputs are the whole provenance mechanism. `PROMPT` is the executing prompt graph — model, seed,
sampler, steps, cfg all live in its node widget values. `EXTRA_PNGINFO` carries the workflow as saved, which is
what gets attached as a file. `UNIQUE_ID` identifies this node instance.

Nothing else needs to be asked of the user; the graph already knows.

## Distribution

Two ways in, and they are not the same thing:

- **Git clone into `ComfyUI/custom_nodes/`** — what a developer does. `requirements.txt` is installed by
  ComfyUI-Manager.
- **The Comfy Registry** — what everyone else does, reached through ComfyUI-Manager or `comfy node install`.
  Publishing needs a `pyproject.toml` with a PEP 621 `[project]` block plus `[tool.comfy]` carrying
  `PublisherId`, `DisplayName` and `Icon`. Publish with `comfy node publish`, or a GitHub Action on
  `REGISTRY_ACCESS_TOKEN` triggered by a version bump.

### Names

`[project].name` on the Registry is immutable, so it is decided here rather than in passing:

    [project].name                comfyui-flow-production-tracking   permanent
    [tool.comfy].DisplayName      Flow Production Tracking
    repo, custom_nodes directory  comfyui-flow-production-tracking
    CATEGORY                      Flow Production Tracking
    node titles                   Flow PT Publish Version, Flow PT Load Version
    Python package                comfyui_fpt

The long form goes in the slots that are searched — a TD looks for the product, not an abbreviation, and
half of them still search "shotgrid", which belongs in the registry keywords and the README where it can
be changed later. Node titles stay short because they render on the node body. The Python package stays
`comfyui_fpt`: it is internal, every import is relative, and `python -m comfyui_fpt.fields` has to be
typable.

`Publish`/`Load` is both vocabularies at once — `tk-multi-publish2`/`tk-multi-loader2` on the Flow PT
side, and on the ComfyUI side `Load` is what a node is called when it is where the pixels come from.
`Fetch` was neither.

`NODE_CLASS_MAPPINGS` keys are written into every saved workflow, so they are permanent from the moment
anyone outside this repo saves a graph: `FPTPublishVersion`, `FPTLoadVersion`.

The cost of the long form is paid twice in the editor, and it is accepted rather than unnoticed: the
Templates browser labels a pack's collection with the `custom_nodes` directory name verbatim
(`title: e` in the frontend bundle) and the node's footer badge is `python_module` split on `.` —
the same string. Neither reads `DisplayName`, and the only override is a frontend i18n key
(`templateWorkflows.category.<name>`) that ships with the frontend and not with a pack. Registry
names allow no spaces, so a short label was reachable only by renaming the repo, which trades a
searched slot for a cosmetic one. `comfyui-flow-production-tracking` on two chips is the price.

### The dependency problem

`_deps.py` resolves `sg_groundtruth` from a sibling checkout. That works here and is **not distributable** — a
registry install gets this repo and nothing else, and `sg-groundtruth` is private.

Three ways out were weighed, and the first is **chosen** (2026-09-04):

1. **Publish the *client* half of `sg-groundtruth` to PyPI as a slim package** and depend on it normally. The
   corpus stays private; only the client ships. Done in `sg-groundtruth`, not here — this repo keeps
   `_deps.py` and the sibling checkout until the package is on PyPI and the green light is given, then swaps
   to a plain dependency in one commit.
2. Vendor the client into this repo. Rejected: it forks, and a client fix would have to land twice.
3. Declare a git dependency. Rejected: fragile, and impossible while the repo is private.

The surface is small enough that the choice was never about effort — 99 lines across two files, `FPT` and
`FPTError` from `client.py` and `load` from `env.py`, with `mcp.py`, `naming.py` and `schema.py` unused and
nothing reaching the corpus. `env.ROOT` resolving to site-packages once installed is a non-issue: `site.py`
already passes this repo's own root to `load`.

Decided before publishing, not after — `[project].name` on the Registry is immutable.
