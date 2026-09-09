# Release plan

Written 2026-09-09 to close a working session and open the next one cold. Everything decided is here
with its reasoning; everything still open is marked and names who decides.

Read `CLAUDE.md`, then this, then `DESIGN.md`. The operator's documents are `README.md`, `INSTALL.md`
and `AGENTS.md`; nothing an operator needs is in here.

---

## State, end of 2026-09-09

`dev` carries everything below, squash-merged, CI green on Linux, macOS and Windows. `main` is
untouched since #80 and is promoted by PR, which is Kevin's.

**Landed today, one PR each.**

- #81 Install docs for humans and agents: README rewritten around a first run, `INSTALL.md` (where
  every local file lives per install type, the CLIs from a Registry install, the profile on one
  page, troubleshooting), `AGENTS.md`, `tools/doctor.py`. `COLD_START.md` deleted; its two durable
  facts are lines in DESIGN.md. `requires-comfyui = "0.34.0"`.
- #82 Offline test suite and CI: `tests/`, a three-line torch stub, an `os` matrix, a lint job, a
  manual smoke job that says where to run it. `.comfyignore` keeps tests, experiments, fixtures and
  a future `site/` out of the Registry archive.
- #84 Frontend: a sequence guard on every project switch; an error answer keeps the saved
  link/task/status and puts the sentence on the panel; one `call()` that turns a 404 into "restart
  ComfyUI"; run listeners removed with the node; the Nodes 2.0 notice names the real setting;
  "Fill from SG defaults" is the button. Seven headless drives under `tools/` prove each one.
- #83 SG Load reads with ComfyUI's decoder: 16-bit PNG and EXR at full precision, a `mask` output
  appended last, the panel's format line, `upload` PublishedFiles visible and readable, newest by
  version number on a site with no `code_regex`, `frame_count` 0 in the signature too. A movie
  still decodes frame by frame and stops at the budget.
- #85 CLAUDE.md matches what runs.
- #87 Settings, then SG, SG Site Setup: "N of 9 provenance fields exist on this site" and a Create
  button, sorted last. Five states in `~/Desktop/sg-site-setup-screenshots/`.
- #86 SG Publish: a `format` widget appended last (8-bit PNG, 16-bit PNG, EXR 32-bit float) written
  by ComfyUI's encoder; provenance typed where the schema has the field and one description line
  per fact otherwise; the setup commands import no torch; `{output}` gone; `version_name.py`;
  `site.context()` and `sequence.plan()` replace five copies of one resolution; a failed publish
  names the files it already wrote; the caches a publish invalidates are the ones it means to.
  Versions 31991 (16-bit PNG, PublishedFile 7009) and 31992 (EXR, PublishedFile 7010) measured.
- #88 Leftovers: the archived experiment graphs carry the 13th value; `--root-name`.

**Live verification, run from this checkout against the sandbox** — see "Measured" below; the
section is filled in as the two verification passes report.

**Machine state, not in git.** ComfyUI runs from `~/dev/ComfyUI` (0.34.0) on 8188 and needs a
restart to load today's routes. `~/dev/ComfyUI/custom_nodes/sg-comfyui` links here. The stale demo
copies in `~/dev/ComfyUI/user/default/workflows/` are gone. Sandbox project 1180 is
**sg-comfyui Sandbox**.

---

## Decisions, 2026-09-09, with Kevin

**Formats.** ComfyUI's IMAGE is a float32 tensor with no file behind it, so a still cannot pass
through the way a file-backed VIDEO does: someone encodes it. That someone is ComfyUI's own encoder,
never ours, and the operator picks the format on the node. EXR pixels are written through unchanged
and the declared colour space is the record; converting to scene-linear is a feature to ask about.
Review media stays 8-bit. SG Load decodes with ComfyUI's decoder and reports the format before a run;
alpha becomes a `mask` output on ComfyUI's convention. A `mask` input on SG Publish waits for feedback.
ComfyUI floor 0.34.0, where the encoder and the PyAV decode path live.

**Provenance.** Our nine fields are the first release's answer. With none of them the description
carries the note, a blank line, then one line per fact, lineage included, and the nodes say nothing
about creating fields. Settings and the docs own the fields: the SG Site Setup group, and the command
for farms and checkouts. Mapping to a studio's own field works since #86 but is not a release feature.

**`{output}` is gone.** Root name is the stream. Nothing ever supplied a value for the token and the
Settings preview faked one.

**A failed publish leaves its copies and names them.** Copy never move; a re-run overwrites the same
paths.

**Docs.** README for what a person decides, INSTALL.md for everything with a path in it, AGENTS.md
as a pointer any harness can follow, `tools/doctor.py` as the offline check. `.claude/settings.json`'s
deny on `.env.local` ships. Version stays 0.1.0.

**Process.** PRs onto `dev`, merged by the agent as they land; Kevin's checkpoints are node
behaviour and template changes, batched with screenshots. `dev` to `main` is Kevin's.

---

## Before the first release

