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
- ~~**`FPTLoadVersion`, the round trip**~~ — **closed 2026-09-07.** `00_example` runs it, and 02
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

### The name stays `comfyui-flow-production-tracking`

Tried and reverted in this session. The Templates browser labels a collection with the
`custom_nodes` directory name verbatim (`title: e` in the frontend bundle), and the node's footer
badge is `python_module` split on `.` — the same string. Neither reads `DisplayName`; the only
override is a frontend i18n key that ships with the frontend, not with a pack. Registry names allow
no spaces, so a shorter chip was reachable only by renaming the repo.

That trade is wrong: `[project].name` is a searched slot and the chip is a cosmetic one, and the
naming rules in DESIGN.md "Names" were already settled deliberately. A long label on two chips is
the accepted price, now written down there so it is not re-litigated.

**There is no repo rename to do.** `origin` stays `comfyui-flow-production-tracking`.

### The publish node takes two inputs

Today `FPTPublishVersion` takes one `images: IMAGE` and manufactures artifacts from the tensor: a
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
    01–07   the VFX stories                core only
    10_*    colour-managed                 requires ComfyUI-OCIO

`00_` is today's `tools/workflows/` fixtures promoted: `publish_demo`, `load_demo`, `round_trip`,
`publish_passes` are the reusable patterns a new user should meet first, and demoting them to test
fixtures hides them. A `10_` template's dependency is carried by ComfyUI-Manager's missing-node
detection plus a `MarkdownNote` in the graph, the way `05_plate_upres` already lists its model
weights and their licences — `pyproject.toml` cannot express a dependency on another node pack.

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

## The demo, respecified

### Why it is being rebuilt

Seven Shots, zero Tasks, one Shot per demo. It is not a pipeline, it is seven unrelated toys, and
it never shows a Task or a second entity type. Worse, every graph has Kevin's sandbox baked into its
widget values (`project 'comfyui-fpt sandbox'`, `link 'demo_01_roto (Shot)'`), so on any other site
the node raises `no Shot named 'demo_01_roto'`. And six of seven demos load input assets that are
not in the repo, so nobody but Kevin can run them.

### Entity structure — **confirmed by Kevin, 2026-09-04**

**`sh010` (Shot)** — the hero plate, six demos, five Tasks:

| Task (`content`) | demo | output(s) |
|---|---|---|
| Plate | *seeded by `seed.py`* | `plate` |
| Roto | 01 roto matte | `matte` |
| Prep | 02 utility passes | `depth`, `normal`, `alpha` |
| Paint | 03 cleanplate paintout | `cleanplate` |
| Comp | 04 set extension, 07 retime | `setext`, `retime` |
| Delivery | 05 plate upres | `upres_esrgan`, `upres_seedvr2` |

**`mp_skyline` (Asset)** — 06 camera move, Task `Concept`, output `cameramove`.

Two entities, nine Versions, one dependency chain running plate → matte → cleanplate → retime →
upres through `sg_ai_generated_from`. Three Tasks carry more than one output, which is the case that
makes `{output}` in the name template necessary rather than decorative. Two entity types, which is
the first time the demos show that `Version.entity` accepts more than Shot.

Name template stays `{entity.code}_{output}_v{version:03d}` — with several outputs on one Task, a
`{task}`-based template would collapse them onto one name.

### What the corpus already says about building it

| entry | consequence |
|---|---|
| **Shot** (entity type) | needs only `project`; `code` is optional **and not unique**, and a re-run duplicates rows. Send `code`, key on `id` |
| **Asset** (entity type) | same — two assets may share a code, key on id never code |
| **Task** (entity type) | named by **`content`, never `code`**; create needs only `project`; `start_date`/`due_date`/`duration` are one triple the server recomputes on every write |
| **Step** (entity type) | site-wide, no project field, partitioned by `entity_type`; list with `entity_type is "Shot"`, and neither code nor short_name is unique |
| **post_entity_batch**, recipe **002_batch** | the create path |
| **028_loud_and_silent** | a batch can return an id for a row it never made |
| **019_create_fields** | the precedent for idempotency: read first, never POST-and-hope |
| **005_link_usage** | only 1% of Versions link through `sg_task` on the sample project — the templates must keep working with `task` empty |

So `/demo-setup` is an `ensure()`, not a create: it reads before it writes and keys on id, because
Shot codes are not unique and it will be re-run many times as plates change. Tasks link to the
site's existing Steps where they exist, keyed on id, falling back to a bare Task with only `content`.

---

## Plate specs

Two plates, down from six. Nothing is generated until Kevin approves these.

### Plate A — hero clip, `sh010`

Serves demos 01, 02, 03, 04, 05 and 07, so what is in frame is decided by six requirements at once:

