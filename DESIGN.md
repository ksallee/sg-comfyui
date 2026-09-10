# Design

## Thesis

Studios generate in ComfyUI. Output lands in Slack and Dropbox with no version history, no review,
and no record of model, prompt, seed or source. Clients are starting to require AI disclosure.

This is not a generation tool. It is the provenance and review path for generation that already
happens.

Rules out: any feature that makes images.

## Local first, agent operable

The tool runs on the operator's machine against their own site. No service, no account, no telemetry.

The operator is not expected to read the code. They fork, point an agent at the repo, and change the
node or the design. That is the product, equally with the node itself.

Requirements this imposes:

- Every convention discoverable from `CLAUDE.md` alone.
- Slash commands in `.claude/commands/` for the recurring jobs. `/inspect-site` measures a project
  and writes the profile. `/track-workflow` puts the nodes into a graph. `/task` does a job against
  the API.
- Probes runnable by an agent to learn the API before editing.
- No framework, no plugin system, no dynamic dispatch.

`tools/qa_node.py` drives one node in a real, headless ComfyUI and prints only what the drive script
returned. `--start` launches an instance with its own port and its own `--base-directory`, which
relocates `custom_nodes`, `input`, `output`, `temp` and `user`. `ComfyUI/custom_nodes/<pack>` is
normally a symlink to a checkout, so without that isolation every instance loads the checkout's code.
`COMFYUI_PATH` overrides where ComfyUI is, and defaults to `~/dev/ComfyUI`.

## Architecture

    __init__.py      re-exports the mappings; ComfyUI reads this file and no other
    src/comfyui_sg/
      credentials.py who the nodes publish as: the signed-in person, else the script key
      site.py        profile.local.json, a connected client, the cached lookups
      publish.py     create Version, three-step upload, attach, register PublishedFile
      sequence.py    frames on disk: written to ComfyUI's output, copied under a LocalStorage root
      provenance.py  extract model/prompt/seed/graph from the ComfyUI prompt object
      nodes/         one file per node
      __init__.py    NODE_CLASS_MAPPINGS

Site access goes through `sg_groundtruth`, the sibling corpus repo's client. This repo holds node
code only.

The root `__init__.py` is required. ComfyUI imports `custom_nodes/<dir>/__init__.py` directly
(`nodes.py:2263`) and a `src/` layout is invisible to it. `sg_groundtruth` is an ordinary installed
dependency, so any module may import it in any order.

### Two paths

**Publish path.** The node at run time. REST and `requests` only, no exceptions.

- A ComfyUI node ships into someone else's Python environment.
- Every dependency is a support burden.
- `shotgun_api3` is heavyweight.

**Setup path.** Schema cache, inspector, field creation. Runs on the operator's machine at
configuration time with an agent present, so it may use the Python API where that is genuinely
better. If REST cannot create schema fields but `shotgun_api3` can, provenance as typed fields
survives as a setup step.

Same line as "LLM at configuration time, never in the publish path".

Probes exercise REST, always. Their job is to prove the node's behaviour, and the two APIs differ in
filter syntax, return shape and upload flow. Findings carry a Python equivalent where the mapping is
non-obvious. TDs read Python, and REST and Python side by side, both verified, does not exist
anywhere else.

### Cheap index, expensive body

An index over every expensive body: `probes/findings/INDEX.md` over the findings, the schema digest
over the raw schema. An agent reads the index, then opens only what it needs.

An agent that must read the corpus to answer one question burns its context on the first call and is
useless for the rest of the session. Findings are therefore tagged, and a verdict is one actionable
sentence.

## Schema cache

The schema is the only source of truth for what a site calls things: which `CustomEntityNN` are
enabled and their display names, which fields exist, their types, per-project status lists. It
changes when anyone adds a field, so it is cached and refreshable, never assumed.

Two layers, because a real studio site has hundreds of entity types by hundreds of fields:

- **raw** is the full JSON, per site and per project, on disk, timestamped, gitignored. Refresh
  explicitly. The node never refreshes on the publish path.
- **digest** is compact and generated from raw: entity types actually in use, display name to
  programmatic name, fields with type and mandatory flag.

"Consultable by the LLM" means a query CLI over the cache, not a blob in context. It lives in the
corpus repo with the client: `python -m sg_groundtruth.schema field Version sg_task`,
`python -m sg_groundtruth.schema entities --custom`.

Cached per site *and* per project. Some field configuration and every status list is project-scoped.

## Site profile

The operator's agent inspects their site and writes a profile the node consumes.

It rests on:

- Every site differs in custom fields, custom entity types, mandatory fields and status lists.
- No site agrees with another on whether a Version hangs off a Task, a Shot, an Asset or a playlist.

Rules out: hardcoding one studio's conventions, and exposing every field.

### Rules for putting these nodes in a graph you already use

Guidance for an operator, and what `/track-workflow` does on its own.

- **A Preview before the Publish.** Looking is constant, publishing is occasional. Tap the same image
  into a `PreviewImage` beside the Publish node. `/track-workflow` adds one when it adds a tap.
- **Muting is how you iterate.** Ctrl-B on the Publish node runs the graph and sends nothing. Say so
  where someone will read it.
- **One root name per stream, and it changes between runs.** Two ideas explored in one session are
  two streams, not two versions of one. `root name` is therefore not in the fold.
- **Lineage comes from the wiring, not from typing.** A Load node upstream of a Publish node fills
  `sg_ai_generated_from`. `source versions` on a graph that already loads its input is work the node
  has done.
- **`Create Published Files` is the other half.** Off means review media only. A house that hands
  files to the next department wants it on, and needs a storage the machine can see.
- **A new entity reaches the link picker once a Version points at it.** Seed the file the graph
  already reads (`comfyui_sg.seed`). The picker's lookups are cached for 600 seconds, so the seed is
  followed by Sync from SG or a page reload.

### Prefilling a node from what the operator is already doing

Open. A fresh Publish node knows the project from the profile and nothing else, so every field is
typed.

The site knows more: who the script key is acting as, which Tasks are assigned to them, which
entities they have touched most recently, and what the codes on those entities look like. The pieces
exist. `site.resolve_paths` walks Flow Production Tracking's own field paths, `naming` infers a
convention from real codes, and the profile is where per-site answers live.

Missing: the read of recent activity, and a decision about how a proposal is shown. A guessed value
that looks typed is worse than an empty field.

### Which fields a house wants in front of it

`src/comfyui_sg/widgets.py` declares each widget's `advanced` flag as a default. A profile may move
any field either way:

    "widgets": {
      "load":    {"advanced": ["task", "statuses", "name_contains"], "normal": ["frame"]},
      "publish": {"normal": ["colour_space"]}
    }

Per project, like everything else here. A field named in neither list keeps what the table declares,
so a profile only says what it disagrees with.

The order never changes. `widgets_values` is positional and folding is presentation, so this is safe
to edit at any time, including after release. It is the one place a site is expected to differ about
the node's shape.

### `batch_budget_gib`

The ceiling on a single IMAGE batch, at the top level of the profile rather than under a project.
How much memory a machine has is a fact about that machine, and it is why the profile is gitignored:
a studio's workstation and its render node do not share an answer.

A batch is one float32 RGB tensor, so a frame costs `w × h × 12` bytes. At the 4 GiB fallback that is
172 frames of HD and 43 of UHD, short of a normal shot at 4K. A workstation should raise it.

The Load node reads the whole sequence by default (`frame_count` 0), so this is the ordinary path and
not a backstop. The panel names the overrun before the Run, and the run refuses with the count that
fits.

### What the profile holds

The schema cache says what *exists*. The profile says what is *practiced* and what to expose. The
cache refreshes when the schema changes; the profile is inference plus operator edits layered on top.

- Rank fields by fill rate over the project's last N Versions, not by what the schema permits. Sites
  carry hundreds of dead legacy fields.
