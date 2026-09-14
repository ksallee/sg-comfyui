# 05 Plate upres

Take a 480p generated section back up to delivery resolution and publish it. This is the terminal
step of the chain: a delivery-res Version whose ancestry runs back through paint-out and roto to the
original plate.

`05_plate_upres.json` opens in ComfyUI, or POSTs as an API prompt.

## What it demonstrates

One 480p input, two upres paths, both landing on 1920x1080, each publishing its own Version. A comp
supervisor compares a route that cannot invent detail against a route that can, on the same frame,
with both recorded.

It is also the case for per-branch provenance. Both publish nodes are in one file and share one
input, and each Version records only what produced its own image: the ESRGAN Version names its
upscale model and no seed, sampler, steps or cfg, because its branch has none.

## The two paths

| | esrgan | seedvr2 |
|---|---|---|
| model | RealESRGAN_x4plus, fixed 4x | SeedVR2 3B int8, one step |
| resize | after the model: 3328x1920 lanczos down to 1920x1080 | before the model: 832x480 lanczos up to 1920x1080, restored at that size |
| invents detail | no | yes |
| repeatable | bit-for-bit | seeded, so repeatable |
| cost | seconds | a model load and a sampler step |

ESRGAN is a deterministic filter: same input, same pixels, nothing in the output that was not in the
input. Use it where the answer has to be defensible, which is the default for a delivery.

SeedVR2 restores rather than magnifies, so use it where the source is soft and a clean upscale would
enlarge the blur: compression artefacts, a section that came out of a generative step at model
resolution, plate detail that is gone rather than small. It hallucinates, so it needs a look before
it ships, which is why it publishes at Pending Review and why both Versions exist side by side.

The order of the resize is the difference. ESRGAN's model decides its own output size (4x), so the
fit to delivery resolution happens after it, which is what the core `utility-gan_upscaler` template
does. SeedVR2 restores at whatever resolution it is given, so the resize happens before it, and that
resize is what plate resolution means on that branch.

## Models

| file | folder | size | licence |
|---|---|---|---|
| `seedvr2_3b_int8_convrot.safetensors` | `models/diffusion_models/` | 3.22 GB | Apache-2.0 |
| `seedvr2_ema_vae_fp16.safetensors` | `models/vae/` | 0.47 GB | Apache-2.0 |
| `RealESRGAN_x4plus.safetensors` | `models/upscale_models/` | 0.06 GB | BSD-3-Clause |

All three are freely downloadable and none is gated. The sources are the links in the core templates
(`Comfy-Org/SeedVR2`, `Comfy-Org/Real-ESRGAN_repackaged`).

Nodes are core only. SeedVR2 is in ComfyUI itself (`comfy_extras/nodes_seedvr.py`), and the
third-party `numz/ComfyUI-SeedVR2_VideoUpscaler` pack is not installed and not needed.

## Why not SUPIR

SUPIR is the better restorer. Its ComfyUI nodes are core (`comfy_extras/nodes_model_patch.py`), but
its weights ship under a non-commercial licence, so a studio cannot put them in a delivery. SeedVR2
is Apache-2.0 and does the same job.

For studio-facing work the model licence is a graph decision, and it belongs beside the sampler
settings.

## Provenance

Both Versions are on Shot demo_05_upres (id 7646), project 1180, at Pending Review.

| Version | code | what it records |
|---|---|---|
| 31794 | `demo_05_upres_esrgan_v001` | `sg_ai_model` = `RealESRGAN_x4plus.safetensors`; `sg_ai_seed`, `sg_ai_sampler`, `sg_ai_steps`, `sg_ai_cfg` all null, because its branch has no sampler |
| 31819 | `demo_05_upres_seedvr2_v001` | `sg_ai_model` = `seedvr2_3b_int8_convrot.safetensors \| seedvr2_ema_vae_fp16.safetensors`; `sg_ai_seed` = `959948902156062`, `sg_ai_sampler` = `euler/simple`, `sg_ai_steps` = 1, `sg_ai_cfg` = `1.0` |

