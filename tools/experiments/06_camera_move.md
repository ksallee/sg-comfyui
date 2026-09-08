# 06 — camera move on a still

> **TD line:** *"give the matte painting a push-in that matches the shot's camera."*

Previs and concept want motion off a still constantly, and they want it before anyone has built a
camera. This graph takes one frame — a matte painting, a concept plate, a lookdev still — and moves
a camera through it along a **named trajectory**, then records the result against the shot in Flow
Production Tracking with the plate it came from.

## Verdict — would you show this to a supervisor?

**Yes, as previs.** The push-in is a real camera move on the plate, not a redraw. Fit a centre crop
of the plate to each output frame and the best-fitting crop falls smoothly and monotonically from
1.00 to 0.78 over the 33 frames — a 28% push with no stalls or reversals — while the street keeps its
identity: same awning, same lamp post, same shopfronts, correct parallax as they pass the frame edge.
Frame-to-frame change is flat at 9–11 (mean abs diff, 0–255) across the whole clip: no flicker, no
jump cuts.

Three things a supervisor will say, and they are all fair:

- **Wan animates the content, not just the camera.** The parked car drives toward camera over the
  clip. For a matte-painting push-in you want a locked scene with only the camera moving, and Wan
  2.1 Fun Camera has no way to be told that.
- **Text does not survive.** The awning's lettering is legible at frame 1 and gibberish by frame 17.
  Anything readable in the plate has to be handled another way.
- **Detail softens as the move progresses.** 1.3B at 480p; the ironwork and the cobbles smear on
  the left-hand shopfronts by the end.

So: fine for a previs board or a "what would this look like" pass, not a plate anyone comps onto.
For a move that has to match a real camera, the answer is `WanUni3CControlnetApply` — see "The
honest upgrade" below.

## What it demonstrates

- **A camera move is a parameter, not a keyframe.** `WanCameraEmbedding` turns a word — `Zoom In`,
  `Pan Left`, `ClockWise (CW)` — into a per-frame camera path and encodes it as a Plücker embedding.
  `WanCameraImageToVideo` conditions Wan 2.1 Fun Camera on that path with the still pinned as the
  first frame. Changing the move is changing one combo and one float.
- **The still comes out of Flow PT, not off disk.** `Flow PT Load Version` resolves *the newest
  Version on `demo_06_camera` whose name contains `plate`* — a rule an artist would say out loud —
  and hands its media to the graph.
- **The clip goes back as a clip.** 33 frames become **one** Version carrying one h264 movie in
  `sg_uploaded_movie`, at the rate the graph states. Not 33 Versions; see "One Version, one movie".
- **The result goes back with its lineage.** `Flow PT Publish Version` records the model, prompt,
  seed, sampler, steps and CFG, attaches the graph, and fills `sg_ai_generated_from` with the plate
  Version the Load node resolved. Nobody typed an id at either end.

Built from the core template `video_wan2.1_fun_camera_v1.1_1.3B` (Comfy-Org/workflow_templates,
MIT). **Core nodes only — no third-party packs.**

## The graph

```
Flow PT Load Version ──┬─► CLIPVisionEncode ──┐
  (newest *plate* on   │                      ├─► WanCameraImageToVideo ─► KSampler ─► VAEDecode ─┬─► CreateVideo ─► SaveVideo
   demo_06_camera)     └──── start_image ─────┤        ▲                                          │
                                              │        │                                          └─► Flow PT Publish Version
        CLIPTextEncode (pos/neg) ─────────────┘   WanCameraEmbedding
                                                  ("Zoom In", 832×480, 33f, speed 0.6)
```

`WanCameraEmbedding`'s `width`/`height`/`length` **outputs are wired into** the video node, so the
embedding node is where format and duration are decided — the numbers shown on
`WanCameraImageToVideo` are overridden by those links. Worth knowing before someone edits the video
node's width and wonders why nothing changed: the stock template ships the embedding at 512×512 and
the video node showing 832×480, and it runs at 512×512. This graph sets both to 832×480, which is the
plate's own aspect and Wan 2.1's native size.

