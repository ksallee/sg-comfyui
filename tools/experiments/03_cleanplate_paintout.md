# 03 Clean plate paint-out

Paint a car out of a locked-off Paris street plate and publish the result to Flow Production
Tracking with the plate Version recorded as its ancestor. The same operation covers rig removal,
boom removal and tracking-marker removal.

## Measured result

Against the plate, inside the matte 24.3% of pixels differ by more than 32/255. Outside the matte
the figure is 0.0%, because the fill is composited back through the matte and the plate is otherwise
untouched. Frame to frame the fill moves 0.5 to 0.9 (mean absolute difference, 0 to 255) against 0.01
outside it.

Three limits of this result:

- Only the car SAM3 matted is removed. The plate has a queue of traffic receding up the street, the
  word `car` matted the near one, and the fill continues the queue behind it. Emptying the street is
  a different matte, not a different fill.
- The fill is softer than the plate. 1.3B at 480p does not retain cobble texture, and inside the matte
  the road is smooth where the plate is crisp. A 2K plate needs regrain, or the 14B.
- The light the car cast is outside the matte and stays. On a plate where the car is the only light
  source the matte has to cover the interactive light as well as the body.

## What it demonstrates

- SAM3 makes the matte from the word `car` instead of from a rotoshape.
- Wan 2.1 VACE fills the hole across the clip in one pass, so the fill is one decision rather than
  seventeen.
- The fill is composited back through a feathered matte, so the model writes the hole and the plate
  supplies every other pixel.
- The clip `CreateVideo` assembles is wired into the publish node's `video` and uploaded rather than
  re-encoded, at the rate the clip states.
- The output Version records model, prompt, seed, sampler, steps, CFG, the workflow JSON, and
  `sg_ai_generated_from` pointing at the plate Version the graph read.
- The graph names no Version id. `SG Load` resolves the newest plate on this Shot and `SG Publish`
  records what it resolved.

## Sampler settings

CausVid is CFG-distilled and requires CFG 1, and at CFG 1 classifier-free guidance is off, so the
negative prompt is inert. On the core `video_wan_vace_outpainting` wiring (CausVid at 0.7,
`uni_pc`/`simple`, 4 steps, CFG 1.0) the hole filled with a different car every time, and growing the
matte (24, 48, 96) produced a bigger wrong car. Without the LoRA, at 20 steps and CFG 6, the car is
removed on the first run. Sampling costs about 13 minutes instead of 3.

### The negative prompt names the failure

With CFG 6, the first 17-frame run replaced the car with a bright orange light smear, temporally
stable. The plate's own headlight pool is just outside the matte and leads into it, and the model
continued it. The same settings at 5 frames produced clean empty road: a short probe does not predict
the long one.

Adding `glare, lens flare, bright light source, light streak, motion blur, long exposure` to the
vehicle words in the negative prompt removes the smear, at the same seed and the same matte. Those
words do nothing at CFG 1.

Rewording the positive prompt to describe the empty plate made no measurable difference. The shipped
positive describes the empty street rather than the object being removed, which is the shape VACE
takes.

### The plate is held everywhere the matte is not

VACE re-encodes the frame, not the masked region. The raw decode redrew the bollards on the
right-hand pavement and drifted frame to frame: 1.2% of the frame outside the matte changed, and
outside-matte frame-to-frame motion ran at 1.2 to 3.0 on a locked-off plate.

`MaskToImage → ImageBlur → ImageToMask → ImageCompositeMasked` puts the decode back over the repeated
plate through a feathered copy of the matte. Four core nodes, no extra sampling, and the numbers move
to 0.0% spill and 0.01 outside-matte motion.

### 14B was not downloaded

The template ships Wan 2.1 VACE 14B fp16 at 32.29 GB. The affordable 14B path is 14B plus
`Wan21_CausVid_14B_T2V_lora_rank32`, which is the CFG-1 case above with a bigger model. 14B without
CausVid, at 20 steps and CFG 6, is about an order of magnitude more compute than the 13 minutes the
1.3B takes here, which is over an hour per iteration on this machine.

## Provenance

| | |
|---|---|
| Project | 1180 `comfyui-fpt sandbox` |
| Shot | `demo_03_cleanplate` (id 7645) |
| Seeded plate | Version 31752 `demo_03_cleanplate_plate_v001`, from `ComfyUI/input/fpt_plate_paris.png` |
| Published | Version 31854 `demo_03_cleanplate_cleanplate_v002`, one `.mp4`, 17 frames at 16 fps |
| `sg_ai_generated_from` | `31752 demo_03_cleanplate_plate_v001` |

`_v001` was the light-smear run: published, reviewed, deleted. The graph as committed produced
`_v002`.