1. **Kevin's checkpoint** on today's operator-facing changes, from the screenshot folders and his own
   ComfyUI after a restart: the `format` widget in the fold, the `mask` output, the Load panel's
   format line, the Settings group, "Fill from SG defaults", the frontend error sentences.
2. **Verification findings** below, each either fixed or recorded as a limit.
3. **Registry mechanics.** `PublisherId`, `Icon` (≤400² square), `Banner` (21:9) in `pyproject.toml`;
   `comfy node pack` and `unzip -l` to prove the archive holds `src`, `web`, `example_workflows`,
   the docs, `pyproject.toml`, `requirements.txt` and nothing else; repo public; tag on `main`;
   `publish-node-action` on a `pyproject.toml` change.
4. **The launch page**, after the captures are final: `tools/qa_node.py --frames DIR --fps 12
   --scale 2` (CDP screencast at device scale 2; Playwright's own recorder is 1 Mbit/s VP8 and
   too soft for UI text), ffmpeg to MP4 and WebM, animated WebP for short loops, never GIF. SvelteKit
   2.70 with `adapter-static` on GitHub Pages from a `gh-pages` branch, GSAP ScrollTrigger (free for
   commercial use since 2025) for the one pinned section, CSS scroll timelines as enhancement,
   reduced motion honoured, no analytics. Hand-written docs pages under `site/`, with the four blocks
   that must match the README diffed in CI. Eight capture sequences; `drive_ui_tour.js` and
   `drive_attach_tour.js` already exist. The full proposal is the launch-page report in the session
   scratchpad; the section list is fourteen sections from hero to footer and a nine-page docs sitemap.

**Feedback list at launch**, in README "What's next, tell us" and at the end of every post: a `mask`
input and RGBA publishes; registering files another node wrote (Save Image (Advanced), OCIO Write);
publishing with no shared storage, the sequence as a zip; publishing on someone's behalf and the artist
on a farm; updating the Task status on publish; newest per stream; any Version field on the node in
one line; a colour-managed template; Windows as a first-class publisher.

---

## Open, and who decides

| question | who |
|---|---|
| Release date | Kevin |
| `PublisherId`, `Icon`, `Banner` | Kevin, release day |
| Registry and PyPI: does `sg-groundtruth` 0.1.3 stay the floor | Kevin |
| Artist attribution on the script-key path: `sudo_as_login` is wired in `credentials.client`; the fallback chain and an `artist` widget are not | after release |
| `data_type -> widget` so any Version field is one line | after release |
| OCIO: `/track-workflow`'s three questions, a `10_` template, registering `OCIO Write`'s files | after release |
| Upload mode for PublishedFile (zip for a sequence); the read side exists since #83 | after release |
| Newest per stream by default | after release |
| sg-groundtruth #48: the text search's page cap and matching rules, which `site.text_search` codes against with a client-side cap of 25 | Kevin, corpus |
| Two corpus gaps found today: whether a `_search` body naming an unknown field behaves like `?fields` (probe 004 does not say), and PublishedFile's own status list (probe 009 measures Version and Task only) | corpus |

---

## Measured

Filled in by the verification passes of 2026-09-09. Each line is a run, the Version or the sentence,
and what was read back.

**SG Publish, from an isolated ComfyUI on this checkout, project 1180.**

- `register_movie` on the two-input node: Version 31993, PublishedFiles 7011 (Rendered Image) and
  7012 (Movie), `path_cache` on both, `sg_path_to_frames` and `sg_path_to_movie` written, the mp4
  beside the frame folder. A re-run with unchanged inputs is cached by ComfyUI and the panel says so.
- The trim guard: a clip sliced to 0.8 s publishes as Version 31996, "20 frames at 25 fps, encoded by
  ComfyUI", the upload decoding as 20 frames. The control with the trim bypassed, Version 31997,
  reads "the source file, uploaded unchanged" and the upload's sha1 equals the file in `input/`.
- A refusal at staging leaves no Version: a storage the site lacks is refused before
  `create_version`, nothing on disk. The unmounted and read-only sentences were exercised through
  `sequence.check_root` directly; `/Volumes/FPT` is a plain directory on this machine, not a mount,
  so neither state can be produced live here without root.
- The batch budget: Version 31998, 24 frames of 1280x720 as 16-bit PNG, PublishedFile 7016; SG Load
  with `frame_count` 0 under a 0.05 GiB budget refuses naming the four frames that fit, and ComfyUI
  survives.
- Windows notation: Version 32000, PublishedFiles 7017 and 7018; `sg_path_to_frames` reads
  `\\fpt\jobs\sh010\...\verify_pub_windows_v001.%04d.png`, backslashes after the root only, the
  frame token intact; `local_path_mac` still the real path and the server filled
  `local_path_windows` itself.
- A single registered image: Version 32002, PublishedFile 7021, type Image, "1 frame" in the log.
  The path was registered as a `%04d` pattern that does not exist on disk; fixed after the run.
- Provenance with every concept mapped to a field the site lacks: Version 32003, the note, a blank
  line, then the facts including `generated from: Version 32002`; mode `description`: Version 32005
  with the full prompt. Nothing about fields in the log or on the panel.
