# 06 Camera move on a still

Move a camera through one still along a named trajectory and record the clip against the shot in
Flow Production Tracking with the plate it came from.

## Measured result

Fit a centre crop of the plate to each output frame and the best-fitting crop falls smoothly and
monotonically from 1.00 to 0.78 over the 33 frames: a 28% push with no stalls or reversals. The
street keeps its identity, with the same awning, lamp post and shopfronts, and correct parallax as
they pass the frame edge. Frame-to-frame change is flat at 9 to 11 (mean absolute difference, 0 to
255) across the clip.

Three limits of this result:

- Wan animates the content as well as the camera. The parked car drives toward camera over the clip.
  A matte-painting push-in wants a locked scene with only the camera moving, and Wan 2.1 Fun Camera
  has no input for that.
- Text does not survive. The awning's lettering is legible at frame 1 and gibberish by frame 17.
- Detail softens as the move progresses. At 1.3B and 480p, the ironwork and the cobbles smear on the
  left-hand shopfronts by the end.

The result suits a previs board. For a move that has to match a real camera, see
`WanUni3CControlnetApply` below.

## What it demonstrates

- A camera move is a parameter, not a keyframe. `WanCameraEmbedding` turns a word (`Zoom In`,
  `Pan Left`, `ClockWise (CW)`) into a per-frame camera path and encodes it as a Plücker embedding.
  `WanCameraImageToVideo` conditions Wan 2.1 Fun Camera on that path with the still pinned as the
  first frame. Changing the move is one combo and one float.
- The still comes out of Flow Production Tracking, not off disk. `SG Load` resolves the newest
  Version on `demo_06_camera` whose name contains `plate` and hands its media to the graph.
- 33 frames become one Version with one h264 movie in `sg_uploaded_movie`, at the rate the graph
  states.
- `SG Publish` records the model, prompt, seed, sampler, steps and CFG, attaches the graph, and fills
  `sg_ai_generated_from` with the plate Version the Load node resolved. No id is typed at either end.

Built from the core template `video_wan2.1_fun_camera_v1.1_1.3B` (Comfy-Org/workflow_templates, MIT).
Core nodes only, no third-party packs.

## The graph

```
SG Load ──┬─► CLIPVisionEncode ──┐
  (newest *plate* on   │                      ├─► WanCameraImageToVideo ─► KSampler ─► VAEDecode ─┬─► CreateVideo ─► SaveVideo
   demo_06_camera)     └──── start_image ─────┤        ▲                                          │
                                              │        │                                          └─► SG Publish
        CLIPTextEncode (pos/neg) ─────────────┘   WanCameraEmbedding
                                                  ("Zoom In", 832×480, 33f, speed 0.6)
```

`WanCameraEmbedding`'s `width`, `height` and `length` outputs are wired into the video node, so the
embedding node is where format and duration are set and the numbers shown on `WanCameraImageToVideo`
are overridden by those links. The stock template ships the embedding at 512x512 and the video node
showing 832x480, and it runs at 512x512. This graph sets both to 832x480, which is the plate's aspect
and Wan 2.1's native size.

`length` is 33 frames, two seconds at 16 fps, where the template ships 81. 33 frames is 29 minutes on
this machine and 81 is over an hour. `length` must stay `4n+1`.

The original `LoadImage` is left in the graph, unwired, at the bottom of the "Start Image" group,
which is `/track-workflow`'s convention.

The template's `SaveAnimatedWEBP` is removed. It sets `fps` 6 against `CreateVideo`'s 16, and two
savers at two rates are two answers to one question. The publish node reads the rate off the clip it
is handed, so `CreateVideo`'s 16 is what is written to the Version.

## Models

No new download.

| slot | file | on disk | note |
|---|---|---|---|
| diffusion | `wan2.1_fun_camera_v1.1_1.3B_bf16.safetensors` | 3.0 GB | as the template asks |
| text encoder | `umt5_xxl_fp16.safetensors` | 11 GB | repointed, see below |
| clip vision | `clip_vision_h.safetensors` | 1.2 GB | as the template asks |
| vae | `wan_2.1_vae.safetensors` | 242 MB | as the template asks |

The template's `CLIPLoader` asks for `umt5_xxl_fp8_e4m3fn_scaled` (6.27 GB, not on this machine). The
template's model note lists `umt5_xxl_fp16.safetensors` as the alternative, so the loader is pointed
at the fp16 already in `models/text_encoders/`. It loads and runs. The fp16 is the larger of the two,
so a machine tight on memory wants the fp8 instead.

## The upgrade: `WanUni3CControlnetApply`

A named trajectory is a preset. It cannot match a real move, honour a lens, or account for the set
geometry the plate depicts. For a move that has to match the shot's camera the node is
`WanUni3CControlnetApply`, a core node (`comfy_extras/nodes_model_patch.py`, marked `EXPERIMENTAL`),
fed by `ModelPatchLoader` ("Load Model Patch") with the Uni3C controlnet weights. Its guidance input
is an IMAGE sequence: "the guidance video rendered from the camera trajectory, most commonly warped
point cloud renders of the input image." Export the camera, render or warp a guidance pass along it,
and Wan follows the pass. It also takes `strength`, `start_percent` and `end_percent`, so the move can
be dialled back where the plate falls apart.