`length` is **33** frames — two seconds at 16 fps — where the template ships 81. That is a demo
concession, not a recommendation: 33 frames is 29 minutes on this machine and 81 would be over an
hour. Raise it on a box that can afford it; `length` must stay `4n+1`.

The original `LoadImage` is left in the graph, unwired, at the bottom of the "Start Image" group —
that is `/track-workflow`'s convention, so it is visible what was swapped and trivial to put back.

**The template's `SaveAnimatedWEBP` is gone**, and not for tidiness. It carries `fps` 6 against
`CreateVideo`'s 16, and two savers at two rates is two answers to a question a clip should answer by
itself. The publish node reads the rate off the clip it is handed, so `CreateVideo`'s 16 is what
lands on the Version — one `fps` in the graph, one rate on the Version.

## Models — zero new download

| slot | file | on disk | note |
|---|---|---|---|
| diffusion | `wan2.1_fun_camera_v1.1_1.3B_bf16.safetensors` | 3.0 GB | as the template asks |
| text encoder | `umt5_xxl_fp16.safetensors` | 11 GB | **repointed** — see below |
| clip vision | `clip_vision_h.safetensors` | 1.2 GB | as the template asks |
| vae | `wan_2.1_vae.safetensors` | 242 MB | as the template asks |

**The fp16 repoint works.** The template's `CLIPLoader` asks for `umt5_xxl_fp8_e4m3fn_scaled`
(6.27 GB, not on this machine). The template's own model note lists
`umt5_xxl_fp16.safetensors` as the alternative — *"Chose one of following model"* — so the loader is
pointed at the fp16 that was already in `models/text_encoders/` and nothing was downloaded. It loads
and runs. The fp16 is the larger file of the two; if a machine is tight on memory the fp8 is the one
to fetch, but it is a memory trade, not a requirement.

## The honest upgrade: `WanUni3CControlnetApply`

A named trajectory is a *preset*, not a shot camera. It cannot match a real move, it cannot honour a
lens, and it has no notion of the set geometry the plate depicts. When a TD says "matches the shot's
camera" and means it literally, the answer is **`WanUni3CControlnetApply`** — now a core node
(`comfy_extras/nodes_model_patch.py`, marked `EXPERIMENTAL`), fed by `ModelPatchLoader` — "Load
Model Patch" — with the Uni3C controlnet weights. Its guidance input is not a word but an IMAGE
sequence: *"the guidance video rendered from the camera trajectory, most commonly warped point cloud
renders of the input image."* That is exactly the shape a real camera fits — export the Maya camera,
render or warp a guidance pass along it, and Wan follows the pass. It also carries `strength`,
`start_percent` and `end_percent`, so the move can be dialled back where the plate falls apart.

It costs a Uni3C checkpoint and a guidance-render step upstream, which is why this demo is
deliberately not that: the point here is the cheapest possible motion off a still, the thing previs
asks for on a Tuesday afternoon. Uni3C is the answer to the follow-up question, and worth knowing
exists before the TD asks it.

## One Version, one movie

A Version's media is single-valued (probe 022), so a sequence cannot *be* media. The publish node
therefore takes the clip, not the batch, and creates **one** Version: the clip goes to
`sg_uploaded_movie`, its first frame goes to `image` so there is a thumbnail before the transcode
lands, and `sg_first_frame`/`sg_last_frame`/`frame_count`/`frame_range` record the range. An earlier
run of this same graph produced 33 Versions and 33 one-frame transcodes; that is gone.

**The frame rate is measured, never assumed.** `CreateVideo`'s VIDEO output is wired into the publish
node's `video`, and the rate is read off the clip rather than off a widget or a sibling node:

    review media: 33 frames at 16 fps — encoded by ComfyUI — VideoInput.save_to

Read back off the Version, `sg_uploaded_movie_frame_rate` is `16.0`. The seeded plate on the same
Shot reads `25.0`, which is what Flow PT stamps on a still it transcoded — so the two are
distinguishable on the site, which is the whole point of not writing the transcoder's fields
ourselves.

Publishing the sequence *as* a sequence is a separate question: the frames are registered as
PublishedFiles under a LocalStorage root, alongside the Version carrying the clip for review. This
graph publishes the clip only, which for a previs board is the right deliverable anyway — wire the
IMAGE batch into `images` as well and tick **Create Published Files** to keep the frames too.

