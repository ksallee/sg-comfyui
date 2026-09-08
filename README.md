# Flow Production Tracking for ComfyUI

Two ComfyUI nodes that publish a generation to Flow Production Tracking (formerly ShotGrid) as a
Version, carrying the model, prompt, seed, sampler and workflow that produced it, and load a Version's
media back into a graph so the next step records what it came from. It makes no images; it records the
ones you already make.

Everything site-specific — what a Version hangs off, what it is called, which statuses exist, where
each piece of provenance lands — is measured from your site and written to a profile you can edit. No
studio's conventions are hardcoded.

## What it needs

- **ComfyUI**, and Python 3.11.
- **A Flow Production Tracking site and a script key.** Auth is `client_credentials`: a Script Name and its Application
  Key, made in the Flow Production Tracking web UI under Admin > Scripts. The script needs to read Projects, Versions,
  Tasks and whatever entities you link to, to create Versions and upload media, and — for the one-off
  field setup — to create fields on Version.
- **`sg-groundtruth`**, the API client, from PyPI. It is an ordinary dependency now — `requirements.txt`
  names it, and ComfyUI-Manager installs that file. Nothing to clone to *run* the nodes.
- **A checkout of `sg-groundtruth` beside this one, to *set up*.** Step 1 below measures your site with
  `../sg-groundtruth/inspect_site.py`, and that inspector is in the corpus repo, not in the PyPI
  package. Without it there is no `profile.local.json`, and no picker has anything to read.

## Install

```sh
cd ComfyUI/custom_nodes
git clone git@github.com:ksallee/sg-comfyui.git
cd sg-comfyui
<comfy-python> -m pip install -r requirements.txt   # ComfyUI-Manager does this for you
```

Then restart ComfyUI, open **Settings, then SG**, enter the site address and click **Log in**.
Approve the request in the browser tab that opens, where you are already logged into Flow
Production Tracking, and every Version you publish is created by you. A render farm, or a machine
nobody signs in on, takes a script name and application key in the same place, with an optional
login to publish as. **Test** proves the connection before the first Run. The same dialog holds the
publish defaults: the project the nodes open on, Version name, root name, status, and where
Published Files land.

A checkout can carry the script key in `.env.local` instead, for the command-line tools below:

`<comfy-python>` is the interpreter ComfyUI itself runs on — `ComfyUI/venv/bin/python`, or whatever
launches `main.py`. Installing into the wrong environment is the one way this fails silently: the pack
imports, the site never answers.

```sh
cp .env.local.example .env.local                    # then fill in the three keys
```

`.env.local` is gitignored and never printed or logged. A missing key is reported by name, never by
value. What Settings holds lives in ComfyUI's protected user directory, outside `custom_nodes`, so a
Manager update leaves it alone.

## Set up, in this order

Each step needs the one before it.

**1. Measure your site.** `/inspect-site` — drives `../sg-groundtruth/inspect_site.py`, prints what it
measured with the evidence beside it, and writes `profile.local.json`. Nothing here works without that
file: it is gitignored, so a fresh clone has none, and every picker in both nodes reads it. Run the
slash command rather than the script directly — the report is inference and needs reading back, in
particular the link field, which is the one it most often gets wrong.

**2. Create the provenance fields.** Once per site:

```sh
PYTHONPATH=src python -m comfyui_sg.fields
```

It reads the schema first and creates only what is missing, so re-running is safe. (Python prints a
`RuntimeWarning` about `comfyui_sg.fields` already being in `sys.modules`; it is cosmetic.)

Field names are permanent — deleting a field frees the field but never its name, and trashed fields
cannot be listed, so a name spent here is spent site-wide forever (probe 019). Pointing the profile's
`provenance.map` at fields your studio already has is the preferred move.

**3. Put the nodes into a graph.** `/track-workflow <workflow.json>` — reads a workflow you already
use, says where a Version would come out of it and where one could go in, and writes an instrumented
copy. It never overwrites the original.

Then restart ComfyUI and open the instrumented workflow. Two nodes appear under the category **Flow
Production Tracking**. If `http://127.0.0.1:8188/sg/projects` lists your shows, the credentials, the
client and the profile are all working.

Restarting is only for installing or upgrading the pack. A later edit to `profile.local.json` reaches
the editor on a **browser refresh**: `INPUT_TYPES` is re-evaluated on every `/object_info` request.

## Running the commands

Everything runs from the repo root.

| command | needs |
|---|---|
| `python src/comfyui_sg/instrument.py <wf.json>` | nothing — no site, no profile, no torch |
| `PYTHONPATH=src python -m comfyui_sg.fields` | `.env.local` |
| `PYTHONPATH=src python -m comfyui_sg.seed <file> ...` | `.env.local`, `profile.local.json` |
| `python ../sg-groundtruth/inspect_site.py --project <id> --out profile.local.json` | `../sg-groundtruth/.env.local` |

