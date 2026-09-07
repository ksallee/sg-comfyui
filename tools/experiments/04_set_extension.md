# 04 — Set extension

> The set stopped at the edge of the bluescreen — pad it and let the model build the rest, using the
> plate's own edges as reference.

## What it demonstrates

Extend the frame, publish the extended plate. A shot is delivered wider and taller than it was
photographed, and Flow PT records that the delivered frame is not the photographed one: which model
built the new territory, on which prompt and seed, and — through `sg_ai_generated_from` — which
Version the untouched pixels came from.

Set extension and reframe-for-delivery are constant studio work, and they are the case where
provenance matters most quietly: the result still looks like a plate. A supervisor opening the
delivered Version sees a generation record where a photographed plate would have none.

The graph is deliberately the *second* generative step in a chain. Its input is a Version, not a
file, so when it sits downstream of a clean-plate graph the delivered frame is two models deep and
both are traceable from the one Version — this one names its source, and its source names its own.

## The graph

Derived from the ComfyUI core template `video_wan_vace_outpainting` (Comfy-Org/workflow_templates,
MIT), on its **1.3B** path. Core nodes only; no third-party packs.

    Flow PT Load Version ──► ImagePadForOutpaint ──┬─► WanVaceToVideo (control_video)
                                                   └─► MASK ─► MaskToImage ─► RepeatImageBatch
                                                              ─► ImageToMask ─► (control_masks)
    UNETLoader (VACE 1.3B) ─► LoraLoader (CausVid) ─► ModelSamplingSD3 ─► KSampler
                                                   └─► CLIPTextEncode ×2 ─► WanVaceToVideo
    KSampler ─► TrimVideoLatent ─► VAEDecode ─┬─► SaveImage
                                              └─► Flow PT Publish Version

`ImagePadForOutpaint` does the reframe and hands back the mask of what it added; that mask *is* the
region the model is allowed to build. VACE takes the padded plate as control video and the mask as
control mask, so the photographed frame is conditioning and only the new territory is sampled. It is
conditioning, not a matte: the whole frame goes through the VAE, so the delivered pixels inside the
original border are a reconstruction of the plate, not the plate. A comp that must keep the original
grain composites the extension back under the plate.

The plate is 512x288. The pad is 96 left, 96 right, 32 top, 64 bottom, so the delivered frame is
**704x384** — both divisible by 16, which `WanVaceToVideo` requires. Change the pad and Width and
Height must change with it, or `WanVaceToVideo` rescales the plate and the original pixels stop
lining up.

`length` is 1: one frame in, one frame out, so the publish is one Version rather than one per frame.
The mask path still goes through `RepeatImageBatch` because that is how the template feeds `length`
frames of mask, and it is left intact so raising `length` turns this back into a moving set
extension without rewiring anything.

Changes from the template, all structural: `LoadVideo`/`GetVideoComponents` replaced by a still
plate; the 14B loaders and the fp8 text encoder dropped in favour of the 1.3B pair; `CreateVideo`/
`SaveVideo` replaced by `SaveImage`; length 81 → 1; the seed fixed rather than randomised, so a
re-run reproduces and the recorded provenance means something.

## Models

Nothing new to download beyond what demo 03 already fetches.

| file | where | size |
|---|---|---|
| `wan2.1_vace_1.3B_fp16.safetensors` | `models/diffusion_models/` | 4.01 GB |
| `Wan21_CausVid_bidirect2_T2V_1_3B_lora_rank32.safetensors` | `models/loras/` | 0.08 GB |
| `umt5_xxl_fp16.safetensors` | `models/text_encoders/` | already installed |
| `wan_2.1_vae.safetensors` | `models/vae/` | already installed |

CausVid is what makes it cheap: 3 steps at cfg 1.0 with shift 8.0, instead of 20 steps at cfg 6.0.

## The upstream input

The Load node resolves *the newest Version on this Shot whose name contains `plate`* — a rule, not
an id. Nothing in the graph is pinned, so pointing it at a real chain is a matter of pointing it at
the Shot.

Wired into the demo chain, that upstream should be **the clean-plate Version** — the graph that
removes rig, wires or bluescreen and publishes a clean frame. This graph then extends that frame,
and the delivered Version's `sg_ai_generated_from` names the clean plate, whose own
`sg_ai_generated_from` names the photographed plate. Two generative steps, one traversable chain.

`name_contains` is `plate` rather than empty on purpose: this graph publishes onto the same Shot, so
"newest on this Shot" would eventually resolve to its own output. The published stream is called
`extension` precisely so the input rule cannot match it.

Standing alone, as built here, the upstream is a seeded Version — the photographed frame put into
Flow PT by `comfyui_fpt.seed`, which carries no generation record, because a file on disk does not
say how it was made.

## Flow PT

Project 1180 (`comfyui-fpt sandbox`), Shot `demo_04_setext` (id 7643).

| Version | code | what |
|---|---|---|
| 31750 | `demo_04_setext_plate_v001` | the seeded input plate, 512x288, no generation record |
| 31795 | `demo_04_setext_extension_v001` | the delivered 704x384 frame, with provenance |

Version 31795 carries all nine provenance fields, and `sg_ai_generated_from` names Version 31750 —
recorded by the graph, not typed by anyone. What landed:

    sg_ai_generator       ComfyUI (unknown client)
    sg_ai_model           wan_2.1_vae | wan2.1_vace_1.3B_fp16 | umt5_xxl_fp16
    sg_ai_seed            40415
    sg_ai_sampler         uni_pc/simple
    sg_ai_steps           3
    sg_ai_cfg             1.0
    sg_ai_generated_from  demo_04_setext_plate_v001 (31750)

`sg_ai_generator` reads *unknown client* because the run was driven over HTTP rather than from the
editor; the workflow attachment depends on the same `EXTRA_PNGINFO`, and a publish never depends on
either. Opened from the ComfyUI frontend, both are filled.

One frame at 704x384, 3 steps: 36 seconds on an M-series Mac, model load excluded.

### A graph written by `instrument.py` needs `widgets_values_named`

`FPTPublishVersion` remaps its own saved values in `onConfigure` (fpt_entity_picker.js, "The node
maps its own saved values"). `FPTLoadVersion` has no such stopgap: it gets the shared
`restoreDeclaredWidgets`, whose positional fallback counts the three DOM pickers because
`addDOMWidget` never copies `serialize` onto the widget. So the ten declared values are walked
across thirteen slots, `newest_by` receives `frame`, `pin_version_id` receives `filters`, and the
graph fails validation before it queues:

    pin_version_id, , invalid literal for int() with base 10: ''
    newest_by: 1 not in ['version number in the name', 'created_at', 'id (creation order)']

Both FPT nodes here therefore carry `widgets_values_named` as well as the positional array — the
same map the editor writes, and the branch `restoreDeclaredWidgets` prefers. `tools/workflows/*.json` and
anything `instrument.py` writes have the same problem and the same fix.

## Running it

    PYTHONPATH=src python -m comfyui_fpt.seed ComfyUI/input/fpt_plate_setext.png \
        --project 1180 --link "demo_04_setext (Shot)" --output plate

then open `example_workflows/04_set_extension.json` in ComfyUI and run it.
