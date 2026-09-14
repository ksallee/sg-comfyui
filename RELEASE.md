# Release plan

Decisions are here with their reasoning. Open questions name who decides.

Read `CLAUDE.md`, then this, then `DESIGN.md`. The operator's documents are `README.md`, `INSTALL.md`
and `AGENTS.md`.

---

## Next session, in order

1. **Corpus**, Kevin's repo: sg-groundtruth #48, and the two gaps under "Open".
2. **`Icon` in `pyproject.toml`**, a square image 400 px or smaller, and `Banner` at 21:9, when
   Kevin has them. A new Registry version needs a version bump in the same commit.

Launched 2026-09-14: posted on LinkedIn and on the Flow Production Tracking community forum, with
the run clip. Feedback arrives as GitHub issues through the Bug and Feature forms, as forum replies,
and as LinkedIn comments. The next session starts by reading those.

Done 2026-09-14, on the Registry: `sg-comfyui` 0.1.0 under publisher `ksallee`, published with
`comfy node publish` from the `dev` checkout at #142, changelog "First release.", status pending
the Registry's review. The archive is the node code, the editor files, the example graphs, README,
INSTALL, DESIGN, AGENTS, CLAUDE, the four commands, `doctor.py` and the licence, 49 files.
Measured: the archive at `cdn.comfy.org/ksallee/sg-comfyui/0.1.0/node.zip` has the same 49 files
as a local `comfy node pack`; unzipped into an empty `--base-directory`, ComfyUI 0.34.0 registers
both nodes with the three path widgets, serves the editor files and `/sg/tokens`, and lists the
three templates; `tools/doctor.py` from that copy reports ok on every line. The dependencies were
already in the interpreter, so the Registry's `pip install` step was not exercised.

Done 2026-09-14, after the release: the repo is public. The process from here is in CLAUDE.md:
an agent branches from `dev`, opens a PR onto `dev` and merges it; `main` is Kevin's. The launch page is at https://sg-comfyui.vercel.app: Vercel project `sg-comfyui`
under kevin-sallees-projects, linked to the GitHub repo with production branch `main`, root
directory `site`, framework SvelteKit, output directory `build`, `BASE_PATH=/` in production.
`site/vercel.json` turns Git deployments off for every branch but `main`, so a push to another
branch creates no deployment; a push to `main` deploys production. The project's ignored build step
is `git diff --quiet HEAD^ HEAD ./`, run in `site`, so a push that changes nothing under `site/` is
skipped before building. `pages.yml` is removed. The `gh-pages` branch is a leftover build and GitHub
Pages is not enabled.

Done 2026-09-14: `dev` merged into `main` by merge commit, tag `v0.1.0`, the GitHub release, Actions
back on at the repository level, the site workflow green on `main` by dispatch. The tests workflow
runs on the next push; a dispatch of it runs its manual smoke job, which fails on a hosted runner
by design.

---

## State, end of 2026-09-14

`main` was promoted at #147; `dev` is #149 and #150 ahead. Tag `v0.1.0` is at the first merge.
Offline suite: 278 passed, 17 skipped.
Actions was off until the release; the suite, the README block check and `npm run build` were run
locally at each merge.

**Landed 2026-09-14, one PR each, onto `dev`.**

- Site SEO and LLM readers: `robots.txt`, `sitemap.xml` with the eleven pages, `llms.txt` from the
  docs list, on the pattern of sg-groundtruth. A `Head` component on every page: title, description,
  canonical, Open Graph and Twitter tags, one share card at `media/og.png`, 1200 by 630, composed
  from the site's font and the SG Publish node picture. The landing title reads "SG ComfyUI: Flow
  Production Tracking for ComfyUI".
- #153, #148 Kevin's brother: dark scheme only; the hero copy left and the clip right; one box style;
  `Clip` takes `control` and `frame` props.
- #150 Every document says which install an instruction applies to. AGENTS.md opens with a
  table of what the Registry pack has and what only the checkout has, and an "also needs" column
  on the procedures: `inspect-site` and `task` need the `sg-groundtruth` checkout. INSTALL.md, the
  three other commands, the agent, install and profile docs pages follow.
