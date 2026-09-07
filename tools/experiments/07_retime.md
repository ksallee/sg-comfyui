# 07 — Retime

Retime a plate, or fill the frames the camera dropped, and publish the conformed result as a Version.

    24 fps plate  ->  FILM  ->  48 fps clip on disk + one Version in Flow PT

TD line: **"24 to 48, or patch the three frames the camera dropped."**

## What it demonstrates

That provenance tracking is not only for hallucinated pixels. This graph invents no content: FILM is
deterministic, takes two real frames and returns what was between them. There is no sampler, no
seed, no prompt — and a Version still comes out of it that somebody will ask about in three months.
A retimed plate is a delivery like any other.

It is also the workflow that gets an AI node adopted without an argument. Nobody debates a retime.

The second half of the TD line is the same graph with a different input: feed it the two frames
either side of a dropout instead of the whole clip, set the multiplier to the size of the hole, and
the frames it returns are the patch. Nothing else changes, including what gets recorded.

## The graph

Based on the core template `utility_video_frame_interpolation` (Comfy-Org/workflow_templates, MIT),
flattened out of its subgraph. Core nodes only — `comfy_extras/nodes_frame_interpolation.py`.

    LoadVideo (fpt_retime_plate.mp4, 12 frames @ 24 fps)
      -> GetVideoComponents            images, audio, fps
           -> FrameInterpolate         film_net_fp16, multiplier 2  -> 23 frames
                -> CreateVideo (fps x multiplier) -> SaveVideo      the conformed clip, on disk
                -> ImageFromBatch (index 1, length 1) -> PreviewImage
                                                     -> Flow PT Publish Version

The multiplier is one `PrimitiveInt` feeding both the interpolator and the output frame rate
(`ComfyMathExpression`, `a * b`), so 24 -> 48 cannot drift apart from 2x.

**Why the graph is flat.** The shipped template puts everything except `LoadVideo` and `SaveVideo`
inside a subgraph. Run as shipped, the analyser is not blind to it — it finds one stream, the
subgraph's own unconsumed IMAGE output, and names it `frame_interpolation`:

    utility_video_frame_interpolation.json: 4 nodes
      publishable streams (1):
        node 16[1] Frame Interpolation  (unconsumed)
            output_name='frame_interpolation'

— but that slot carries all 23 frames, and every node worth naming in the provenance is inside the
subgraph, which `instrument.py` could not walk into when this was written (it can now). Flattening is what lets
the stream be tapped at one frame, and lets a reader see what the graph does without opening it.

**Why one frame is published, not 23.** The publish path made one Version per frame when this graph
was cut.

> **Out of date, and this graph wants re-cutting.** A batch now publishes as one Version carrying an
> encoded movie, and `instrument.py` walks into subgraphs, so the tap this note asks for below is
> available: move the publish input from `ImageFromBatch` to `FrameInterpolate` and delete the
> single-frame branch. Tapping the retimed stream
directly would have made 23 Versions of one shot. So the tap is `ImageFromBatch` at index 1 — the
first frame FILM invented, the one frame in the clip that was not in the plate — and the conformed
clip itself is SaveVideo's output on disk. The alternative was to fake a movie Version, which is
exactly the kind of thing this repo does not do.

When the publish node learns to turn a batch into one Version carrying an encoded movie, the fix
here is to move the publish node's input from `ImageFromBatch` to `FrameInterpolate` and delete the
batch pick. The rest of the graph, and everything recorded, stays as it is.

## FILM, not RIFE

Both load in the same core node and both are small. The demo uses **FILM**
(`film_net_fp16.safetensors`, 0.06 GB) rather than RIFE (`rife_v4.26`, 0.02 GB) for licence reasons
a studio will be asked about:

- **FILM** is Google Research's `frame-interpolation`, **Apache-2.0** — a licence a facility's legal
  team already has an answer for.
- **RIFE**'s code is MIT, but upstream Practical-RIFE explicitly disclaims its pretrained weights and
  training data, which may carry further restrictions. The code licence is not the weights licence.
- The `Comfy-Org/frame_interpolation` repackage declares its licence as "other", so neither model's
  terms come from the mirror; they come from upstream.

Weights and code are separately licensed, and the weights are what ships in the render. For a demo
about being able to answer "what made this", the model whose provenance is answerable is the one to
put on screen.

Do **not** install `ComfyUI-Frame-Interpolation` for this. It drags in `cupy-wheel`, is
CUDA-version-sensitive, and core already has both models.

## What provenance looks like when nothing was generated

This is the clearest case in the demo set of the tool being honest about what it does and does not
know. Of the nine typed fields on Version, three fill and six stay empty — and every one of the six
is empty because the graph genuinely has no such value, not because anything failed:

| field | value | why |
|---|---|---|
| `sg_ai_generator` | `ComfyUI (comfyui-frontend)` | which generator, and which client submitted the prompt |
| `sg_ai_model` | `film_net_fp16.safetensors` | `FrameInterpolationModelLoader`'s `model_name` — `provenance.MODEL_KEYS` reads the generic key, so an auxiliary loader is a model like any other |
| `sg_ai_generated_from` | the plate Version | typed into `source_versions`; see below |
| `sg_ai_prompt` | empty | no conditioning in this graph |
| `sg_ai_negative_prompt` | empty | same |
| `sg_ai_seed` | empty | nothing is sampled; nothing is random |
| `sg_ai_sampler` | empty | there is no sampler |
| `sg_ai_steps` | empty | same |
| `sg_ai_cfg` | empty | same |

`fields.concepts` drops a concept whose value is empty rather than writing `""` or `0`, so the
Version carries no zero that could later read as a real setting. The `.provenance.json` attachment
says the same thing structurally: `samplers: []`, `loras: []`, one entry in `models`.

That is the behaviour to point at in a demo. A tool that filled `sg_ai_seed` with `0` here would be
lying quietly, in a field somebody would later quote.

## Lineage without a Load node

The plate is seeded into Flow PT first, so the chain starts somewhere:

    PYTHONPATH=src python -m comfyui_fpt.seed input/fpt_retime_plate_f001.png \
      --project 1180 --link "demo_07_retime (Shot)" --output plate --note "..."

The graph then names that Version in the publish node's `source_versions`, and it lands in
`sg_ai_generated_from`. The **Load node is deliberately absent**: this graph's input is a movie, and
`Flow PT Load Version` delivers a frame. Wiring it in would have meant retiming a still, which is
not a retime. `instrument.py` agrees — it reports zero image inputs a Load could replace, because
`LoadVideo` is not an image loader. The typed id is the documented path for exactly this: "a source
no upstream Load node can show".

The seeded plate Version reads as `unrecorded` in the Load panel — no AI fields — which is correct.
A file on disk does not say how it was made.

## The run

Project 1180 (`comfyui-fpt sandbox`), Shot `demo_07_retime` (7647). An isolated ComfyUI on port
8957 — its own `custom_nodes` and `user`, with `--input-directory`, `--output-directory` and
`--models-directory` pointed back at the real tree — with the graph opened in the editor and
started with Run, so the prompt carries `EXTRA_PNGINFO` and a real `COMFY_USAGE_SOURCE`.

    prompt executed in 14.18 s          12 frames in, 11 interpolation passes, 23 frames out
    ComfyUI/output/video/demo_07_retime_00001_.mp4    832x480, 23 frames, 48/1 fps

Versions on the Shot:

| Version | code | how it got there |
|---|---|---|
| 31754 | `demo_07_retime_plate_v001` | `comfyui_fpt.seed`, frame 1 of the source clip |
| 31790 | `demo_07_retime_retime_v001` | the publish node, status Pending Review |

31790 carries, in the three fields the graph could fill:

    sg_ai_generator       ComfyUI (comfyui-frontend)
    sg_ai_model           film_net_fp16.safetensors
    sg_ai_generated_from  [31754]

and nothing at all in `sg_ai_prompt`, `sg_ai_negative_prompt`, `sg_ai_seed`, `sg_ai_sampler`,
`sg_ai_steps`, `sg_ai_cfg`. The attached `.provenance.json` is the same statement in full:

    {"generator": "ComfyUI",
     "models": [{"node_id": "3", "class_type": "FrameInterpolationModelLoader",
                 "role": "model_name", "name": "film_net_fp16.safetensors"}],
     "loras": [], "samplers": [], "node_count": 7,
     "workflow_attached": true, "comfy_usage_source": "comfyui-frontend"}

`samplers: []` is the whole point of this workflow in one line. `node_count: 7` is the branch the
publish node walked — `LoadVideo`, `GetVideoComponents`, the FILM loader, the multiplier, the
interpolator, the batch pick, itself — and not `CreateVideo`, `SaveVideo` or the fps expression,
which are downstream or on another branch.

Attachments on the Version: `…_v001.png`, `…_v001.provenance.json`, `…_v001.workflow.json`, plus the
one-frame `.mp4` and thumbnail Flow PT transcodes for itself because the node uploads to
`sg_uploaded_movie` as well as `image`. That transcode is worth knowing about: a graph that publishes
a whole retimed sequence gets one Version *and one one-frame movie* per frame. Another reason this
one taps a single frame.

