# Flow Production Tracking for ComfyUI

Two ComfyUI nodes that publish a generation to Flow Production Tracking (formerly ShotGrid) as a
Version, carrying the model, prompt, seed, sampler and workflow that produced it, and load a Version's
media back into a graph so the next step records what it came from. It makes no images; it records the
ones you already make.

Everything site-specific — what a Version hangs off, what it is called, which statuses exist, where
each piece of provenance lands — is measured from your site and written to a profile you can edit. No
studio's conventions are hardcoded.

## What it needs

- **ComfyUI 0.34.0 or newer.** The nodes read and write media through ComfyUI's own encoder and
  decoder, which is where 16-bit PNG and EXR come from. An older ComfyUI has neither, so the format
  widget has nothing to write with.
- **Python 3.11**, which is the interpreter ComfyUI itself runs on. You do not install a second one.
- **A Flow Production Tracking site you can log into.** At a workstation the nodes publish as you:
  click Log in under Settings, then SG, and approve the request in your browser. A render farm, and a
  machine nobody signs in on, takes a script name and application key instead, made under Admin >
  Scripts. That script needs to read Projects, Versions, Tasks and whatever entities you link to, and
  to create Versions and upload media.
- **`sg-groundtruth`**, the API client, from PyPI. `requirements.txt` names it, and both install paths
  below install that file.

## Install

Two paths. Both end in a restart of ComfyUI.

**ComfyUI-Manager, or the command line.** The pack is not on the Comfy Registry yet. It will be
published there as `sg-comfyui`, and this is the path once it is:

```sh
comfy node install sg-comfyui
```

Until then it says the node was not found, and you clone it instead.

**A git clone into `custom_nodes`.**

```sh
cd ComfyUI/custom_nodes
git clone https://github.com/ksallee/sg-comfyui.git
cd sg-comfyui
<comfy-python> -m pip install -r requirements.txt
```

`<comfy-python>` is the interpreter ComfyUI itself runs on, `ComfyUI/venv/bin/python` or whatever
launches `main.py`. Installing into the wrong one is the single way this fails quietly: the pack
imports and the site never answers. `tools/doctor.py` names the interpreter it is run with and says
whether the client is importable there. INSTALL.md has the one command that proves it.

## First run

1. **Connect.** Restart ComfyUI, open **Settings, then SG**, and put your site address under
   Connection. Then either click **Log in** under Log In As Yourself and approve the request in the
   browser tab that opens, or enter a Script name and Application key under Script Authentication.
   **Test** asks the site to confirm who the nodes publish as.
2. **Pick the project.** Under SG Defaults, choose the project both nodes open on. The publish
   defaults below it are for that project: root name, version name, status, storage, and where
   Published Files land.
3. **Open the example.** In the Templates browser, category **sg-comfyui**, open `00_example`. Typing
   **SG** into the node search finds both nodes on their own, under the category Flow Production
   Tracking.

The example opens with a still on the top row and a sequence on the bottom. Each SG Publish node
shows a panel: the Version name it would create, where the files would land, and what provenance it
found on its branch. It sends nothing until a project and a link are picked, and Create Published
Files is off on the top row, so nothing is written to disk. Each SG Load node names the Version it
would read, its format and its frame range, before you run it.

Restart ComfyUI only to install or upgrade the pack. A later edit to the profile reaches the editor on
a **browser refresh**, because `INPUT_TYPES` is re-evaluated on every `/object_info` request.

## Optional setup

Three things, each worth doing when the sentence below it describes you.

**Measure your site.** Do this when your show names its Versions to a convention, hangs them off
something other than a Shot, or hides statuses the site's schema still lists. `/inspect-site` drives
the inspector in the `sg-groundtruth` checkout, prints what it measured with the evidence beside it,
and writes `profile.local.json`. Without it the pickers run on the site's own defaults, which suit a
Shot-linked show. INSTALL.md says where the checkout goes and how to run the inspector without an
agent. You do not need this to publish.

**Create the provenance fields.** Do this when you want the nine AI fields queryable on Version, in
a filter or a page layout. Open **Settings, then SG, SG Site Setup**: it reads how many of the nine
exist on this site and creates the rest at one press. It reads the schema first and creates only what
is missing, so pressing it twice is safe. A farm, or a checkout with no browser on it, runs the same
thing from the command line:

```sh
PYTHONPATH=src <comfy-python> -m comfyui_sg.fields
```

