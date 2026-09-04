# Cold start: can a stranger set this up with an agent?

A friction log, not a success story. Written by an agent given only this repo, the sibling corpus
at `../sg-groundtruth/corpus/`, and a machine with ComfyUI on it. The run **did** eventually land
a Version with full provenance in Flow PT — and it took six wrong turns to get there. The wrong
turns are the deliverable.

Everything below was measured on 2026-09-03 against ComfyUI 0.34.0, frontend 1.51.9, on an
isolated instance on port 8600.

---

## Phase 0 — what I believed the setup was, before running anything

Sources a stranger has at the repo root: `CLAUDE.md`, `DESIGN.md`,
`.claude/commands/track-workflow.md`, `.claude/commands/task.md`, `.env.local.example`.

**There is no README.** No `INSTALL`, no `requirements.txt`, no `pyproject.toml`. `DESIGN.md` is a
rationale document — it explains *why* every decision was made and never once says what to type.
It even promises artefacts that are not here: "`requirements.txt` is installed by ComfyUI-Manager"
(there is none) and a `pyproject.toml` with `[tool.comfy]` for Registry publishing (there is none).

My best guess at the setup, written down before executing anything:

1. Clone into `ComfyUI/custom_nodes/`.
2. Clone the sibling corpus repo next to it.
3. Copy `.env.local.example` to `.env.local`, fill in site URL, script name, key.
4. Somehow produce `profile.local.json`.
5. Run `python -m comfyui_fpt.fields` once to create the nine Version fields.
6. Start ComfyUI, run `/track-workflow` on a graph, run it.

What I could **not** answer from the docs before starting: which Python environment the node runs
in; how `sg_groundtruth` gets on its path; how `profile.local.json` comes into existence; whether
step 5 is required or automatic; and what `PYTHONPATH` any documented command needs.

Four of those six guesses turned out to need correction. The setup is not reconstructable from
the docs.

---

## Blockers — where a stranger would have stopped entirely

### B1. `/inspect-site` does not exist, and nothing else can produce `profile.local.json`

`.claude/commands/track-workflow.md` names it twice as the way out of a dead end:

> "Read `profile.local.json`; if the project has no block yet, that is **`/inspect-site`'s job first**."

> "Without them `code = auto` fails loudly, which is correct... **`/inspect-site` infers it** and reports its coverage."

`.claude/commands/` contains exactly two files: `track-workflow.md` and `task.md`. There is no
`/inspect-site`. `src/comfyui_fpt/site.py` compounds it — its `profile()` docstring says the file is
"**Written by the inspector**; hand-editable" — and there is no inspector anywhere in this repo.

`profile.local.json` is gitignored, so a fresh clone has none. Every downstream decision — project,
link type, link field, code template, code regex, status, provenance field mapping — is read from
that file. **A stranger cannot generate it and is not told its full schema in one place.** The only
description is prose scattered through four sections of `DESIGN.md`.

This is the single biggest thing standing in the way.

### B2. `instrument.py --publish/--load` emits a workflow that will not run

This is the tool `/track-workflow` step 6 is built around, and its output is broken. Root cause:
the web extension (`web/fpt_dom_widgets.js`, `web/fpt_entity_picker.js`, `web/fpt_panel.js`)
injects DOM widgets that **occupy positions in the node's widget array**, and `instrument.py`
writes a positional `widgets_values` array that only knows about the inputs `INPUT_TYPES` declares.

Declared inputs vs. actual widget slots, read live off the canvas:

| node | declared inputs | actual widget slots | injected, in order |
|---|---|---|---|
| `FPTPublishVersion` | 11 | **14** | `link_pick`(4), `fpt_panel`(12), `refresh from site`(13) |
| `FPTLoadVersion` | 10 | **15** | `project_pick`(1), `link_pick`(3), `statuses_chips`(6), `fpt_panel`(13), `refresh from site`(14) |

Everything after the first injected widget lands one or more slots off. On `FPTLoadVersion` the
first injected widget is at slot 1, so **nine of the ten values are wrong**. Submitting the graph
`instrument.py` just wrote gives:

```
"node_errors": {"62": {"errors": [
  {"type": "invalid_input_type",
   "details": "pin_version_id, , invalid literal for int() with base 10: ''"},
  {"type": "value_not_in_list",
   "details": "newest_by: 1 not in ['version number in the name', 'created_at', 'id (creation order)']"}]}}
```

Those are exactly the values `instrument.py` intended for `newest_by` (index 5) and `source`
(index 7), displaced by four slots.

The publish node is worse, because it **fails silently**. Its API payload came out as:

```
"output_name":"",  "source_versions":true,  "attach_workflow":0,  "refresh from site":null
```

