# Release plan

Written 2026-09-04 to close a working session and open the next one cold. Everything decided in
that session is here with its reasoning; everything still open is marked as such and names who
decides. `../sg-groundtruth/PLAN.md` is the older shared plan and is **stale** — its Phase 2 and 3
are largely done and it still calls this repo `comfyui-fpt`. Reconcile the two before trusting it.

Read `CLAUDE.md`, then this, then `DESIGN.md`.

---

## State

Both branches are **merged into `dev`** (PR #55, PR #56), squashed, `main` untouched. Kevin decides
every merge; this one was granted on 2026-09-04.

Landed in `bd12f49` (#55):

- `demo/` → `example_workflows/`. ComfyUI scans a custom node for `example_workflows`, `example`,
  `examples`, `workflow` or `workflows` and serves what it finds at `/workflow_templates`
  (`app/custom_node_manager.py:94`). The seven demos were in a directory it never reads.
- `workflows/` → `tools/workflows/`, beside `smoke.py` which runs them. Out of any scanned name, so
  the Templates browser offers the story and not the test material.

Verified after a restart: `/workflow_templates` returns the seven demos under this pack, keyed by
the `custom_nodes` directory name.

### The two-input node is built and merged

`07aef73` (#56), rebased onto `dev` so the merge commit is gone and the three commits squash to one.
DESIGN.md gained "The node records; ComfyUI makes the media". `movie.encode` is gone;
`movie.stage()` returns the source file untouched where the VIDEO is one, else `save_to()`;
`movie.poster()` takes the thumbnail off the file about to be uploaded. All 11 shipped graphs moved
to the 12-widget order in the same commit.

`smoke.py` passes 4/4 over `tools/workflows/` and 7/7 over `example_workflows/` — re-run on the
rebased branch before the merge, `publish_demo.json` reporting 12 widgets over 1 node — and a live
`/object_info` shows `required: []` with `images`, `video`, then 12 widgets, no `fps`, no
`published_files`.

The harness needs `uv run --with playwright --python 3.11 python tools/smoke.py`, which `smoke.py`
documents in its own docstring; neither the system Python nor ComfyUI's venv carries playwright, and
`tools/qa_node.py --start` brings up its own isolated instance, so nothing needs to be running.

**Verified 2026-09-04.** Version 31874 then 31875 in the sandbox, from the rebuilt `01`: the clip
encoded by `save_to()`, the thumbnail off `poster()`, the mp4 streamed to `sg_uploaded_movie`
(`link_type upload`, `video/mp4`), frame fields `1-8`, `sg_path_to_frames` holding the `%04d`
pattern, and PublishedFile 6869 with `link_type local` and the server's own LocalStorage join. The
trim guard remains reasoned from ComfyUI source, not measured — no trimmed clip has been published.

**Two deviations from the brief, both kept:** the impossible-state error fires only when no VIDEO is
wired (with a clip wired the frames are simply not registered, which is coherent, and it logs rather
than refuses); and `register_movie` gates the movie only where frames are also present, because
otherwise a video-only tick becomes a silent no-op.

**Two latent bugs found and fixed on the way.** `instrument.PUBLISH_WIDGETS` and the picker's
`DECLARED` both stopped at `link_id` while the class declared 13 widgets, so
`vals.length === DECLARED.length` never matched a shipped graph and the picker's `onConfigure`
correction — the block that exists because a mismatch otherwise writes wrong values silently — had
been dead since `published_files` was appended. And `smoke.py` decided widget-vs-socket with a
denylist, which would have counted the new `VIDEO` input as a widget.

**Follow-up it left deliberately:** `07_retime` still taps one frame from `ImageFromBatch` though
its own notes argue for publishing the clip. Wiring its `CreateVideo` into `video` changes what that
demo publishes and its .md records a past run, so it wants a decision, not a rewrite.

### One clean run does not exist yet — audited 2026-09-04

Every demo has a Version. Almost none has a PublishedFile:

| entity | Versions | PublishedFiles |
|---|---|---|
| `demo_01_roto` | v004, v005, v006 | 6869, 6870 — frames |
| `pf_seq` (a fixture, not a demo) | v001-v003 | frames **and** movie — 6838, 6841, 6844 |
| `demo_02_passes`, `03`, `04`, `05`, `06`, `07` | one each | **none** |

So the demos have published *review media* end to end and never a *deliverable*, because
`register_files` was off. Half of what the node is for is unexercised on six of seven demos.

Still untested end to end, and each of these is a real gap rather than a nicety:

- ~~**PublishedFiles for 02-07.**~~ — those demos are archived; the path itself is proven above.
- **06 camera move** — the one demo no survey covered at all. `mp_skyline` is its input.
- ~~**`SGLoadVersion`, the round trip**~~ — **closed 2026-09-07.** `00_example` runs it, and 02
  chains a load into a publish three times over with the lineage checked each time.
- **`/track-workflow`** — the actual product feature. Never run against a real graph.
- ~~A browser-submitted publish~~ — **closed, and the claim was wrong.** `EXTRA_PNGINFO` is not
  browser-only: two agents attached a real `.workflow.json` from a plain API POST by passing the graph
  in `extra_data.extra_pnginfo.workflow` (Versions 31880 and 31882). ComfyUI's frontend sends it for
  you; a script has to send it itself, and the node's "this client sent no EXTRA_PNGINFO" line is
  telling the truth about the caller rather than reporting a limitation.
- **The trim guard** — reasoned from ComfyUI source, never measured against a trimmed clip.
- **`register_movie` on the new node** — it worked on `pf_seq` under the old one.

### Machine state, not in git

- ComfyUI runs from `~/dev/ComfyUI`, port 8188:
  `./venv/bin/python main.py --port 8188 --disable-auto-launch`
- `~/dev/ComfyUI/user/default/workflows/` was emptied of seven stale graphs (backed up to the
  session scratchpad) and the seven demos copied in for hand-editing. Copies, not symlinks:
  ComfyUI saves with `tempfile.mkstemp` + `os.replace` (`app/user_manager.py:405`), which replaces
  a symlink instead of writing through it.
- `example_workflows/demo_01_roto_plate.mp4` copied into `~/dev/ComfyUI/input/`.

---

## Decisions

### The name

`comfyui-flow-production-tracking` was kept on 2026-09-04 because `[project].name` is a searched
slot and the two chips that show the directory name are cosmetic. Reopened by #76 and closed on
2026-09-08: the pack is `sg-comfyui`. See "The next session opens here — written 2026-09-08,
evening".

### The publish node takes two inputs

Today `SGPublishVersion` takes one `images: IMAGE` and manufactures artifacts from the tensor: a
batch >1 goes through our own `movie.encode()` (hardcoded libx264/yuv420p, no crf, no audio, no
colour properties), and a four-way `published_files` combo decides what lands on disk.

ComfyUI has a first-class VIDEO type we ignore. `comfy_api/latest/_input/video_types.py`:

    VideoInput.save_to(path, format, codec, metadata, bit_depth, crf, color_space, preset)
      # color_space="sRGB" -> BT.709/sRGB, "HDR" -> BT.2020/HLG, "HDR PQ" -> BT.2020/PQ
    VideoFromFile.get_stream_source() -> the actual source file
    get_components() -> VideoComponents(images, audio, frame_rate)

120+ nodes produce VIDEO on a stock install — `LoadVideo`, `CreateVideo`, `SaveVideo`, and every API
video model. Today publishing one means `GetVideoComponents` → IMAGE → our re-encode: a decode and
re-encode of a file that already exists, with the audio dropped.

The governing rule, made structural rather than promised: **review media is derived and may be
transcoded; deliverable files are never transformed.**

| `images` | `video` | review media | registered when the box is ticked |
|---|---|---|---|
| — | wired | that video; a `VideoFromFile` uploads **untouched** | the movie |
| wired | — | frame 1 as a still | the frames |
| wired | wired | the video | frames and movie |
| — | — | loud error | — |

Gone: `fps` (a VIDEO carries its own; `CreateVideo` is where a user sets one) and the four-way
combo. Added: `register_files` BOOLEAN, "Create Published Files" — a per-publish question, is this a
deliverable or only review. New profile key `published_files.register_movie` (default false) — whether
the studio also keeps the review mp4 on disk is a house convention and belongs beside `storage`,
`path_template` and `colour_space`.

Three constraints that must survive:

1. **`widgets_values` is positional.** Removing two widgets and adding one shifts every value in
   every saved graph. It is only safe because no graph outside this repo exists yet. One move,
   before release, with every graph in `example_workflows/` and `tools/workflows/` updated in the
   same commit. `tools/smoke.py` is the only thing that catches displacement.
2. **A sequence cannot be a Version's media** (probe 022) — a PublishedFile is its only container.
   So `images` with count > 1 and `register_files` off is impossible: raise a loud, specific error.
   Do **not** disable the checkbox from the frontend — the batch size does not exist until
   execution and the browser must not guess.
3. **A single image with `register_files` off** is the commonest publish there is and must behave
   exactly as today: PNG to `image` and `sg_uploaded_movie`, no PublishedFile, no storage touched.

### Colour management is an external pack, opt-in

Core ComfyUI has **no** colour management: 908 nodes on this instance, zero OCIO/ACES/LUT/view
transform. Two packs exist —
[ComfyUI-OCIO](https://github.com/SlavaSexton/ComfyUI-OCIO) (Apache-2.0, in the Registry, 13
Nuke-shaped nodes, EXR/DPX/ProRes read and write, and it preserves float32 where ComfyUI's default
path clamps to 8-bit) and
[ComfyUI-ACES-IO](https://github.com/BISAM20/ComfyUI-ACES-IO).

Three tiers, so the base templates keep their "core nodes only, anyone can open this" promise:

- `/setup` asks at install whether the user wants colour management, and installs the pack, sets
  `OPENCV_IO_ENABLE_OPENEXR=1` in the launch environment, and checks for ffmpeg if they say yes.
- `/track-workflow` offers to add it when instrumenting an existing graph, asking for *working
  space* and *delivery space* rather than one colour space, and wiring OCIO Read at the loader,
  OCIO Display before the review tap, OCIO Write before the publish.
- One shipped template features it.

**Open consequence, not yet designed:** with OCIO in the graph the frames come from `OCIO Write` as
float EXR, and our node must *register files someone else wrote* rather than writing PNGs itself.
Writing 8-bit PNGs of scene-linear data under a truthful `colour_space` label would be worse than
refusing. This is the one piece of the colour story with real design left in it.

### Template tiers

    00_*    the node, minimum viable       core only
    01, 02  the stories                    core only
    10_*    colour-managed                 requires ComfyUI-OCIO

`00_` is today's `tools/workflows/` fixtures promoted: `publish_demo`, `load_demo`, `round_trip`,
`publish_passes` are the reusable patterns a new user should meet first, and demoting them to test
fixtures hides them. A `10_` template's dependency is carried by ComfyUI-Manager's missing-node
detection plus a `MarkdownNote` in the graph listing the pack and the model weights —
`pyproject.toml` cannot express a dependency on another node pack.

### Branching, for the public repo

    main    public, always releasable    <- tags, releases, Registry publish, prod deploys
    dev     merge here and QA            <- promoted to main by PR
    *       feature branches

Same two-branch shape Kevin already uses, with the names the ecosystem expects: `main` is what
GitHub shows, what `git clone` gives, and what a forker's agent lands on — and CLAUDE.md is explicit
that forkers drive this with an agent rather than by reading it.

**Done:** `dev` created at `main` (`0041646`) and pushed, tracking `origin/dev`. `main` is still the
default branch. Nothing has been merged into either.

**Branch cleanup, not done, needs Kevin.** 56 remote branches. `git branch -r --merged` is useless
here because this repo squash-merges and squashes leave no ancestry — it reports 1. Cross-checking
against merged PRs instead: **54 of 56 have a merged PR**, and the two that do not are
`node/publish-version` and a branch literally named `origin`. To sweep:

    gh pr list --state merged --limit 200 --json headRefName -q '.[].headRefName' | sort > /tmp/m
    git branch -r --format='%(refname:short)' | sed 's|origin/||' \
      | grep -vE '^(main|dev|HEAD)$' | sort > /tmp/r
    comm -12 /tmp/m /tmp/r | xargs -n1 git push origin --delete

---

## The next session opens here — written 2026-09-08, evening

**Decided with Kevin, 2026-09-08, and built on `rename/sg-comfyui` (#76).** The pack is
**`sg-comfyui`**: repo, Registry name and `custom_nodes` directory. His example in the issue, and
it sorts under S in a Templates sidebar full of `comfyui-*` packs, so the chip reads SG first; the
Registry name is immutable once claimed, which is why it is decided rather than tried. Node titles
**SG Load** and **SG Publish**. Class keys **`SGLoadVersion`** and **`SGPublishVersion`**, with no
deprecated aliases for the old keys: nothing has shipped, the shipped graphs moved in the same
commit, and a graph saved from the sandbox era is one substitution. The internals moved with them
rather than carrying two vocabularies: package `comfyui_sg`, routes `/sg/*`, web files `sg_*.js`,
CSS classes `sg-*`, and the protected user directory `user/__sg_comfyui/`, which is where the
session and settings files live, so an update signs the operator out once. On this machine the
old directory's files were copied across, so nothing is lost. ComfyUI's `custom_nodes/sg-comfyui`
symlink points at the checkout, which is still named `comfyui-flow-production-tracking` on disk;
the GitHub repo is renamed to `sg-comfyui` and the old URL redirects.

**Words.** A sentence the operator reads says Flow Production Tracking in full, or SG where a short
name is needed. Before a status code it is "The site answered", which credentials.py already said.
Comments and docstrings say SG. Nothing says Flow PT or fpt. `CATEGORY` and the Registry
`DisplayName` keep the full product name: both are searched, and SG in the title already lands a
search for SG. `sg` joins the Registry keywords.

**Also decided.** `PublisherId` and `Icon` stay empty until release day, since both are the
publisher's and not the repo's. Setup is a README paragraph *and* a `/setup` command. No fine-print
line on the panel saying who the Version will be created by: the Settings Test button already says
who. Create Published Files stays off in every shipped template, so a first run never copies onto a
shared volume; the README and each template note say to tick it.

**Superseded, and removed from this file.** The seven-demo entity structure, plate specs A and B,
the plate rebuild and the plate licensing question all belonged to a demo that no longer exists.
The demo is `00_example`, `01_concept_and_style` and `02_style_from_a_reference`: 01 generates its
concept on the operator's machine and publishes it, 02 loads that Version and publishes the fusion,
00 is the bare round trip. Nothing is seeded and nothing ships that needs a licence line.
`example_workflows/demo_01_roto_plate.mp4`, which no graph read, is deleted. `seed.py` stays: it is
how `/track-workflow` gets an existing graph's file into the site, not a demo tool.

**SG Load has two outputs, decided with Kevin.** `image` and `video`, each taking the best the
Version has on its own, `source` folded as the override, the site's transcode never offered, the
thumbnail a fallback and not a choice, the clip fetched only when the output is wired. DESIGN.md
"Two outputs, one rule each" has the reasoning and the measured counts. Kevin: saved graphs before
the release may break; nothing has shipped. `00_example`'s sequence row ends in a Save Video on the
Load node's video output.

**Typed link searches go through the site's text search**, one call for every type the show
uses, 0.55 s through ComfyUI where the `contains` filter per type took 1.6 to 2.7 s on 14 types.
Case is ignored, a word matches anywhere in the name, and `sbx 020` finds sbx_0020. The page is
capped at 25 rows, a typeahead's worth. The list on open, with nothing typed, still comes per type
because the text must not be empty. What the corpus does not record is sg-groundtruth issue #48.

**`qa_node.py`** serves the pack under `[project].name` from `pyproject.toml` rather than the
checkout's directory name, so the Templates category and the footer badge in a headless run show
what a Registry install shows.

## The next session opens here — written 2026-09-08, night

**State.** Kevin clicked through Settings on his own ComfyUI on 2026-09-08 and granted the merge:
PR #75 squashed onto `dev`, then `dev` promoted to `main` by PR. `sg-groundtruth` has probe 052 on
`main` at 0.1.3 and **Kevin cuts the PyPI release**; until then ComfyUI's venv runs the checkout as
an editable install and a Registry install cannot satisfy `requirements.txt`. Issue #76 records the
SG rename.

**Settings, then SG.** One category in ComfyUI's Settings dialog, ids `SG.*`, drawn by
`web/sg_settings.js`, backed by `/sg/settings`, `/sg/test`, `/sg/defaults` and
`/sg/preview_template`. Nothing enters ComfyUI's settings store, which anyone on the port can read;
the values live in the protected user directory beside the session file. Groups, in the order the
dialog sorts them, which is alphabetical and is why the names are what they are:

- **Connection**: Site address; Publishing as, with **Test**, which reports the site's own sentence
  for a wrong key, a refused Publish as login, and a wrong address, each ending with where to fix it.
- **Log In As Yourself**: Log in, the App Session Launcher flow moved off the node. Log in is the
  site's own word, the field on the People page being Login.
- **Script Authentication**: Script name, Application key (write-only), Publish as. Each row says
  where its value comes from: the environment, saved on this ComfyUI, or not set.
- **SG Defaults**: Project, the one both nodes open on.
- **SG Publish Defaults**: Root name, Version name, Status, Create Published Files, Storage,
  Operating system, Sequence path, Movie path, Review movie, Path to Frames, Path to Movie, Colour
  space. They edit `profile.local.json` for that project. Each template shows the value in force
  and the example it renders, with the project's own fields resolved from the site; a lone storage
  is shown as chosen; the two booleans are switches drawn in the dialog's colours. Every row says
  Loading… until the profile has answered.

A 404 from any route means the running ComfyUI predates the pack, and every row says to restart:
routes register at import, so a pack update needs a restart, not a reload.

**What the nodes do with it.** They reload their pickers on a `sg:session` window event and say
nothing about the connection except the error sentence, which names Settings; both previews refuse
before rendering when nothing is connected, so that sentence is the alert rather than a line in the
fold. Root name, Version name, Status, Create Published Files and Colour space are widget defaults:
a node on the canvas keeps its values, a new node takes the defaults after a reload. Storage,
Operating system, the paths and the four toggles are read at publish time, so every publish uses
them at once. A graph saved with "(none)" for the project opens on the Settings project, which is
what lets a template land on the operator's show. An empty root name or version name on a node
means the Settings default on the naming path and the file path alike; the three example templates
ship with an empty version name for that reason and keep their own root names, which are the
demo's streams.

**Also this session.** The profile is read from the protected directory first and the checkout
root second, so the inspector's file still counts and a Registry install has somewhere to write.
The pickers say Searching… and dim their rows from the keystroke to the site's answer, and a wheel
over a picker's list scrolls the list instead of closing it and zooming the canvas. `smoke.py`
accepts a project resolved from "(none)".

**Decided with Kevin, 2026-09-08.** The short name is **SG** everywhere a short name is needed, the
full product name otherwise, never "Flow Production Tracking" (#76). The default root name carries the pipeline step
through the Task, `{entity}_{sg_task.Task.step.Step.short_name}`, by `short_name` as Toolkit's
`{Step}` reads it; every token is optional and drops out with its separator. A sequence lands in a
folder named for the version beside the movie,
`{entity}/{root_name}/{version_name}/{version_name}.%04d{ext}`, so no folder holds both.
`sg_path_to_frames` and `sg_path_to_movie` each hold one absolute path (probe 021), so the profile
picks the operating system they are written for from the roots the storage defines, and two
toggles decide whether each field is written at all; a Windows value takes backslashes after the
root, reasoned rather than measured. The file-path defaults are not disabled when Create Published
Files is off: they are defaults. Custom fields on the nodes stay an agent's job for the first
release. Updating linked entities from a publish, a Task's status for instance, is after release.

**Measured, in `~/Desktop/sg-settings-screenshots/`:** every Settings state from a credential-free
copy of the checkout and from this one, signed in as Kevin and expired included, the Load and
Publish nodes not connected, the defaults after edits, a template loaded with the resolved project
and the previewed name, new nodes taking changed defaults while a node on the canvas keeps its
values, the busy state on open and on typing, and the wheel over the list. **Not measured:** a live
publish since the platform rewrite and the new sequence folder, so `sg_path_to_frames` in the other
notation and the `{version_name}/` folder are reasoned from the code; and the deliverable half has
still never run from a template.

## Before the first release

In the order they block each other. State at the end of 2026-09-08.

1. ~~`sg-groundtruth` 0.1.3 on PyPI~~ **released 2026-09-08**, v0.1.3 cut from `main`; the
   release workflow publishes it.
2. ~~PR #80, the rename and everything built on it today~~ **merged 2026-09-08**, granted by
   Kevin. The checkout is `~/dev/sg-comfyui` and `~/dev/ComfyUI/custom_nodes/sg-comfyui` points at
   it.
3. ~~One live publish from `00_example` with Create Published Files ticked~~ **done 2026-09-08**,
   by Kevin from the template: `sbx_0020_example_sequence_v001`, twelve frames under
   `/Volumes/FPT`, PublishedFile 6933, `sg_path_to_frames` written, read back by SG Load. This machine's profile had the sequence template as
   `{project}/{entity}/{root_name}/{root_name}/{version_name}.%04d{ext}`, set by hand; cleared on
   2026-09-08 so the shipped default applies.
4. **`/track-workflow` against a real graph**, never done, and its three new questions (colour
   space, register files, the OCIO offer) still unbuilt.
5. **README.** Rewritten today for Settings, the colour-management paragraph, the two Load outputs
   and the naming rule; thumbnails exist for the three templates. Left: say which set-up steps
   are optional on a plain site, since the defaults carry a Shot-linked show without the inspector.
6. ~~`/setup`~~ **done 2026-09-08**: a README paragraph and a slash command.
7. `pyproject.toml` needs `PublisherId` and `Icon` on release day. The branch sweep is done: five
   remote branches remain.

**Decided 2026-09-08, evening, Kevin: the provenance fields stay a command for the first
release.** `python -m comfyui_sg.fields` creates the nine typed fields once per site and needs a
key allowed to create fields; without them a publish still carries the whole record as the
`.provenance.json` attachment and the panel strikes through the fields the site lacks. Where each
concept lands is the profile's `provenance` block. A Settings group with a "Create provenance
fields" button and a readout of which exist is the obvious later shape, and it waits for users to
ask for it.

**Open on the corpus:** sg-groundtruth #48, the text search's page cap and matching rules, which
`site.text_search` codes against.

**Still to do, not blocking:** the fold table (each widget shown, in the fold, or hidden, which the
profile's `widgets` block already decides), the first content of an SG Load Defaults group;
per-project defaults for a project other than the one the nodes open on stay a file edit;
`instrument.py` and `smoke.py` read no profile-added widgets, which only matters once custom fields
are built; a `10_` colour-managed template; the demo copies in
`~/dev/ComfyUI/user/default/workflows/` want removing now that the templates are rebuilt.

**How to test UI here.** `uv run --with playwright --python 3.11 python tools/qa_node.py --start
--node <type> --drive <file.js>`: an isolated ComfyUI, headless, prints what the drive returns. Pass
`--repo <copy>` for a checkout without `.env.local`, and `--keep` to leave the instance for more
drives on the same `--port`. A session file written into the instance's
`user/__sg_comfyui/` gives the signed-in and expired states. Not the live
browser tool; Kevin can see that session and it is slower.

## Three things the next session opened with — written 2026-09-08, morning

### 1. Credentials: decided and built on 2026-09-08, sign in as a person

`.env.local` inside the pack could not ship: ComfyUI Manager replaces `custom_nodes/<pack>/` on
update and the keys with it. It no longer has to. The nodes carry a Sign in row, the operator approves
a request in the browser where they are already logged into Flow Production Tracking, and the session token the site
returns is kept in ComfyUI's protected `user/__sg_comfyui/` directory. See
DESIGN.md "Who the nodes publish as" for the design and sg-groundtruth probe 052 for every measured
fact behind it. A script key from the launch environment is the farm path and the fallback.

Proven end to end on 2026-09-08: Version 31952 (`sh010_example_v003`) published from the editor with
`created_by` and `user` both the person, HumanUser 253, not the script.

What the research settled, so it is not re-derived:

- ComfyUI has no secret store and no server auth. `GET /settings` and `/userdata` answer anyone on
  the port. The one protected place is a `__`-prefixed user directory (v0.3.76+), added for packs to
  keep keys out of HTTP; ComfyUI-Manager moved its own config there.
- Comfy-Org's API nodes keep their key in the browser and send it per request; community packs use
  an env var or a file in the pack. Nobody uses the OS keychain.
- The session lives for the site's `User Session Expiry` window from the last use, and minting a
  bearer is a use, recorded at most once every five minutes. One day on the sandbox.

Still open: a headless run has no browser, so a farm still needs a script key, and `/setup` should
say which of the two applies. Kevin has not yet tried the button flow himself from a fresh session.

### 2. Artist attribution: decided, not built

`Version.user` is the field Flow Production Tracking shows as **Artist** and it defaults to whoever called, so every
Version this pack has ever published is authored by `comfyui-fpt 1.0` rather than by a person
(sg-groundtruth `findings/entity_types/Version`).

Decided by Kevin: impersonate by default, fall back rather than fail. **Narrowed 2026-09-08:** with
the Sign in row, a workstation publishes as the person outright and none of this applies there. The
three steps below are the script-key path, a farm or a checkout.

1. `FPT.from_env(env, sudo_as_login=<login>)` — needs sg-groundtruth **0.1.2**, released 2026-09-08.
   Sets `created_by` and `user` to the person.
2. If the token is refused, send `user` explicitly and keep publishing. Refusals arrive at the token
   endpoint before anything is written and name the reason.
3. If no login resolves, the script, which is today's behaviour.

The panel says which of the three happened as an ordinary readout row, never an alert: an alert is
for something that stops a Run and this does not. `artist` becomes an advanced widget, appended last,
defaulting to the resolved operator, so a supervisor can publish on someone's behalf.

### 3. Adding a field is still not mechanical, and that was the point

`widgets.py` made the order and the folding declarative, which is what was asked for at the time. It
did not make **field types** declarative. Its `kind` vocabulary is ComfyUI's widget set — `text`,
`multiline`, `int`, `bool`, `combo` — not Flow Production Tracking's `data_type` set, so an `entity` field like Artist
fits none of them and the first instinct was to fudge it as a login string.

What the table needs is `data_type -> widget`: `entity` to a searchable picker, `multi_entity` to a
multi-picker, `date` to a date input, `list` to a combo built from the schema's own valid values,
`checkbox` to a boolean, `text`/`float`/`number` to what they already are. Then adding a field is one
`Field(...)` line naming a Flow Production Tracking field, and the widget follows from the schema rather than from a
guess. The entity picker already exists for `link` and `project`; it is not reusable by name yet.

That is the difference between "an operator with an LLM can add a field" and "an operator with an LLM
can add a text field".

## Open, and who decides

| question | who |
|---|---|
| Release date: the node contract lands before release, so Monday is at risk | Kevin |
| ~~How credentials ship~~ | **closed 2026-09-08.** Sign in as a person through the App Session Launcher, session token in ComfyUI's protected user directory, script key from the environment for farms. DESIGN.md "Who the nodes publish as" |
| Artist attribution is decided and unbuilt: impersonate, fall back to the `user` field, then the script | built next |
| `data_type -> widget` so adding a Flow Production Tracking field of any type is one line | built next |
| ~~Plate licensing~~ | **closed 2026-09-08.** No plates: 01 generates on the operator's machine, nothing ships that needs a licence |
| How our node registers files written by `OCIO Write` instead of writing PNGs | **designed** — DESIGN.md, "Where someone else wrote the files, we register them". Kevin to read |
| ~~Should `frame_count` default to 0 or stay 1?~~ | **closed 2026-09-07 — 0.** See below |
| ~~`sg_groundtruth` is not installable, so a Registry install cannot run~~ | **closed 2026-09-05.** `sg-groundtruth` 0.1.1 is on PyPI, `_deps.py` and `SG_GROUNDTRUTH_PATH` are gone, and `requirements.txt` — the file ComfyUI-Manager installs — names it. The corpus checkout is still wanted to *set up*: `inspect_site.py` is not in the wheel |
| `pyproject.toml` has no `PublisherId` or `Icon` | Kevin, release day |
| ~~**Node names.**~~ Kevin, 2026-09-08: "Flow PT for searching nodes is not great, SG is faster to search in the UI. SG Load, SG Publish is great, but other names like repo name etc need to change as well." Issue #76 | **closed 2026-09-08.** `sg-comfyui`, SG Load, SG Publish, `SGLoadVersion`, `SGPublishVersion`, internals swept. See "written 2026-09-08, evening" |
| Updating linked entities from a publish, a Task's status for instance | after release, Kevin |

### `frame_count`'s default — closed 2026-09-07: 0, "all of it"

Decided alongside the widget reorder, because they are one decision. Kevin: statuses and
name_contains belong in front of the operator, and `frame`/`frame_count` belong in the fold *if the
default already reads the whole thing*. A widget only earns the fold when leaving it alone is right.

So `frame_count` is 0 and both frame widgets are advanced. The batch-budget argument below still
stands and is the cost of this: a 100-frame 4K plate is refused out of the box, naming the 43 that
fit. What makes that acceptable is that the refusal is a sentence with the number in it, and the
panel states the range before the run rather than after it.

The argument as it stood:

`frame` defaults to **0**, "wherever this source starts". `frame_count` defaults to **1**. Kevin's
question is the obvious one: why isn't that 0 too, meaning "the whole clip as published"?

For **0** — consistency. Two magic values that mean different kinds of "auto" is exactly the
"not self-explanatory" complaint the Load node has already been through once. And a plate is a clip;
one frame of a 48-frame plate is rarely what anyone wants.

For **1**, and this is the argument that decided it for now: `frame` 0 changes *which* frame,
`frame_count` 0 changes *how much work*, and the output tensor's shape then depends on how many
frames someone else happened to publish. Against `media.BATCH_BUDGET` (4 GiB) that is 172 frames of
HD but only **43 of 4K** — so a 100-frame 4K plate, exactly the content this node exists for, would
fail out of the box: add node, point at plate, read a batch-budget refusal. At 1 it always works and
the panel says `1001-1100, 100 frames` so the operator can ask for the rest.

What weakens the case for 1: the panel now shows what will be read *before* a run, so neither default
is silent any more.

It is a one-line change either way (`"default": 0` in `load_version.py`, plus the tooltip).

### "Newest" needs a stream to be newest OF — found 2026-09-07

Running `00_example` for the first time turned this up. A link carries several streams, each
versioned on its own, and `newest_by` "version number in the name" compares the numbers across all
of them: on `sh010` it picked `sh010_uidemo_v003` over the `sh010_example_v001` just published,
because 3 > 1. The two streams have nothing to do with each other.

`name_contains` is what makes it deterministic, which is the argument for it being a main field
rather than an advanced one — it now is. `00_example` ships with `name_contains` set to the stream
its own Publish node writes.

Open: whether "newest by version number" should be per stream by default, which would mean parsing
the stream out of the code and grouping first. Nothing is decided.

### Run three times, not once — 2026-09-07

"Does it even work consistently?" is the right question and one run is not an answer. 01 then 02,
three times end to end against the sandbox:

    01 published         02 published        02 generated_from
    sh010_concept_v002   sh010_fusion_v002   [concept_v002, style_v001]
    sh010_concept_v003   sh010_fusion_v003   [concept_v003, style_v001]
    sh010_concept_v004   sh010_fusion_v004   [concept_v004, style_v001]

Three things this settles. Version numbers increment per stream. Each 02 read the concept published
seconds earlier, so `site.forget()` after a publish really does invalidate the cached version list
and the 600s TTL is not in the way. And the two Load nodes track their own streams: `style` stayed
at v001 while `concept` advanced, rather than both grabbing the newest thing on the Shot.

Still unproven, and not by omission: `register_files` is off in every shipped template, so the
deliverable half has still never run from one. Nothing exercises the batch-budget refusal, an
unmounted storage root, or `register_movie`. One machine, one site, one link, three iterations.

### The deliverable half needs no profile at all — measured 2026-09-07

`register_files` was described here as blocked on configuration. It is not. This site has exactly
one LocalStorage row (`primary` -> `/Volumes/FPT`, mounted and writable), and `sequence.root_for`
only demands `published_files.storage` when there are several to choose between. So one row is
unambiguous and the deliverable path runs with an empty profile.

Proven by running it: Version 31919, three frames at 768 copied to
`/Volumes/FPT/sh010/sh010_deliverable/v001/`, registered as PublishedFile 6900 with the `%04d`
pattern, type `Rendered Image`, colour `sRGB`, and the Version's own media left as frame 1.

Open, and it is a product decision rather than a gap: the shipped templates all carry
`register_files` off, on the reasoning that a first run must not copy onto a shared volume nobody
was asked about. That reasoning holds for `00_example` and is arguable for the rest, since
registering the files is half of what this pack does and most people will never tick a box they
have not been told about.

### The templates are about the nodes, not the pictures — 2026-09-08

Kevin, after a run of image tuning: "The goal is more to showcase the nodes themselves, how to set
them up in example workflows than anything else."

Recorded because the pull the other way is strong and cost real time. Flux dev at 1280x720 is a
clear step up from schnell and worth the swap; past that, tuning a fusion is not what these graphs
are for. LoRA training for a demo was considered and dropped for the same reason.

One thing the tuning did settle: on dev, Redux at `strength` 1.0 with `denoise` 0.65 replaces the
scene outright — the published image was the style plate with a moon in it. Shipped at 0.45/0.60,
which keeps the shot and takes the look. Those two knobs are the whole balance and the note names
them.

Also settled, and it is a framing rather than an asset: a style reference in a Flow Production Tracking shop is
already a Version — mood boards and look refs live there. So 02 pulling one out of Flow Production Tracking is the
real workflow, and only 01 manufacturing a stand-in is artificial. Shipping a reference image in the
repo does not work anyway: `LoadImage` reads ComfyUI's `input/`, not this package.

## Facts worth not re-deriving

- **`frame` on the Load node is a frame number, not a position** — fixed 2026-09-05. It used to be
  both: `media._at_frame` substituted the number into the pattern while `media.load_frames`, which
  is what the node calls, indexed the sorted glob. On a 1001-based plate that returned frame 1008
  for `frame` 1003, clamped and silent. Both read the numbers off the filenames now, out of range is
  refused with the range that exists, and `frame` 0 / `frame_count` 0 mean "wherever it starts" and
  "to the end". The panel shows the range beside the source. The numbers come off disk —
  `sg_first_frame`/`sg_last_frame` are a claim nothing keeps true.
- **A widget's declared default decides what every graph saved *before* that widget existed does.**
  Measured 2026-09-05: a `SGLoadVersion` graph holding 10 values instead of 11 loads `frame_count`
  at the declared default, not at nothing. So a default is not only about new nodes — it reaches
  backwards. This is the argument that has to be answered before `frame_count`'s default changes.
- ComfyUI scans five folder names for templates; `example_workflows` is the blessed one
  (`app/custom_node_manager.py:94`).
- The templates collection label and the node footer badge are both the `custom_nodes` directory
  name. Neither reads `DisplayName`, and no pack can override either. Settled: see DESIGN.md,
  "Names".
- `INPUT_TYPES` is re-evaluated on every `/object_info` request, so a profile edit reaches the editor
  on a browser refresh; a code change needs a ComfyUI restart.
- ComfyUI writes user files with `os.replace`, so a symlink into this repo is replaced, not written
  through.
- `env.load` layers `.env.local` over `os.environ`, so `FPT_API_*` can come from the launch
  environment — which is how one machine reaches two sites today, with no UI for it.
- `VideoFromFile.get_stream_source()` returns the **whole** source path even for a trimmed or
  cropped clip: `as_trimmed`/`as_cropped` return a new `VideoFromFile` over the same file with the
  window recorded beside it (`_input_impl/video_types.py:1040,1053`). Uploading on the strength of
  the class alone files a ten-second plate as the two-second selection, silently.
- `save_to`'s `color_space` accepts only `sRGB`, `HDR` and `HDR PQ`, so the node's freeform
  `colour_space` widget is not passed to it — it stays a declaration on the record.
- `smoke.py` needs `.env.local` and `profile.local.json` at the checkout root; a worktree has
  neither, and without them every site-backed combo reads `(none)` and every graph reports failure.
- `OCIOWrite` is `OUTPUT_NODE = True` **and** declares `RETURN_TYPES = ("STRING",)` /
  `RETURN_NAMES = ("path",)`, so its path is on a wire and nobody types one. What comes down it is a
  single concrete path — the file for a still, the movie for a video, and `paths[0]`, the *first
  frame*, for a sequence (`io_nodes.py:4239`). Never a `%04d` pattern.
- `OCIO Write` also drops a `<name>.json` metadata sidecar (`write_sidecar`, default on) and a `.wav`
  beside a sequence carrying audio. A folder of frames is not only frames.
- `OCIO Read` hands back a native ComfyUI `VIDEO` on slot 4 alongside IMAGE, so a colour-managed graph
  can feed the `video` input directly.
- `tools/smoke.py` runs as `uv run --with playwright --python 3.11 python tools/smoke.py`, per its own
  docstring. Neither the system Python nor ComfyUI's venv has playwright, and `qa_node.start_comfy`
  brings up an isolated instance, so ComfyUI does not need to be running.
- The `sg_groundtruth` surface this repo actually uses is **99 lines across two files**: `FPT` and
  `FPTError` (`client.py`, 72) and `env.load` (`env.py`, 27). `mcp.py`, `naming.py` and `schema.py`
  are never imported, and nothing imported touches the corpus. DESIGN.md's "about sixty lines" for
  option 2 is the right order of magnitude.
- **`status: "(none)"` does not mean no status.** The node sends no `sg_status_list` at all, so the
  site applies the field's own default and the Version comes back `rev`, Pending Review. Correct
  behaviour, and a template note should say so rather than let it surprise someone.
- Packaging that client does **not** break `.env.local` discovery. `env.ROOT` defaults to the
  package's own `parents[2]`, which would be wrong from site-packages — but `site.py:51` already
  calls `load_env(ROOT)` with this repo's root, so the default is never used here.

## The storage root is not required after all — measured 2026-09-04

`register_files` today needs a LocalStorage root: `sequence.root_for` raises when
`published_files.storage` is unset and the site has anything but one row, `check_root` raises when it
is not mounted, and recipe 004 measured an unrooted `local_path` as `400 code 104`. That made
"anyone can open this template" and "publish files" mutually exclusive.

They are not. **A PublishedFile's stock `path` field accepts the three-call upload** (probe 013's
flow, aimed at `/entity/published_files/{id}/path/_upload`), and an image sequence goes up as a zip.
Measured end to end on the live site, row created and deleted:

    create PublishedFile                          201
    GET  .../published_files/{id}/path/_upload    200
    PUT  presigned S3                             200
    POST complete_upload                          201
    read back path                                link_type "upload"
    GET the url                                   200, sha1 IDENTICAL to what was sent
    DELETE                                        204

    path = {url, name, content_type, link_type, type, id}
    content_type  "application/zip"   set by the server, not sent
    type/id       Attachment 2718     persist THIS, not the url
    local_path_mac / relative_path / local_storage   ABSENT

So there are two file modes, and they belong in the profile beside `storage` and `path_template`:

| mode | needs | what the record is worth |
|---|---|---|
| `local_path` under a LocalStorage root | a storage row, mounted, maybe an admin | the real thing — Toolkit, RV and Nuke resolve it in place |
| **`upload`, zip for a sequence** | **nothing** | portable, round-trips on any machine, but a DCC cannot open it in place |

`local` stays right for a facility with shared storage; `upload` is what makes a cloned repo work for
a stranger. **Zip only when the count is > 1** — a single image is the commonest publish there is and
should go up as itself.

**`file:///` is dropped.** It exists on the site (2 of 192 PublishedFile rows carry a `web` link with
a percent-encoded `file://` url) and `url.md` says a url field reads back exactly what was sent, but
it is one machine's answer and loses to `upload` on portability, multi-OS and round trip.

**`sg_uploaded_file` is NOT usable** — it is a custom field, so depending on it means a field creation
on every client site, which DESIGN.md refuses (probe 019: a name spent is spent site-wide forever).

**Two consequences for code, neither done:**

1. `publish.upload` hardcodes `/entity/versions/{id}/...`. It needs the entity type as a parameter.
2. `media.published_files` reads `(a.get("path") or {}).get(LOCAL_PATH)`, so every `upload` and `web`
   row flattens to `""` and disappears from the Load picker. It must read `link_type` first. This is
   already live: the two `file:///` rows on the site are invisible to our own Load node today.

### Telling a stock field from a custom one, without a reference site

`visible.editable` in `/schema/<Type>/fields`. On PublishedFile's 33 fields it separates them
perfectly: all 7 with `visible.editable = true` are `sg_`-prefixed customs, the only `sg_` field on
the stock side is `sg_status_list`, and no plain-named field lands in the custom bucket. Worth a
corpus entry — it answers "is this field on every site?" with one read.