| demo | needs from the plate |
|---|---|
| 01 roto | one person, unambiguous to the prompt "the actor", clean silhouette, holding across every frame |
| 02 passes | a real depth gradient — subject near, background receding — and surfaces with enough shape for normals to read |
| 03 paint-out | **one** discrete removable object, clearly bounded, against a static background. 03's own doc names its current weakness: a queue of traffic where `car` matted only the nearest |
| 04 set extension | content that runs out at the frame edge — architecture continuing past both borders, sky headroom above |
| 05 upres | real texture worth recovering: cobbles, brick, fabric weave — detail a 480p generative pass destroys |
| 07 retime | motion at a constant pace, so a retime is legible |

Those resolve to one image rather than fighting:

> **Locked-off camera. One person walking through frame at a steady pace. One parked car,
> isolated, well clear of any other vehicle. A street with buildings running out of frame on both
> sides and sky above. Textured ground.**

Locked-off satisfies 03 (the fill must hold still) while the subject satisfies 07 (motion to
retime). The car is alone so `car` mattes exactly one thing.

    resolution   1920x1080
    rate         24 fps
    length       48 frames (2s) — enough for a matte to hold and a retime to read, short enough to iterate
    colour       sRGB, 8-bit, declared and never converted
    files        plate_A.mp4 (h264, bt709) + plate_A_f0001.png (the reference still 01 also loads)

**On making a 1920x1080 clip:** generate at model resolution and bring it up with the same ESRGAN
path `05_plate_upres` already uses. That is self-consistent — we dogfood our own upres to make the
plate — and it leaves demo 05 meaningful, because the *generated* work downstream still happens at
480p while the plate is delivery res. Today the plate is itself 480p, so "upres to delivery
resolution" is upres from nothing.

**Acceptance, before it is seeded:** a person `SAM3_Detect` finds from "the actor" on every one of
the 48 frames; `car` matting exactly one vehicle; visible texture in the road at 100%; both side
borders cut through architecture rather than sky.

### Plate B — matte painting, `mp_skyline`

Serves demo 06 only, and is deliberately not photographic — a matte painting is an Asset, not a
Shot, which is the point of it being the second entity.

> **A painted skyline with three separated depth layers: a dark foreground silhouette (rooftop edge
> or foliage) across the lower third, a midground of buildings, and a far horizon with sky. Painterly
> brushwork, not photoreal.**

    resolution   1920x1080 still
    model        flux-dev, ~28 steps, cfg ~3.5
    colour       sRGB, 8-bit
    file         mp_skyline.png

The three layers exist so a push-in has real parallax; a flat painting gives a camera move nothing
to work with and the demo reads as a zoom.

### Why the current plates are being replaced

Embedded `prompt` metadata in `~/dev/ComfyUI/input/fpt_plate_paris.png` and `fpt_plate_figure.png`:

    ckpt   flux1-schnell-fp8.safetensors
    steps  4        cfg 1.0      sampler euler/simple
    latent 832x480
    negative prompt: ""

Schnell at 4 steps is the lowest-fidelity setting the model has, and 832x480 is a sixth of HD. Both
Paris prompts are the same street at different times of day, so 03, 05 and 06 read as one location.
`fpt_plate_setext.png` is 512x288. `demo_01_roto_plate_f0001.png`, which `01_roto_matte.json` loads,
**exists nowhere** — not in the repo and not in Kevin's `input/`.

**Licensing is still open** — `../sg-groundtruth/PLAN.md` line 15 wants a "public demo clear of
anyone else's asset licensing". Generated plates from a permissively-licensed model answer it; the
decision has not been written down.

---

## Work, in order

Dependencies are real: nothing that touches the node should start before the running agent reports.

1. **Publish node, two inputs** — **done, and published through the new contract.** Versions 31874
   and 31875 in the sandbox: `save_to()` encoded the review clip, `poster()` took the thumbnail off
   it, `upload_file` streamed it, and `write_frames` -> `place` -> PublishedFiles 6869/6870
   registered the sequence under `/Volumes/FPT`.

   **Said precisely, because it is easy to overclaim:** the repo had published ~34 Versions earlier
   the same day through the *old* node. What had never run, and now has, is the two-input path —
   a wired VIDEO, `save_to` in place of the deleted `movie.encode`, and `poster()` reading the file
   about to be uploaded.
