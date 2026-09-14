# 07 Retime

Retime a plate, or fill the frames the camera dropped, and publish the conformed result as a Version.

    24 fps plate  ->  FILM  ->  48 fps clip on disk + one Version in Flow Production Tracking

## What it demonstrates

Provenance tracking on a graph that invents no content. FILM is deterministic: it takes two real
frames and returns what was between them. There is no sampler, no seed and no prompt, and a Version
still comes out of it.

The second use is the same graph with a different input: feed it the two frames either side of a
dropout, set the multiplier to the size of the hole, and the frames it returns are the patch. Nothing
else changes, including what is recorded.

## The graph

Based on the core template `utility_video_frame_interpolation` (Comfy-Org/workflow_templates, MIT),
flattened out of its subgraph. Core nodes only, `comfy_extras/nodes_frame_interpolation.py`.

    LoadVideo (fpt_retime_plate.mp4, 12 frames @ 24 fps)
      -> GetVideoComponents            images, audio, fps
           -> FrameInterpolate         film_net_fp16, multiplier 2  -> 23 frames
                -> CreateVideo (fps x multiplier) -> SaveVideo      the conformed clip, on disk
                -> ImageFromBatch (index 1, length 1) -> PreviewImage
                                                     -> SG Publish

The multiplier is one `PrimitiveInt` feeding both the interpolator and the output frame rate
(`ComfyMathExpression`, `a * b`), so 24 to 48 cannot drift apart from 2x.

### Why the graph is flat

Run as shipped, the analyser finds one stream in the template, the subgraph's own unconsumed IMAGE
output, and names it `frame_interpolation`:

    utility_video_frame_interpolation.json: 4 nodes
      publishable streams (1):
        node 16[1] Frame Interpolation  (unconsumed)
            output_name='frame_interpolation'

That slot is all 23 frames, and the nodes worth naming in the provenance are inside the
subgraph. Flattening lets the stream be tapped at one frame and lets a reader see what the graph does
without opening it.

### Why one frame is published, not 23

The tap is `ImageFromBatch` at index 1, the first frame FILM invented, and the conformed clip is
SaveVideo's output on disk. Tapping the retimed stream directly made one Version per frame when this
graph was cut.

A batch now publishes as one Version with an encoded movie, and `instrument.py` walks into
subgraphs. The re-cut is to move the publish input from `ImageFromBatch` to `FrameInterpolate` and
delete the single-frame branch. The rest of the graph, and everything recorded, stays as it is.

## FILM, not RIFE

Both load in the same core node and both are small. The demo uses FILM
(`film_net_fp16.safetensors`, 0.06 GB) rather than RIFE (`rife_v4.26`, 0.02 GB) for licence reasons:

- FILM is Google Research's `frame-interpolation`, Apache-2.0.
- RIFE's code is MIT, but upstream Practical-RIFE disclaims its pretrained weights and training data,
  which may impose further restrictions. The code licence is not the weights licence.
- The `Comfy-Org/frame_interpolation` repackage declares its licence as "other", so neither model's
  terms come from the mirror. They come from upstream.

Weights and code are separately licensed, and the weights are what ships in the render.

Do not install `ComfyUI-Frame-Interpolation` for this. It pulls in `cupy-wheel`, is
CUDA-version-sensitive, and core has both models.

## Provenance when nothing was generated

Of the nine typed fields on Version, three fill and six stay empty, and each of the six is empty
because the graph has no such value:

| field | value | why |
|---|---|---|
| `sg_ai_generator` | `ComfyUI (comfyui-frontend)` | which generator, and which client submitted the prompt |
| `sg_ai_model` | `film_net_fp16.safetensors` | `FrameInterpolationModelLoader`'s `model_name`. `provenance.MODEL_KEYS` reads the generic key, so an auxiliary loader is a model like any other |
| `sg_ai_generated_from` | the plate Version | typed into `source_versions`; see below |
| `sg_ai_prompt` | empty | no conditioning in this graph |
| `sg_ai_negative_prompt` | empty | same |
| `sg_ai_seed` | empty | nothing is sampled |
| `sg_ai_sampler` | empty | there is no sampler |
| `sg_ai_steps` | empty | same |
| `sg_ai_cfg` | empty | same |

`fields.concepts` drops a concept whose value is empty rather than writing `""` or `0`, so the
Version records no zero that could later read as a real setting. The `.provenance.json` attachment
says the same structurally: `samplers: []`, `loras: []`, one entry in `models`.

## Lineage without a Load node

The plate is seeded into Flow Production Tracking first, so the chain starts somewhere:

    PYTHONPATH=src python -m comfyui_sg.seed input/fpt_retime_plate_f001.png \
      --project 1180 --link "demo_07_retime (Shot)" --root-name plate --note "..."

The graph names that Version in the publish node's `source_versions`, and it is written to
`sg_ai_generated_from`. There is no Load node: this graph's input is a movie, and `SG Load` delivers
a frame, so wiring it in would mean retiming a still. `instrument.py` reports zero image inputs a
Load could replace, because `LoadVideo` is not an image loader. The typed id is the documented path
for a source no upstream Load node can show.

The seeded plate Version reads as `unrecorded` in the Load panel, with no AI fields. A file on disk
does not record how it was made.

## The run

