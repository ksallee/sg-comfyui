# 05 — Plate upres

> "Take the 480p generated section back up to plate resolution without it looking AI-smeared."

Generative work happens at model resolution. Delivery does not. This is the step that closes the gap,
and it is the terminal node of the chain: a delivery-res Version whose ancestry runs back through
paint-out and roto to the original plate.

`05_plate_upres.json` — open it in ComfyUI, or POST it as an API prompt.

## What it demonstrates

One 480p input, **two upres paths**, both landing on the same 1920x1080 delivery resolution, each
publishing its own Version. The contrast is the deliverable: a comp supervisor gets to compare a
route that cannot invent anything against a route that can, on the same frame, with both recorded.

It is also the case that proves provenance is **per branch, not per graph**. Both publish nodes sit
in one file and share one input, and each Version carries only what produced its own image: the
ESRGAN Version names its upscale model and nothing else — no seed, no sampler, no steps, no cfg —
because its branch has none of those things.

## The two paths

| | **esrgan** | **seedvr2** |
|---|---|---|
| model | RealESRGAN_x4plus, fixed 4x | SeedVR2 3B int8, one step |
| resize | after the model — 3328x1920 lanczos down to 1920x1080 | before the model — 832x480 lanczos up to 1920x1080, restored at that size |
| invents detail | no | yes |
| repeatable | bit-for-bit | seeded, so repeatable in practice |
| cost | seconds | a model load and a sampler step |

**Use ESRGAN when the answer has to be defensible.** It is a deterministic filter: same input, same
pixels, nothing in the output that was not in the input. When a comp supervisor asks "did the machine
put that there", the answer is no, and it stays no. This is the default for a delivery.

**Use SeedVR2 when the source is genuinely soft** and a clean upscale would only make a bigger blur —
compression artefacts, a section that came out of a generative step at model resolution, plate detail
that is gone rather than small. It restores rather than magnifies, which means it does hallucinate,
which means it needs a look before it ships. That is why it publishes at *Pending Review* and why
both Versions exist side by side rather than one replacing the other.

The order of the resize is the whole difference. ESRGAN's model decides its own output size (4x, always),
so the fit to delivery res happens after it — the core `utility-gan_upscaler` template says exactly
this: upscale 4x first, then resize down. SeedVR2 restores at whatever resolution it is handed, so the
resize happens before it, and the resize is what "plate resolution" means on that branch.

## Models

| file | folder | size | licence |
|---|---|---|---|
| `seedvr2_3b_int8_convrot.safetensors` | `models/diffusion_models/` | 3.22 GB | Apache-2.0 |
| `seedvr2_ema_vae_fp16.safetensors` | `models/vae/` | 0.47 GB | Apache-2.0 |
| `RealESRGAN_x4plus.safetensors` | `models/upscale_models/` | 0.06 GB | BSD-3-Clause |

All three are freely downloadable and none is gated. Sources are the links the core templates
themselves carry (`Comfy-Org/SeedVR2`, `Comfy-Org/Real-ESRGAN_repackaged`).

Nodes are **core only**. SeedVR2 is in ComfyUI itself (`comfy_extras/nodes_seedvr.py`) — the
third-party `numz/ComfyUI-SeedVR2_VideoUpscaler` pack is not installed and is not needed.

## Why not SUPIR

SUPIR is the better restorer and it is the wrong answer here. The ComfyUI nodes are core
(`comfy_extras/nodes_model_patch.py`) and that is not the problem: the **weights** ship under a
non-commercial licence. A studio cannot put them in a delivery, and a demo that shows a studio a
pipeline it is not allowed to use is worse than no demo. SeedVR2 is Apache-2.0 and does the same job
one licence grade down.

The general shape of the rule: for anything studio-facing, the model licence is a graph decision, not
a footnote. It belongs beside the sampler settings in the same write-up.

## Provenance

Both Versions land on Shot **demo_05_upres** (id 7646), project 1180, at *Pending Review*.

| Version | code | what it records |
|---|---|---|
| 31794 | `demo_05_upres_esrgan_v001` | `sg_ai_model` = `RealESRGAN_x4plus.safetensors`; `sg_ai_seed`, `sg_ai_sampler`, `sg_ai_steps`, `sg_ai_cfg` all **null** — its branch has no sampler |
| 31819 | `demo_05_upres_seedvr2_v001` | `sg_ai_model` = `seedvr2_3b_int8_convrot.safetensors \| seedvr2_ema_vae_fp16.safetensors`; `sg_ai_seed` = `959948902156062`, `sg_ai_sampler` = `euler/simple`, `sg_ai_steps` = 1, `sg_ai_cfg` = `1.0` |