2. **Confirm the entity structure and plate specs** — Kevin. Everything below waits on this.
3. **`/demo-setup`** — **the entity half exists**: `tools/demo_setup.py` ensures `sh010` (Shot 7712,
   six Tasks) and `mp_skyline` (Asset 10058, Concept) on the sandbox, reading before it writes and
   keying on id because a Shot's `code` is not unique. Run twice, it creates nothing the second time.
   Roto, Comp, Delivery and Concept matched real site Steps; Plate, Prep and Paint are bare Tasks,
   because minting a Step would add it to every show on the site. Still to do: `seed.py` the plates onto them as
   Versions; fill the template graphs' project and link values. Needs an entity-create path, which
   this repo does not have today (it creates Versions and PublishedFiles and nothing else).
4. **Templates committed with `(none)`** for project and link, filled in by `/demo-setup` on install.
   Decided: a committed graph pointing at whoever ran it last is worse than an empty picker.
5. **`/setup`** — first-run walkthrough. Today a missing `.env.local` gives empty pickers and a raw
   error sentence from `FPT.from_env` on the node panel: honest, and useless to a newcomer. Nothing
   says *copy `.env.local.example`, fill three keys, refresh*. Also asks the colour-management
   question.
6. **`/track-workflow` gains three questions** — colour space (always, defaulted from the profile),
   register files (only when the profile has a storage root), and the OCIO wiring offer. It asks six
   questions today and none of them decide what lands on disk.
7. **Rebuild the templates** on the new entity structure and the new node contract. 01 and 07 want
   rebuilding around the VIDEO input rather than `GetVideoComponents`.
8. **Register-don't-write** for frames when OCIO is present. Designed, not built — a third input
   `files: STRING`, a socket so no widget moves. See DESIGN.md.
9. **A `10_` colour-managed template.**
10. **README** — last. It cannot be written honestly until the node contract and the demo settle.
    Needs: what this is in one screen, a real setup path, and screenshots. The Templates browser
    reads `<name>.jpg` beside each `<name>.json` as a card thumbnail, which is where demo
    screenshots belong.

Not on the critical path, worth doing: promote the four `tools/workflows/` fixtures to `00_`
templates; remove the demo copies from `~/dev/ComfyUI/user/default/workflows/` once the templates
are rebuilt.

---

## The next session opens here — written 2026-09-08, night

**State.** PR #75 onto `dev` is open and **not to merge** until Kevin has clicked through Settings
himself. It carries the sign-in work, the release commits since #56, and now the Settings surface
below. `sg-groundtruth` has probe 052 merged to `main` at 0.1.3, and **Kevin cuts the PyPI release**;
until then ComfyUI's venv runs the checkout as an editable install. Issue #76 records the SG rename.

**Settings, then SG, is built and tested headless.** One category in ComfyUI's Settings dialog, ids
`SG.*`, drawn by `web/fpt_settings.js`, backed by `/fpt/settings`, `/fpt/test`, `/fpt/defaults` and
`/fpt/preview_template`. Nothing enters ComfyUI's settings store. Groups, in the order the dialog
sorts them:

- **Connection**: Site address; Publishing as, with **Test**, which reports the site's own sentence
  for a wrong key, a refused Publish as login, and a wrong address.
- **Log In As Yourself**: Log in, the App Session Launcher flow moved off the node.
- **Script Authentication**: Script name, Application key (write-only), Publish as. Each row says
  where its value comes from: the environment, saved on this ComfyUI, or not set.
- **SG Defaults**: Project, the one both nodes open on.
- **SG Publish Defaults**: Version name, Root name, Status, Published Files tick, Storage, Sequence
  path, Movie path, Review movie, Colour space. They edit `profile.local.json` for that project;
  each template shows the value in force and its rendered example. Group names are chosen for the
  dialog's alphabetical sort, which is why the person group says Log In and the defaults say SG.

A 404 from any route means the running ComfyUI predates the pack, and every row says so: routes
register at import, so a pack update needs a restart, not a reload.

`web/fpt_signin.js` and both `addSignIn` calls are gone. The nodes reload their pickers on a
`fpt:session` window event and say nothing about the connection except the error sentence, which
names Settings. The Publish node's preview now refuses before rendering a name when nothing is
connected, so that sentence is the alert rather than a line in the fold.