Read back off the site:

    code                          demo_03_cleanplate_cleanplate_v002
    sg_uploaded_movie             demo_03_cleanplate_cleanplate_v002.mp4
    sg_uploaded_movie_frame_rate  16.0            (the rate the clip states)
    frame_range / frame_count     1-17 / 17
    sg_ai_generator               ComfyUI (unknown client)
    sg_ai_model                   wan2.1_vace_1.3B_fp16 | umt5_xxl_fp16 | wan_2.1_vae | sam3.1_multiplex_fp16
    sg_ai_prompt                  Empty wet cobblestone street at dusk in Paris, ...
    sg_ai_negative_prompt         car, vehicle, van, truck, bus, headlights, tail lights, glare, ...
    sg_ai_seed                    303198301
    sg_ai_sampler                 uni_pc/simple
    sg_ai_steps / sg_ai_cfg       20 / 6.0
    sg_ai_generated_from          [Version 31752 demo_03_cleanplate_plate_v001]

Three attachments: the `.mp4`, `*.provenance.json` and `*.workflow.json`. The workflow attachment
is written only where the caller sent `extra_pnginfo`, which the standard frontend does and several other
clients do not (README).

`sg_ai_model` names the SAM3 checkpoint alongside the three Wan files because `provenance.extract`
walks the branch and reports each model the branch loaded, and the matte is part of what made this
image.

The seeded plate on the same Shot reads `sg_uploaded_movie_frame_rate` 25.0, which is what Flow
Production Tracking stamps on a still it transcoded. 16.0 against 25.0 distinguishes a movie from a
transcoded frame on the site, which is why the node does not write the transcoder's own fields
(probe 022).

## The graph

Flattened from the core `video_wan_vace_inpainting` template, which ships the same chain inside a
subgraph. `instrument.py` does not walk into subgraphs (README, "Not ready yet"), so the template as
shipped reports no publishable stream and `/track-workflow` has nothing to offer.

    SG Load ──► RepeatImageBatch ──┬──► SAM3_Detect ──► GrowMask ──┬──► WanVaceToVideo
      (the plate, from        (locked-off clip, │    ("car")             │      │      │
       Flow Production Tracking, not disk)      17 frames)       │                       │      │      ▼
                       │                        └──► ImageCompositeMasked ─────┘   KSampler
                       │                             (blank out the car)              │
                       │                                                              ▼
                       │                        MaskToImage ─► ImageBlur ─┐    TrimVideoLatent
                       │                          (feather the matte)     │            │
                       │                                                  ▼            ▼
                       └───────────────────────► ImageCompositeMasked ◄── ImageToMask  VAEDecode
                            (destination: plate)      │        ▲                       │
                                                      │        └───────────────────────┘
                                                      │            (source: the fill)
                                                      ├──► CreateVideo ──► SaveVideo
                                                      └──► SG Publish

Core nodes only. No third-party packs.

`instrument.py` found two publishable streams, the decoded frames (`cleanplate`) and the composited
paint-out target (`paintout_target`), and one loader it could replace. Only `cleanplate` is tapped.
`LoadImage` is still in the graph, unwired, because a replaced loader is left in place.

The plate is a still repeated into a short locked-off clip rather than a source movie. A locked-off
tripod plate is the case rig removal is simplest to show on, and it is the shape that lets the seeded
Version, an image, feed the graph. Temporal stability here means the fill is one pass over the clip,
not a measurement on moving footage.

## Models

Everything below is Apache-2.0.

| file | size | role |
|---|---|---|
| `wan2.1_vace_1.3B_fp16.safetensors` | 4.01 GB | the VACE diffusion model |
| `umt5_xxl_fp16.safetensors` | 11.37 GB | text encoder (already installed) |
| `wan_2.1_vae.safetensors` | 0.25 GB | VAE (already installed) |
| `sam3.1_multiplex_fp16.safetensors` | 1.75 GB | the matte |

No LoRA.

### 1.3B instead of the shipped 14B

The template ships Wan 2.1 VACE 14B fp16 at 32.29 GB. This workflow uses the 1.3B at 4.01 GB, an 8x
smaller download. What the 1.3B gives up:

- 480p only. It was not trained at 720p; the model card says so and the template repeats it.
- Low fidelity. The fill is soft and does not retain fine texture, which is visible inside the matte
  here.
- Weak prompt adherence, which is why the negative prompt names the failure mode literally.

Swapping to 14B is one widget value (`unet_name`) and no rewiring. Read the CausVid note above first.

## Running it

    # models
    hf download Comfy-Org/Wan_2.1_ComfyUI_repackaged split_files/diffusion_models/wan2.1_vace_1.3B_fp16.safetensors
    hf download Comfy-Org/sam3.1 checkpoints/sam3.1_multiplex_fp16.safetensors

    # the plate, into Flow Production Tracking, so the graph has something to read
    PYTHONPATH=src python -m comfyui_sg.seed ~/dev/ComfyUI/input/fpt_plate_paris.png \
      --project 1180 --link "demo_03_cleanplate (Shot)" --root-name plate

Then open `example_workflows/03_cleanplate_paintout.json` and run it. 1262 s end to end on an M4 Pro
sharing the machine with other work: SAM3 over 17 frames, 20 VACE steps at 832x480 (about 45 s per
step), the composite, and one publish.
