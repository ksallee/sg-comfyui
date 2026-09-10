# 02 Utility passes

Depth, normals and an alpha off one photographic still, published as three Versions that each name
the plate they were derived from. No render layers, no CG, no 3D package in the chain.

The passes unlock relight, atmos-by-depth, defocus and depth holdouts on plates with no render
layers: stock, an archive shot, a second unit that never went through layout.

## What it demonstrates

- Fan-out. One image in, three Versions out. Each Publish node taps a different stream and creates
  its own Version on the same Shot, in one run, from one queue.
- Per-branch provenance. The Publish node takes `UNIQUE_ID` and walks back through its own inputs
  (`provenance.ancestors`), so each Version describes what produced its own image. The depth Version
  names Depth Anything 3, the normals Version names MoGe-2, the alpha Version names the SAM3
  checkpoint. Three models are loaded in one graph and no Version names another's.
- Lineage nobody types. The plate is read back out of Flow Production Tracking by a Load node on the
  rule "newest Version on `demo_02_passes` whose name contains `plate`", so all three Versions record
  `sg_ai_generated_from` pointing at that source Version.

## Models

Nothing to download. The two geometry models are in `ComfyUI/models/geometry_estimation/` and the
SAM3 checkpoint in `ComfyUI/models/checkpoints/`.

| pass | nodes | model |
|---|---|---|
| depth | `DA3Inference` / `DA3Render` | `depth_anything_3_mono_large.safetensors` |
| normal_opengl | `MoGeInference` / `MoGeRender` | `moge-2-vitl-normal.pt` |
| alpha | `SAM3_Detect` + `InvertMask` + `JoinImageWithAlpha` | `sam3.1_multiplex_fp16.safetensors` |

The plate is `ComfyUI/input/fpt_plate_figure.png`, a figure on a street: a gradient for the depth
pass, shape for the normals, and a subject for SAM3.

Core nodes only, no third-party pack. The graph is flat rather than built out of the subgraphs the
shipped templates use, because `instrument.py` cannot walk into a subgraph and would have found no
publishable stream.

`MoGePointMapToMesh` into `SaveGLB` runs off the same MoGe geometry and publishes nothing.

## What it publishes

Three Versions on Shot `demo_02_passes` in project 1180, named by the show's convention
(`{root_name}_v{version:03d}`), each `Pending Review`:

| stream | Version | `sg_ai_model` |
|---|---|---|
| depth | `demo_02_passes_depth_v001` (31822) | `depth_anything_3_mono_large.safetensors` |
| normal_opengl | `demo_02_passes_normal_opengl_v001` (31820) | `moge-2-vitl-normal.pt` |
| alpha | `demo_02_passes_alpha_v001` (31821) | `sam3.1_multiplex_fp16.safetensors` |

All three record `sg_ai_generated_from` as `demo_02_passes_plate_v001` (Version 31756), the seeded
plate, and `sg_ai_generator` as `ComfyUI (unknown client)`, with a `.provenance.json` attachment
beside a `.workflow.json`.

`sg_ai_prompt`, `sg_ai_seed`, `sg_ai_sampler`, `sg_ai_steps` and `sg_ai_cfg` are empty on all three:
nothing here samples. `provenance.extract` reads text conditioning back from a sampler's
`positive`/`negative`, so the SAM3 text prompt that decides what is cut out is not recorded as a
prompt.

Two notes on the alpha:

- It uses `SAM3_Detect`, not `SAM3_TrackToMask`. `TrackToMask` reads `SAM3_TRACKS` out of
  `SAM3_VideoTrack` and is the video path. On a still, `SAM3_Detect` is the node that returns a
  `MASK`.
- `InvertMask` is between them because `JoinImageWithAlpha` does `alpha = 1.0 - mask`
  (`nodes_compositing.py:206`): ComfyUI's `MASK` means masked out. Without it the figure is the
  transparent part and the street is the matte, which is the wrong way round for a holdout. The
  shipped SAM3 template has the same shape and the same result.

## How it was made

    python3 src/comfyui_sg/instrument.py 02_base.json \
      --publish 11:0 --publish 21:0 --publish 42:0 --load 4 \
      --project "comfyui-fpt sandbox" --link "demo_02_passes (Shot)" \
      --out example_workflows/02_utility_passes.json

The plate was seeded first, because a graph that reads from disk cannot be pointed at Flow
Production Tracking until what it reads is in Flow Production Tracking:

    PYTHONPATH=src python -m comfyui_sg.seed ~/dev/ComfyUI/input/fpt_plate_figure.png \
      --project 1180 --link "demo_02_passes (Shot)" --root-name plate --note "..."

`instrument.py` leaves the replaced `LoadImage` in place but unwired, so an operator can see what was
swapped. It is deleted here: in a demo file an unwired loader reads as a fourth publishable stream.