- #149 `GET /sg/paths` answers where the running ComfyUI reads the profile from and the directory
  Settings writes to. `/inspect-site` asks it for the `--out` path. `tools/doctor.py` says which
  path each route reads. Measured in ComfyUI Manager's code: a Registry update deletes only the
  files the previous archive shipped (`cnr_switch_version_instant`, `glob/manager_core.py`), so a
  profile in the pack directory survives one. Six tests.
- #147 Issue forms: Bug (install route, versions, what happened as the panel reads it) and Feature
  (what you need, where it fits). Labels `feature` and `user request` created on the repo.
- #146, #145, #144 README Install: "1. From the Registry" and "2. From the repo", each opening with
  why to pick it. The landing page's Install is the requirements, three sentences pointing at the
  docs, and two agent prompts, one per route. The install docs page reads "Two ways to install".
  The footer names the Registry entry and links to its page.
- #143, #142 `PublisherId` `ksallee`; `.comfyignore` leaves every tool but `doctor.py`, RELEASE.md
  and `LAYOUT_API.md` out of the archive.
- #141 `pages.yml` removed.
- #140 `site/vercel.json`: Git deployments off for every branch but `main`.
- #139, #138, #137 RELEASE.md and CLAUDE.md's Process section; the SG Publish Info tab retaken.
- #136 `LAYOUT_API.md` as reference prose.
- #133 No em dash in a runtime string. The source label separator is a middle dot
  (`Rendered Image · sh010_v001.mov, uploaded file`), the clip sentence takes a comma
  (`240 frames at 24 fps, encoded by ComfyUI`), an instrumented node is titled
  `SG Publish: <name>`. README's What's next reads "Publishing from a Windows machine is
  untested. You can contribute." and the site's copy of the block follows.
- #134 The two comment lines in `pyproject.toml` and one in `tests.yml`.
- #135 SG Publish takes its three path templates as advanced inputs: `sequence_path`,
  `still_path`, `movie_path`, appended after `format`. Empty is the template under Settings, drawn
  greyed inside the field; brace completion with a Default row; `sequence.plan` takes the node's
  three and the run and the preview call it the same way. Ten SG Publish nodes across the shipped
  graphs gained three values. The SG Publish Info tab capture retaken at 780 px, 1560 by 2606,
  in `docs/images` and `site/static/media`.
- #136 `LAYOUT_API.md` as reference prose, 1,858 words to 1,749, names checked against the three
  editor files. Its Exports table lists what it listed before; `textRows`, `setPlaceholder`,
  `templateCompletion`, `styleOnce`, `esc`, `rgbParts` and `rgbCss` are exported and not in it.

---

## State, end of 2026-09-11

`dev` has everything below. Kevin's QA of #126 passed on his own ComfyUI. `main` is untouched since
#80. Offline suite: 267 passed, 17 skipped. GitHub Actions is off at the repository level, so no
check ran on the day's PRs; the suite and `npm run build` were run locally at each merge.

**Landed 2026-09-11: #126 onto `dev`, assembled from #127 to #130 and direct commits, then #131.**

- A bare linked field in a template, `{sg_task.Task.step}`, resolves to the link's name (probe 003:
  an entity field is answered under `relationships`).
- Sync from SG calls `POST /sg/sync`, which drops every cached site read (`site.forget()` with no
  prefix). A Task or Step edited on the site is read again rather than served for up to 600 s.
- The version name in the readout is selectable, and a click copies it.
- An empty root name or version name shows the Settings template greyed inside the field. The
  frontend drops `placeholder` from a single-line STRING spec at build, so the editor sets the input's
  own attribute after each preview (`setPlaceholder`). `nodeElement` finds the node by the
  `data-node-id` Nodes 2.0 stamps: the node keeps a detached copy of a rebuilt DOM widget.
- Typing `{` in a template field, on the node and in the four Settings rows, opens a completion:
  the documented tokens (`naming.TOKENS`, served by `/sg/tokens`), then a linked type's own fields
  from `/sg/schema_fields` (one schema read per type, cached, probe 002), two hops, single `entity`
  fields only. `{entity}` descends into the picked link's type, else the profile's, else the types
  the project's Versions link to, offered as rows. A Default row, always last, writes the Settings
  template into the field. `/sg/preview_code` returns `settings`, the two templates in force.