`PYTHONPATH=src` is required for every `-m comfyui_sg.*`: the package lives under `src/` and nothing
installs it. `instrument.py` is deliberately run as a file instead — `-m` would import the package
`__init__`, which imports the nodes and therefore torch, and a graph should be analysable on a machine
that has neither torch nor a route to Flow Production Tracking.

The inspector reads credentials from **its own** `.env.local`, in the `sg-groundtruth` checkout, not
this one. Same three keys either way.

## The two nodes

**SG Publish** — an IMAGE or a VIDEO in, a Version out: created, media uploaded,
provenance attached. You give it a name template (`{entity.code}_{output}_v{version:03d}`), a
project, what the Version hangs off, optionally a Task and a status, and what the stream *is*
(`depth`, `normals`, `mask`). The project, link, Task and status lists are your site's real ones,
read live. `code = auto` numbers per link, so two graphs chain without anyone copying an id.

Two inputs, `images` and `video`, and at least one of them wired. What you wire is what the Version
carries — there is no combo asking you to say it again:

| `images` | `video` | the Version's media | registered as files, when the box is ticked |
|---|---|---|---|
| — | wired | that clip | the clip |
| wired | — | frame 1, as a still | the frames |
| wired | wired | the clip | the frames, and the clip where your profile keeps it |
| — | — | the run refuses, and says so | — |

**The clip is never re-encoded when it does not have to be.** A `VIDEO` off `LoadVideo` — or any
node that hands you a file — goes up as that file, byte for byte, at its own extension. Anything
else (a `CreateVideo` assembling a batch, a hosted model answering with frames) is written by
ComfyUI's own `VideoInput.save_to()`, which carries the colour space, the bit depth and the audio.
The panel says which of the two happened. There is no `fps` widget: a `VIDEO` states its own rate,
and `CreateVideo` is where you set one.

An IMAGE batch of more than one frame is not media — a Version's media is single-valued (probe 022) —
so with **Create Published Files** off the run refuses rather than uploading frame 1 and dropping the
rest. Tick the box to register the sequence, or send the batch through `CreateVideo`.

Provenance is scoped per branch, not per graph: the node walks back through its own inputs, so three
lookdev variants off a shared depth pass each record only what produced their own image.

**SG Load** — a Version's media back into the graph, and the link recorded. The inputs
are a rule an artist would say out loud — *the newest approved depth on this shot* — not an id. An id
(`pin_version_id`) is the escape hatch. Anything published downstream records the Version it came
from, without anyone typing an id.

`source` lists what that Version can actually deliver, best first, and published files lead. Where a
Version published several, each is its own choice named by type and filename —
`Rendered Image · sh010_comp_v003.%04d.png #6843` beside `Movie · sh010_comp_v003.mp4 #6844` — so the
rendered sequence and the mp4 are told apart at a glance. A file whose path is on a root this machine
has not mounted is not offered at all.

`frame` is the first frame and `frame_count` is how many, as one IMAGE batch — which is what makes a
loaded clip a real input to a video graph.

`frame` is the frame **number**, the one in the filename: `1003` means `plate.1003.exr`, not the 1003rd
file. Leave it at **0** and it starts wherever the sequence starts, which is what a 1001-based plate
wants and why it usually needs no typing at all; the panel shows the range the source actually has, so
you are not guessing. Ask for a frame that is not there and it is refused, naming the range — it will
never quietly hand back a different frame. `frame_count` **0** reads to the end; it defaults to `1`,
the single image the node always returned, so nothing already saved changes. The ceiling is a size
rather than a count: past 4 GiB of float32 the node refuses and says how many frames fit at that
resolution, instead of running out of VRAM. Frames of differing resolution cannot stack and are
refused by name.

`colour_space` comes back as a fourth output and on the panel when the publisher declared one. Read
back, never applied — nothing here converts, and a Version that declared nothing says nothing.

## Where provenance lands

Nine typed fields on Version, created by step 2 above:

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

Alongside them: `description` is your note, the whole structure rides up as a `.provenance.json`
attachment, and the workflow is attached when the client sent one. The fields are the queryable
summary; the attachment is the record.

The workflow attachment is **best effort and says so**. `PROMPT` is guaranteed — execution cannot
happen without it — but `EXTRA_PNGINFO` is whatever the client put in `extra_data`. The standard
frontend sends it; the `comfy` CLI, the ComfyUI MCP server and wrapper UIs that build their own
API-format prompt do not. A publish never depends on it, and reports when it is missing.

The client's name is **the client's own claim, not an environment variable.** It is
`extra_data.comfy_usage_source` on whatever POSTed `/prompt`; ComfyUI passes it to the node under the
hidden name `COMFY_USAGE_SOURCE`, which is where the misreading starts. The standard frontend puts
`comfyui-frontend` in the body of every Run. A script of your own that omits it publishes Versions
reading `ComfyUI (unknown client)` — set it, and the field explains a missing workflow later instead
of shrugging:

    POST /prompt  {"prompt": {...}, "extra_data": {"comfy_usage_source": "my-farm-submitter"}}