- Keyed per project, not per site. One studio runs shows with different conventions.

`Version.entity` is not one type. The schema lists **15** valid ones, identical on every project:
Asset, Level, MocapTake, Reel, ShootDay, Shot, Sequence, Delivery, Launch, Camera, Slate, SourceClip
and three `CustomEntity` slots. One show hangs Versions off Shots, another off Assets, and plenty use
several at once: the reference show links 99 Shots and 1 Asset, another links Assets, Shots and
Sequences. A single `link_type` was never Flow Production Tracking's model.

So the picker offers **every type the show actually uses**, each option carrying its own type
(`bunny_030_0090 (Shot)`), and the type written to the Version comes from what was picked. Which
types to search is observed from recent Versions, with Shot, Asset and Sequence added regardless.

- Searching all 15 would be slow and mostly empty.
- Observation alone is circular: a brand new Asset cannot be picked while no Version points at one.
- `link_types` in the profile overrides the lot.

Top-level keys are the site default; a `projects` block overrides them per show. Nothing is global
that a show can disagree about:

    {
      "default_project": 1180,
      "projects": {
        "1180": {"name": "sandbox",   "link_type": "Shot",  "link_field": "entity", "code_prefix": "corridor_v001"},
        "91":   {"name": "Kids Room", "link_type": "Asset", "link_field": "entity", "code_prefix": "comfy_v001"}
      }
    }

Two graphs open in one ComfyUI publish into two shows that link Versions differently. The node
resolves `link_type` from the project the operator picked on that node, and `/sg/profile` tells the
editor the same thing so the link picker searches the right entity type. One ComfyUI, one profile,
many shows.

- Plain JSON, human-editable, regenerable. Operator edits win over inference.
- Gitignored. Field naming and pipeline conventions are potentially confidential, unlike
  `probes/findings/`, which document the API itself and are safe to publish.

**The LLM runs at configuration time, never in the publish path.** It probes, then writes data.
Publishing is deterministic, offline, and costs no tokens.

## Nodes (v0)

- `SG Publish` takes an image or a video, creates the Version, uploads the media, attaches the
  provenance. Inputs are built from the site profile: link target and exposed fields are resolved,
  not hardcoded.
- `SG Load` brings a Version's media back into the graph and records the link.

`av` (PyAV) joins `requests` and `Pillow` as a dependency ComfyUI already ships, backing ComfyUI's
own video nodes. It is imported lazily wherever a frame has to be decoded: `media.py` reading a
Version's movie back, `movie.py` taking a poster frame off the clip it is about to upload. An install
without it still loads every node and fails only when someone asks for a movie frame. Nothing here
encodes and nothing shells out to ffmpeg. `VideoInput.save_to()` is ComfyUI's own encoder and owns
that side.

## What a run publishes

A run is one Version. What that Version carries is decided by what is wired into the node, not by a
combo asking the operator to restate what the graph already states:

    images    video    the Version's media       what a tick registers as files
    -         wired    that video                the movie
    wired     -        frame 1, as a still       the frames
    wired     wired    the video                 the frames, plus the movie where the house keeps it
    -         -        nothing to publish. The run refuses, loudly

ComfyUI has had a first-class `VIDEO` since its video nodes landed. Over 120 classes on a stock
install emit it: `LoadVideo`, `CreateVideo`, `SaveVideo`, and every hosted model from Kling to Veo to
Sora to Runway to Wan. Most of the video work a studio does runs through it.

**Review media is derived and may be transcoded; a deliverable file is never transformed.** That is
structural, not a habit. `movie.encode` does not exist. Where a `VIDEO` is a file on disk, that file
goes up byte for byte. Where it is not, as with `CreateVideo` assembling a batch or a hosted model
answering with frames, `VideoInput.save_to()` writes it. That encoder knows what a hand-rolled one
does not: sRGB is BT.709, HDR is BT.2020/HLG, HDR PQ is BT.2020/PQ, the bit depth is the clip's, and
the audio comes with it.

`sg_first_frame`, `sg_last_frame`, `frame_count` and `frame_range` are written by this node where the
site has them.

`sg_uploaded_movie_mp4`, `_frame_rate` and `_transcoding_status` are the transcoder's and are never
written. probe 022 measured `_mp4` serving a transcode of a replaced file while status read 1.
Writing them here manufactures that desync in any player that trusts them.

Image sequences stay supported as *input*. The Load node's `frames` tier is untouched.

### Source file, or encode

A `VIDEO` is uploaded untouched only when the object and the file are the same video: same duration
and same dimensions as a plain `VideoFromFile` over that path.

- `VideoFromFile.get_stream_source()` hands back the *whole* source path even where the graph trimmed
  or cropped the clip. `as_trimmed` and `as_cropped` return a new `VideoFromFile` over that same file
  with a window recorded beside it.
- Trusting the class alone would file a ten-second plate as the two-second selection a supervisor
  asked for, silently. That is corpus 028's failure mode.
- Both checks are container metadata reads. Neither decodes.

A clip that fails the test is encoded rather than copied. Which of the two happened is on the panel.

A `VIDEO` whose source is a `BytesIO` has no file to preserve and takes the encode path.

### `fps` and `published_files`, removed

Both are answers the graph already gives.

- **`fps`.** A `VIDEO` carries its rate, and `CreateVideo` is where a person sets one. A rate read off
  the media beats a rate inferred from a sibling node. A batch of frames carries no rate, and an
  invented 24 must not read as a measured one.
- **`published_files`.** One IMAGE batch cannot tell a sequence from the frames of a movie. Two
  inputs can: frames arrive as `images`, a movie arrives as `video`. The combo's four rows, `(none)`,
  `frames`, `movie`, `frames and movie`, are the truth table's four rows, and the operator decides by
  wiring.

One genuinely per-publish question is left, and it is not about media: is this a deliverable, or only
review? `register_files`, "Create Published Files", is that question and nothing else.

### `register_movie` and `register_files`

`register_movie` is the house's convention and sits in the profile with `storage`, `path_template`
and `colour_space`. `register_files` is the per-publish tick.

    "published_files": {
      "storage":        "primary",
      "path_template":  "{entity}/{root_name}/{version_name}/{version_name}.%04d{ext}",
      "colour_space":   "sRGB",
      "register_movie": false
    }

The two compose in one place. `register_files` off registers nothing. On, it registers the frames
wherever `images` is wired, and the movie where `video` is wired and either the house keeps it or
there are no frames. A movie published on its own is the deliverable, and a tick that registered
nothing would be a silent no-op.

### A batch that cannot be published

`images` alone, more than one frame, `register_files` off: the node refuses at run time, naming the
count and the two ways out. Tick the box, or send the batch through `CreateVideo` and wire the
`VIDEO`.

- A Version's media is single-valued (probe 022), so the frames cannot be the media.
- They are not being registered as files, so the only container left is frame 1 and the rest are
  dropped.

The frontend must not pre-empt this by disabling the checkbox. A batch size does not exist until
execution, so the browser could only guess, and a box greyed out on a guess is worse than an error
that knows.

### The widget window

`widgets_values` is positional, so removing `fps` and `published_files` and adding `register_files`
shifts every value below them in every saved graph. That is normally forbidden, and it was done once,
at 0.1.0 with an empty `PublisherId` and nothing published: the only graphs in the world carrying
these widgets were in this repo, and they moved in the same commit. After the first Registry release
the rule is append, never insert, never remove.

A node's real widget array is longer than `INPUT_TYPES` declares, because the editor extension injects
its own pickers, chips and panel between the declared widgets. `instrument.py`, `tools/smoke.py` and
`web/sg_entity_picker.js` therefore write values against one declared order instead of counting
inputs. A value written by position without it lands in the wrong widget and nothing reports it.

## Frames as PublishedFiles