- Fill from SG defaults is gone: the button, `/sg/node_defaults`, the clip, the docs.
- A `mask` input on SG Publish, appended after the widgets. Frames are written RGBA, alpha
  `1 - mask`, in all three formats. One mask spreads over a batch; a size mismatch is refused with
  both sizes. The review still keeps the alpha. A mask with `video` alone is refused.
- SG Load declares `OUTPUT_TOOLTIPS`, one sentence per output, read by the Info tab.
- The Info tab of each node captured at 780 px (`tools/drive_info_tab.js`), in the README and on the
  site. The root name and version name tooltips shortened to three lines at that width.
- Every capture showing SG Publish retaken: two clips, eight stills, the hero. `08_publish_mask` is
  new: a mask SG Load read, inverted, published as the frames' alpha. Load, Settings and Site Setup
  captures kept.
- The site's header bar and page titles read SG ComfyUI. The hero and the footer keep the full name.
- #131 A still takes its own path template, `published_files.still_path_template`, default
  `{entity}/{root_name}/{version_name}{ext}`, beside the movie. A Still path row in Settings. Before
  a run the readout shows the frames path and the still path, since the count is settled by the run;
  after it, the one written. A still's files row after a run reads as one frame, not as a clip.

**Landed 2026-09-10, one PR each.**

- #97 `taste-skill` and `minimalist-skill` copied verbatim into `.claude/skills/`, pinned to one
  commit, excluded from the Registry archive. AGENTS.md names the skill the launch page is written
  under and the four overrides.
- #98 SG Load outputs reordered: `image`, `video`, `mask`, `version_id`, `code`, `colour_space`.
  Eleven Load nodes in ten shipped graphs rewritten; one link remapped. `tests/test_nodes.py` pins
  the order and checks each graph.
- #99 The pre-run panel names no client. After a Run the row reads the client the Run recorded.
  Read-only and unmounted storage roots refuse before the Run with the same sentence the Run uses,
  measured through a disk image.
- #100 `drive_load_shot.js` closes the run toast. `drive_movie_budget.js` answers its routes for the
  project the picker loaded.
- #101, #107, #108 CLAUDE.md: the Writing rule and its banned list.
- #102 README, INSTALL.md, AGENTS.md as reference prose. README 3,567 words to 1,313.
- #103 `tools/capture.py`: one command per clip, a CDP screencast at device scale 2, MP4, WebM and
  animated WebP. The harness stops its instance on every exit path, picks a random high port and
  refuses one it did not spawn.
- #104 DESIGN.md and every docstring and comment under `src/` and `tests/` as reference prose. No
  code line changed.
- #105 README pictures: the example graph's top row as the hero (`tools/drive_hero_shot.js`), SG
  Publish after a run, SG Load on an EXR Version.
- #106 `task` and `status` are search pickers. Nodes 2.0 builds a dropdown from the node definition
  once, so a list fetched later never reached it. Task rows show the pipeline step. Status rows keep
  the site's icon and colour (recipe 010).
- #109 `carry`, `hold` and the other banned words gone from docs, `src` and `tests`. The README media
  claim: a Version has one uploaded media file (probe 022); `sg_path_to_frames` and
  `sg_path_to_movie` are path references; a sequence registers as a PublishedFile linked to the Version.
- #111 `tools/` as reference prose: drive headers, harness docstrings, the experiment notes (10,969 words to 8,480).
- #113 The launch page under `site/`: SvelteKit 2.70 static, fourteen sections, nine docs pages, five
  clips, Geist self-hosted, no analytics. `site.yml` checks the four README blocks and builds on every
  push. `pages.yml` deploys to `gh-pages` by hand or on a push to `main`. Fourteen captures in
  `~/Desktop/sg-comfyui-site-2026-09-10/`.

**Sandbox project 1180.** Version 31995 keeps its row (drives pin it); its lineage is cleared.
Retired: five unlinked probe rows, 32001 (Windows path notation from a mac publish), every Version
the drives of the 10th created (32037 to 32049), and the day's: 32070 to 32074 with PublishedFiles
7065 to 7068. Their frames and folders under `/Volumes/FPT/sbx_0020` are deleted.

**Machine state, not in git.** ComfyUI 0.34.0 runs from `~/dev/ComfyUI` on 8188.
`~/dev/ComfyUI/custom_nodes/sg-comfyui` links here. Review captures: `~/Desktop/sg-comfyui-2026-09-11-site/`,
thirteen files in page order; older folders under `~/Desktop/sg-screenshots-archive/`.

