# 03 — clean plate paint-out

**Mask it once, get a temporally stable clean plate back.**

Paint a car out of a locked-off Paris street plate and publish the result to Flow Production
Tracking with the plate it came from recorded as its ancestor. After roto this is the second-biggest
fixed cost in comp, and it is what almost every published VFX workflow is actually about: rig
removal, boom removal, tracking-marker removal.

## Verdict — would you show this to a supervisor?

**Yes, as a first pass.** The car is gone and the fill holds still. Measured against the plate,
inside the matte 24.3% of pixels differ by more than 32/255 — the car is not there any more — while
outside the matte the figure is **0.0%**, because the fill is composited back through the matte and
the plate is otherwise untouched. Frame to frame the fill moves 0.5–0.9 (mean abs diff, 0–255)
against 0.01 outside it: a faint shimmer on the road, no boil, no wander, nothing that pops when you
scrub.

What a supervisor will say back, and all three are fair:

- **Only the car SAM3 matted went.** The plate has a queue of traffic receding up the street; the
  word `car` matted the near one, and the fill continues the queue behind it. "Empty the street" is
  a different matte, not a different fill.
- **The fill is softer than the plate.** 1.3B at 480p does not hold cobble texture; inside the matte
  the road is smooth where the plate is crisp. On a real 2K plate this wants regrain, or the 14B.
- **The light the car cast is outside the matte and stays.** Here that is survivable — the street is
  full of lamps and the leftover pool reads as one of them. On a plate where the car is the only
  light source it would give the paint-out away, and the matte would have to cover the interactive
  light, not just the body.

It is a clean plate you would put up for review, not one you would ship without a comp pass.

## What it demonstrates

- SAM3 makes the matte from a word — `car` — instead of from a rotoshape.
- Wan 2.1 VACE fills the hole across the whole clip in one pass, so the fill is one decision rather
  than seventeen independent ones.
- The fill is composited back through a feathered matte, so **the model owns the hole and the plate
  owns every other pixel**.
- A batch is **one Version carrying one movie**, at the rate the graph states.
- The output Version records what made it: model, prompt, seed, sampler, steps, CFG, the workflow
  JSON, **and `sg_ai_generated_from` pointing back at the plate Version the graph read**.
- The graph never names a Version id. `Flow PT Load Version` resolves *the newest plate on this
  Shot*, and `Flow PT Publish Version` records what it resolved. That is the whole point of the
  pair.

## What made it work

The graph in this directory is not the one first written for this demo, and the difference is worth
recording because both failures were instructive.

### CausVid off, 20 steps at CFG 6

The first version cribbed the core `video_wan_vace_outpainting` wiring: the **CausVid** 4-step
distillation LoRA at 0.7, `uni_pc`/`simple`, 4 steps, **CFG 1.0**. It filled the hole with a
different car, every time, and growing the matte (24 / 48 / 96) only produced a bigger wrong car.

CausVid is CFG-distilled: it *requires* CFG 1, and at CFG 1 classifier-free guidance is off, so the
negative prompt is inert. Every "no vehicles" in the prompt was decoration. Dropping the LoRA and
running **20 steps at CFG 6** removes the car on the first try. That costs about 13 minutes of
sampling instead of 3 — the whole price of the fix.

### The negative prompt has to name what actually goes wrong

With CFG live, the first 17-frame run replaced the car with a **bright orange light smear** — rock
solid temporally, and completely wrong. The plate's own headlight pool sits just outside the matte
and leads into it, so the model continued it.

The same settings at 5 frames had produced clean empty road, which is the trap: a short probe does
not predict the long one. What fixed it was naming the failure in the negative prompt —
`glare, lens flare, bright light source, light streak, motion blur, long exposure` on top of the
vehicle words. Same seed, same matte, same everything else. That is only possible because CFG is 6;
at CFG 1 those words would have done nothing.

Rewording the *positive* to describe the empty plate more explicitly was also tried, and made no
measurable difference — the shipped positive already describes the empty street rather than the
thing being removed, which is the right shape for VACE.

### The plate is held everywhere the matte is not

VACE re-encodes the whole frame, not just the masked region. The raw decode came back with the
bollards on the right-hand pavement redrawn and drifting frame to frame: 1.2% of the frame outside
the matte changed, and outside-matte frame-to-frame motion ran at 1.2–3.0 on a **locked-off** plate.

So `MaskToImage → ImageBlur → ImageToMask → ImageCompositeMasked` puts the decode back over the
repeated plate through a feathered version of the matte. Four core nodes, no extra sampling, and the
numbers move to 0.0% spill and 0.01 outside-matte motion. It is also just what a comp artist would
do, and it makes "locked-off, temporally stable" a property of the graph rather than a hope.

### 14B was considered and not downloaded

The template ships Wan 2.1 VACE **14B fp16** at 32.29 GB, and there is disk for it. It was not
fetched, for a reason rather than for the download: the 14B path that is affordable to *run* is 14B
plus `Wan21_CausVid_14B_T2V_lora_rank32`, which is the same CFG-1 trap that broke the 1.3B — a
bigger model with a dead negative prompt. 14B **without** CausVid, at 20 steps and CFG 6, is roughly
an order of magnitude more compute than the 13 minutes the 1.3B takes here, which is an hour-plus
per iteration on this machine. The cheap route worked, so the expensive one was not needed.

## Provenance that landed

| | |
|---|---|
| Project | 1180 `comfyui-fpt sandbox` |
| Shot | `demo_03_cleanplate` (id 7645) |
| Seeded plate | Version **31752** `demo_03_cleanplate_plate_v001` — from `ComfyUI/input/fpt_plate_paris.png` |
| Published | Version **31854** `demo_03_cleanplate_cleanplate_v002` — one `.mp4`, 17 frames at 16 fps |
| `sg_ai_generated_from` | `31752 demo_03_cleanplate_plate_v001` |

