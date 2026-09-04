# 02 — utility passes

**The plate never went through 3D and comp still gets a Z and an N.**

Depth, normals and an alpha off one photographic still. No render layers, no CG, no 3D package
anywhere in the chain — and the three passes come out of Flow PT as three Versions that all cite the
plate they were derived from.

Studios care because it unlocks relight, atmos-by-depth, defocus and depth holdouts on plates that
have no render layers to hand them over: stock, an archive shot, a second unit that never went
through layout.

## What it demonstrates

**Fan-out.** One image in, *three* Versions out. This is the workflow that exists to show it. Each
Publish node taps a different stream and creates its own Version on the same Shot, in one run, from
one queue.

**Per-branch provenance.** The Publish node takes `UNIQUE_ID` and walks back through its own inputs
(`provenance.ancestors`), so each Version describes only what produced *its* image. The depth
Version names Depth Anything 3 and nothing else; the normals Version names MoGe-2 and nothing else;
the alpha Version names the SAM3 checkpoint and nothing else. Three models are loaded in the same
graph and none of the three Versions claims another's.

**Lineage nobody types.** The plate is read back out of Flow PT by a Load node — the rule is
"newest Version on `demo_02_passes` whose name contains `plate`", not an id — so all three Versions
record `sg_ai_generated_from` pointing at that same source Version.

## Models

Nothing to download. The two geometry models live in `ComfyUI/models/geometry_estimation/` and the
SAM3 checkpoint in `ComfyUI/models/checkpoints/`.

| pass | nodes | model |
|---|---|---|
| depth | `DA3Inference` / `DA3Render` | `depth_anything_3_mono_large.safetensors` |
| normal_opengl | `MoGeInference` / `MoGeRender` | `moge-2-vitl-normal.pt` |
| alpha | `SAM3_Detect` + `InvertMask` + `JoinImageWithAlpha` | `sam3.1_multiplex_fp16.safetensors` |

The plate is `ComfyUI/input/fpt_plate_figure.png` — a figure on a street, which gives the depth pass
a real gradient, the normals something with shape in them, and SAM3 something worth cutting out.

Core nodes only — nothing from a third-party pack. The graph is flat rather than built out of the
subgraphs the shipped templates use, because `instrument.py` cannot walk into a subgraph and would
have found no publishable stream at all.

`MoGePointMapToMesh` → `SaveGLB` hangs off the same MoGe geometry: the "and here it is in 3D"
moment. It publishes nothing; it is there to make the point that the geometry is real.

## What it publishes

Three Versions on Shot `demo_02_passes` in project 1180, named by the show's convention
(`{entity.code}_{output}_v{version:03d}`), each `Pending Review`:

| stream | Version | `sg_ai_model` |
|---|---|---|
| depth | `demo_02_passes_depth_v001` (31822) | `depth_anything_3_mono_large.safetensors` |
| normal_opengl | `demo_02_passes_normal_opengl_v001` (31820) | `moge-2-vitl-normal.pt` |
| alpha | `demo_02_passes_alpha_v001` (31821) | `sam3.1_multiplex_fp16.safetensors` |

Three models loaded in one graph, three Versions, and not one of them names another's model. That
column is the whole demonstration.

All three carry `sg_ai_generated_from` → `demo_02_passes_plate_v001` (Version 31756), the seeded
plate, `sg_ai_generator` → `ComfyUI (unknown client)`, and the whole structure as a
`.provenance.json` attachment beside a `.workflow.json`.

`sg_ai_prompt`, `sg_ai_seed`, `sg_ai_sampler`, `sg_ai_steps` and `sg_ai_cfg` are empty on all three,
and correctly so: nothing here samples. `provenance.extract` reads text conditioning back from a
sampler's `positive`/`negative`, so the SAM3 text prompt that decides what gets cut is not recorded
as a prompt. Worth knowing before someone reads an empty `sg_ai_prompt` as a bug.

Two notes on the alpha:

- It uses `SAM3_Detect`, not `SAM3_TrackToMask`. `TrackToMask` reads `SAM3_TRACKS` out of
  `SAM3_VideoTrack` and is the video path; on a still, `SAM3_Detect` is the node that gives a `MASK`.
- `InvertMask` sits between them because `JoinImageWithAlpha` does `alpha = 1.0 - mask`
  (`nodes_compositing.py:206`) — ComfyUI's `MASK` means *masked out*. Without it the figure is the
  transparent part and the street is the matte, which is the wrong way round for a holdout. The
  shipped SAM3 template has the same shape and the same result.

## How it was made

    python3 src/comfyui_fpt/instrument.py 02_base.json \
      --publish 11:0 --publish 21:0 --publish 42:0 --load 4 \
      --project "comfyui-fpt sandbox" --link "demo_02_passes (Shot)" \
      --out demo/02_utility_passes.json

The plate was seeded first, because a graph that reads from disk cannot be pointed at Flow PT until
what it reads is *in* Flow PT:

    PYTHONPATH=src python -m comfyui_fpt.seed ~/dev/ComfyUI/input/fpt_plate_figure.png \
      --project 1180 --link "demo_02_passes (Shot)" --output plate --note "..."

`instrument.py` leaves the replaced `LoadImage` in place but unwired, so an operator can see what was
swapped. It is deleted here: in a demo file an unwired loader reads as a fourth publishable stream.
