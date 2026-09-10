# 01 Roto matte

Segment the subject of a plate from a text prompt and publish the matte as a Version that records
the plate Version it came from. Nothing here generates an image.

## What it demonstrates

- The input is a Flow Production Tracking Version, not a file on disk, and the output is a Version
  whose `sg_ai_generated_from` points at that input. Two graphs of this shape compose without
  anyone copying an id.
- `sg_ai_generator` and `sg_ai_model` are read from the executing prompt object.
- Provenance is per branch. The graph has two image streams, the published matte and the clip
  review, and only the matte is tapped, so the Version describes that branch.
- Core nodes only. No third-party packs.

## The graph

```
CheckpointLoaderSimple ──MODEL──┬──────────────────────────┐
  sam3.1_multiplex_fp16         │                          │
        └─CLIP→ CLIPTextEncode ─┼─CONDITIONING─┐           │
                  "the actor"   │              │           │
                                │              ↓           │
SG Load - plate ──IMAGE────┴────→ SAM3_Detect         │
  demo_01_roto_plate_v001                      ↓ masks     │
                                          MaskToImage      │
                                               ↓           │
                        ┌──────────────────────┴────┐      │
                  PreviewImage            Flow Production Tracking Publish   │
                                                            │
LoadVideo → GetVideoComponents ──images(24)────→ SAM3_Detect ┘
  demo_01_roto_plate.mp4                             ↓ masks(24)
                                                MaskToImage
                                                     ↓
                                               PreviewImage
```

Two branches, one prompt, one model. The upper branch is published: the plate Version is read out of
Flow Production Tracking, `SAM3_Detect` returns the mask for the words "the actor", and the matte
goes back as a Version. The lower branch runs the same prompt over the 24 frames of the clip.

`SAM3_Detect` takes the frame batch at once (`B,H,W,C`): per frame, open-vocabulary, no memory
between frames. That is how the core video template segments a clip.

## Mask coverage by prompt

Measured on this plate:

| prompt | coverage |
|---|---|
| `person` | 23.03% |
| `pedestrian` | 23.03% |
| `the actor` | 23.02% |
| `woman` | 23.01% |
| `the woman in the coat` | 22.32% |
| `man in a coat` | 17.05% |
| `person:1` | 0.16% |
| `figure` | 0.15% |

`the actor` is within 0.01% of `person`. `figure`, an equally plausible word at the same silhouette,
returns 0.15%, and the template's `:N` count syntax collapses the same mask to 0.16%. A prompt that
matches nothing produces a black matte, not an error, so a text prompt needs the preview checked
before the pass is used. Threshold 0.5 and 0.25 were identical on every prompt.

The same node takes `bboxes` and `positive_coords`, so a click is an alternative to a prompt.

## SAM3_VideoTrack returns nothing on this plate

`SAM3_Detect` found the subject on frame 1: 23% of frame, a correct silhouette. Fed in as
`initial_mask`, `SAM3_VideoTrack` returned no objects at `max_objects` 1 and at 0 (the model's cap of
64), with `object_indices` both empty and `0`, and the published matte was black both times.
`SAM3_TrackToMask` returns a zero mask where `track_data["packed_masks"]` is `None`, which is
consistent with the tracker producing nothing rather than producing something wrong. The failure is
silent: a black matte, a green execution, and a Version that reads as valid.

The per-frame path is what both core templates ship, and it works on this plate.

## Models

| model | file | size | licence |
|---|---|---|---|
| SAM 3.1 multiplex (fp16) | `models/checkpoints/sam3.1_multiplex_fp16.safetensors` | 1.63 GiB (1,745,546,848 bytes) | Meta SAM License, 19 Nov 2025 |