`_v002` because `_v001` was the light-smear run: published, looked at, judged wrong, deleted. The
gap in the numbering is the record of that, and the graph as committed is the one that produced
`_v002`.

Read back off the site:

    code                          demo_03_cleanplate_cleanplate_v002
    sg_uploaded_movie             demo_03_cleanplate_cleanplate_v002.mp4
    sg_uploaded_movie_frame_rate  16.0            (the rate the node encoded)
    frame_range / frame_count     1-17 / 17
    sg_ai_generator               ComfyUI (unknown client)
    sg_ai_model                   wan2.1_vace_1.3B_fp16 | umt5_xxl_fp16 | wan_2.1_vae | sam3.1_multiplex_fp16
    sg_ai_prompt                  Empty wet cobblestone street at dusk in Paris, ...
    sg_ai_negative_prompt         car, vehicle, van, truck, bus, headlights, tail lights, glare, ...
    sg_ai_seed                    303198301
    sg_ai_sampler                 uni_pc/simple
    sg_ai_steps / sg_ai_cfg       20 / 6.0
    sg_ai_generated_from          [Version 31752 demo_03_cleanplate_plate_v001]

plus three attachments — the `.mp4`, `*.provenance.json` and `*.workflow.json`. The workflow
attachment is the interesting one: it only lands because the caller sent `extra_pnginfo`, which the
standard frontend does and several other clients do not (README).

`sg_ai_model` naming the SAM3 checkpoint alongside the three Wan files is not a special case —
`provenance.extract` walks the branch and reports every model the branch loaded, and the matte is
part of what made this image.

The seeded plate on the same Shot reads `sg_uploaded_movie_frame_rate` **25.0** — what Flow PT
stamps on a still it transcoded. 16.0 against 25.0 is how you tell a real movie from a transcoded
frame on the site, which is why the node never writes the transcoder's own fields (probe 022).

## The graph

Flattened from the core `video_wan_vace_inpainting` template, which ships the same chain inside a
subgraph. Flat on purpose: `instrument.py` does not walk into subgraphs (README, "Not ready yet"),
so the template as shipped reports no publishable stream and `/track-workflow` has nothing to offer.

    Flow PT Load Version ──► RepeatImageBatch ──┬──► SAM3_Detect ──► GrowMask ──┬──► WanVaceToVideo
      (the plate, from        (locked-off clip, │    ("car")             │      │      │
       Flow PT, not disk)      17 frames)       │                       │      │      ▼
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
                                                      └──► Flow PT Publish Version

Core nodes only. No third-party packs.

`instrument.py` found two publishable streams — the decoded frames (`cleanplate`) and the composited
paint-out target (`paintout_target`) — and one loader it could replace. Only `cleanplate` is tapped;
publishing every pass is usually wrong. `LoadImage` is still in the graph, unwired, because a
replaced loader is left in place so you can see what was swapped and put it back.

The plate is a still repeated into a short locked-off clip rather than a source movie, and that is a
choice, not a shortcut: a locked-off tripod plate is exactly the case rig removal is easiest to show
on, and it is the only shape that lets the seeded Version — an image — actually feed the graph and
prove the lineage. It also flatters the "temporally stable" claim, so read that claim as *the
mechanism is one pass over the clip*, not as a measurement on moving footage.

## Models

Everything below is Apache-2.0.

| file | size | role |
|---|---|---|
| `wan2.1_vace_1.3B_fp16.safetensors` | 4.01 GB | the VACE diffusion model |
| `umt5_xxl_fp16.safetensors` | 11.37 GB | text encoder (already installed) |
| `wan_2.1_vae.safetensors` | 0.25 GB | VAE (already installed) |
| `sam3.1_multiplex_fp16.safetensors` | 1.75 GB | the matte |

No LoRA. `Wan21_CausVid_bidirect2_T2V_1_3B_lora_rank32` used to be here and is gone; see "What made
it work".

### 1.3B instead of the shipped 14B

The template ships Wan 2.1 VACE **14B fp16, 32.29 GB**. This workflow uses the **1.3B, 4.01 GB** — an
8× smaller download and the difference between a demo that runs on a laptop and one that does not.

What you give up, plainly:

- **480p only.** 1.3B was not trained at 720p; the model card says so and the template repeats it.
- **Low fidelity.** The fill is soft and does not hold fine texture — visible inside the matte here.
- **Prompt adherence is weak**, which is why the negative prompt has to name the failure mode
  literally rather than gesture at it.

Swapping to 14B is one widget value (`unet_name`) and no rewiring — but read the note above about
CausVid before assuming 14B is a free upgrade.

## Running it

    # models
    hf download Comfy-Org/Wan_2.1_ComfyUI_repackaged split_files/diffusion_models/wan2.1_vace_1.3B_fp16.safetensors
    hf download Comfy-Org/sam3.1 checkpoints/sam3.1_multiplex_fp16.safetensors

    # the plate, into Flow PT, so the graph has something to read
    PYTHONPATH=src python -m comfyui_fpt.seed ~/dev/ComfyUI/input/fpt_plate_paris.png \
      --project 1180 --link "demo_03_cleanplate (Shot)" --output plate

Then open `example_workflows/03_cleanplate_paintout.json` and run it. **1262 s end to end** on an M4 Pro sharing
the machine with other work: SAM3 over 17 frames, 20 VACE steps at 832×480 (about 45 s/step), the
composite, and one publish.