---

## Decisions, 2026-09-14, with Kevin

- **Two installs, one reason each.** The Registry to use the nodes: Manager updates the pack,
  Settings and the profile keep the configuration. The repo to change the nodes: tests, harness,
  history, and `/inspect-site`, which needs the `sg-groundtruth` checkout beside it.
  Configuration is not a reason to pick the repo.
- **The Registry display name stays "Flow Production Tracking"**: it is what a Registry or Manager
  search reads. SG is the short name on the node and in the editor.
- **Vercel builds production only.** No preview deployment for any branch, for the monthly quota.
- **Issues have forms and labels**: Bug, Feature; `bug`, `feature`, `user request`.
- **The launch page is Kevin's brother's**, from `main`, which is kept level with `dev` when Kevin
  says promote.
- **The three path templates are inputs on SG Publish**, advanced, empty meaning Settings, the
  Settings template as the placeholder, on the pattern of root name and version name. Storage,
  operating system, the two path-field toggles and review movie stay in Settings only.
- **The readout keeps both the frames path and the still path before a Run.** The labels stay.
- **Windows** is listed as untested with an invitation to contribute, not as a feature.
- **No em dash in a runtime string.** The source label separator is a middle dot.
- **Merging onto `dev` is authorized in the session; `main` is QA-gated and human-gated** unless
  Kevin says otherwise in the session. Before the repo was public, on 2026-09-14, `main` was
  granted too, for the release.
- **The Registry is the last step**, after the release, the public repo, the launch page and the
  corpus.

## Decisions, 2026-09-11, with Kevin

- **A still takes a path template of its own**, `published_files.still_path_template`, default
  `{entity}/{root_name}/{version_name}{ext}`: a batch of one frame is one file, written beside the
  folder a sequence takes.
- **Sync from SG drops the site cache.** The button's name is its promise.
- **Empty template fields show the Settings template as a placeholder**, the template alone, no
  suffix. The tooltip and the docs say where it comes from.
- **Brace completion on template fields**, on the pattern of `~/dev/sg-widgets` (`pickers.ts`,
  `picker-keys.ts`, the picker contract): hop by hop from the schema, single `entity` fields only,
  Default row always listed. The root list is what exists before the Version does: the link, the
  Task, the project, the number. Version fields are not offered.
- **`{sg_task.Task.step}` is the step token**, not `{sg_task.Task.step.Step.code}`: shorter, same
  result.
- **Fill from SG defaults is removed.** The placeholder and the Default row replace it for the
  templates; status, Create Published Files and colour space are the node's defaults on creation.
- **A `mask` input on SG Publish is in.** Frames only. A clip with alpha is a re-encode and is not
  planned.
- **Tooltips fit four lines** in the Info tab at 780 px. The two long ones were shortened.
- **The site's header reads SG ComfyUI.** The hero and the footer keep the full name.
- **GitHub Actions stays off** until the repo is public: the private repo's runs used up the monthly
  minutes. Tests and the site build run locally before a PR is called ready.
- **The launch page goes to Vercel**, after the public release, not to GitHub Pages.

---

## Decisions, 2026-09-10, with Kevin

- **Load outputs**: media first. The order is frozen from the first release, like widgets.
- **Shipped Load nodes keep link `(none)`.**
- **Release route**: GitHub release from `main` first. The Registry later, when Kevin does the
  mechanics below.
- **`sg-groundtruth` 0.1.3 stays the floor.** This repo imports `FPT`, `FPTError`, `launcher` and
  `env.load`, all in 0.1.3. The floor moves only when a change here needs a newer client.
- **Clips, not stills, for the page and for posts.** MP4 for LinkedIn and the forum, MP4 and WebM
  for the page, animated WebP for loops. Never GIF. Pacing: stepped scrolling, a settle after each
  click, visible pointer travel, typing at normal speed.
- **Writing**: reference prose, one fact once, the banned list in CLAUDE.md. Applies to every file
  and to messages to Kevin.
- **Process**: every PR merges onto `dev` on CI green. Kevin QAs on `dev`. Each parallel agent works
  in its own git worktree.

## Decisions, 2026-09-09, with Kevin

