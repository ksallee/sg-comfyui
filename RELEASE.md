# Release plan

Written 2026-09-04 to close a working session and open the next one cold. Everything decided in
that session is here with its reasoning; everything still open is marked as such and names who
decides. `../sg-groundtruth/PLAN.md` is the older shared plan and is **stale** — its Phase 2 and 3
are largely done and it still calls this repo `comfyui-fpt`. Reconcile the two before trusting it.

Read `CLAUDE.md`, then this, then `DESIGN.md`.

---

## State

Branch `readme-and-example-workflows`, commit `a93df52`, not merged. Kevin decides every merge.

Landed in that commit:

- `demo/` → `example_workflows/`. ComfyUI scans a custom node for `example_workflows`, `example`,
  `examples`, `workflow` or `workflows` and serves what it finds at `/workflow_templates`
  (`app/custom_node_manager.py:94`). The seven demos were in a directory it never reads.
- `workflows/` → `tools/workflows/`, beside `smoke.py` which runs them. Out of any scanned name, so
  the Templates browser offers the story and not the test material.

Verified after a restart: `/workflow_templates` returns the seven demos under this pack, keyed by
the `custom_nodes` directory name.

### An agent is running

Branch `publish-node-two-inputs`, in its own worktree, on the input-contract change below. It was
briefed to write the DESIGN.md entry first and to merge nothing. **Check its report before touching
`publish_version.py`, `movie.py`, `sequence.py`, `publish.py` or the panel JS.**

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
that forkers drive this with an agent rather than by reading it. Cheap to set up while the repo is
still private.

---

## The demo, respecified

### Why it is being rebuilt

Seven Shots, zero Tasks, one Shot per demo. It is not a pipeline, it is seven unrelated toys, and
it never shows a Task or a second entity type. Worse, every graph has Kevin's sandbox baked into its
widget values (`project 'comfyui-fpt sandbox'`, `link 'demo_01_roto (Shot)'`), so on any other site
the node raises `no Shot named 'demo_01_roto'`. And six of seven demos load input assets that are
not in the repo, so nobody but Kevin can run them.

### Entity structure — **awaiting Kevin's confirmation**

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

1. **Publish node, two inputs** — *agent running*, branch `publish-node-two-inputs`. DESIGN.md entry
   first, then code, then every shipped graph updated, then `smoke.py` over both directories.
2. **Confirm the entity structure and plate specs** — Kevin. Everything below waits on this.
3. **`/demo-setup`** — `ensure()` a Shot, an Asset and their Tasks; `seed.py` the plates onto them as
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
8. **Register-don't-write** for frames when OCIO is present.
9. **A `10_` colour-managed template.**
10. **README** — last. It cannot be written honestly until the node contract and the demo settle.
    Needs: what this is in one screen, a real setup path, and screenshots. The Templates browser
    reads `<name>.jpg` beside each `<name>.json` as a card thumbnail, which is where demo
    screenshots belong.

Not on the critical path, worth doing: promote the four `tools/workflows/` fixtures to `00_`
templates; remove the demo copies from `~/dev/ComfyUI/user/default/workflows/` once the templates
are rebuilt.

---

## Open, and who decides

| question | who |
|---|---|
| Entity structure and plate specs above | Kevin — blocks most of the list |
| Release date: the node contract lands before release, so Monday is at risk | Kevin |
| Plate licensing: is "generated by a permissive model" the written answer? | Kevin |
| How our node registers files written by `OCIO Write` instead of writing PNGs | design, not yet done |
| `sg_groundtruth` is not installable, so a Registry install cannot run — DESIGN.md, "The dependency problem" | unchanged, still blocking publication |
| `pyproject.toml` has no `PublisherId` or `Icon` | Kevin |

## Facts worth not re-deriving

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