- Formats: Version 32006 16-bit PNG (PublishedFile 7023, `rgb48be`, 13107/26214/39321 for
  0.2/0.4/0.6); Version 32007 EXR (PublishedFile 7024, `gbrpf32le`, the tensor unconverted, the
  description carrying `colour space: ACEScg (declared by the publisher, not converted)`).
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
  publish (31995) comes back with a real 512x512 mask; the others give the 64x64 zero mask.
- `00_example` run node by node: Version 31999 (the still) and 32001 (24 frames and the mp4,
  PublishedFiles 7019 and 7020, first and last frame 1 and 24), both loaded back, the `video`
  output reaching Save Video. `01_concept_and_style`: 32008 and 32009. `02_style_from_a_reference`:
  32010 with `sg_ai_generated_from` exactly the two Versions 01 made.
- The movie budget: with 0.05 GiB an uploaded mp4 is refused at frame 8 of 24, naming the seven
  that fit; the clip was not decoded whole and ComfyUI survived.
- An `upload` PublishedFile (7022, created by probe 013's four calls on 31995) downloads and
  decodes bit-exact, alpha intact, and the panel names it as an upload.
- `/track-workflow` on `video_ltx2_i2v`, a template with a 41-node subgraph: the stream is tapped
  at the subgraph's new output, SG Publish lands at the top level, `smoke.py` reports 13 widgets
  over the copy, the original is untouched.
- A Version that does not exist and one with no media each refuse with a sentence; a thumbnail-only
  Version (32004) loads its 480x480 preview.

Found by that pass and fixed the same day: a Load result cached by node id and credited to a
different graph's node (Version 31995 carried a lineage it never had; the fingerprint of the Load
node now has to match); provenance written to the description never read back; the pre-run panel
silent about the budget for a movie; the sentences for a missing Version, a Version with nothing
published, a thumbnail fallback and an upload row; "1 frames".

**Tainted by the two passes sharing one profile:** 32001's path fields are in Windows notation and
32008 and 32009 differ in provenance treatment, because the other pass was editing
`profile.local.json` at that minute. Neither is a defect; neither Version should be cited.

**For Kevin's checkpoint, not a defect:** the shipped SG Load nodes carry link `(none)`, so
`name_contains` searches the whole project and can resolve to another entity's stream, and Run on a
freshly opened `00_example` fails on both Loads and publishes nothing until a link is picked, which
the note says but a first click does not read.

---

## Facts worth not re-deriving

- **ComfyUI 0.34.0 decodes through PyAV into float32** (`nodes.py`, `LoadImage`, via
  `VideoFromFile.get_components()`) and **Save Image (Advanced)** writes 16-bit PNG and 32-bit float
  EXR (`comfy_extras/nodes_images.py`, `_encode_image`). Measured here: a 16-bit greyscale gradient
  decodes to 256 levels through core and to 2 through Pillow's `convert("RGB")`; Pillow cannot open
  the EXR. Core's Load Image file picker does not list `.exr`.
- **`get_components()` has no incremental form.** A movie decoded through it is decoded whole, so
  the node keeps its own frame-by-frame PyAV loop for movies, in core's pixel-format rule, and the
  budget is checked as the batch grows.
- **`frame` on the Load node is a frame number, not a position.** Both `frame` 0 and `frame_count`
  0 mean "wherever it starts" and "to the end"; out of range is refused with the range that exists.
  The numbers come off disk; `sg_first_frame`/`sg_last_frame` are a claim nothing keeps true.
- **A widget's declared default decides what every graph saved before that widget existed does.** A
  graph holding fewer values than declared loads the missing widget at the declared default. That is
  why `format` defaults to 8-bit PNG and every shipped graph carries it anyway.
- **`comfy node publish` zips every git-tracked file** minus `.comfyignore` (gitignore syntax);
  `[tool.comfy].includes` adds a directory even if ignored; no git means the whole tree. Prove the
  archive with `comfy node pack` and `unzip -l`.
- ComfyUI scans five folder names for templates; `example_workflows` is the blessed one
  (`app/custom_node_manager.py:94`). The templates collection label and the node footer badge are
  both the `custom_nodes` directory name; neither reads `DisplayName`.
- `INPUT_TYPES` is re-evaluated on every `/object_info` request, so a profile edit reaches the editor
  on a browser refresh; a code change needs a ComfyUI restart, and so does a route.
- ComfyUI writes user files with `os.replace`, so a symlink into this repo is replaced, not written
  through.
- `env.load` layers `.env.local` over `os.environ`, so `FPT_API_*` can come from the launch
  environment.
- `VideoFromFile.get_stream_source()` returns the **whole** source path even for a trimmed or
  cropped clip; `movie.source_file` compares dimensions and duration against a plain `VideoFromFile`
  and falls back to encoding when they differ.
- `save_to`'s `color_space` accepts only `sRGB`, `HDR` and `HDR PQ`, so the freeform `colour_space`
  widget is not passed to it; it stays a declaration on the record.
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