### How it reads on the node

Opened in the editor, the publish node answers the question before it is run:

    project   comfyui-fpt sandbox
    link      demo_07_retime (Shot)
    task      (none)
    status    Pending Review
    output    retime
    note      Retimed 24 -> 48 fps with FILM. ...

    Version Name  demo_07_retime_retime_v002
    Pending Review    VALID

`v002`, because `v001` is already on the Shot — `code = auto` counts per link, and the panel shows
the code that would actually be written rather than the template that produces it.

Behind **Show advanced inputs** is the concept-by-concept readout, which is where the honesty is
visible before anything runs. All nine are listed, not only the ones with a value
(`routes.preview_publish`):

    made by          ComfyUI (…)
    model            film_net_fp16.safetensors
    prompt                              nothing in this graph
    negative prompt                     nothing in this graph
    seed                                nothing in this graph
    sampler                             nothing in this graph
    steps                               nothing in this graph
    cfg                                 nothing in this graph
    generated from                      nothing in this graph
    description      Retimed 24 -> 48 fps with FILM. …      the note below
    sg_status_list   rev
    entity           Shot 7647
    sg_task                             no task

    uploads          image (thumbnail), sg_uploaded_movie, <name>.provenance.json,
                     <name>.workflow.json — only if this client sends EXTRA_PNGINFO

"nothing in this graph" beside six of the nine is the sentence this whole workflow exists to
produce. It is not an error state and it is not styled as one.

**One thing the panel gets wrong here**: `generated from` reads `nothing in this graph`, but the
published Version does carry `sg_ai_generated_from: [31754]`. `preview_publish` builds its lineage
from upstream `FPTLoadVersion` nodes only and never reads the `source_versions` widget, which the
publish path does read. The panel understates lineage whenever the operator typed the id by hand —
the one case this graph is in, because its input is a movie.

## What this ran into

- **The template is a subgraph.** Analysable, but only from the outside; see "Why the graph is flat".
- **One Version per frame, and one one-frame movie with it.** Flow PT transcodes whatever goes to
  `sg_uploaded_movie`, so a 23-frame publish would leave 23 Versions and 23 one-frame `.mp4`s behind.
  Nothing was published as a batch here; the tap is one frame, deliberately.

  **This workflow is the strongest argument for the movie-as-a-Version work**, stronger than any
  generative one can make. A retime's deliverable *is* the timing. Twenty-three separate Versions do
  not say 48 fps — they do not say anything about frame rate at all, which is the only thing the
  operation changed. And because the operation is deterministic, there is nothing else interesting to
  record instead: no seed, no prompt, no sampler. Take away the movie and the Version is a picture of
  a frame that was already nearly there. A single Version carrying the encoded clip, with Flow PT
  filling `_frame_rate` from it, is the whole record.
- **The panel understates hand-typed lineage.** See above: `preview_publish` reads Load nodes, the
  publish path also reads `source_versions`.
- **`tools/qa_node.py --start` came up with no models.** `--base-directory` resets *every* default
  path, `models` included (`folder_paths.py:15`), though its help text lists only custom_nodes,
  input, output, temp and user. Every loader's combo was empty and the prompt failed validation with
  `Value not in list: model_name: 'film_net_fp16.safetensors' not in []`. Fixed on `main` by passing
  `--models-directory` and `--input-directory` back at the real tree.
- **No Load node in the graph**, for the reason above — a movie in, a frame out of the Load node.

## Reproduce

The model, 0.06 GB, into `ComfyUI/models/frame_interpolation/`:

    curl -L -o ComfyUI/models/frame_interpolation/film_net_fp16.safetensors \
      https://huggingface.co/Comfy-Org/frame_interpolation/resolve/main/frame_interpolation/film_net_fp16.safetensors

The plate: any 24 fps clip in `ComfyUI/input/` named `fpt_retime_plate.mp4`, plus one frame of it as
a PNG to seed. The one used here is a 12-frame push-in cropped out of `fpt_plate_paris.png`:

    ffmpeg -framerate 24 -i f%03d.png -c:v libx264 -pix_fmt yuv420p -crf 16 \
      ComfyUI/input/fpt_retime_plate.mp4

Then the ordinary path — seed the plate, check what the analyser sees, open the graph:

    PYTHONPATH=src python -m comfyui_fpt.seed <frame>.png --project 1180 \
      --link "demo_07_retime (Shot)" --output plate --note "..."
    python src/comfyui_fpt/instrument.py example_workflows/07_retime.json \
      --template "{entity.code}_{output}_v{version:03d}"

`source_versions` on the publish node holds the seeded Version id and will need repointing at yours.