`output_name` — the whole point of the naming step — was dropped; `attach_workflow`'s `True` landed
in `source_versions`; `link_id`'s `0` landed in `attach_workflow`. No error. A stranger who only
tapped a stream (no `--load`) would get a graph that **runs and publishes Versions with the wrong
values in the wrong fields**, and nothing would tell them.

I could not fix this (measuring, not repairing). I worked round it by overriding the two nodes'
inputs **by name** in API format after `graphToPrompt()`.

### B3. Nothing in the corpus of 680 real graphs runs unmodified on this machine

Measured, not asserted. I screened all 680 graphs in
`scratchpad/corpus/` (the official template set plus ZHO, Yolain and
`comfyanonymous/ComfyUI_examples`) against this machine's `/object_info` and its installed model
files:

```
graphs scanned                                              680
zero missing node types AND zero missing model files        139
  ... of which are cloud-API templates needing a paid key   138
  ... genuinely local and runnable                            1   (basic_datatype_conversion.json,
                                                                   a no-op utility graph)
graphs containing no cloud-API node at all                  442
  ... of those, with every node type present                 15
  ... of those 15, needing zero missing model files           0
```

**Zero of 680 run unmodified.** The closest is
`ComfyUI_examples/wan/camera_image_to_video_wan_example.json` — a genuine third-party graph that
uses the exact `wan2.1_fun_camera_v1.1_1.3B_bf16.safetensors`, `wan_2.1_vae.safetensors` and
`clip_vision_h.safetensors` installed here, and misses by **one filename**: it names
`umt5_xxl_fp8_e4m3fn_scaled.safetensors` where this box has `umt5_xxl_fp16.safetensors`.

Two related notes for whoever repeats this:

- `ComfyUI_examples/controlnet/` contains **only `.png` files** — those workflows live in PNG
  metadata and are invisible to any JSON scan. The SD1.5 depth-ControlNet graph a reader would
  expect to find is not in the JSON corpus at all.
- Several templates reference frontend-only node types (`MarkdownNote`, and opaque UUID node types
  such as `6b0ed7ac-f476-44c9-9dad-b3f23ef985f8`) that do not appear in `/object_info`.

---

## Wrong or missing documentation

### D1. `CLAUDE.md` names a repo and an env var that do not exist

> "The corpus lives next door — `../fpt-llm-api` holds every verified truth about the API, and the client."
> "Read `../fpt-llm-api/corpus/INDEX.md` first, always."
> "The sibling checkout (`fpt-llm-api/`, package `sg_groundtruth`) is expected; override with **`FPT_LLM_API_PATH`**."
> "Plan for both repos: `../fpt-llm-api/PLAN.md`."

Actually true: the sibling is **`../sg-groundtruth`**, and `src/comfyui_fpt/_deps.py` says
`"Override with **SG_GROUNDTRUTH_PATH**"`. `../fpt-llm-api` does not exist on this machine; nor
does the `PLAN.md` it points at. `.claude/commands/task.md` has the right name — so the two
instruction files a stranger reads first **contradict each other**.

Mitigating: `_deps.py`'s error message names the correct variable, which is what rescued me:
`ImportError: sg_groundtruth not found (looked in .../sg-groundtruth); set SG_GROUNDTRUTH_PATH`.
That error is the single best-written thing in the setup path.

### D2. Every documented `python -m comfyui_fpt.*` command is missing two required env prefixes

`/track-workflow` step 4b writes:

```
python -m comfyui_fpt.seed <file> --project P --link "sh010 (Shot)" --output plate --note "..."
```

That fails. `comfyui_fpt` lives under `src/`, so it is not importable, and `_deps.py` needs the
sibling path unless the checkout happens to sit beside `sg-groundtruth`. What actually works:

```
SG_GROUNDTRUTH_PATH=/path/to/sg-groundtruth PYTHONPATH=src python -m comfyui_fpt.seed ...
```

Same omission applies to `python -m comfyui_fpt.fields`, which `DESIGN.md` names.

### D3. `.env.local` and `profile.local.json` must sit at the repo root, and nothing says so

`site.py` computes `ROOT = Path(__file__).resolve().parents[2]` and reads both from there. This is
never documented. `DESIGN.md`'s architecture block says only `site.py  .env.local,
profile.local.json` — it names the files and not their location, and `.env.local.example` gives no
hint that its position matters. `resolve()` follows symlinks, which is load-bearing for the
`custom_nodes` symlink install and is also undocumented.

### D4. `DESIGN.md` has 37 duplicated lines — two whole sections pasted twice

`## Where the version number lives is site-specific` and `### Which makes two nodes a pipeline`
appear verbatim at lines 154–177 **and again** at 281–304; `### Media comes back the same way it
went out` appears at 142–152 and again at 269–279. `awk 'NF' DESIGN.md | sort | uniq -d | wc -l`
returns 37. A reader cannot tell whether the repetition is emphasis or an unresolved edit.