It costs a Uni3C checkpoint and a guidance-render step upstream. This demo is the cheapest motion off
a still.

## One Version, one movie

A Version's media is single-valued (probe 022), so a sequence cannot be media. The publish node takes
the clip, not the batch, and creates one Version: the clip goes to `sg_uploaded_movie`, its first
frame goes to `image` so there is a thumbnail before the transcode finishes, and `sg_first_frame`,
`sg_last_frame`, `frame_count` and `frame_range` record the range.

The frame rate is measured, not assumed. `CreateVideo`'s VIDEO output is wired into the publish
node's `video`, and the rate is read off the clip rather than off a widget or a sibling node:

    review media: 33 frames at 16 fps — encoded by ComfyUI — VideoInput.save_to

Read back off the Version, `sg_uploaded_movie_frame_rate` is `16.0`. The seeded plate on the same
Shot reads `25.0`, which is what Flow Production Tracking stamps on a still it transcoded, so the two
are distinguishable on the site. That is why the node does not write the transcoder's fields.

Publishing the sequence as a sequence is a separate question: the frames are registered as
PublishedFiles under a LocalStorage root, alongside the Version with the clip for review. This
graph publishes the clip only. Wire the IMAGE batch into `images` as well and tick Create Published
Files to keep the frames.

## Flow Production Tracking, as run

| | |
|---|---|
| project | 1180, `comfyui-fpt sandbox` |
| shot | `demo_06_camera` (id 7644) |
| plate in | `demo_06_camera_plate_v001`, Version 31751, seeded from `input/fpt_plate_paris.png` |
| clip out | `demo_06_camera_push_in_v001`, Version 31851, one `.mp4`, 33 frames at 16 fps |
| status | Pending Review (`rev`) |
| name template | `{root_name}_v{version:03d}` |

Read back off Version 31851:

| field | value |
|---|---|
| `entity` | Shot 7644 `demo_06_camera` |
| `sg_uploaded_movie` | `demo_06_camera_push_in_v001.mp4` |
| `sg_uploaded_movie_frame_rate` | `16.0`, the rate the node encoded |
| `frame_range` / `frame_count` | `1-33` / `33` |
| `sg_ai_generated_from` | Version 31751 `demo_06_camera_plate_v001` |
| `sg_ai_generator` | `ComfyUI (unknown client)` |
| `sg_ai_model` | `wan2.1_fun_camera_v1.1_1.3B_bf16 \| umt5_xxl_fp16 \| wan_2.1_vae \| clip_vision_h` |
| `sg_ai_seed` | `606060606` |
| `sg_ai_sampler` | `uni_pc/simple` |
| `sg_ai_steps` / `sg_ai_cfg` | `20` / `6.0` |
| attachments | `..._v001.mp4`, `..._v001.provenance.json`, `..._v001.workflow.json` |

`sg_ai_model` names the encoder the run loaded, which is the record of the fp16 repoint. No id was
typed: the Load node resolved 31751 from newest plate on this shot and the publish node recorded it.

The plate was seeded with:

```sh
PYTHONPATH=src python -m comfyui_sg.seed ~/dev/ComfyUI/input/fpt_plate_paris.png \
  --project 1180 --link "demo_06_camera (Shot)" --root-name plate --note "..."
```

A seeded Version has no generation record, and the Load panel says so. The first graph in a chain
gets its plate into Flow Production Tracking before it can read it back out.

## Running it

```sh
tools/qa_node.py --start --port 8956 --repo <this checkout>
```

Then open `example_workflows/06_camera_move.json`.

- `--base-directory` relocates models as well as `custom_nodes`, `input`, `output`, `temp` and `user`
  (`folder_paths.py:15`). An isolated instance started that way has an empty model list and every
  loader fails validation. Add `--models-directory ~/dev/ComfyUI/models` and
  `--input-directory ~/dev/ComfyUI/input` to point them back at the real tree.
- The workflow attachment needs `EXTRA_PNGINFO`, which a client that sends `extra_data` supplies and
  the standard frontend does. A run driven straight at `/prompt` posts
  `extra_data.extra_pnginfo.workflow` itself or the publish reports "no workflow attached". This run
  posted it, and `..._v001.workflow.json` is on the Version.
- `SaveVideo`'s `format` is a `DynamicCombo` (`COMFY_DYNAMICCOMBO_V3`) with a nested `codec` input
  rather than a plain widget value. A litegraph-to-API converter that recognises only
  `INT`/`FLOAT`/`STRING`/`BOOLEAN`/combo-as-list drops both, and the node then raises
  `SaveVideo.execute() missing 1 required positional argument: 'format'` after everything upstream
  has run. Emit `format` and `codec` (`"auto"`/`"auto"` is what the graph has) and it writes its
  `.mp4`.

Cost, measured: 1758 s end to end. 20 steps at 832x480x33 frames is 28 minutes of sampling at about
85 s per step on an M4 Pro sharing the machine with other work, and the publish is seconds. Sampling
scales with `length`, so the template's 81 frames is about three times as long.