It needs no torch, so any Python with `requirements.txt` installed runs it, and it reads a script key
from `.env.local` rather than from Settings. That key has to be allowed to create fields on Version,
which most artist accounts are not.
Without the fields a publish records everything anyway, in the Version's description. Field names are
permanent: deleting a field frees the field but never its name, and trashed fields cannot be listed,
so a name spent here is spent site-wide forever (probe 019). Pointing the profile's `provenance.map`
at fields your studio already has is the preferred move. You do not need this to publish.

**Colour management.** Do this when your pipeline is colour managed. Core ComfyUI has none, and the
shipped templates use core nodes only so that anyone can open them. Install the
[ComfyUI-OCIO](https://github.com/SlavaSexton/ComfyUI-OCIO) pack, set `OPENCV_IO_ENABLE_OPENEXR=1` in
the environment that launches ComfyUI, and put `ffmpeg` on the path. You do not need this to publish.

`/setup` walks all of this with an agent and asks only what it cannot find out.

## The two nodes

**SG Publish** — an IMAGE or a VIDEO in, a Version out: created, media uploaded, provenance attached.
You give it a project, what the Version hangs off, optionally a Task and a status, the root name that
says what the stream *is* (`{entity}_depth`, `{entity}_matte`), and a version name built on it
(`{root_name}_v{version:03d}`). The project, link, Task and status lists are your site's real ones,
read live. The version number is picked per link and per root name, so two graphs chain without
anyone copying an id.

An empty root name or version name means Settings names it, so a Settings change reaches every saved
graph and every shipped template. The panel shows the template in force, tagged Settings. Press
**Fill from SG defaults** to write those values into the node and edit from them.

Two inputs, `images` and `video`, and at least one of them wired. What you wire is what the Version
carries, so there is no combo asking you to say it again:

| `images` | `video` | the Version's media | registered as files, when the box is ticked |
|---|---|---|---|
| — | wired | that clip | the clip |
| wired | — | frame 1, as a still | the frames |
| wired | wired | the clip | the frames, and the clip where your profile keeps it |
| — | — | the run refuses, and says so | — |

**`format`** decides how the frames are written: 8-bit PNG, 16-bit PNG, or EXR 32-bit float. They are
written by ComfyUI's own encoder, and the extension follows the format rather than the template.
Review media stays 8-bit PNG whatever the frames are, because it is what a browser shows. EXR pixels
are written through unchanged and nothing converts them; the `colour_space` widget is the record of
what they already are, and the Version's description says what was declared.

**The clip is never re-encoded when it does not have to be.** A `VIDEO` off `LoadVideo`, or off any
node that hands you a file, goes up as that file, byte for byte, at its own extension. Anything else,
such as a `CreateVideo` assembling a batch or a hosted model answering with frames, is written by
ComfyUI's own `VideoInput.save_to()`, which carries the colour space, the bit depth and the audio.
The panel says which of the two happened. There is no `fps` widget: a `VIDEO` states its own rate,
and `CreateVideo` is where you set one.

An IMAGE batch of more than one frame is not media, because a Version's media is single-valued
(probe 022). With **Create Published Files** off the run refuses rather than uploading frame 1 and
dropping the rest. Tick the box to register the sequence, or send the batch through `CreateVideo`.

Provenance is scoped per branch, not per graph: the node walks back through its own inputs, so three
lookdev variants off a shared depth pass each record only what produced their own image.

**SG Load** — a Version's media back into the graph, and the link recorded. The inputs are a rule an
artist would say out loud, *the newest approved depth on this shot*, rather than an id. An id
(`pin_version_id`) is the escape hatch. Anything published downstream records the Version it came
from, without anyone typing an id.

Media is decoded by ComfyUI's own decoder, so 16-bit PNG and EXR come back at full precision. The
panel states the format of what it will read before you run it, for example `16-bit PNG, RGBA,
1920x1080, 48 frames`, with the colour space the publisher declared.

Two media outputs, and each takes the best the Version has on its own:

| output | takes, in order |
|---|---|
| `image` | the sequence, as a Published File then as path to frames; else a clip decoded; else the uploaded still; else the thumbnail |
| `video` | a Movie Published File; else path to movie; else the uploaded mp4, untouched; else the frames wrapped at the Version's frame rate, or 24 fps when it records none |

`mask` is the last output and comes off the alpha channel, on ComfyUI's own convention of `1 - alpha`.
A source with no alpha gives a 64x64 zero mask, which is what core Load Image gives.

A Published File beats a path field of the same shape because it carries a type, a path per platform
and the declared colour space. A file on a root this machine has not mounted does not count, so a
laptop without the storage falls through to the upload by itself. The site's own transcode is never
read: it is derived from the upload, lags it, and can describe a file that was replaced. The panel
shows what each output will take before you run.

`source`, in the fold, is the override: pick one file and both outputs read it. Where a Version
published several, each is its own choice named by type and filename,
`Rendered Image · sh010_comp_v003.%04d.png #6843` beside `Movie · sh010_comp_v003.mp4 #6844`, so the
rendered sequence and the mp4 are told apart at a glance.

`frame` is the first frame and `frame_count` is how many, as one IMAGE batch, which is what makes a
loaded clip a real input to a video graph.

`frame` is the frame **number**, the one in the filename: `1003` means `plate.1003.exr`, not the
1003rd file. Leave it at **0** and it starts wherever the sequence starts, which is what a 1001-based
plate wants and why it usually needs no typing at all. The panel shows the range the source actually
has, so you are not guessing. Ask for a frame that is not there and it is refused, naming the range;
it will never quietly hand back a different frame. `frame_count` **0**, the default, reads to the
end. The ceiling is a size rather than a count: past 4 GiB of float32 the node refuses and says how many frames fit at that
resolution, instead of running out of VRAM. Frames of differing resolution cannot stack and are
refused by name.

`colour_space` comes back as an output and on the panel when the publisher declared one. Read back,
never applied: nothing here converts, and a Version that declared nothing says nothing.

## Where provenance lands

Nine typed fields on Version, created under Settings, then SG, SG Site Setup:

| field | programmatic name | from |
|---|---|---|
| AI Generator | `sg_ai_generator` | ComfyUI, plus the name the submitting client gave itself — see below |
| AI Model | `sg_ai_model` | the checkpoints the graph loaded |
| AI Prompt | `sg_ai_prompt` | positive conditioning on this branch — no sampler needed, so a roto graph's "the actor" lands here too, and a dual encoder's two texts both do |
| AI Negative Prompt | `sg_ai_negative_prompt` | negative conditioning on this branch |
| AI Seed | `sg_ai_seed` | text, not a number — ComfyUI seeds reach 2\*\*64-1 (probe 019) |
| AI Sampler | `sg_ai_sampler` | sampler and scheduler |
| AI Steps | `sg_ai_steps` | the last sampler on the branch |
| AI CFG | `sg_ai_cfg` | the last sampler on the branch |
| AI Generated From | `sg_ai_generated_from` | multi-entity of Version: what this was made from |

**A site with none of these fields still records everything.** The Version's description carries your
note first, then a blank line, then one line per fact, lineage and the whole prompt included. Where
some of the fields exist, those take their values and the description carries the rest. The nodes say
nothing about creating fields, because a publish never depends on them.

Alongside the fields: `description` is your note, the whole structure rides up as a
`.provenance.json` attachment, and the workflow is attached when the client sent one. The fields are
the queryable summary; the attachment is the record.

The workflow attachment is **best effort and says so**. `PROMPT` is guaranteed, because execution
cannot happen without it, but `EXTRA_PNGINFO` is whatever the client put in `extra_data`. The
standard frontend sends it; the `comfy` CLI, the ComfyUI MCP server and wrapper UIs that build their
own API-format prompt do not. A publish never depends on it, and reports when it is missing.

The client's name is **the client's own claim, not an environment variable.** It is
`extra_data.comfy_usage_source` on whatever POSTed `/prompt`; ComfyUI passes it to the node under the
hidden name `COMFY_USAGE_SOURCE`, which is where the misreading starts. The standard frontend puts
`comfyui-frontend` in the body of every Run. A script of your own that omits it publishes Versions
reading `ComfyUI (unknown client)`. Set it, and the field explains a missing workflow later instead of
shrugging:

    POST /prompt  {"prompt": {...}, "extra_data": {"comfy_usage_source": "my-farm-submitter"}}

Or send a `Comfy-Usage-Source` header, which the server copies into `extra_data` only when the body
left the key out (`server.py:1120`).

Where each piece lands is yours, not ours. A studio that already records seeds in `sg_render_seed`, or
that wants nothing but a readable paragraph, sets `provenance` in the profile rather than forking the
node. See DESIGN.md, "Where each piece lands is the operator's, not ours", and INSTALL.md for the
profile on one page.

## Keeping the frames

`Version` media is single-valued, so a sequence cannot BE a Version's media (probe 022). The frames
are a `PublishedFile` instead, and a PublishedFile's path has to sit under one of your site's
LocalStorage roots, because the server refuses anything else.

**Create Published Files** on the node is one question and it is not about media: is this publish a
deliverable, or only review? What gets registered follows from what is wired, the frames where
`images` is and the clip where `video` is. Whether your house *also* keeps the review clip as a file
beside a sequence is a convention rather than a per-publish call, so it is Review movie under
Settings, then SG, SG Publish Defaults. A clip published on its own is the deliverable and is
registered either way.

**Nothing has to change about where ComfyUI writes.** The frames land in ComfyUI's own output
directory as usual, and the node *copies* them into place under the root. The copy is what a failed
publish is recovered from, so the originals are never moved. A publish that fails after the frames
were copied leaves the copies where they are and names their paths.

Settings, then SG, SG Publish Defaults holds every key of this, per project: Storage, Operating
system, Sequence path, Movie path, Review movie, Path to Frames, Path to Movie and Colour space. They
are written into `profile.local.json`, which is plain JSON and yours to edit. INSTALL.md lists every
key with its default and who writes it.

A path template is the same language as the name template, Flow Production Tracking's dotted field
paths and Python's format spec, with two rules of its own:

- `{version}` is the publish revision; `%04d`, `####` and `@@@@` are the frame. They are different
  numbers, so in a *path* template the printf form always means the frame.
- The extension follows the files, not the template. It comes from the `format` widget, so a template
  ending `.png` on an EXR publish registers `.exr` and says so. Nothing is transcoded.

`colour_space` is recorded and never applied: it goes in the PublishedFile's description and in the
provenance record, and the node's own `colour_space` widget overrides the profile per publish.

Where an upstream Version published files of its own, they are linked through
`upstream_published_files`, the file-level twin of `sg_ai_generated_from`, written from the same
ancestors the node already walked. Where a Load node upstream read one of those files, the link is
that one file rather than every file the ancestor published; where it read a path field or an upload
there is no file to name, and the whole ancestor is linked as before.

A sequence publish also fills `sg_path_to_frames` on the Version with the frame pattern, so the Load
node resolves the real frames even on a site that never looks at published files.

## Driving it with an agent

Three procedures, in `.claude/commands/`. They are plain markdown, so an agent that does not read
slash commands can follow the file:

    /setup               walk a first run: connection, profile, colour management, the example
    /inspect-site        measure a project and write the profile
    /track-workflow      add tracking to a workflow you already use

`tools/doctor.py` is the check to run first: it prints one line per thing a publish needs, with the
fix appended where it fails.

```sh
<comfy-python> tools/doctor.py            # the interpreter, the paths, the profile
<comfy-python> tools/doctor.py --site     # also the connection, the fields, the storage and the link types
```

`AGENTS.md` is the entry point for an agent, `CLAUDE.md` holds the conventions for changing this
code, and `DESIGN.md` the reasoning behind them.

`tools/qa_node.py` drives one node in a real, headless ComfyUI and prints only what the drive script
returned. `--start` launches an instance with its own port and its own `--base-directory`, which
relocates `custom_nodes`, `input`, `output`, `temp` and `user`. That isolation is the point:
`ComfyUI/custom_nodes/<pack>` is normally a symlink to a checkout, so without it every instance loads
that checkout's code. `COMFYUI_PATH` overrides where ComfyUI is, and defaults to `~/dev/ComfyUI`.

## What's next, tell us

This is the list we know about, and the order is not decided. If one of these is what stands between
you and using the pack, say so in an issue; if the one you need is not here, that is the more useful
issue.

- A `mask` input on SG Publish, so an RGBA publish carries its alpha.
- Registering files another node wrote, such as Save Image (Advanced) or an OCIO Write.
- Publishing where there is no shared storage, by uploading a zip.
- Publishing on someone's behalf, and naming the artist on a farm.
- Updating the Task's status when a Version is published.
- Newest per stream, rather than newest on the link.
- Any Version field on the node, in one line.
- A colour-managed template.
- Windows as a first-class publisher.

## Known limits

- **A loader inside a ComfyUI subgraph** is replaced inside that subgraph rather than promoted out to
  the top level, because a definition's interior is shared by every instance of it and rewiring it
  would break the others. Output streams inside a subgraph are found and tapped normally.
- **A zip uploaded to a Version is not unpacked.** SG Load shows and downloads what someone attached
  as an upload, and hands a zip back as the file it is.
- **`pyproject.toml` has no `PublisherId` or `Icon`.** Both are per-publisher and are left empty
  rather than guessed; `comfy node publish` will not accept an empty `PublisherId`.

## Where to read next

- **INSTALL.md** — which interpreter, where every local file lives, running the command-line tools,
  the profile on one page, and what to do when something does not answer.
- **AGENTS.md** — the entry point for an agent working on or with this pack.
- **DESIGN.md** — why each of these decisions is the one that was made.