**Measured, in `~/Desktop/sg-settings-screenshots/`**, eleven states from a credential-free copy of
the checkout and from this one: not connected (dialog and node), site only with Sign in enabled,
signed in as Kevin (the probe's session token copied in), sign-in expired, script from the
environment with Test passing, a wrong key, a refused login, a wrong address, and the Defaults group
after edits. Kevin has **not** yet run the Sign in button from the dialog himself, and the Load
node's not-connected state was not captured.

**Decided with Kevin, 2026-09-08.** The short name is **SG** everywhere a short name is needed, the
full product name otherwise, never "Flow PT" (#76). Custom fields on the nodes stay an agent's job
for the first release; the Defaults group carries what an operator sets by hand. Updating linked
entities from a publish, a Task's status for instance, is a nice-to-have after release.

**Still to do here:** the fold table (each widget shown, in the fold, or hidden, which the profile's
`widgets` block already decides), which would be the first content of an SG Load Defaults group;
per-project defaults for a project other than the one the nodes open on stay a file edit; `instrument.py` and `smoke.py` read no profile-added widgets, which only
matters once custom fields are built.

**How to test UI here.** `uv run --with playwright --python 3.11 python tools/qa_node.py --start
--node <type> --drive <file.js>`: an isolated ComfyUI, headless, prints what the drive returns. Pass
`--repo <copy>` for a checkout without `.env.local`, and `--keep` to leave the instance for more
drives on the same `--port`. Not the live browser tool; Kevin can see that session and it is slower.

## Three things the next session opened with — written 2026-09-08, morning

### 1. Credentials: decided and built on 2026-09-08, sign in as a person

`.env.local` inside the pack could not ship: ComfyUI Manager replaces `custom_nodes/<pack>/` on
update and the keys with it. It no longer has to. The nodes carry a Sign in row, the operator approves
a request in the browser where they are already logged into Flow PT, and the session token the site
returns is kept in ComfyUI's protected `user/__comfyui_flow_production_tracking/` directory. See
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

`Version.user` is the field Flow PT shows as **Artist** and it defaults to whoever called, so every
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
`multiline`, `int`, `bool`, `combo` — not Flow PT's `data_type` set, so an `entity` field like Artist
fits none of them and the first instinct was to fudge it as a login string.

What the table needs is `data_type -> widget`: `entity` to a searchable picker, `multi_entity` to a
multi-picker, `date` to a date input, `list` to a combo built from the schema's own valid values,
`checkbox` to a boolean, `text`/`float`/`number` to what they already are. Then adding a field is one
`Field(...)` line naming a Flow PT field, and the widget follows from the schema rather than from a
guess. The entity picker already exists for `link` and `project`; it is not reusable by name yet.

That is the difference between "an operator with an LLM can add a field" and "an operator with an LLM
can add a text field".

## Open, and who decides

| question | who |
|---|---|
| Plate specs above (Plate A, Plate B) | Kevin — blocks `/demo-setup` and the template rebuild |
| Release date: the node contract lands before release, so Monday is at risk | Kevin |
| ~~How credentials ship~~ | **closed 2026-09-08.** Sign in as a person through the App Session Launcher, session token in ComfyUI's protected user directory, script key from the environment for farms. DESIGN.md "Who the nodes publish as" |
| Artist attribution is decided and unbuilt: impersonate, fall back to the `user` field, then the script | built next |
| `data_type -> widget` so adding a Flow PT field of any type is one line | built next |
| Plate licensing: is "generated by a permissive model" the written answer? | Kevin |
| How our node registers files written by `OCIO Write` instead of writing PNGs | **designed** — DESIGN.md, "Where someone else wrote the files, we register them". Kevin to read |
| ~~Should `frame_count` default to 0 or stay 1?~~ | **closed 2026-09-07 — 0.** See below |
| ~~`sg_groundtruth` is not installable, so a Registry install cannot run~~ | **closed 2026-09-05.** `sg-groundtruth` 0.1.1 is on PyPI, `_deps.py` and `SG_GROUNDTRUTH_PATH` are gone, and `requirements.txt` — the file ComfyUI-Manager installs — names it. The corpus checkout is still wanted to *set up*: `inspect_site.py` is not in the wheel |
| `pyproject.toml` has no `PublisherId` or `Icon` | Kevin |
| **Node names.** Kevin, 2026-09-08: "Flow PT for searching nodes is not great, SG is faster to search in the UI. SG Load, SG Publish is great, but other names like repo name etc need to change as well." Issue #76, research first; DESIGN.md "Names" settled the current ones and would be reopened | research, then Kevin |
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

Also settled, and it is a framing rather than an asset: a style reference in a Flow PT shop is
already a Version — mood boards and look refs live there. So 02 pulling one out of Flow PT is the
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
  Measured 2026-09-05: a `FPTLoadVersion` graph holding 10 values instead of 11 loads `frame_count`
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
- Packaging that client does **not** break `.env.local` discovery. `env.ROOT` defaults to the
  package's own `parents[2]`, which would be wrong from site-packages — but `site.py:51` already
  calls `load_env(ROOT)` with this repo's root, so the default is never used here.

## Plate sources investigated 2026-09-04, and what was ruled out

Recorded so a later keying template does not re-derive any of it.

### Tears of Steel — real VFX plates, CC-BY 3.0, but only two shots

`media.xiph.org/tearsofsteel/linear-exr/` holds **two** shots, not the 4 TB the press coverage
mentions: `03_2a` (599 frames) and `04_5f` (262 frames). Both 4096x2160 **float32 scene-linear
EXR**, decoded from Sony F65 raw, **51 MB per frame**. `raw/` holds two `.mxf` files. The README
states Creative Commons Attribution 3.0.

- `04_5f` is a close-up of an actor against green. Not a plate for anything here.
- `03_2a` is a green-screen stage: a rooftop set with a stone balustrade, candles, figures, a rope
  hanging through frame. The camera pushes in and **settles by about frame 400**, so 400–448 is a
  near-locked 48-frame window and the best-looking part of the shot.

Why it was tempting: rig removal (the rope) is a better paint-out than a parked car; the real 4K
gives demo 05 **ground truth to show the upres against**, which nothing generated can; and a keyed
plate composited over `mp_skyline` would make one Version whose sources sit on two different
entities. Provenance reads true — the plate is `unrecorded` because it came off a camera.

Why it was not taken: dark and candle-lit so it screenshots poorly, almost no motion in the window
so 07 retime gets worse, and the licence stack below.

**51 MB/frame is the hard fact**: 48 frames is 2.4 GB, and even 1080p half-float is ~400 MB. Scene-
linear EXR is not repo-shippable at any useful length. A 1080p h264 derivative is ~2 MB and CC-BY
grants that redistribution explicitly, so a derivative ships in-repo with an attribution line and no
install step.

### CorridorKey — usable, but not by the base templates

Corridor Digital's neural keyer (`nikopueringer/CorridorKey`, ~14.6k stars). Four ComfyUI wrappers
exist; none installed here. Nodes: Load CorridorKey Model (~300 MB from HuggingFace), Chroma Key
Prepass, CorridorKey Greenscreen, CorridorKey Composite.

Three separate licences, the `05_plate_upres` situation again — wrapper code, tool, and weights:

- **CorridorKey itself is CC BY-NC-SA 4.0 plus additional terms.** §1 permits commercial *processing*
  of images, so a facility using it on a job is fine. §2b forbids paid inference services. **§2c
  requires a separate written agreement to incorporate it into a commercial software package** —
  the clause a forker hits. §3 requires the "CorridorKey" name in attribution. §4 is ShareAlike.
- **Both leading wrappers report NO licence on GitHub** — `cnoellert/comfyui-corridorkey` (14 stars,
  real MPS paths, "tested at 6K on Apple M4 Max") and `pixelworldai/ComfyUI-CorridorKeyWrapper`
  (2 stars). No licence is a weaker grant than NC-SA, and neither is Registry-grade.

So keying can only ever be a **tier-2 template requiring an external pack**, the shape already
decided for ComfyUI-OCIO. It can never be in the base set, because "core nodes only, anyone can open
this" cannot survive an unlicensed wrapper.

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

## Matting, measured 2026-09-04 — what the demo templates must know

A session spent on one question: why did `01_roto_matte` look bad. The answer was a **prompt**, not a
pipeline, and most of what was built before finding that was compensation. Written down because
every one of these cost real time to find.

### Start from ComfyUI's own templates, not from scratch

291 non-API templates ship in `comfyui_workflow_templates_json`, including
`utility_video_segment_sam3`, `utility_birefnet_remove_background`, `video_wan_vace_inpainting` and
`video_wan21_scail2_character_replacement`. The official SAM3 graph is
`LoadVideo -> GetVideoComponents -> SAM3_Detect -> MaskPreview` and nothing more — **simpler than
what this repo invented**, and its Note carried the fix below. Read them first.

### SAM3's prompt takes a count, and `:1` is poison

From the official template's own Note: max 32 tokens, comma-separate multiple subjects, and cap each
with `:N` — `eye:2, window panels:4`. Measured on the plate, frames 8–12, where frame 10 had been
losing one of two people:

| prompt | frame 10 | verdict |
|---|---|---|
| `the couple` | **2.91%** against 5.44 either side | drops one person |
| `person:2` | 5.50% | holds |
| `woman:1, man:1` | 5.48% | holds |
| `people:2` | 5.50% | holds |

And on a single subject, measured on a green-screen plate where the subject is 23.6% of frame:

| prompt | coverage |
|---|---|
| `person` | 23.65% |
| `man` | 23.64% |
| `the man in the purple shirt` | 23.61% |
| **`person:1`** | **0.10% — matted a tracking marker instead of the man** |

**The rule: a bare noun for one subject, `:N` only for N ≥ 2, never `:1`.**

With `person:2` and `refine_iterations 5` the plate runs **48 frames with no frame-to-frame jump over
0.6pt at all**. No tracking, no cropping, no bounding box.

### SAM3 makes a stencil; BiRefNet makes a matte

`SAM3_Detect` at `refine_iterations 5` returns **2 of 256 levels** — pure binary, zero partial alpha.
`RemoveBackground` returns 256/256 levels with real falloff. For a roto *deliverable* the stencil may
actually be preferable (real roto is hard-edged splines, softened deliberately downstream), but they
are different products and the demo should not pretend otherwise.

`refine_iterations` (0–5, default 2) visibly smooths SAM3's staircase; 5 is the best and costs
nothing but time. It does **not** fix identity loss — that was always the prompt.

### BiRefNet is core, and needs only a model

`RemoveBackground` + `LoadBackgroundRemovalModel` are `comfy_extras.nodes_bg_removal`, backed by
`comfy/background_removal/birefnet.py`. **A 424 MB weights download, not a custom node pack**, so a
BiRefNet template keeps the "core nodes only, anyone can open this" promise.

    Comfy-Org/BiRefNet -> background_removal/birefnet.safetensors  424 MB   sharp, real alpha
                       -> background_removal/lucida.safetensors    844 MB   over-soft, reads blurred

It is salient-object, not prompt-driven — which on a green-screen plate is an advantage (no prompt to
get wrong) and on a busy plate is a limitation.

### Both models resize to 1024, so subject size in frame decides quality

The single most useful fact here. `birefnet.json` declares `image_size: 1024`, and SAM3's encoder is
likewise fixed. The whole frame is resized to fit, so a small subject gets few model pixels:

| subject size in a 1920x1080 frame | BiRefNet partial-alpha |
|---|---|
| 6.8% of frame (plate frame 1) | 5.42%, hair strands visible |
| 3.0% of frame (plate frame 47) | 2.37%, blobby |

Cropping to the subject before inference recovers it — a fixed work area of 655x566 put **2.93x more
model pixels on the subject** and lifted partial-alpha from 2.37% to 17.82%. But **ComfyUI has no
bounding-box concept**: `SAM3_Detect` emits `bboxes` and `ImageCropV2`/`CropByBBoxes` consume them,
yet nothing converts a `BOUNDING_BOX` back to x/y integers and there is no paste-by-bbox node. So an
automatic per-frame crop cannot be closed and a work area has to be a fixed, operator-set
`PrimitiveBoundingBox` composited back with `ImageCompositeMasked`. Nuke gives this away free; here
it is manual.

With the prompt fixed, the plate no longer needs it. It stays the answer for a subject that is small
in frame.

### Core has no chroma keyer

`ImageColorToMask(image, color)` is an exact-colour match — no tolerance, no spill suppression, no
edge softness. There is nothing else. A green-screen template therefore either takes an external
keyer (CorridorKey: CC BY-NC-SA plus terms, and **both leading ComfyUI wrappers carry no licence at
all**) or does not key: measured on a cottonbro green-screen plate, **BiRefNet alone produced a clean
matte of the subject with no prompt and no keyer**. On green screen the subject fills frame and the
background is uniform, so both of this section's problems disappear at once.

### Things that were tried and are dead

- **`SAM3_VideoTrack` seeded with `initial_mask`** — collapses to 0% coverage within 8 frames.
- **SAM3 x BiRefNet multiplied** — inherits SAM3's holes while gaining nothing.
- **`ImageCropToMask` as a crop** — it also *applies* the mask, so it cannot be used to test
  resolution in isolation. `ImageCropV2` with a `PrimitiveBoundingBox` is the clean crop.
- **`SAM3_VideoTrack` instead of `SAM3_Detect`** — genuinely fixes the dropout, but so does the
  correct prompt, at better edge quality and half the run time.

## 02 and 07, measured 2026-09-04

Both built on ComfyUI's own templates rather than invented, per the lesson above.

### 02 utility passes — normals are the strongest thing in the demo set

`utility_depth_anything3_video_depth_estimation` and `utility_moge_depth_estimation` are the
starting points. Both ship as **subgraphs**, so `definitions.subgraphs` has to be unpacked to get the
real node types.

- **Normals, MoGe-2 (`moge-2-vitl-normal.pt`) — excellent.** Every building face resolves as a
  distinct plane, the ground reads, window reveals, drainpipes, the arch and the backpack all carve
  out. Structurally identical frame to frame, no flicker. Sky is flat grey, correctly marked invalid.
- **Depth, DA3 (`depth_anything_3_mono_large`) — good gradient, compressed near end.** The alley
  recedes properly and `apply_sky_clip` clips the far end and sky to black, but the near end crowds
  white (2.8% of pixels at 255, mean 202) and the figures read as near-flat silhouettes with little
  internal relief. Try `min_max` normalization if figure modelling matters.
- **Alpha comes from BiRefNet, not from MoGe.** MoGe's `mask` output is a **valid-geometry** mask —
  it marks sky — and is *not* a subject alpha. Presenting it as one would be a lie about what the
  model computed.

The DA3 dynamic combo serialises flat in the API format: `output`, `output.normalization`,
`output.apply_sky_clip`.

### 07 retime — FILM is good, and `multiplier` above 2 is broken

Based on `utility_video_frame_interpolation`.

Quality against ground truth, predicting a real frame: **FILM 37.5 dB, a crossfade 32.4 dB, a frame
hold 29.9 dB.** No ghosting, no double edges, no limb tearing on the hands or hair, and sharpness
holds (Laplacian variance 474 -> 465). Error maps show only thin edge outlines — a sub-pixel timing
offset, not synthesis failure — with the background error-free.

**But `multiplier` > 2 in a single `FrameInterpolate` misplaces its in-betweens.** FILM's fusion net
is trained at t=0.5 and ComfyUI asks it for other times by scaling the flow (`film_net.py:232`).
Measured placement at `multiplier=4`:

| | t values produced | |
|---|---|---|
| one node, `multiplier=4` | **0.385 / 0.531 / 0.672** | wanted 0.25/0.5/0.75 — the clip judders |
| two chained `multiplier=2` | **0.266 / 0.531 / 0.778** | +1.7 and +2.0 dB on the off-centre frames |

**Chain powers of two. Never set `multiplier` to 3 or 4 directly.**

One honest caveat for the demo: this plate carries real motion blur, and slowing it down exposes
that. It is the plate, not the model.

### 05 plate upres — ESRGAN ships, SeedVR2 must not

Based on `utility-gan_upscaler` and `utility_seedvr2_3b_int8_upscale_video` (the latter unpacked from
its subgraph). Measured by downscaling the real plate to 480x270, upressing back to 960x540, and
comparing against the true frame:

| | PSNR | SSIM | gradient (truth 5.98) | frame-to-frame MAD (truth 0.40) |
|---|---|---|---|---|
| bicubic | **33.26** | **0.925** | 4.70 | 0.39 |
| RealESRGAN_x4plus | 31.52 | 0.904 | 5.62 | 0.65 |
| SeedVR2 (cc=none) | 22.72 | 0.673 | 7.12 | — |
| SeedVR2 (cc=lab) | 25.24 | 0.715 | 7.01 | **2.23** |

**SeedVR2 is disqualified, and the reason is the one this project exists to care about: it invents.**
It turned a plain dark wall into a hallucinated fibrous texture, redrew a window sill that is not in
the plate, shifted the tone darker and more contrasty, and flickers **5x more than the source** frame
to frame. Sharper on paper, wrong in fact. That is restoration-style invention — reasonable for the
grainy crf32 source its own template targets, and not something to put under a plate a supervisor
will trust.

It also **does not run on this machine**: the int8 build hits `aten::_int_mm` unimplemented on MPS,
and forcing `SelectModelDevice device=cpu` takes 88 s for 3 frames at 960x540 — hours for a 48-frame
1080p pass.

**Ship `RealESRGAN_x4plus` -> downscale to target.** Zoomed, it puts cables, window bars, poster edges
and the drainpipe back almost exactly where the true frame has them.

**And state the limit honestly in the demo:** ESRGAN recovers **structure, not micro-texture**.
Gradient energy goes 4.41 -> 5.21 against a true 5.51, so edges genuinely come back — but hair
strands become smooth ribbons and plaster grain becomes a waxy surface. It also scores *worse* than
plain bicubic on PSNR and SSIM (31.52 vs 33.26), which is the normal GAN-upscaler trade and worth
saying out loud rather than quietly claiming a win.

### 03 cleanplate paintout — the matte is excellent, the fill is not

Based on `video_wan_vace_inpainting`, though the repo's own `example_workflows/03_cleanplate_paintout.json`
already ships a flattened debugged version of it, and its `.md` records both traps: CausVid is
CFG-distilled so CFG 1 makes the negative prompt inert, and VACE redraws the whole frame so the result
has to be composited back through a feathered matte. Both still true.

**The matte half is the best evidence yet for the bare-noun rule.** `banner` gives a tight, correct
matte with **IoU 0.998 across 5 frames and no drift**, and removal is clean — 99.4-100% of masked
pixels change, 0.1% spill outside.

**The fill half does not hold up.** Two runs:

- a dark maroon slab carrying the banner's exact silhouette — a textbook ghost;
- with that failure named in the negative, a flat neutral-brown panel with a fine crosshatch: no
  stone, no wood grain, and it does not continue the horizontal grey band running across the wall
  behind it.

At full-frame size it reads as shadowed masonry and would pass as a first pass. At 100% it is
obviously painted. And it **boils**: inside-matte frame-to-frame difference is **3.6-14.6 against
0.12-0.22 on the plate**, a visible luminance strobe, and worse on the better-coloured run.

**The cause is the same one that broke matting: subject size against a fixed model input.** The
banner is ~90x225 px at the 848x480 the 1.3B model wants, so there is almost nothing to work with.
The fix is the same too — crop, inpaint at native resolution, recomposite — or a 14B model. Neither
tried.

So the work-area pattern is not a matting trick, it is **the general rule for every model in this
demo set**: a fixed-resolution model gets what the frame gives it, and a small subject starves it.

Also: the repo's existing 03 uses a locked-off still, while this plate has a moving camera, which is
why temporal stability here is far worse than the 0.5-0.9 its `.md` claims. Five frames only, and
that `.md`'s own warning stands — a short probe does not predict a long one.

### 04 set extension — upward works, sideways is a lottery

Based on `video_wan_vace_outpainting` (the 1.3B path; the 14B loaders ship mode-4 bypassed).
`flux_fill_outpaint_example` was reviewed and rejected: **no `flux1-fill-dev` is installed**, and
`flux1-schnell-fp8` is not a fill model, so VACE 1.3B is the only working route.

**Upward extension is genuinely good.** Padding 192px up, the left building continues with a correct
window — stone surround, glazing bars, a curtain — verticals converge correctly, the cornice line
carries through, the centre facade runs up to a terracotta eave and the sky slot opens plausibly.
Backlit haze matches, and a row-gradient across the seam shows no spike.

**Sideways depends on having video context.** A single frame padded at the sides produced a **dead
flat grey plane** on the right (band std 6.7, gradient 0.78, against 20.5/3.71 on the left): the
plate's right edge is a near-black shadowed wall, so the model had no cue and invented a void. The
same pad over 5 frames built a real facade with a stone lintel. **A still-only demo should pad top
only.**

Two gotchas worth keeping:

- `RepeatImageBatch.amount` must equal `length`, because `ImagePadForOutpaint` returns a single 2D
  mask rather than a batch (`nodes.py` `expand_image`).
- `WanVaceToVideo` truncates `control_video` itself, but its `width`/`height` must equal the padded
  size or it centre-crops and the plate stops lining up.

### What 03 and 04 share, and it matters

- **The same cross-hatch / mesh-weave artifact** over dark flat surfaces, in both demos, bleeding into
  the plate region. Unchanged at 6 steps/lora 0.7 and 10 steps/lora 0.5, so it is not a step count —
  it is what WAN VACE 1.3B does here.
- **Neither preserves the plate.** VACE redraws the whole frame; 04 measures the VAE round-trip drift
  inside the original border at **mean 6.0/255, p99 36**, concentrated on high-frequency edges. Both
  demos therefore *must* composite the original back under the result through a feathered matte, and
  04's graph does not yet do it.

Both were capped at 5 frames on a shared queue. Neither is proven at 48.

### Two things the first sh010 publish taught us

**`status: "(none)"` does not mean no status.** It makes the node send no `sg_status_list` at all, so
Flow PT applies the field's own default and the Version comes back **`rev`, Pending Review**. The node
is behaving correctly — the site fills it — but a template that reads `(none)` implies a statusless
Version and there is no such thing here. Say so in the templates rather than let it surprise someone.

**The upres numbers, measured over all 48 frames rather than one:**

| | PSNR | SSIM |
|---|---|---|
| plain bicubic | **31.88** | **0.929** |
| RealESRGAN_x4plus | 30.81 | 0.900 |

Same verdict as the single-frame survey — bicubic wins both — but different absolutes (that survey
said 31.52/0.904 against 33.26/0.925). The published note on Version 31879 carries the single-frame
figures. These are the ones to quote.

**And the gap this run did NOT close:** every demo in it loads its plate from a repo file, so
`provenance.ancestors` finds no upstream Version and every publish lands with an empty
`sg_ai_generated_from`. Seven unconnected Versions, where the demo's whole spine is meant to be
plate -> matte -> cleanplate -> retime -> upres. 05 is the sharpest case: it degrades the plate to
480p and upresses that, and **the degraded plate — the actual input — exists nowhere on the site**.

The fix is a `00_` seed template that publishes the repo's plates as Versions, after which `01`-`07`
pull through `FPTLoadVersion` and the chain builds itself, because `provenance.ancestors` already
walks upstream Load nodes. The overnight run had already reached for this: `demo_05_upres_gen480_v001`
is the degraded plate as its own Version.