The frames are a `PublishedFile`, and asking for them changes nothing about the Version. One run is
still one Version carrying one piece of review media.

    video wired            one Version, the movie uploaded. A PublishedFile where the house keeps one
    images wired           one Version carrying frame 1 for review, PLUS a PublishedFile per frame
    images and video       the movie for review, the frames as files
    a single image, no tick  PNG to `image` and `sg_uploaded_movie`, no file, no storage root

It rests on:

- probe 022: a Version's media is single-valued.
- A movie is what a supervisor reviews; the frames are what the next department opens.
- Attachments are storage rather than review.

### Copy, never move

The frames land in ComfyUI's own output directory, and the node **copies** them to
`<root>/<path rendered from the template>`.

- A PublishedFile's path has to sit under one of the site's LocalStorage roots. Anything else is 400
  code 104 (recipe 004).
- The run stays where the artist expects it.
- A publish that fails half way leaves something to re-publish from.
- A second attempt costs a copy rather than a re-render.

Rules out: constraining ComfyUI's output directory.

Everything that touches disk happens *before* the Version is created: root resolved, frames written,
copies made. A Version pointing at frames nobody wrote is worse than a run that refused. An unmounted
share stops the publish, and `/sg/preview_publish` says so before the Run.

### The path template

The storage root and the path template are profile data, per project like every other site-specific
decision:

    "published_files": {
      "storage":       "primary",
      "path_template": "{entity}/{root_name}/{version_name}/{version_name}.%04d{ext}",
      "colour_space":  "sRGB"
    }

`naming.render` already speaks Flow Production Tracking's dotted field paths and Python's whole format
spec, so a path template is the same language as a code template. No second vocabulary is invented.
Two things are particular to a path:

- **`{version}` is the publish, `%04d` is the frame.** They are different numbers.
  `naming.normalise_template` reads *any* printf pad as the version, which is right where a TD writes
  `v%04d` by habit and would freeze a sequence to one frame here. The frame token is lifted out
  before rendering and put back after (`sequence._protect`), and in a path template the printf form
  means the frame. `####` and `@@@@` work too, because `sg_path_to_frames` accepts all three
  (`media.SEQ`).
- **The extension follows the files, not the template.** It is the one the node's `format` widget
  names. A template reading `.exr` does not make 8-bit frames scene-linear, so the real extension
  wins and the panel says the template was overruled.

The version number is the Version's own, so `pf_seq_depth_v001` and `.../v001/` cannot disagree.

### Two names, composed, and a path that refers to them

    root name     {entity}_matte              the STREAM.  PublishedFile.name, and the folder
    version name  {root_name}_v{version:03d}  one version of it.  Version.code

The shipped root name is `{entity}_{sg_task.Task.step.Step.short_name}`: the pipeline step through
the Task, by `short_name` as Toolkit's `{Step}` key reads it. Steps are a studio's fixed vocabulary
where Task names are free text. Every token is optional. One with no value drops out with its
separator, so the same template reads `sh010_RTO` on a Task and `sh010` on a bare Version.

    sequence      {entity}/{root_name}/{version_name}/{version_name}.%04d{ext}
    movie         {entity}/{root_name}/{version_name}{ext}

Three publish nodes on one Task read `{entity}_depth`, `{entity}_normal`, `{entity}_alpha` on their
faces.

Rules out: a single `output` text field whose only effect is to fill `{output}` in a template hidden
in the advanced fold.

**Composed, never subtracted.** recipe 004 says `name` is the stream and `code` is one version of it.
Deriving the stream by stripping the version token out of a template breaks the moment a path
template merely *refers* to a name: stripping the version from
`{entity}/{root_name}/{version_name}/{version_name}.%04d{ext}` hands back the whole filename, frame
number and all. Rendering `{root_name}` from its own template cannot fail that way.

**The path refers to the names rather than respelling them.** A sequence gets a folder named for the
version because it is many files; a movie sits beside that folder because it is one. No folder holds
frames and a movie together. Two templates, each sayable in a sentence.

**Tokens are Flow Production Tracking's own syntax, to any depth.** `{entity.Shot.code}` works, and so
does `{sg_task.Task.entity.Shot.code}`. The server does the traversal and answers under the literal
dotted key (probe 003), so the client hands over everything after the hop it already holds an id for
rather than parsing the chain itself. A **bare** token is that link's own name, the way Flow
Production Tracking returns one in a relationship dict: `{entity}` is the Shot's code, `{sg_task}` the
Task's `content`, never its code (`entity_types/Task`).

**An empty token is reported, not swallowed.** `_clean` collapses the `//` an unresolved token
leaves, which is right for the path and wrong as the only response: probe 016 has a dotted read
returning 200 with the key silently absent. The staging step names every token that came back blank.
A path that rendered proves as little as a 200 does (corpus 028).

### The `format` widget

One advanced widget, three choices:

    8-bit PNG          the default. What every graph already produced
    16-bit PNG         the same pixels, quantised at 16 bits a channel
    EXR 32-bit float   the tensor, written through unchanged

Anyone whose plate is scene-linear needs more than 8-bit PNG: a 32-bit render quantised to 8 bits and
registered under a truthful `colour_space` label is a lie told twice.

The frames are written by `comfy_extras.nodes_images._encode_image`, ComfyUI's own encoder, the one
`Save Image (Advanced)` uses. Bit depth, channel count and any colour transform are its business.
The import is inside the call, so an install older than ComfyUI 0.34.0 still loads every node and
only refuses the write, naming the version.

**EXR converts nothing.** The encoder takes a `colorspace` saying what the incoming tensor *is* and
converts to scene-linear before writing. `sRGB` would apply an inverse EOTF to pixels this project
never measured, so EXR passes `linear`, the encoder's write-through. The `colour_space` widget stays
a statement about the pixels, recorded in the description and in the attachment, never applied.

**PNG's colorspace does not modify pixels at all**, per the encoder's own docstring, so both PNG rows
pass `sRGB` and the bit depth is the only difference.

**The review media stays 8-bit PNG.** The thumbnail and the uploaded still are for a person in a
browser. A 16-bit still would be bigger and identical on screen, and an EXR would not display.

`widgets_values` is positional, so `format` is appended **last** and every graph in this repo carries
a thirteenth value. `tools/smoke.py` proves it, because only loading a saved graph in a real ComfyUI
shows a value that has shifted into the widget next door.

### Colour space, recorded not converted

`colour_space` is a widget the operator fills in. Declared, never inferred from the tensor, and never
applied. A colour transform is the most consequential pixel change in a comp, and this project does
not make images.

It lands in `PublishedFile.description` and in the `.provenance.json` attachment.

- This site's `PublishedFile` has 33 fields and none of them is a colour space.
- probe 019: a name spent is spent site-wide forever, so no field is created for it.
- `description` is a real field this type already has and the place a person reads.
- A studio whose site *does* carry a colour space field points at it in the profile, like every other
  concept.

It is a per-node widget rather than a profile value alone because two outputs of one graph can
differ. A depth pass is not the beauty. The show's usual answer is seeded from the profile.

### File-level dependencies

`upstream_published_files` is the PublishedFile-level twin of `sg_ai_generated_from`. The publish node
knows which Versions this one came from, and where those Versions published files, those files are
what a downstream tool opens. It is written from the same ancestor set, resolved with one `_search`,
and left empty, reported rather than invented, when the ancestors published nothing.

`sg_status_list` is deliberately *not* copied from the Version. PublishedFile carries its own status
list, `wtg`, `ip`, `cmpt` here, and the Version's codes are a different set entirely (probe 009). The
field's own default applies.

`path_cache` is written by hand. The server fills `path_cache_storage` from the path it resolved but
leaves `path_cache` null after a REST create, so a filter on it misses every row published this way
(`entity_types/PublishedFile`). It is a plain text field, it takes a write, and the client already
knows the answer.