From [`Comfy-Org/sam3.1`](https://huggingface.co/Comfy-Org/sam3.1). Not gated, no token needed, a
plain `curl` of the `resolve/main` URL works. One checkpoint with MODEL, CLIP and VAE, so
`CheckpointLoaderSimple` is the only loader.

The licence permits commercial use and sets no user-count ceiling. It is not Apache or MIT, and its
terms are:

- Derivatives and redistribution stay under the same agreement, and a copy of it ships with them.
- Trade Controls: no ITAR-subject activity, no military or warfare purposes, no nuclear
  applications, no espionage, no guns or illegal weapons.
- No reverse engineering or decompiling of the materials.
- Published research using it acknowledges it.
- An IP claim against Meta over the materials terminates the licence.
- Governed by California law, no warranty, liability disclaimed.

Read it before this goes near a deliverable.

## What it publishes

One Version on Shot `demo_01_roto` in project 1180 (`comfyui-fpt sandbox`), named by the show's
convention `{root_name}_v{version:03d}`:

| | |
|---|---|
| Version code | `demo_01_roto_matte_v004` (id 31825) |
| media | the matte, as `image` and `sg_uploaded_movie` |
| `sg_ai_generator` | `ComfyUI (unknown client)` |
| `sg_ai_model` | `sam3.1_multiplex_fp16.safetensors` |
| `sg_ai_generated_from` | Version 31753, `demo_01_roto_plate_v001` |
| attachments | `.provenance.json`, `.workflow.json` |

### Why the published stream is one frame

The clip branch takes its frames from `LoadVideo` on disk, so it has no Version upstream of it and
its `sg_ai_generated_from` would be empty. The single-frame branch reads a Version, so it records
its ancestor.

The Load node now takes a `frame_count` beside `frame` and returns a batch, and a Version's
PublishedFiles are a source it reads a sequence from. The publish node turns an IMAGE batch into one
Version with an encoded movie. The clip branch can therefore take its frames from Flow
Production Tracking and publish a matte movie that names its plate. This graph is due a re-cut.

Typing the plate id into the publish node's `source_versions` is the id-copying this project removes.

### sg_ai_prompt

A prompt is text that reached a conditioning input, seed or no seed, so a re-run of this graph
records `the actor`. On Version 31825, `sg_ai_prompt`, `sg_ai_seed`, `sg_ai_sampler`, `sg_ai_steps`
and `sg_ai_cfg` are all null: the graph has no sampler and no seed, and the words are in a
`CLIPTextEncode`. The `.workflow.json` attachment records the prompt text.

### The plate

The plate is seeded once, because a chain starts somewhere:

```sh
PYTHONPATH=src python -m comfyui_sg.seed <frame1.png> --project 1180 \
  --link "demo_01_roto (Shot)" --root-name plate --note "..."
```

That Version has no AI fields and reads as `unrecorded` in the Load panel. A file on disk does not
record how it was made.

The Load node's `name_contains` is `plate`. Without it, "newest Version on this Shot" resolves to
what this graph published on its last run.

## Running it

1. `models/checkpoints/sam3.1_multiplex_fp16.safetensors`, as above.
2. Copy `example_workflows/demo_01_roto_plate.mp4` into `ComfyUI/input/`.
3. Seed a plate Version and point the Load node at it, or point it at your own.
4. Open `example_workflows/01_roto_matte.json`.

The plate clip here is a 24-frame, 24 fps, 832x480 push-in built over
`ComfyUI/input/fpt_plate_figure.png`. Frame 1 is the plate frame, which is what lets a mask found on
the plate Version line up with the clip. A real plate needs no change to the graph.

## Provenance

Adapted from the ComfyUI core templates `utility_image_segment_sam3` and `utility_video_segment_sam3`
([Comfy-Org/workflow_templates](https://github.com/Comfy-Org/workflow_templates), MIT), flattened out
of their subgraphs. `instrument.py` does not walk into a ComfyUI subgraph, so a graph that hides its
stream inside one reports nothing to publish.

The Flow Production Tracking nodes were added by the repo's own tool:

```sh
python src/comfyui_sg/instrument.py <base>.json --out example_workflows/01_roto_matte.json \
  --publish 10:0 --load 3 --project "comfyui-fpt sandbox" --link "demo_01_roto (Shot)"
```