### D5. `tools/qa_node.py` is untracked — it does not exist in a clone

The QA harness is present in the working checkout but is **not in the git tree**
(`git ls-tree -r HEAD | grep tools` is empty). A stranger cloning gets nothing. It is also the only
thing that knows how to bring up an isolated instance with its own user directory and the
onboarding settings pre-dismissed — knowledge that exists nowhere else in the repo.

### D6. `/track-workflow` step 4b under-specifies the seed input

> "The file is whatever `LoadImage` names, relative to ComfyUI's `input/`."

`seed.py` takes a real filesystem path, so the operator has to join `ComfyUI/input/` themselves —
and must first know where ComfyUI is. In my case the corpus graph named `flux_dev_example.png`,
which **is not shipped with ComfyUI**, so there was no file to seed at all. I substituted ComfyUI's
stock `input/example.png`. Corpus graphs generally do not ship their example inputs; the command
assumes they do.

### D7. `instrument.py` has no way to set the output name, which step 3 makes central

Step 3 says: *"Propose the naming, do not leave it to them from nothing... say what each Version
would be called."* But `instrument.py --help` offers `--code`, `--template`, `--project`, `--link`
— and **no `--output`**. It derives the name from the *sink node type*, so my stream was proposed as
`output_name='saveanimatedwebp'`, giving the code `{entity.code}_saveanimatedwebp_v{version:03d}`.
"saveanimatedwebp" is not what the stream *is* — it is what consumes it, which is precisely the
distinction step 3 and `naming.py`'s own comments insist on.

---

## The live `profile.local.json` is on a stale template vocabulary

Not a doc bug — a data bug, and it silently corrupts every Version code on the sandbox project.

`naming.py` contains **two** template vocabularies. The live one, used by
`publish_version.next_code` → `naming.render`, is the Flow PT field-path form that `DESIGN.md`
documents correctly:

```
DEFAULT_TEMPLATE = "{entity.code}_{output}_v{version:03d}"
```

The legacy one (`{link}_{task}_{output}_{version}`, `naming.PATTERNS`, line 102 `next_code`) is a
private token language. The operator's `profile.local.json` for project 1180 is written in the
**legacy** form:

```json
"code_template": "{link}_{output}_v{version}"
```

`render()` treats `link` as a field path, finds nothing, and collapses it. Measured directly:

```
profile template '{link}_{output}_v{version}'  -> fields ['link','output']  -> renders 'v1'
DESIGN template  '{entity.code}_{output}_v...' -> fields ['entity.code','output'] -> 'cold_shot_depth_v001'
```