### The `files` input

A third input, `files`, registers files another node already wrote. `images` and `video` are the
review side and may be derived; `files` is the deliverable side and is never touched.

    images  wired    review media, plus PNGs written from the tensor when the box is ticked
    video   wired    review media; a file on disk is uploaded untouched
    files   wired    the deliverable, registered where it already lies. No PNG is written at all

- Where `OCIO Write` has written 32-bit EXR in a known space, writing the same pixels again is a copy
  nobody asked for, and the space is measured on the Write rather than typed on the node.
- Core ComfyUI 0.34.0 writes 16-bit PNG and 32-bit float EXR itself, out of `Save Image (Advanced)`,
  so this is not an OCIO case only. The files a graph wants registered are often written by a stock
  node on a site with no colour management at all.

**It is a socket, not a widget**, so this lands without moving `widgets_values`. `OCIOWrite` declares
`RETURN_TYPES = ("STRING",)` and `RETURN_NAMES = ("path",)` alongside `OUTPUT_NODE = True`, so the
path is already on a wire and nobody types one. Adding an input slot is additive; adding a widget is
not.

**What comes down that wire is one concrete path, not a pattern.** `OCIOWrite` returns the written
file for a still and for a movie, and `paths[0]`, the *first frame*, for a sequence:
`<folder>/<name>.0086.exr`, four-digit, re-based to its own `start_number`. Everything here speaks the
other notation (`media.SEQ`: `%04d`, `####`, `@@@@`), so the first job is `sequence.discover(first)`:
same folder, same stem, same extension, digits in the frame slot and nothing else, giving back the
pattern, the frames and the real range. Anchored on all four, because a loose glob in a render folder
collects the neighbours.

**The folder holds more than pictures.** `write_sidecar` defaults on, so `<name>.json` sits beside the
frames, and a sequence carrying audio gets a `.wav` as well. Only the pictures are registered. The
sidecar is named in the description, because an artist who cannot find a tag needs to know the file is
there. It gets no PublishedFile of its own: this site has no type for it, a PublishedFileType has no
`project`, so minting one adds it to every show on the site (recipe 004), and that is probe 019's rule
again.

**The copy is conditional.** Already under the root, register in place. Anywhere else, copy. An
operator who points `output_folder` straight at the storage root has already put the file where the
site can resolve it, and copying it beside itself would duplicate a 4K EXR sequence for nothing.
`sequence.relative` answers `path_cache` either way.

**Colour space stops being a claim where it can be measured.** `output_colorspace` is a value on the
`OCIO Write` that made the file, sitting in the graph this node already reads whole for provenance
(`provenance.extract`). Where the wire leads back to a Write that can be identified, that value wins
and the panel says where it came from. The widget stays for everything else, and for when
identification fails. The two are never blended, and the record always names which it was. Nothing is
converted either way.

**`register_files` does not gate it.** `files` wired means registered. A tick that registered nothing
would be a silent no-op, the same argument that already registers a clip published on its own.

**The residual risk is `partial_execution_targets`, and it is not closed.** Both nodes are
`OUTPUT_NODE`s, and ComfyUI's front end can send a list naming which output nodes to run. Every
output node not in it is dropped before execution starts, so a selective run can execute this node
while `OCIO Write` never fires, leaving `files` pointing at whatever was on disk from the last run. A
missing file refuses loudly. A *stale* one cannot be refused: a cached Write that legitimately did not
re-run returns the same path with the same mtime, so treating that as an error would break the normal
case. The panel reports the path, the frame count and the mtime of what it registered. Closing it
properly needs a probe of what the front end sends on a selective run, and that probe does not exist.

## Loading a Version's media

A fetched Version is an ancestor, not just pixels. `version_id` is a plain widget, so it is already
in the prompt graph: the branch walk that scopes provenance answers "what did this come from" for
free, and the operator never types an id. A plate becomes a previs, several Versions become one
output, and the chain lives in Flow Production Tracking.

Which media a Version can deliver is a property of that Version, not of the site (probe 021), so the
editor asks per pick and offers only sources that resolve to a real file.

PublishedFiles come **first** among the sources.

- A PublishedFile is the only source that names a *type*, which is what makes "the rendered sequence"
  and "the mp4" on one Version distinguishable.
- It is the only one carrying the colour space the publisher declared.
- A publish registers a PublishedFile per file and the server resolves the path in the 201 itself
  (recipe 004), so there are real files to read.

Before this repo wrote them, the types a graph wants carried no path at all on the only site
available. That was recorded as unproven, not as absent.

The `source` combo holds a *type and a filename*: `Rendered Image · sh010_comp_v003.%04d.png #6843`,
with the id last as the tiebreak two publishes of one stream differ by. Nobody picks by id. It is also
the stored widget value, so a file later renamed or re-typed stops matching and the node lists what
the Version does have, by label, rather than loading a plausible neighbour.

**A source is offered only when it can actually deliver.** A PublishedFile with no path, or a path on
a root this machine has not mounted, is absent from the picker rather than a run that fails at the
end.

Still unproven, and the same shape of gap: a path resolved for a platform other than the one
publishing, and a site whose PublishedFiles a real publisher wrote rather than this node. The only
LocalStorage row here defines `mac_path` and leaves the other two null, so `local_path_windows` and
`local_path_linux` read null on every row written.

Tier 2 resolves on anything this node published: a sequence publish writes the real `%04d` pattern
into `sg_path_to_frames`, and a registered movie into `sg_path_to_movie`. probe 021 found
`sg_path_to_frames` filled on 0 of 53 Versions, and probe 022's verdict was to put the pattern there.

### Two outputs and a mask, one rule each

Each output takes the best source it can on its own:

- `image`: a sequence, else a clip decoded, else a still, else the thumbnail.
- `video`: a Movie Published File, else the movie on the storage, else the uploaded mp4 untouched,
  else the frames wrapped at the rate the site measured on the upload, or 24 fps said out loud.

A Published File beats a path field of the same shape: it carries a type, a path per platform and the
colour space.

Measured fill on the sandbox, across 110 Versions: Published Files with a path on 27, path fields on
27, an upload on 107, the site's transcode on 106, a thumbnail on 106. On the probed studio site
(probe 021) most Versions have only the upload and the thumbnail.

`sg_uploaded_movie_mp4` is never a source. It is derived from the upload, lands later, keeps
describing a replaced file while the status reads done, and its frame rate is wrong for a still
(probe 022). Nothing it offers is better than the upload it came from.

The thumbnail is the last fallback of `image` and not a choice. A Version that only ever had a still
image stays loadable, and nobody picks a 240px reference on purpose.

`source` stays, in the fold, as the override: two sequence Published Files on one Version, or exactly
the clip a reviewer saw. Picking one feeds both outputs from that file. There is no Load setting for
storage versus cloud, which is a fact of the machine rather than a preference, and none for which
Published File type is the deliverable, which is the profile's `TYPE_CANDIDATES` order.

The clip is fetched only when the `video` output is wired. The hidden `PROMPT` says who reads which
slot.

**Decoding is ComfyUI's decoder**, `VideoFromFile(path).get_components()`, the call core `Load Image`
makes. Frames arrive float32 `[N,H,W,3]` with the alpha channel separate, so a 16-bit PNG keeps its
levels and a 32-bit float EXR keeps values above 1. Pillow reads the first as two levels and cannot
open the second at all, and it is off this path entirely: the frame size on the panel is a PyAV header
read.

That call reads a whole container into memory, so it is for one image. A **movie is decoded frame by
frame**, in the pixel format core picks for that stream: an 8-bit RGB or full-range JPEG stream to
`rgb24`/`rgba` scaled by 255, everything else straight to planar float. The ceiling has to refuse a
long plate before all of it is in memory rather than after. A **sequence** is refused off the first
file's header, before one frame is decoded.