Or send a `Comfy-Usage-Source` header, which the server copies into `extra_data` only when the body
left the key out (`server.py:1120`).

Where each piece lands is yours, not ours. A studio that already records seeds in `sg_render_seed`, or
that wants nothing but a readable paragraph, sets `provenance` in the profile rather than forking the
node. See DESIGN.md, "Where each piece lands is the operator's, not ours".

## Keeping the frames

`Version` media is single-valued, so a sequence cannot BE a Version's media (probe 022). The frames
are a `PublishedFile` instead, and a PublishedFile's path has to sit under one of your site's
LocalStorage roots — the server refuses anything else.

**Create Published Files** on the node is one question and it is not about media: is this publish a
deliverable, or only review? What gets registered follows from what is wired — the frames where
`images` is, the clip where `video` is. Whether your house *also* keeps the review clip as a file
beside a sequence is a convention rather than a per-publish call, so it is `register_movie` in the
profile below; a clip published on its own is the deliverable and is registered either way.

**Nothing has to change about where ComfyUI writes.** The frames land in ComfyUI's own output
directory as usual, and the node *copies* them into place under the root. The copy is what a failed
publish is recovered from, so the originals are never moved.

Two profile keys per project, beside every other per-show decision:

    "published_files": {
      "storage":        "primary",
      "path_template":  "{entity.code}/{output}/v{version:03d}/{entity.code}_{output}_v{version:03d}.%04d.png",
      "colour_space":   "sRGB",
      "register_movie": false
    }

`storage` is a LocalStorage `code` from your site. `path_template` is the same language as the name
template — Flow Production Tracking's dotted field paths and Python's format spec — with two rules of its own:

- `{version}` is the publish revision; `%04d` (or `####`, or `@@@@`) is the frame. They are different
  numbers, so in a *path* template the printf form always means the frame.
- The extension follows the files, not the template. The node writes PNG, so a template ending
  `.exr` registers `.png` and says so. Nothing is transcoded.

`register_movie` says whether the review clip is registered as a file too, beside the frames. It is
false by default: most shows deliver the sequence and review the clip.

`colour_space` is recorded and never applied: it goes in the PublishedFile's description and in the
provenance record, and the node's own `colour_space` widget overrides the profile per output. This
site has no colour space field on `PublishedFile` and none was created for it — a field name is spent
site-wide forever (probe 019).

Where an upstream Version published files of its own, they are linked through
`upstream_published_files` — the file-level twin of `sg_ai_generated_from`, written from the same
ancestors the node already walked. Where a Load node upstream read one of those files, the link is
that one file rather than every file the ancestor published; where it read a path field or an upload
there is no file to name, and the whole ancestor is linked as before.

A sequence publish also fills `sg_path_to_frames` on the Version with the `%04d` pattern, so the Load
node resolves the real frames even on a site that never looks at published files.

## Files this repo writes on your machine

Both gitignored, both yours to edit:

    .env.local           site URL, script name, script key
    profile.local.json   what your site practices, per project — written by /inspect-site

## Driving it with an agent

Two slash commands, in `.claude/commands/`. They are the interface, not a shortcut around one:

    /inspect-site        measure a project and write the profile
    /track-workflow      add tracking to a workflow you already use

`CLAUDE.md` holds the conventions, `DESIGN.md` the reasoning behind them.

## QA harness

`tools/qa_node.py` drives one node in a real, headless ComfyUI and prints only what the drive script
returned:

```sh
pip install playwright && playwright install chromium     # once
tools/qa_node.py --start --node SGLoadVersion --drive drive.js --shot out.png
```

`--start` launches an instance of its own: its own port, and its own `--base-directory`, which
relocates `custom_nodes`, `input`, `output`, `temp` and `user`. That isolation is the point —
`ComfyUI/custom_nodes/<pack>` is normally a symlink to your main checkout, so without it every
instance loads main's code and you verify someone else's work instead of your own. Nodes 2.0 is seeded
on, the onboarding coachmarks are seeded off (otherwise the Templates browser opens over the canvas
and every selector queries a node nobody can see), and the "leave site?" dialog is auto-accepted.

It exists instead of a browser MCP because an MCP returns an accessibility snapshot and a console log
on every call, which is most of what a UI session costs. This shape is a CLI that writes to disk and
lets the agent read back only its own answer.

`COMFYUI_PATH` overrides where ComfyUI is (default `~/dev/ComfyUI`).

## Not ready yet

- **`sg_groundtruth` is not installable.** A sibling checkout is required. Until that is resolved a
  Comfy Registry install would not run, so this is not on the Registry.
- **`pyproject.toml` has no `PublisherId` or `Icon`.** Both are per-publisher and are left empty
  rather than guessed; `comfy node publish` will not accept an empty `PublisherId`.
- **A loader inside a ComfyUI subgraph** is replaced inside that subgraph rather than promoted out to
  the top level, because a definition's interior is shared by every instance of it and rewiring it
  would break the others. Output streams inside a subgraph are found and tapped normally.