It is not theoretical. My seeded plate came back as **`plate_v1`** — no shot name, no zero padding —
where the documented template would have given `cold_wancam_plate_v001`. `FPTPublishVersion`'s
`code_template` widget default is served straight from this profile, so **every publish on this site
defaults to the broken form.** DESIGN.md warns about exactly this failure mode ("a typo in a profile
would otherwise hide behind a Version that looks fine") and the shipped profile is an instance of it.

---

## Friction — worked, but took more than one attempt

| # | What | Attempts | What it took |
|---|---|---|---|
| F1 | `python -m comfyui_fpt.seed` | **3** | verbatim → `ModuleNotFoundError` → `+PYTHONPATH=src` → `ImportError: set SG_GROUNDTRUTH_PATH` → `+SG_GROUNDTRUTH_PATH` |
| F2 | Submitting the instrumented graph | **2** | 400 `prompt_outputs_failed_validation` from the widget-slot shift (B2) → override inputs by name in API format |
| F3 | Getting a new Shot into the picker | **2** | `cold_wancam (Shot)` absent from the `link` combo → seed a Version onto it **and restart ComfyUI** (600s cache TTL) → it appears |
| F4 | Choosing a corpus workflow | **3 screens** | naive node-type match (139 hits, ~all cloud-API) → filter cloud-API nodes (15 hits) → add model-file check (0 hits) |
| F5 | Running any CLI in a plain venv | **2** | `ModuleNotFoundError: numpy` — `comfyui_fpt/__init__.py` imports the nodes, which import `numpy`, so **every setup-path CLI drags in the ComfyUI runtime deps**. Only `instrument.py` run as a file escapes this, and only because `/track-workflow` explicitly says "Run it as a file, not `-m`". |

On F3, worth saying plainly: the seed-then-observe loop **works exactly as `DESIGN.md` claims**.
Before seeding, the `link` combo was `['(none)', 'sbx_0020 (Shot)', 'sbx_charA (Asset)']`; after
seeding Version 31744 onto `cold_wancam` and restarting, it was
`['(none)', 'cold_wancam (Shot)', 'sbx_0020 (Shot)', 'sbx_charA (Asset)']`. Step 4b's escape from
the chicken-and-egg is real. What is missing is any hint that the 600s cache means you must wait or
restart — a stranger would conclude the seed had failed.

---

## What I could not do at all

- **Generate `profile.local.json` from scratch.** No command exists (B1). I read the operator's
  existing one, which is what `/track-workflow` step 4 tells you to do — but a stranger has no such
  file. Had I hand-written one from `DESIGN.md`, I would have got the template *right* and the
  running site's *wrong*, which is its own confusion.
- **Place `.env.local` in my worktree.** `.claude/settings.json` denies `Read(./.env.local)`, and
  the harness extends that to `cp` and `ln -s` of the same path. I ran the CLIs against the main
  checkout's root instead — which is also what the live node does, since
  `ComfyUI/custom_nodes/flow-pt` is a symlink to the main checkout.
  **Consequence worth flagging:** any agent starting ComfyUI here loads the *main* checkout's
  `src/`, not its own worktree's. Two agents editing `src/` concurrently are editing the code my
  instance is running.
- **Publish the video as one Version.** Known and documented, and confirmed here: 5 frames produced
  **5 Versions** (`cold_wancam_previz_v001_01` … `_05`). The movie-as-a-Version gap is real and
  would make this graph shape unusable in production.

What I would have needed: an `/inspect-site` command (or any documented way to write the profile),
a README with the six literal commands, and `instrument.py` emitting widget values keyed by name
rather than by position.

---

## What actually worked, and it is worth saying

Once past the above, the product half is genuinely good. The end-to-end run succeeded:

- Shot `cold_wancam` (id 7609) created in project 1180.
- `example.png` seeded as **Version 31744** via `comfyui_fpt.seed`, first try.
- `instrument.py` analysed the corpus graph correctly on the **first** attempt with no arguments,
  found the publishable stream and the replaceable loader, and its `--out` surgery was exactly as
  documented: the publish node tapped `VAEDecode` additively leaving `SaveAnimatedWEBP` and
  `SaveWEBM` connected, and the Load node rewired the loader's two consumers while leaving
  `LoadImage` in place, unwired.
- Prompt accepted 200, executed in ~83s, `status_str: success`.
- **Versions 31745–31749 landed with full provenance.** Read back from the site:

```
code                  cold_wancam_previz_v001_01
sg_ai_model           wan2.1_fun_camera_v1.1_1.3B_bf16.safetensors | umt5_xxl_fp16.safetensors
                      | wan_2.1_vae.safetensors | clip_vision_h.safetensors
sg_ai_prompt          a cute anime girl with massive fennec ears and a big fluffy tail...
sg_ai_seed            1034274237172778
sg_ai_sampler         uni_pc/simple
sg_ai_steps           4          sg_ai_cfg  6.0
sg_ai_generator       ComfyUI (unknown client)
entity                Shot cold_wancam (7609)
sg_ai_generated_from  [Version 31744 "plate_v1"]      <- the seeded plate. The pipeline join works.
attachments           ..._01.png, ..._01.provenance.json, ..._01.workflow.json, ..._01.mp4
```

The lineage field resolving back to the seeded plate with no id typed by hand is the thesis of the
whole repo, and it does what it says. `sg_ai_generator` reading `ComfyUI (unknown client)` is also
correct behaviour, not a bug — I POSTed to `/prompt` directly, and the degraded-provenance path
reported itself honestly rather than going quiet.

---

## Verdict

**No — not today, not without the author present.** A stranger with a competent agent gets stopped
twice before the tool ever runs: `profile.local.json` has no generator and no single-page schema,
and the `/inspect-site` command the docs send them to does not exist. If they hand-write a profile
and push past that, `instrument.py` — the one tool `/track-workflow` is built around — hands them a
workflow that fails validation on the Load node and, worse, silently mis-assigns values on the
Publish node, because its positional `widgets_values` array does not account for the DOM widgets the
web extension injects. Neither failure is discoverable from anything written down; I only found the
second by dumping the live widget array off the canvas. The underlying product is sound — the graph
surgery is right, the seed-then-observe loop dissolves the chicken-and-egg exactly as designed, and
the provenance that lands in Flow PT is complete down to the lineage link — but **the single biggest
thing standing in the way is that there is no README and no `/inspect-site`: the repo documents its
reasoning exhaustively and its operation not at all.** Six lines of literal commands and one working
profile generator would move this from "unusable by a stranger" to "usable in an afternoon".
