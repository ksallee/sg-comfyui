# 01 — Roto matte

> Type "the actor" and get a matte — no shapes, no keyframes.

Roto is the biggest fixed cost in comp, and it is the first thing a supervisor judges. This graph
takes a plate that is already a Version in Flow Production Tracking, segments the subject from a text prompt, and
publishes the matte back as a Version that records the plate it came from.

Nothing here generates an image. The point is the trail: the published matte carries the model, the
client that submitted it, the whole workflow as an attachment, and a link back to the plate Version —
so six months later "how was this matte made" has an answer.

## What it demonstrates

- **A chain, not a one-shot.** The graph's input is a Flow Production Tracking Version, not a file on disk. Its output
  is a Flow Production Tracking Version whose `sg_ai_generated_from` points at that input. Two graphs like this
  compose without anyone copying an id.
- **Provenance from the graph, not from the artist.** `sg_ai_generator` and `sg_ai_model` come out of
  the executing prompt object. Nobody typed them.
- **Branch-scoped provenance.** The graph has two image streams — the published matte and the
  whole-clip review — and only one is tapped. The Version describes the branch that made *it*.
- **Core nodes only.** No third-party packs. Anyone with a current ComfyUI can open this.

## The graph

```
CheckpointLoaderSimple ──MODEL──┬──────────────────────────┐
  sam3.1_multiplex_fp16         │                          │
        └─CLIP→ CLIPTextEncode ─┼─CONDITIONING─┐           │
                  "the actor"   │              │           │
                                │              ↓           │
SG Load — plate ──IMAGE────┴────→ SAM3_Detect         │
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

Two branches, one prompt, one model. The upper one is what gets published: the plate Version comes
out of Flow Production Tracking, `SAM3_Detect` answers *which pixels are him* from the words "the actor", and the
matte goes back as a Version. The lower one runs the same prompt across all 24 frames of the clip so
a supervisor can see the matte hold before approving anything.

`SAM3_Detect` takes the whole frame batch at once (`B,H,W,C`), which is how the core video template
segments a clip: per frame, open-vocabulary, no memory between frames.

### The prompt is the interface, and the word matters

The pitch is "type it or click it once" — the same node takes `bboxes` / `positive_coords` instead,
so a click works as well as a prompt. That was worth measuring rather than assuming. Mask coverage on
this plate, by prompt:

| prompt | coverage |
|---|---|
| `person` | 23.03% |
| `pedestrian` | 23.03% |
| `the actor` | **23.02%** |
| `woman` | 23.01% |
| `the woman in the coat` | 22.32% |
| `man in a coat` | 17.05% |
| `person:1` | 0.16% |
| `figure` | 0.15% |

`the actor` lands within 0.01% of `person`, so the demo's own line is honest — an abstract,
role-shaped phrase does as well as the concrete noun. But `figure`, an equally reasonable thing for a
comp artist to type at the same silhouette, returns essentially nothing. **The vocabulary is not
uniform, and a prompt that fails fails silently — as a black matte, not an error.** Two things follow
for a supervisor: the click path is the reliable one, and any text prompt wants eyes on the preview
before the pass is trusted. The template's `:N` count syntax is not a free addition either —
`person:1` collapses the same mask to 0.16%. Threshold changed nothing: 0.5 and 0.25 were identical
on every prompt.

### SAM3_VideoTrack is not in this graph, and that is a finding

The obvious build is the fancier one: detect on frame 1, then propagate through the clip with
`SAM3_VideoTrack`'s memory tracker. It was built that way first and **it does not work on this
plate**. `SAM3_Detect` found the subject cleanly on frame 1 — 23% of frame, a correct silhouette —
fed it in as `initial_mask`, and the tracker returned no objects at all. The published matte came
back entirely black, twice, at `max_objects` 1 and 0 (the model's own cap of 64), with `object_indices`
both empty and `0`. `SAM3_TrackToMask` returns a zero mask when `track_data["packed_masks"]` is
`None`, which is consistent with the tracker producing nothing rather than producing something wrong.

Not chased further — the per-frame path is what both core templates actually ship, and it works. But
anyone reaching for `SAM3_VideoTrack` should know it can fail this way, and that it fails *silently*:
a black matte, a green execution, and a Version that looks fine until someone opens it.

## Models

| model | file | size | licence |
|---|---|---|---|
| SAM 3.1 multiplex (fp16) | `models/checkpoints/sam3.1_multiplex_fp16.safetensors` | 1.63 GiB (1,745,546,848 bytes) | Meta **SAM License**, 19 Nov 2025 |

From [`Comfy-Org/sam3.1`](https://huggingface.co/Comfy-Org/sam3.1) — not gated, no token needed, a
plain `curl` of the `resolve/main` URL works. One checkpoint carrying MODEL, CLIP and VAE, so
`CheckpointLoaderSimple` is the only loader.

**The licence permits commercial use and has no user-count ceiling, but it is not Apache/MIT and the
carve-outs are real:**

- Derivatives and redistribution stay under the same agreement, and you must ship a copy of it.
- Trade Controls: no ITAR-subject activity, no military or warfare purposes, no nuclear applications,
  no espionage, no guns or illegal weapons.
- No reverse engineering or decompiling of the materials.
- Research you publish using it must acknowledge it.
- Bringing an IP claim against Meta over the materials terminates your licence.
- Governed by California law, no warranty, liability disclaimed.

A studio should read it before this goes near a deliverable. "Commercial use permitted" is true and
is not the whole sentence.

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

### Why the published stream is one frame and not the clip

The publish node now turns a whole IMAGE batch into **one** Version carrying an encoded movie, so
"24 frames means 24 Versions" is no longer a reason to publish a single frame. For roto, a matte
*movie* is plainly the better deliverable. This graph still publishes the single-frame branch, for a
different reason worth stating plainly:

**`SG Load` returned exactly one frame when this graph was cut.** It read one image out
of a Version — a `frame` widget, no range.

> **Out of date, and this graph wants re-cutting.** The Load node now takes a `frame_count` beside
> `frame` and returns a batch, and a Version's PublishedFiles are a source it can read a sequence
> from. Both blockers below are gone: the clip branch can take its frames from Flow Production Tracking and publish a
> matte movie that knows its plate. The reasoning is kept because it is why the graph looks like this. So the clip branch, which gets its frames from `LoadVideo` on disk,
has no Flow Production Tracking Version anywhere upstream of it. Publishing that branch would produce a handsome
24-frame matte movie with an **empty `sg_ai_generated_from`** — a matte that cannot say which plate
it came from. In a repo whose entire purpose is the trail, that is the wrong trade: the single frame
that knows its ancestor beats the movie that does not.

The fix is not in the publish node, it is in the Load node — a Version that can deliver a *sequence*
into the graph. Until then, a graph whose input genuinely comes from Flow Production Tracking is a single-frame graph,
and that is the honest shape of this demo. Typing the plate id into the publish node's
`source_versions` would paper over it, and is exactly the id-copying this project exists to remove.

**`sg_ai_prompt` comes back empty, and that is a real gap, not a misconfiguration.**
`provenance.extract` used to reach for conditioning text only from a node carrying a *seed* — it
walked `positive`/`negative` back from a sampler. **That is fixed**: a prompt is now text that reached
a conditioning input, seed or no seed, so a re-run of this graph records `the actor`. A roto graph has no sampler and no seed, so the words
"the actor" sit in a `CLIPTextEncode` the extractor never visits, and `sg_ai_prompt`, `sg_ai_seed`,
`sg_ai_sampler`, `sg_ai_steps` and `sg_ai_cfg` are all null. Four of those five are honestly empty —
this graph samples nothing. The prompt is not: it is the single most important thing about this
Version, it is right there in the graph, and the extractor is shaped like a diffusion pipeline rather
than like "a graph that has text in it". The `.workflow.json` attachment does carry it, so nothing is
lost, but the queryable field a supervisor would filter on is blank.

The plate it reads is seeded once, by hand, because a chain has to start somewhere:

```sh
PYTHONPATH=src python -m comfyui_sg.seed <frame1.png> --project 1180 \
  --link "demo_01_roto (Shot)" --root-name plate --note "..."