The null columns on the ESRGAN row are the point, not an omission. One graph, one input, two publish
nodes — and the deterministic Version does not claim sampler settings it never used, because
`provenance.ancestors` walks back from each publish node's own `UNIQUE_ID`.

Both carry `sg_ai_generated_from` → Version **31755** (`demo_05_upres_gen480_v001`), verified on the
site, and neither id was ever typed: the Load node resolved it by rule
(`highest version of 1 matching the convention`) and `lineage` recorded what it resolved. Media, the
`.provenance.json` structure and the `.workflow.json` are all attached, and `sg_ai_generator` reads
`ComfyUI (unknown client)` — honest, because a plain HTTP client sends no `COMFY_USAGE_SOURCE`.

### The SeedVR2 branch does not run at delivery resolution on an Apple GPU

`seedvr2_3b_int8_convrot` executes `aten::_int_mm`, which MPS does not implement. Without
`PYTORCH_ENABLE_MPS_FALLBACK=1` the KSampler raises `NotImplementedError` and the branch dies; with
it, the one sampler step ran **47 minutes at 1920x1080 without completing** on an M-series Mac with
48 GB. At 960x544 — a quarter of the pixels — the same step took **16 minutes** and Version 31819 is
that run.

So the graph keeps the real 1920x1080 delivery resolution and the recorded pixels are smaller. The
limit is this machine's, not the graph's: on a CUDA box the int8 kernel is native and the step is
seconds, which is the whole reason the 3B **int8** build exists. Worth knowing before promising a
studio this path on Apple silicon — and worth contrasting with ESRGAN, which upresed the same frame
to full 1080p and published it in seconds on the same machine. That gap is a second, quieter
argument for the deterministic path.

## The upstream input

Standalone, the input is seeded from disk:

```sh
PYTHONPATH=src python -m comfyui_sg.seed ~/dev/ComfyUI/input/fpt_plate_figure.png \
  --project 1180 --link "demo_05_upres (Shot)" --root-name gen480 --status Approved --note "..."
```

832x480 — model resolution, which is what a generative step produces. A seeded Version carries **no
generation record**, and says so: a file on disk does not know how it was made.

**Wired into the chain, that seed goes away.** The Load node already resolves by rule —
`statuses: Approved`, `name_contains: gen480`, newest by version number in the name — so the real
upstream is whatever the paint-out step published, on whatever Shot the chain runs on. Point `link`
at that Shot and change `name_contains` to the paint-out's stream name; nothing else in the graph
moves. That is the join: no id is copied between graphs, and `sg_ai_generated_from` records it by
itself.

## One frame, and why that is enough

The graph is single-frame: one image in, one Version out per branch. The contrast it exists to show
is what each upres does to *pixels*, and a frame carries that as well as a clip does — while costing
one sampler step instead of one per frame.

**The video path is the same wiring.** Swap `LoadImage`/`SGLoadVersion` for `LoadVideo` +
`GetVideoComponents` and the frames flow through both branches unchanged; the publish node taps an
IMAGE stream and decides for itself what a batch becomes. Nothing between the loader and the publish
node moves. The core `utility-gan_upscaler` and `utility_seedvr2_3b_int8_upscale_video` templates
this is derived from are exactly that shape.

## Notes on the graph

- Derived from the core templates `utility_seedvr2_3b_int8_upscale_image` and `utility-gan_upscaler`
  (`Comfy-Org/workflow_templates`, MIT).
- **The SeedVR2 subgraph is expanded to plain nodes.** The template ships it as a ComfyUI subgraph,
  and `instrument.py` cannot walk into one (README, "Not ready yet") — nor could `provenance.extract`
  see the sampler inside it. Expanding it is the difference between a Version that records its seed
  and one that does not.
- `ImageScale` rather than the template's `ResizeImageMaskNode`: the demo resizes to an explicit
  delivery resolution instead of a multiplier, which is what makes the two paths comparable. Same
  operation, and `ImageScale` takes a plain widget list, which keeps the API prompt readable.
- `crop: center` on both resizes. 832x480 is 1.733:1 and HD is 1.778:1 — a 2.5% side crop, which is
  what a comp would do anyway.
- The original `LoadImage` is left in the graph, unwired, exactly as `/track-workflow` leaves it, so
  it is visible what was swapped for Flow Production Tracking.