The sixth output is `mask`: the alpha the decoder hands back, as `1 - alpha`, and a 64×64 zero mask
where there is none, which is ComfyUI's own convention. It sits third, beside the two media, and the
record, `version_id`, `code`, `colour_space`, follows them.

An output is positional exactly as `widgets_values` is. A saved graph names a slot by its index, so a
slot inserted, removed or reordered rewires every graph already saved. The order in `RETURN_NAMES` is
frozen from the first release, and appending is the only safe change after it.

A Published File whose `path` is an `upload` is a source too. `link_type` is read before anything else
(`field_types/url`): a `local` value has no `url` key and an `upload` one has no local path, so a
reader that indexes one shape drops every row of the other. A `web` row stays out, naming a file on
somebody else's machine. A zip is offered and named but not unpacked, so it is its own kind and no
output picks it on its own.

### A clip, not a frame

A source can deliver a **batch of N frames**: a sequence off disk, or a movie decoded. A sequence that
comes back one frame at a time is not an input to a video graph. `frame` is the first frame of the
range; `frame_count` beside it says how many.

`frame` is a frame **number**, the one in the filename and the one Flow Production Tracking shows, in
both the single and the batch path. `media.frame_numbers` reads the numbers off the filenames. A frame
the sequence does not have is refused with the range it does have. This repo cannot return a different
frame than the one asked for.

The numbers come off **disk**, not from `sg_first_frame`/`sg_last_frame`. Those are a claim a publisher
made once and nothing keeps them true. The filenames are the sequence.

`frame` **0** is "whatever this source starts at", the answer nearly every time. A plate that runs
1001-1048 needs nothing typed. The range is on the panel beside the source: a number you must know
before you can type it is not a widget an artist can use.

The panel says what it will read for the same reason: `16-bit PNG, RGBA, 1920x1080, 48 frames.` off the
first file's container header, plus the declared colour space. Bit depth and channel count decide
whether a source is a plate or a preview and neither is in a filename.

`frame_count` **0** is every frame to the end. A movie carries no numbering inside it, so there `frame`
counts decoded frames from 1, 0 means the same as 1, and the panel says nothing rather than inventing a
range.

`frame_count` defaults to **0** in the widget declaration and in the Python signature alike. Two
defaults for one value is a node that behaves differently depending on which caller reached it. The
widget is *appended*, last, after the multiline filter box it has no business sitting under.
`widgets_values` is positional, so a widget inserted above an existing one displaces every value in
every graph already saved, including graphs this repo will never see. A row in the wrong place is
cosmetic; a silently shifted value is not.

The batch is bounded by a **size**, not a count. `media.BATCH_BUDGET` is 4 GiB, checked against the
real resolution after the first frame is read, and the refusal names the resolution, the total, and
how many frames do fit at it. 300 frames of 4K is 27.8 GiB of float32 and an allocator's answer to
that is a stack trace. `MAX_FRAMES` (512) is only the widget's own guard against a typo.

With `frame_count` 0 there is no count to check up front. A sequence knows its length from the glob
before it reads anything, so it still gets the one check; a movie gets it against what has
accumulated. A short read comes back short and says so, because padding a batch to the number asked
for would be this node inventing frames. Frames whose size changes mid-sequence are refused by
filename rather than by two shapes in a torch traceback: they cannot stack, and no resize belongs
here.

### Colour space on Load

Publish records a declared colour space on the PublishedFile description and in the
`.provenance.json`. The Load node reads it back onto the panel and out of a fourth output, so a claim
made once upstream reaches the artist about to comp instead of being retyped.

**Recorded, never applied.** Nothing converts, nothing infers, and a Version that declared nothing
says nothing rather than defaulting to sRGB.

### Upstream file links

The Load node records the file it actually opened (`lineage.py`, beside the Version id it resolved),
and the publish node links that one file. Ancestors that were read through a path field or an upload
opened no PublishedFile, so they still get the search: approximate is the honest answer where nothing
narrower is known, and the two cases are decided per ancestor rather than per run.

Rules out: claiming every PublishedFile of every ancestor Version, which on a Version carrying both a
sequence and its mp4 claims a dependency on both when the graph read one.

What `lineage.py` remembers is keyed by node id, and one ComfyUI server runs many graphs: node 1 of
the graph open now is a different node from node 1 of the graph before it. An entry therefore carries
a fingerprint of the Load node as it ran, its class and its inputs off the PROMPT it was given, and is
credited only where the node at that id is still that Load with those inputs. ComfyUI hands a node no
prompt id, so the fingerprint is the guarantee and clearing stale entries is only hygiene. Crediting
the wrong one writes provenance that is plausible and false.

## The version number

Both paths are supported and neither is assumed.

- A Toolkit-driven site usually carries a real numeric field on Version, `sg_version_number` or
  similar. That is authoritative when present, so `version_number_field` names it in the profile and
  the node writes it.
- Many sites have none. This one has none; `PublishedFile.version_number` is a different entity. The
  version then lives inside `code` as a freeform convention that differs per show.

The convention is inferred from the codes a show already uses, shown to the operator with its
coverage, and stored in the profile as data:

    "code_template":   "{entity.code}_{output}_v{version:03d}",
    "code_regex":      "^(?P<entity>.+)_(?P<output>[A-Za-z]+)_v(?P<version>\\d+)$",
    "approved_status": "apr"

Measured on three real projects: the reference show scores 100/100, this sandbox 2/3, and a project of
ad-hoc test names 0/53. **The coverage number is the point.** 0% is the honest answer, and the
operator sees it rather than getting a confident wrong guess.

There is deliberately **no "approved" concept**. A Load node takes a status the operator picks from
that project's real list, and empty means any.

- Flow Production Tracking has no approved concept. Approved is one status code among many.
- The codes differ per project (probe 009).
- A show may care about `rev`, `ip`, a custom code, or none.

Rules out: a hardcoded "latest approved", which invents vocabulary the API does not have.

### Two nodes, one pipeline

`code = auto` numbers per link. `select = newest matching` resolves at run time using Flow Production
Tracking's own rule: order newest-first (`id` or `created_at`), optionally require a status,
optionally require a substring in the code. Ordering by the convention's version number is offered as
a third option, because a re-published v002 is newer by id but older by intent.

Step N publishes and step N+1 consumes it, with no id copied between graphs, and the lineage field
records the join by itself.

A Version resolved at run time is not in the prompt graph, so `lineage.py` records what each Load node
resolved and the publish node reads back only its own ancestors' entries.

## Provenance

Captured per publish:

| field | source |
|---|---|
| model, seed, sampler | ComfyUI prompt graph |
| prompt | text that reached a conditioning input in this branch, not "text near a seed" |
| workflow JSON | attachment, best effort |
| submitting client | whoever POSTed `/prompt` said so |
| input Version ids | upstream `SG Load` nodes, or typed by hand |
| user, timestamp | client |

### The workflow attachment

Best effort. A publish never depends on the workflow, and says when it is missing rather than quietly
omitting it.

- `PROMPT` is guaranteed. Execution cannot happen without it.
- `EXTRA_PNGINFO` is whatever the client put in `extra_data`, and `None` otherwise
  (`execution.py:199`).
- The standard frontend sends it. The `comfy` CLI, the ComfyUI MCP server, and every wrapper UI that
  builds its own API-format prompt do not.

Which client submitted the prompt is what explains an absent workflow later, and that is what the
generator field carries. It is also why the demo drives ComfyUI over plain HTTP rather than through
its MCP server: an MCP-submitted prompt exercises the degraded provenance path.

### The submitting client

`COMFY_USAGE_SOURCE` is the hidden-input spelling and reads like an environment variable. It is not
one. ComfyUI hands the node `extra_data.get("comfy_usage_source")` from the submitted prompt
(`execution.py:224`), a string chosen by whoever POSTed `/prompt`, never read from the environment of
the running server. A `Comfy-Usage-Source` header is copied into `extra_data` only when the body
omitted the key (`server.py:1120`), so the body always wins.