## Flow PT, as run

| | |
|---|---|
| project | **1180** — `comfyui-fpt sandbox` |
| shot | `demo_06_camera` (id 7644) |
| plate in | `demo_06_camera_plate_v001` — Version **31751**, seeded from `input/fpt_plate_paris.png` |
| clip out | `demo_06_camera_push_in_v001` — Version **31851**, one `.mp4`, 33 frames at 16 fps |
| status | Pending Review (`rev`) |
| name template | `{entity.code}_{output}_v{version:03d}` |

Read back off Version 31851:

| field | value |
|---|---|
| `entity` | Shot 7644 `demo_06_camera` |
| `sg_uploaded_movie` | `demo_06_camera_push_in_v001.mp4` |
| `sg_uploaded_movie_frame_rate` | `16.0` — matches the rate the node encoded |
| `frame_range` / `frame_count` | `1-33` / `33` |
| `sg_ai_generated_from` | Version 31751 `demo_06_camera_plate_v001` |
| `sg_ai_generator` | `ComfyUI (unknown client)` |
| `sg_ai_model` | `wan2.1_fun_camera_v1.1_1.3B_bf16 \| umt5_xxl_fp16 \| wan_2.1_vae \| clip_vision_h` |
| `sg_ai_seed` | `606060606` |
| `sg_ai_sampler` | `uni_pc/simple` |
| `sg_ai_steps` / `sg_ai_cfg` | `20` / `6.0` |
| attachments | `..._v001.mp4`, `..._v001.provenance.json`, `..._v001.workflow.json` |

`sg_ai_model` is the receipt for the fp16 repoint: the encoder the run actually loaded is named in the
Version. The lineage is the point of the whole graph — nobody typed `31751` anywhere; the Load node
resolved it from *newest plate on this shot* and the publish node carried it forward.

The plate was seeded with:

```sh
PYTHONPATH=src python -m comfyui_fpt.seed ~/dev/ComfyUI/input/fpt_plate_paris.png \
  --project 1180 --link "demo_06_camera (Shot)" --output plate --note "..."
```

A seeded Version carries **no generation record** — a file on disk does not say how it was made — and
the Load panel says so. That is the chicken-and-egg escape: the first graph in a chain has to get its
plate into Flow PT before it can read it back out.

## Running it

```sh
tools/qa_node.py --start --port 8956 --repo <this checkout>
```

Then open `example_workflows/06_camera_move.json`. Three things worth knowing:

- `--base-directory` relocates **models** as well as `custom_nodes`, `input`, `output`, `temp` and
  `user` (`folder_paths.py:15`), contrary to the docstring in `tools/qa_node.py`. An isolated
  instance started that way sees an empty model list and every loader fails validation. Add
  `--models-directory ~/dev/ComfyUI/models` (and `--input-directory ~/dev/ComfyUI/input`) to point
  them back at the real tree.
- The workflow attachment needs `EXTRA_PNGINFO`, which only a client that sends `extra_data` supplies
  — the standard frontend does. A run driven straight at `/prompt` must post
  `extra_data.extra_pnginfo.workflow` itself or the publish reports "no workflow attached", by design.
  This run posted it, and `..._v001.workflow.json` is on the Version.
- `SaveVideo`'s `format` is a `DynamicCombo` (`COMFY_DYNAMICCOMBO_V3`) carrying a nested `codec`
  input rather than a plain widget value. A hand-rolled litegraph→API converter that only recognises
  `INT`/`FLOAT`/`STRING`/`BOOLEAN`/combo-as-list drops both and the node then raises
  `SaveVideo.execute() missing 1 required positional argument: 'format'` **after** everything
  upstream has already run. Emit `format` and `codec` (`"auto"`/`"auto"` is what the graph carries)
  and it writes its `.mp4` normally.

Cost, measured: **1758 s end to end** — 20 steps at 832×480×33 frames is 28 minutes of sampling at
about 85 s/step on an M4 Pro sharing the machine with other work, and the single publish is seconds
rather than the five minutes 33 of them used to take. Sampling scales with `length`, so the
template's 81 frames roughly triples it.