**Formats.** ComfyUI's IMAGE is a float32 tensor with no file behind it, so a still is encoded
before upload, unlike a file-backed VIDEO. The encoder is ComfyUI's, and the operator picks the
format on the node. EXR pixels are written unchanged and the declared colour space is the record.
Converting to scene-linear is a feature to ask about. Review media stays 8-bit. SG Load decodes with
ComfyUI's decoder and reports the format before a run. Alpha becomes a `mask` output on ComfyUI's
convention. A `mask` input on SG Publish waits for feedback. ComfyUI floor 0.34.0, which has the
encoder and the PyAV decode path.

**Provenance.** The nine fields are the first release's answer. With none of them the description
records the note, a blank line, then one line per fact, lineage included, and the nodes say nothing
about creating fields. Settings and the docs own the fields: the SG Site Setup group, and the command
for farms and checkouts. Mapping to a studio's own field works but is not a release feature.

**`{output}` is gone.** Root name is the stream.

**A failed publish leaves its copies and names them.** Files are copied, never moved. A re-run
overwrites the same paths.

**Docs.** README for what a person decides, INSTALL.md for everything with a path in it, AGENTS.md
as a pointer any harness can follow, `tools/doctor.py` as the offline check. `.claude/settings.json`'s
deny on `.env.local` ships. Version stays 0.1.0.

---

## After the Registry

The two items under "Next session".

**Feedback list at launch**, in README "What's next" and at the end of every post: registering files
another node wrote (Save Image (Advanced), OCIO Write); publishing with no shared storage, the
sequence as a zip; publishing on someone's behalf and the artist on a farm; newest per stream; any
Version field on the node in one line; a colour-managed template; publishing from a Windows machine, untested.

---

## Open, and who decides

| question | who |
|---|---|
| Release date | Kevin |
| `PublisherId`, `Icon`, `Banner` | Kevin, Registry day |
| Artist attribution on the script-key path: `sudo_as_login` is wired in `credentials.client`; the fallback chain and an `artist` widget are not | after release |
| `data_type -> widget` so any Version field is one line | after release |
| OCIO: `/track-workflow`'s three questions, a `10_` template, registering `OCIO Write`'s files | after release |
| Upload mode for PublishedFile (zip for a sequence); the read side exists | after release |
| Newest per stream by default | after release |
| sg-groundtruth #48: the text search's page cap and matching rules, which `site.text_search` codes against with a client-side cap of 25 | Kevin, corpus |
| Two corpus gaps: whether a `_search` body naming an unknown field behaves like `?fields` (probe 004 does not say), and PublishedFile's own status list (probe 009 measures Version and Task only) | corpus |

---

## Measured

Filled in by the verification passes of 2026-09-09. Each line is a run, the Version or the sentence,
and what was read back.

**SG Publish, from an isolated ComfyUI on this checkout, project 1180.**

- `register_movie` on the two-input node: Version 31993, PublishedFiles 7011 (Rendered Image) and
  7012 (Movie), `path_cache` on both, `sg_path_to_frames` and `sg_path_to_movie` written, the mp4
  beside the frame folder. A re-run with unchanged inputs is cached by ComfyUI, and the panel
  reports the cache.
- The trim guard: a clip sliced to 0.8 s publishes as Version 31996, "20 frames at 25 fps, encoded by
  ComfyUI", the upload decoding as 20 frames. The control with the trim bypassed, Version 31997,
  reads "the source file, uploaded unchanged" and the upload's sha1 equals the file in `input/`.
- A refusal at staging leaves no Version: a storage the site lacks is refused before
  `create_version`, nothing on disk. The unmounted and read-only sentences were exercised through
  `sequence.check_root` directly; `/Volumes/FPT` is a plain directory on this machine, not a mount,
  so neither state can be produced live here without root.
- The batch budget: Version 31998, 24 frames of 1280x720 as 16-bit PNG, PublishedFile 7016; SG Load
  with `frame_count` 0 under a 0.05 GiB budget refuses naming the four frames that fit, and ComfyUI
  does not crash.
- Windows notation: Version 32000, PublishedFiles 7017 and 7018; `sg_path_to_frames` reads
  `\\fpt\jobs\sh010\...\verify_pub_windows_v001.%04d.png`, backslashes after the root only, the
  frame token intact; `local_path_mac` still the path on disk and the server filled
  `local_path_windows` itself.