The standard frontend sets it to `comfyui-frontend`, hardcoded in the body of every Run, confirmed by
driving a browser and reading the request off the wire. A Version reading `ComfyUI (unknown client)`
was published by a script that POSTed a prompt and said nothing about itself, not by a person clicking
Run.

That value survives only if this repo's own harnesses fill it in. `tools/qa_node.py` rewrites the body
of every `/prompt` it drives, so a QA run is not filed as an artist at a keyboard.

### Where each piece lands

The nine fields are a default, not a schema. The mapping is data, per project, beside every other
per-show decision:

    "provenance": {
      "mode": "fields",
      "map": {
        "seed":   "sg_render_seed",
        "prompt": "description",
        "cfg":    null
      }
    }

A studio that already records seeds in `sg_render_seed`, or that wants nothing but a readable
paragraph, should not have to fork the node.

`mode` is the fallback for concepts the map does not name. `fields` uses the defaults; `description`
folds everything into the note. That is the difference between one word and nine null entries, and
"put it all in the description" is a real request.

The concepts are what the graph knows: generator, model, prompt, negative_prompt, seed, sampler,
steps, cfg, generated_from. `fields.concepts` produces them and `fields.targets` resolves the
operator's decision once. Both the publish path and `/sg/preview_publish` read that same resolution,
so the panel shows where a value will actually land.

A target the site does not have is **reported, not dropped**. A typo in a profile would otherwise hide
behind a Version that looks fine.

Pointing at a field the studio already has is the preferred move, and cheaper than it looks.
`fields.ensure` only creates what `FIELDS` names, and every name it spends is spent site-wide forever
(probe 019).

### Typed fields, not a JSON blob

`fields.py` defines nine fields on Version and creates them idempotently
(`python -m comfyui_sg.fields`). `description` is then the operator's note, and the complete structure
rides up as a `.provenance.json` attachment. The fields are the queryable summary; the attachment is
the record.

A site that has none of the nine takes the same facts in the description instead: the note, a blank
line, then one `label: value` line per fact. The description is therefore provenance, and the Load
panel parses those lines back into the same facts a typed field produces and counts them the same way.
Reading only the fields would call a Version's own record absent and print the whole paragraph as a
truncated note.

Three constraints out of probe 019, not negotiable:

- **Seed is `text`.** A `number` field takes 2**31-1 but 400s at 2**63; ComfyUI seeds reach 2**64-1.
- **`ensure()` reads `/schema` first.** Re-POSTing an existing display name does not error, it
  silently creates `<name>_1`, so a POST-and-hope ensure quietly multiplies fields on every run.
- **Field names are permanent.** DELETE frees the field but never its name, and trashed fields cannot
  be enumerated, so the collision is invisible. Adding to `FIELDS` spends a name site-wide, forever.

Lineage is `sg_ai_generated_from`, a `multi_entity` of Version. probe 019 confirms multi_entity
round-trips `{type, id}` hashes and takes exactly one `valid_types` element.

Not "source versions": the sources need not be AI, and a scanned plate feeding a previs is the
ordinary case. The `AI` describes this Version's generation, not its inputs.

Display and programmatic names are kept in step, so a TD reading `sg_ai_generated_from` finds "AI
Generated From" in the UI. A rename means a new field, never a relabel.

## Per branch, not per graph

The publish node takes `UNIQUE_ID` and walks back through its own inputs (`provenance.ancestors`), so
each Version describes only what produced *its* image.

- One graph holds several independent branches, such as three lookdev variants off a shared depth
  pass.
- Without the walk every Version carries every other variant's prompt and seed, and a depth AOV claims
  sampler settings it never used.

Tracing conditioning respects the input it started from. `ControlNetApplyAdvanced` takes both
`positive` and `negative`, so following every link merges the two prompts into one.

C2PA where the writer supports it; custom fields plus attachment otherwise. Field names are decided by
probe, not by the docs.

## What counts as a prompt

**Text becomes a prompt when an encoder turns it into CONDITIONING and a node consumes it**
(`provenance.directing_text`).

- Half the graphs a VFX shop runs never sample. `SAM3_Detect` takes a text prompt that decides what
  gets cut out, and there is no seed anywhere in the graph.
- A sampler consuming conditioning and `SAM3_Detect` consuming conditioning are the same event.
- The same walk picks up modern custom-sampler graphs, where the seed sits on `RandomNoise` and the
  conditioning on a `CFGGuider`.

Rules out: walking back from a node that carries a seed, a diffusion-shaped assumption under which
the most important creative input in a roto graph is recorded nowhere queryable.

The consumption test is also the whole of the conservatism. Scraping every string widget puts
`filename_prefix`, `ckpt_name` and a format enum into `sg_ai_prompt` and makes the field useless. None
of those reaches a conditioning input. Neither `TextOverlay`'s caption nor `SaveText`'s payload
reaches one, so the loose `text` key is safe here and would not be on its own.

Roles: `positive` and `negative` name one, a bare `conditioning` input does not. Text found with no
role reads as positive **unless a roled walk already claimed it**, so a `FluxGuidance` sitting on a
sampler's negative cannot smuggle the negative prompt into the positive one.

One exception to "must be conditioning": a widget named `prompt` or `negative_prompt`. Every cloud
generator node takes its words that way and encodes nothing: Kling, Veo, Runway, Bria, the Qwen edit
encoders, 147 core classes. All 147 declare it multiline and none of them ever names a file, so the
name alone is enough. That is the only widget name trusted without the conditioning test.

### One node, several tokenisers

`ENCODER_TEXT_KEYS` names all eleven spellings. `CLIPTextEncodeSDXL` takes `text_g` and `text_l`,
`CLIPTextEncodeFlux` takes `clip_l` and `t5xxl`, and SD3, HiDream, HunyuanDiT, Kandinsky5 and Lumina2
each spell it differently again. Reading only `text` publishes an empty `sg_ai_prompt` on every SDXL
and Flux graph, with a sampler present.

Across the 908 core classes each name but `text` occurs on exactly one class, always a multiline
STRING on a node returning CONDITIONING, so the name alone identifies it.

**Two encoders that disagree are two texts, not one sentence.** They usually hold the same line and
dedupe to one. Where they differ, a scene in `text_g` and a style in `text_l`, or keywords for
`clip_l` and a paragraph for `t5xxl`, both are kept separately. Concatenating would put a sentence
nobody typed into the field a supervisor searches; picking one would silently drop the other. The list
already carries several texts wherever a graph has several encoders, and `fields.concepts` joins them
with " | " like any other.

**`ConditioningZeroOut` is a wall.** It erases what it is handed, so text behind it reached nothing. A
Flux or SD3 negative is conventionally the positive encoder zeroed out, so without the wall these keys
report every such graph's positive prompt as its negative one too. 31 publish points in the corpus do
exactly that through plain `CLIPTextEncode`.

Deliberately **not** captured, each for a reason:

- **A click instead of a prompt.** `SAM3_Detect.positive_coords` is a JSON point list. The role prefix
  would otherwise catch it, so `_coords` is excluded by name.
- **`WanTrackToVideo.tracks`**, a multiline STRING of motion paths on a node that does return
  CONDITIONING, and `MakeTrainingDataset.texts`, a file list.
- **`tags`, `lyrics` and `caption`** on the AceStep and MiniMax music encoders. They are conditioning
  and they are words, but an audio graph publishes no image, and a lyric sheet is a document rather
  than a direction.
- **A `prompt` input wired from a string node** rather than typed. The words are then in a
  `PrimitiveString`'s `value`, which is a generic string widget again.