Project 1180 (`comfyui-fpt sandbox`), Shot `demo_07_retime` (7647). An isolated ComfyUI on port 8957,
with its own `custom_nodes` and `user` and with `--input-directory`, `--output-directory` and
`--models-directory` pointed back at the real tree, the graph opened in the editor and started with
Run, so the prompt includes `EXTRA_PNGINFO` and a `COMFY_USAGE_SOURCE`.

    prompt executed in 14.18 s          12 frames in, 11 interpolation passes, 23 frames out
    ComfyUI/output/video/demo_07_retime_00001_.mp4    832x480, 23 frames, 48/1 fps

Versions on the Shot:

| Version | code | how it got there |
|---|---|---|
| 31754 | `demo_07_retime_plate_v001` | `comfyui_sg.seed`, frame 1 of the source clip |
| 31790 | `demo_07_retime_retime_v001` | the publish node, status Pending Review |

31790 records, in the three fields the graph could fill:

    sg_ai_generator       ComfyUI (comfyui-frontend)
    sg_ai_model           film_net_fp16.safetensors
    sg_ai_generated_from  [31754]

and nothing in `sg_ai_prompt`, `sg_ai_negative_prompt`, `sg_ai_seed`, `sg_ai_sampler`, `sg_ai_steps`,
`sg_ai_cfg`. The attached `.provenance.json`:

    {"generator": "ComfyUI",
     "models": [{"node_id": "3", "class_type": "FrameInterpolationModelLoader",
                 "role": "model_name", "name": "film_net_fp16.safetensors"}],
     "loras": [], "samplers": [], "node_count": 7,
     "workflow_attached": true, "comfy_usage_source": "comfyui-frontend"}

`node_count: 7` is the branch the publish node walked: `LoadVideo`, `GetVideoComponents`, the FILM
loader, the multiplier, the interpolator, the batch pick, and itself. It excludes `CreateVideo`,
`SaveVideo` and the fps expression, which are downstream or on another branch.

Attachments on the Version: `…_v001.png`, `…_v001.provenance.json`, `…_v001.workflow.json`, plus the
one-frame `.mp4` and thumbnail Flow Production Tracking transcodes for itself, because the node
uploads to `sg_uploaded_movie` as well as `image`. A graph that publishes a retimed sequence frame by
frame therefore gets one Version and one one-frame movie per frame.

### How it reads on the node

Opened in the editor, the publish node answers before it is run:

    project   comfyui-fpt sandbox
    link      demo_07_retime (Shot)
    task      (none)
    status    Pending Review
    output    retime
    note      Retimed 24 -> 48 fps with FILM. ...

    Version Name  demo_07_retime_retime_v002
    Pending Review    VALID

`v002`, because `v001` is already on the Shot: `code = auto` counts per link, and the panel shows the
code that would be written rather than the template that produces it.

Behind Show advanced inputs is the concept-by-concept readout. All nine are listed, not only the ones
with a value (`routes.preview_publish`):

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

"nothing in this graph" beside six of the nine is not an error state and is not styled as one.

The panel understates lineage here: `generated from` reads `nothing in this graph`, and the published
Version records `sg_ai_generated_from: [31754]`. `preview_publish` builds its lineage from upstream
`SGLoadVersion` nodes and does not read the `source_versions` widget, which the publish path reads.
The panel understates lineage wherever the operator typed the id, which is the case here, because the
input is a movie.

## What this ran into

- The template is a subgraph, analysable only from the outside. See "Why the graph is flat".
- Flow Production Tracking transcodes whatever goes to `sg_uploaded_movie`, so a 23-frame publish
  leaves 23 Versions and 23 one-frame `.mp4`s. The tap here is one frame.

  A retime's deliverable is the timing. Twenty-three separate Versions record nothing about frame
  rate, which is the only thing the operation changed, and the operation is deterministic, so there
  is no seed, prompt or sampler to record instead. One Version with the encoded clip, with Flow
  Production Tracking filling `_frame_rate` from it, is the record.
- `tools/qa_node.py --start` came up with no models. `--base-directory` resets every default path,
  models included (`folder_paths.py:15`), though its help text lists only custom_nodes, input,
  output, temp and user. Each loader's combo was empty and the prompt failed validation with
  `Value not in list: model_name: 'film_net_fp16.safetensors' not in []`. `--models-directory` and
  `--input-directory` point them back at the real tree.
- No Load node in the graph, for the reason above: a movie in, a frame out of the Load node.

## Reproduce

The model, 0.06 GB, into `ComfyUI/models/frame_interpolation/`:

    curl -L -o ComfyUI/models/frame_interpolation/film_net_fp16.safetensors \
      https://huggingface.co/Comfy-Org/frame_interpolation/resolve/main/frame_interpolation/film_net_fp16.safetensors

The plate: any 24 fps clip in `ComfyUI/input/` named `fpt_retime_plate.mp4`, plus one frame of it as
a PNG to seed. The one used here is a 12-frame push-in cropped out of `fpt_plate_paris.png`:

    ffmpeg -framerate 24 -i f%03d.png -c:v libx264 -pix_fmt yuv420p -crf 16 \
      ComfyUI/input/fpt_retime_plate.mp4

Then seed the plate, check what the analyser sees, and open the graph:

    PYTHONPATH=src python -m comfyui_sg.seed <frame>.png --project 1180 \
      --link "demo_07_retime (Shot)" --root-name plate --note "..."
    python src/comfyui_sg/instrument.py example_workflows/07_retime.json \
      --template "{root_name}_v{version:03d}"

`source_versions` on the publish node has the seeded Version id and needs repointing at yours.