The null columns on the ESRGAN row are the demonstration: one graph, one input, two publish nodes,
and the deterministic Version records no sampler settings, because `provenance.ancestors` walks back
from each publish node's own `UNIQUE_ID`.

Both record `sg_ai_generated_from` as Version 31755 (`demo_05_upres_gen480_v001`), verified on the
site, and neither id was typed: the Load node resolved it by rule (`highest version of 1 matching the
convention`) and `lineage` recorded what it resolved. Media, the `.provenance.json` structure and the
`.workflow.json` are attached, and `sg_ai_generator` reads `ComfyUI (unknown client)`, because a
plain HTTP client sends no `COMFY_USAGE_SOURCE`.

### The SeedVR2 branch does not run at delivery resolution on an Apple GPU

`seedvr2_3b_int8_convrot` executes `aten::_int_mm`, which MPS does not implement. Without
`PYTORCH_ENABLE_MPS_FALLBACK=1` the KSampler raises `NotImplementedError`. With it, the one sampler
step ran 47 minutes at 1920x1080 without completing on an M-series Mac with 48 GB. At 960x544, a
quarter of the pixels, the same step took 16 minutes, and Version 31819 is that run.

The graph keeps the 1920x1080 delivery resolution and the recorded pixels are smaller. On a CUDA box
the int8 kernel is native and the step is seconds, which is what the 3B int8 build is for. ESRGAN
upresed the same frame to full 1080p and published it in seconds on the same machine.

## The upstream input

Standalone, the input is seeded from disk:

```sh
PYTHONPATH=src python -m comfyui_sg.seed ~/dev/ComfyUI/input/fpt_plate_figure.png \
  --project 1180 --link "demo_05_upres (Shot)" --root-name gen480 --status Approved --note "..."
```

832x480 is model resolution, which is what a generative step produces. A seeded Version has no
generation record, and says so: a file on disk does not record how it was made.

Wired into the chain, the seed is not needed. The Load node resolves by rule: `statuses: Approved`,
`name_contains: gen480`, newest by version number in the name. The upstream is then whatever the
paint-out step published, on whatever Shot the chain runs on. Point `link` at that Shot and change
`name_contains` to the paint-out's stream name; nothing else in the graph moves. No id is copied
between graphs, and `sg_ai_generated_from` records the join.

## One frame

The graph is single-frame: one image in, one Version out per branch. What each upres does to pixels
is visible on a frame, at one sampler step instead of one per frame.

The video path is the same wiring. Swap `LoadImage`/`SGLoadVersion` for `LoadVideo` +
`GetVideoComponents` and the frames flow through both branches unchanged; the publish node taps an
IMAGE stream and decides what a batch becomes. Nothing between the loader and the publish node moves.
The core `utility-gan_upscaler` and `utility_seedvr2_3b_int8_upscale_video` templates this is derived
from are that shape.

## Notes on the graph

- Derived from the core templates `utility_seedvr2_3b_int8_upscale_image` and `utility-gan_upscaler`
  (`Comfy-Org/workflow_templates`, MIT).
- The SeedVR2 subgraph is expanded to plain nodes. The template ships it as a ComfyUI subgraph, and
  `instrument.py` cannot walk into one (README, "Not ready yet"), nor could `provenance.extract` see
  the sampler inside it. Expanded, the Version records its seed.
- `ImageScale` rather than the template's `ResizeImageMaskNode`: the demo resizes to an explicit
  delivery resolution instead of a multiplier, which is what makes the two paths comparable.
  `ImageScale` takes a plain widget list, which keeps the API prompt readable.
- `crop: center` on both resizes. 832x480 is 1.733:1 and HD is 1.778:1, a 2.5% side crop.
- The original `LoadImage` is left in the graph, unwired, as `/track-workflow` leaves it, so what was
  swapped for Flow Production Tracking is visible.