- A single registered image: Version 32002, PublishedFile 7021, type Image, "1 frame" in the log.
  The path was registered as a `%04d` pattern that does not exist on disk; fixed after the run.
- Provenance with every concept mapped to a field the site lacks: Version 32003, the note, a blank
  line, then the facts including `generated from: Version 32002`; mode `description`: Version 32005
  with the full prompt. Nothing about fields in the log or on the panel.
- Formats: Version 32006 16-bit PNG (PublishedFile 7023, `rgb48be`, 13107/26214/39321 for
  0.2/0.4/0.6); Version 32007 EXR (PublishedFile 7024, `gbrpf32le`, the tensor unconverted, the
  description reading `colour space: ACEScg (declared by the publisher, not converted)`).
- Read back through ComfyUI's decoder, a 16-bit PNG comes back within 5/65535 of what was written;
  an EXR comes back exact.

Found by that pass and fixed the same day: the single-still path; the run log cleared from the panel
1.2 s after a publish; a pinned Load hiding the budget refusal; a budget under 0.1 GiB printing as
0.0; an unresolvable storage reading VALID before the Run; "1 frames" on the panel; dead
strike-through code. Left: the pre-Run panel names `comfyui-frontend` whatever client will submit.

**SG Load, the templates and `/track-workflow`, from a second isolated instance.**

- 16-bit PNG (Version 31991) and EXR (31992) read back bit-exact through Save Image (Advanced) and
  ComfyUI's decoder; the 16-bit still decodes to 12,329 distinct values where an 8-bit path gives
  256. The panel reads `16-bit PNG, RGB, 512x512, 1 frame.` and `32-bit float EXR, ...`. An RGBA
  publish (31995) comes back with a 512x512 mask; the others give the 64x64 zero mask.
- `00_example` run node by node: Version 31999 (the still) and 32001 (24 frames and the mp4,
  PublishedFiles 7019 and 7020, first and last frame 1 and 24), both loaded back, the `video`
  output reaching Save Video. `01_concept_and_style`: 32008 and 32009. `02_style_from_a_reference`:
  32010 with `sg_ai_generated_from` set to the two Versions 01 made.
- The movie budget: with 0.05 GiB an uploaded mp4 is refused at frame 8 of 24, naming the seven
  that fit; the clip was not decoded in full and ComfyUI did not crash.
- An `upload` PublishedFile (7022, created by probe 013's four calls on 31995) downloads and
  decodes bit-exact, alpha intact, and the panel names it as an upload.
- `/track-workflow` on `video_ltx2_i2v`, a template with a 41-node subgraph: the stream is tapped
  at the subgraph's new output, SG Publish is added at the top level, `smoke.py` reports 13 widgets
  over the copy, the original is untouched.
- A Version that does not exist and one with no media each refuse with a sentence; a thumbnail-only
  Version (32004) loads its 480x480 preview.

Found by that pass and fixed the same day: a Load result cached by node id and credited to a
different graph's node (Version 31995 got a lineage from another graph; the fingerprint of the Load
node now has to match); provenance written to the description never read back; the pre-run panel
silent about the budget for a movie; the sentences for a missing Version, a Version with nothing
published, a thumbnail fallback and an upload row; "1 frames".

**Retired since:** 32001 (Windows path notation, the other pass was editing `profile.local.json`
at that minute). 32008 and 32009 differ in provenance treatment for the same reason; do not cite them.

**For Kevin's checkpoint, not a defect:** the SG Load nodes in the shipped graphs have link
`(none)`, so `name_contains` searches the project and can resolve to another entity's stream. Run on
a freshly opened `00_example` fails on both Loads and publishes nothing until a link is picked. The
template note states this.

---

## Facts worth not re-deriving

- **ComfyUI 0.34.0 decodes through PyAV into float32** (`nodes.py`, `LoadImage`, via
  `VideoFromFile.get_components()`) and **Save Image (Advanced)** writes 16-bit PNG and 32-bit float
  EXR (`comfy_extras/nodes_images.py`, `_encode_image`). Measured here: a 16-bit greyscale gradient
  decodes to 256 levels through core and to 2 through Pillow's `convert("RGB")`; Pillow cannot open
  the EXR. Core's Load Image file picker does not list `.exr`.