```

That Version carries **no AI fields** and reads as `unrecorded` in the Load panel — a file on disk
does not say how it was made, and inventing a provenance for it would defeat the point.

The Load node's `name_contains` is set to `plate`. Without it, "newest Version on this Shot" is
whatever this graph published last run, and the roto would start from its own output.

## Running it

1. `models/checkpoints/sam3.1_multiplex_fp16.safetensors` — see above.
2. Copy `example_workflows/demo_01_roto_plate.mp4` into `ComfyUI/input/`.
3. Seed a plate Version and point the Load node at it, or repoint the node at your own.
4. Open `example_workflows/01_roto_matte.json`.

The plate clip shipped here is a 24-frame, 24 fps, 832×480 push-in built over
`ComfyUI/input/fpt_plate_figure.png`, because the machine this was built on had no video plate at
all. Frame 1 is the plate frame exactly, which is what lets a mask found on the plate Version line up
with the clip. Swap in a real plate and nothing about the graph changes.

## Provenance

Adapted from the ComfyUI core templates `utility_image_segment_sam3` and `utility_video_segment_sam3`
([Comfy-Org/workflow_templates](https://github.com/Comfy-Org/workflow_templates), MIT), flattened out
of their subgraphs — `instrument.py` does not walk into a ComfyUI subgraph yet, so a graph that hides
its stream inside one reports nothing to publish.

The Flow Production Tracking nodes were added by the repo's own tool, not by hand:

```sh
python src/comfyui_sg/instrument.py <base>.json --out example_workflows/01_roto_matte.json \
  --publish 10:0 --load 3 --project "comfyui-fpt sandbox" --link "demo_01_roto (Shot)"
```