- **Text assembled by third-party concat nodes**, as in the ZHO gallery graphs. Nothing readable
  reaches the encoder, so nothing is recorded.

### One field, `sg_ai_prompt`

"What did you tell it to cut?" and "what did you tell it to generate?" are one question, the words the
artist gave the model, and a supervisor filtering Versions types them in one box.

Rules out: a second field. It would split that query in half, spend a name site-wide forever
(probe 019), and force every operator to map two concepts for one idea in `site.provenance_map`.

Which node the text reached is not lost. `provenance.extract` records `prompts` alongside `samplers`,
and the whole structure rides up as the `.provenance.json` attachment.

A graph that genuinely has nothing to say records nothing. `07_retime` fills `generator`, `model` and
`generated_from` and leaves `prompt`, `seed` and `sampler` empty, and that is correct.

## Coverage, measured

"Works on any workflow" is a claim, so it is measured. The corpus is 680 real graphs: the 629 ComfyUI
template workflows every user sees in the template browser, plus the three most-starred public
collections (ZHO, Yolain, `comfyanonymous/ComfyUI_examples`).

                                    before   after
    analysed without error         680/680  680/680
    finds a publishable stream     509/680  546/680   75% to 80%
    finds a loader to replace      428/680  430/680
    publishable streams, in total      977     1419

The before column is the state before `instrument.py` learned to see through subgraphs.

**The count is the small half of it.** 246 of the 680 graphs put their work inside a subgraph, and of
those, 200 already reported *something*: the instance's own output slot, or a plate feeding it. What
they reported was the wrong thing. 297 streams moved from a subgraph instance's output onto the node
that actually makes the picture, which is where the name lives. `video_ltx2_i2v` offered
`scale_dimensions`, a node feeding the block, and now offers the `VAEDecode` inside it.
`3d_moge_perspective_to_mesh` now offers `normal_opengl` and `normal_directx` by those names, which
existed only inside. 215 graphs have a stream that exists nowhere else.

29 old addresses are gone rather than moved, and all 29 were wrong: 27 were an IMAGE feeding a
subgraph that only *looked* like a video sink because the instance declares a VIDEO output, the input
plate reported as an output, and 2 were an instance output slot nothing inside ever fed. **Every graph
that found a stream before still finds one.**

14 of the 37 newly-covered graphs came from a second, smaller correction in the same pass: a save node
is an end even when it also hands the picture on. `SaveImage` feeding an `ImageCompare` so the
operator can see before and after is the shape, and it hid every SeedVR2 int8 upscaler.

Instrumenting is measured too, not just analysis. All 586 corpus graphs that have anything to
instrument were tapped and had their loader replaced, and all 586 came out with unique node and link
ids across the document, no dangling endpoint, every instance's output count matching its definition's,
and the publish node fed by exactly the stream that was asked for.

The 134 that still find nothing are mostly 3D, audio and text graphs with no image output at all,
correctly out of scope.

Before the sink rule learned that frames assembled into another medium end an image stream too
(`instrument._is_sink`) the number was 57%. That one fix moved 124 workflows, nearly all of them
video. Those graphs end in a `VIDEO`, which is what the publish node takes. See "What a run
publishes".

### Subgraphs

`instrument.py` analyses a flattened view (`_flatten`). A subgraph instance is a relay rather than a
node: what the definition's `inputNode` hands on is whatever the instance's input was fed, and what
its `outputNode` receives is what the instance's output emits. Splicing those pairs gives the graph
ComfyUI itself executes, confirmed against `graphToPrompt`, which addresses the same interior node as
`306:296` where this addresses it `306/296`. Nesting comes out for free and does occur: 76 places in
the corpus instantiate a definition inside another, one level deep, never more.

Tapping crosses the boundary at the instance's output. The stream is **promoted** to an output slot,
exactly as dragging an interior output onto the subgraph's output panel does in the editor, so the
publish node stays at the top level with its pickers rather than being buried a level down. If the
stream already leaves through an output, as a template's own `depth` pass does, that slot is reused
and nothing is added.

Promotion is additive and safe. The reverse is not: a definition's interior is shared by every
instance of it, so rewiring an interior input to feed it from outside would break the other instances.
A loader inside a subgraph is therefore replaced *inside* that same subgraph. Only 3 corpus graphs
have one, and no corpus graph instantiates a definition twice, but the file is someone else's, so the
rule is the rule and not the measurement.

What a stream is called comes from what the graph already says, and inside a subgraph the graph says
one more thing: the subgraph's own name. Its useful half is the *opposite* half from a sink label's.
"Preview Image (normal_opengl)" says what the stream is inside the brackets; "Depth Estimation (Depth
Anything 3)" says it before them and names a model inside. The trailing bracket is dropped, and the
name is tried only after everything nearer the stream.

## Non-goals

Charts, dashboards, reports, webhooks, automations, per `CLAUDE.md`. Video and OTIO. Inpainting UI.
three.js. Browser extension.

## Later

React review surface showing iteration lineage, extracted into an MIT component registry. Not in this
repo.

## Node anatomy

A custom node is a Python class registered from `__init__.py`. Verified against docs.comfy.org.

    class SGPublishVersion:
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

    NODE_CLASS_MAPPINGS = {"SGPublishVersion": SGPublishVersion}
    NODE_DISPLAY_NAME_MAPPINGS = {"SGPublishVersion": "SG Publish"}

`INPUT_TYPES` is a classmethod evaluated at load, which is what lets the mapping drive the inputs.

There is a second, newer schema: `io.ComfyNode` with `define_schema()` returning an `io.Schema`, which
is how the stock `comfy_extras/*` nodes are now written. `execution.py` branches on `is_v3`. Both are
live and v1 is not deprecated.

**This repo targets v1.**

- A registry node should load on the older ComfyUI a studio actually has installed.
- The dict form is the one a forker's agent can read without learning a second vocabulary.
- The cost: v1 hidden inputs are raw dict lookups, where v3's `HiddenHolder` returns `None` for
  anything absent (`_io.py:1545`), so the `None` cases are handled here.

### Where provenance comes from

The hidden inputs are the whole provenance mechanism.

- `PROMPT` is the executing prompt graph. Model, seed, sampler, steps and cfg live in its node widget
  values.
- `EXTRA_PNGINFO` carries the workflow as saved, which is what gets attached as a file.
- `UNIQUE_ID` identifies this node instance.

Nothing else is asked of the user. The graph already knows.

## Who the nodes publish as

A person, signed in through the App Session Launcher, or a script key from the environment. The person
wins when both are present.

**One surface: Settings, then SG.** The site address, Log in, the script authentication and the publish
defaults are rows in ComfyUI's own Settings dialog, drawn by the pack rather than by ComfyUI's form
controls, so nothing entered there reaches ComfyUI's settings store. Each row posts to the pack's own
routes and saves on change. The node shows nothing about the connection except the error sentence that
names Settings. Who a ComfyUI publishes as is one fact per ComfyUI, and a row on every node is the
wrong place for it.

**The person.** The operator enters the site address under Settings and clicks Log in. The server asks
the site for an approval page (`POST /internal_api/app_session_request`, probe 052), the dialog opens
it in a new tab, where the operator is already logged into Flow Production Tracking through Autodesk
Identity, and they click approve. The site hands back a session token, which spends at the token
endpoint as `grant_type=session_token` and mints a bearer for that `HumanUser`. Every Version is then
created by the person, and Flow Production Tracking's Artist field is them, with no script key, no
password and no impersonation. `credentials.py` owns this; `sg_groundtruth.launcher` speaks the
protocol.

**The script.** A script name and application key entered under Settings, else `FPT_API_SITE_URL`,
`FPT_API_SCRIPT_NAME` and `FPT_API_API_KEY` from the launch environment or from `.env.local` in a
checkout. A farm has no browser, and a machine nobody signs in on wants the same. Publish as, a login
from the People page, makes the script act as that person (`sudo_as_login`, probe 027). The site's
refusal, when the person cannot be impersonated, is read from Test under Settings rather than on the
first Run.