- **`get_components()` has no incremental form.** A movie decoded through it is decoded in full, so
  the node keeps its own frame-by-frame PyAV loop for movies, in core's pixel-format rule, and the
  budget is checked as the batch grows.
- **`frame` on the Load node is a frame number, not a position.** Both `frame` 0 and `frame_count`
  0 mean "wherever it starts" and "to the end"; out of range is refused with the range that exists.
  The numbers come off disk. `sg_first_frame`/`sg_last_frame` are not kept in sync with the files.
- **A widget's declared default decides what every graph saved before that widget existed does.** A
  graph with fewer values than declared loads the missing widget at the declared default. That is
  why `format` defaults to 8-bit PNG and every shipped graph writes it anyway.
- **`comfy node publish` zips every git-tracked file** minus `.comfyignore` (gitignore syntax);
  `[tool.comfy].includes` adds a directory even if ignored; with no git, every file. Prove the
  archive with `comfy node pack` and `unzip -l`.
- ComfyUI scans five folder names for templates; `example_workflows` is the one this repo uses
  (`app/custom_node_manager.py:94`). The templates collection label and the node footer badge are
  both the `custom_nodes` directory name; neither reads `DisplayName`.
- `INPUT_TYPES` is re-evaluated on every `/object_info` request, so a profile edit is read on a
  browser refresh; a code change needs a ComfyUI restart, and so does a route.
- ComfyUI writes user files with `os.replace`, so a symlink into this repo is replaced, not written
  through.
- `env.load` layers `.env.local` over `os.environ`, so `FPT_API_*` can come from the launch
  environment.
- `VideoFromFile.get_stream_source()` returns the path of the **untrimmed** source even for a
  trimmed or cropped clip; `movie.source_file` compares dimensions and duration against a plain `VideoFromFile`
  and falls back to encoding when they differ.
- `save_to`'s `color_space` accepts only `sRGB`, `HDR` and `HDR PQ`, so the freeform `colour_space`
  widget is not passed to it; it stays a declaration on the record.
- `qa_node.py --start` picks a random high port and exits unless the pid on it is the one it spawned.
  `--keep` prints the port and base directory. Loading a graph over the harness's modified default
  workflow is fine; clicking a generic Close button closes the workflow tab and empties the graph.
- **Nodes 2.0 builds a combo from the node definition once.** A list written to `options.values`
  later never reaches it. A widget whose list depends on another widget is drawn with `searchPicker`.
- **Parallel agents get one git worktree each.** A worktree has no `.env.local` and no
  `profile.local.json`; run the harness from it with `--repo /Users/salleek/dev/sg-comfyui`.
- `hdiutil create` and `hdiutil attach [-readonly]` produce a real mount without root, for the
  read-only and unmounted storage-root states.
- `tools/smoke.py` and `tools/qa_node.py --repo <checkout>` need `.env.local` and `profile.local.json`
  at that checkout's root; a worktree has neither. Without the profile the isolated instance registers
  no nodes at all.
- The repo-root `__init__.py` is ComfyUI's entry point; pytest would collect it as a package, so
  `tests/conftest.py` stands a stub in its place.
- `OCIOWrite` is `OUTPUT_NODE = True` and returns a `STRING` path: the file for a still, the movie
  for a video, the first frame for a sequence, never a pattern; it also writes a `.json` sidecar and a
  `.wav` beside a sequence with audio. `OCIO Read` returns a native `VIDEO` on slot 4.
- The `sg_groundtruth` surface this repo uses is `FPT`, `FPTError` and `env.load`; nothing imported
  touches the corpus.
- **`status: "(none)"` does not mean no status.** The node sends no `sg_status_list`, so the site
  applies the field's default and the Version comes back `rev`, Pending Review.
- The site's own transcode is never read by SG Load: it is derived from the upload, lags it, and can
  describe a file that was replaced.
- **A PublishedFile's stock `path` field accepts the three-call upload** (probe 013's flow at
  `/entity/published_files/{id}/path/_upload`); `link_type` reads `upload`, `content_type` is set by
  the server, and the Attachment id is what persists. `sg_uploaded_file` is a custom field and is not
  usable. `visible.editable` in `/schema/<Type>/fields` separates stock fields from custom ones.