**Where they live.** `user/__sg_comfyui/session.local.json` and `settings.local.json` beside it, mode
600.

- ComfyUI serves a `__` directory over no HTTP route (`folder_paths.get_system_user_directory`, v0.3.76
  and later).
- It sits outside `custom_nodes/`, so a Manager update leaves it alone.
- It follows `--user-directory`, so the Desktop app keeps it too.
- Outside ComfyUI the same file sits beside `.env.local`, under the same gitignore rule.

Rules out: ComfyUI's settings store and `/userdata`, which both answer to anyone who can reach the
port, and a node widget, because `widgets_values` is saved into every workflow and every PNG.

**How long it lasts.** The site's `User Session Expiry` preference, one day on the probed site, from
the last use. Minting a bearer counts as use, so a ComfyUI that publishes or even opens a graph with
these nodes once a day never asks again. Left idle past the window the token dies, the token endpoint
refuses it, and Settings says so and offers Log in. Nothing renews on a timer: the site's preference
is the administrator's decision and a clock would defeat it.

**One session per ComfyUI.** The `comfy-user` header is a plain string any client may send, so a
per-user file would separate users in name only. A shared ComfyUI where two people publish under their
own names needs a real login in front of it, and that is out of scope. The pack's own routes are as
open as ComfyUI's: anyone on the port can write a key or sign out, and can read the script name and the
login. The key and the token never leave the server on any route.

**The publish defaults are the profile.** The Defaults rows under Settings edit `profile.local.json`
for the project the nodes open on: the Version name and root name templates, the status, and the
`published_files` block. There is no second store.

Each template row shows the value in force, the default when the profile has none, beside the example
it renders on sample values by the node's own renderer. Typing the default back in clears the profile
key.

The Version's `sg_path_to_frames` and `sg_path_to_movie` each hold one absolute path (probe 021), so
the profile also picks the operating system they are written for, from the roots the storage defines,
and whether each is written at all. The files themselves always go under this machine's root.

The profile lives in the protected directory when one exists there, and at the checkout root
otherwise, so the inspector's file is read as long as it is the only one and a Registry install, which
has no checkout, still has somewhere to write.

Adding a field of the operator's choosing is not in Settings for the first release. It is a `Field(...)`
line an agent adds, governed by the append-only rule under "widgets_values is positional".

## Distribution

Two ways in, and they are not the same thing:

- **Git clone into `ComfyUI/custom_nodes/`** is what a developer does. `requirements.txt` is installed
  by ComfyUI-Manager.
- **The Comfy Registry** is what everyone else does, reached through ComfyUI-Manager or
  `comfy node install sg-comfyui`. Publishing needs a `pyproject.toml` with a PEP 621 `[project]`
  block plus `[tool.comfy]` carrying `PublisherId`, `DisplayName` and `Icon`. Publish with
  `comfy node publish`, or a GitHub Action on `REGISTRY_ACCESS_TOKEN` triggered by a version bump.
  Nothing is published there yet, so the README says to clone until it is.

`[tool.comfy].requires-comfyui` is `0.34.0`, a hard floor rather than a preference. The frames are
written by ComfyUI's own encoder and read back by its own decoder, which is where 16-bit PNG and EXR
come from, and an older ComfyUI has neither that nor the routes the Settings dialog calls.

The operator's documentation is three files and one script, and they do not overlap.

| file | holds |
|---|---|
| `README.md` | what the nodes do, and the first run |
| `INSTALL.md` | where every local file lives per install type, which interpreter runs which command, the profile key by key, and what to do when something does not answer |
| `AGENTS.md` | a page for an agent, pointing at both and at `.claude/commands/*.md` |
| `tools/doctor.py` | the offline check: run as a file so it needs no torch, one line per check with the fix appended, non-zero on anything that would fail a publish |

`.claude/commands/*.md` are plain markdown procedures any harness can follow. `CLAUDE.md` and this file
are for whoever changes the code, and an operator never needs either.

### Names

`[project].name` on the Registry is immutable, so it is decided here rather than in passing:

    [project].name                sg-comfyui   permanent
    [tool.comfy].DisplayName      Flow Production Tracking
    repo, custom_nodes directory  sg-comfyui
    CATEGORY                      Flow Production Tracking
    Settings category             SG
    node titles                   SG Publish, SG Load
    NODE_CLASS_MAPPINGS keys      SGPublishVersion, SGLoadVersion   permanent
    Python package                comfyui_sg
    routes                        /sg/*
    protected user directory      __sg_comfyui

SG is the short name everywhere a short name is needed, the full product name everywhere else, and
"Flow PT" nowhere.

- SG is what people type into the node search and it lands instantly.
- The full name is slow to type, and half the audience still searches "shotgrid".
- The full name stays in the slots a Registry search reads: `DisplayName`, the description and the
  keywords, which also carry "shotgrid". Those can be changed later.

The `custom_nodes` directory name is shown verbatim on two chips: the Templates browser labels a pack's
collection with it (`title: e` in the frontend bundle) and the node's footer badge is `python_module`
split on `.`, the same string. Neither reads `DisplayName`, and the only override is a frontend i18n key
(`templateWorkflows.category.<name>`) that ships with the frontend and not with a pack. So the directory
name is the product's chip, and it is `sg-comfyui` rather than `comfyui-sg`: in a sidebar of `comfyui-*`
packs it sorts under S and the chip reads SG first.

`NODE_CLASS_MAPPINGS` keys are written into every saved workflow, so they are permanent from the moment
anyone outside this repo saves a graph. Nothing had shipped when they became `SGPublishVersion` and
`SGLoadVersion`, so the old keys were renamed outright rather than kept as deprecated aliases, and the
shipped graphs moved in the same commit.

The internals follow: package, routes, web files, the protected directory. No surface says `fpt`. The
Python package is internal, every import is relative, and `python -m comfyui_sg.fields` has to be
typable.

Operator sentences use the full name or SG. Before a status code they say "The site answered", which
names the thing that answered without naming the product a third time.

`Publish`/`Load` is both vocabularies at once: `tk-multi-publish2`/`tk-multi-loader2` on the Flow
Production Tracking side, and on the ComfyUI side `Load` is what a node is called when it is where the
pixels come from. `Fetch` was neither.

### The dependency problem

**Closed.** `sg-groundtruth` is on PyPI and this repo depends on it normally, in `requirements.txt`
(what ComfyUI-Manager installs) and in `pyproject.toml` (what the Registry reads). The floor is the
first release carrying `FPT.from_session` and the launcher module the Log in button needs. Nothing puts
a sibling checkout on `sys.path`, and there is no `SG_GROUNDTRUTH_PATH`.

The checkout is still expected for two things the PyPI package does not ship: the corpus, and
`inspect_site.py`, which `/inspect-site` drives. Neither is needed to run the nodes. INSTALL.md says the
checkout goes anywhere except `custom_nodes`, where ComfyUI would try to load it as a pack.

Three ways out were weighed, and the first was chosen:

1. **Publish the *client* half of `sg-groundtruth` to PyPI as a slim package** and depend on it
   normally. The corpus stays private; only the client ships.
2. Vendor the client into this repo. Rejected: it forks, and a client fix would have to land twice.
3. Declare a git dependency. Rejected: fragile, and it pins every install to one host.

The surface is 99 lines across two files: `FPT` and `FPTError` from `client.py` and `load` from
`env.py`, with `mcp.py`, `naming.py` and `schema.py` unused and nothing reaching the corpus.
`env.ROOT` resolving to site-packages once installed is a non-issue: `site.py` passes this repo's own
root to `load`.

Decided before publishing, not after. `[project].name` on the Registry is immutable.
