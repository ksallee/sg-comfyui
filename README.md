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
- **A Flow PT site and a script key.** Auth is `client_credentials`: a Script Name and its Application
  Key, made in the Flow PT web UI under Admin > Scripts. The script needs to read Projects, Versions,
  Tasks and whatever entities you link to, to create Versions and upload media, and — for the one-off
  field setup — to create fields on Version.
- **A checkout of `sg-groundtruth` beside this one.** That is the API client and the corpus of probe
  findings the code cites. It is **private and not on PyPI**, so today there is no way to install this
  without access to it. Whether to publish the client half is an open decision (DESIGN.md, "The
  dependency problem"); until it is made, a Registry install of this repo alone would not run. This is
  the single thing standing between here and a normal install.

## Install

```sh
cd ComfyUI/custom_nodes
git clone git@github.com:ksallee/flow-pt.git
git clone <sg-groundtruth>            # beside it, not inside it
cd flow-pt
cp .env.local.example .env.local      # then fill in the three keys
```

`sg-groundtruth` is looked for in the directory *containing* this repo — so cloning into
`custom_nodes/` puts it at `custom_nodes/sg-groundtruth`, which works. To keep it elsewhere, export
`SG_GROUNDTRUTH_PATH=/path/to/sg-groundtruth` in the environment ComfyUI is launched from.

`.env.local` is gitignored and never printed or logged. A missing key is reported by name, never by
value.

## Set up, in this order

Each step needs the one before it.

**1. Measure your site.** `/inspect-site` — drives `../sg-groundtruth/inspect_site.py`, prints what it
measured with the evidence beside it, and writes `profile.local.json`. Nothing here works without that
file: it is gitignored, so a fresh clone has none, and every picker in both nodes reads it. Run the
slash command rather than the script directly — the report is inference and needs reading back, in
particular the link field, which is the one it most often gets wrong.

**2. Create the provenance fields.** Once per site:

```sh
PYTHONPATH=src python -m comfyui_fpt.fields
```

It reads the schema first and creates only what is missing, so re-running is safe. (Python prints a
`RuntimeWarning` about `comfyui_fpt.fields` already being in `sys.modules`; it is cosmetic.)

Field names are permanent — deleting a field frees the field but never its name, and trashed fields
cannot be listed, so a name spent here is spent site-wide forever (probe 019). Pointing the profile's
`provenance.map` at fields your studio already has is the preferred move.

**3. Put the nodes into a graph.** `/track-workflow <workflow.json>` — reads a workflow you already
use, says where a Version would come out of it and where one could go in, and writes an instrumented
copy. It never overwrites the original.

Then restart ComfyUI and open the instrumented workflow. Two nodes appear under the category **Flow
Production Tracking**. If `http://127.0.0.1:8188/fpt/projects` lists your shows, the credentials, the
client and the profile are all working.

Restarting is only for installing or upgrading the pack. A later edit to `profile.local.json` reaches
the editor on a **browser refresh**: `INPUT_TYPES` is re-evaluated on every `/object_info` request.

## Running the commands

Everything runs from the repo root.

| command | needs |
|---|---|
| `python src/comfyui_fpt/instrument.py <wf.json>` | nothing — no site, no profile, no torch |
| `PYTHONPATH=src python -m comfyui_fpt.fields` | `.env.local` |
| `PYTHONPATH=src python -m comfyui_fpt.seed <file> ...` | `.env.local`, `profile.local.json` |
| `python ../sg-groundtruth/inspect_site.py --project <id> --out profile.local.json` | `../sg-groundtruth/.env.local` |

`PYTHONPATH=src` is required for every `-m comfyui_fpt.*`: the package lives under `src/` and nothing
installs it. `instrument.py` is deliberately run as a file instead — `-m` would import the package
`__init__`, which imports the nodes and therefore torch, and a graph should be analysable on a machine
that has neither torch nor a route to Flow PT.

The inspector reads credentials from **its own** `.env.local`, in the `sg-groundtruth` checkout, not
this one. Same three keys either way.

## The two nodes

**Flow PT Publish Version** — an IMAGE in, a Version out: created, media uploaded, provenance
attached. You give it a name template (`{entity.code}_{output}_v{version:03d}`), a project, what the
Version hangs off, optionally a Task and a status, and what the stream *is* (`depth`, `normals`,
`mask`). The project, link, Task and status lists are your site's real ones, read live. `code = auto`
numbers per link, so two graphs chain without anyone copying an id.

Provenance is scoped per branch, not per graph: the node walks back through its own inputs, so three
lookdev variants off a shared depth pass each record only what produced their own image.

`published_files` decides whether the frames themselves are kept. A batch always publishes as one
Version carrying one movie for review; ask for `frames` as well and the node copies the sequence to
`<storage root>/<path template>` and registers a `PublishedFile` for it, linked to that Version. The
default is `(none)` — a movie publish and a single image are untouched.

**Flow PT Load Version** — a Version's media back into the graph, and the link recorded. The inputs
are a rule an artist would say out loud — *the newest approved depth on this shot* — not an id. An id
(`pin_version_id`) is the escape hatch. Anything published downstream records the Version it came
from, without anyone typing an id.

`source` lists what that Version can actually deliver, best first, and published files lead. Where a
Version published several, each is its own choice named by type and filename —
`Rendered Image · sh010_comp_v003.%04d.png #6843` beside `Movie · sh010_comp_v003.mp4 #6844` — so the
rendered sequence and the mp4 are told apart at a glance. A file whose path is on a root this machine
has not mounted is not offered at all.

`frame` is the first frame and `frame_count` is how many, as one IMAGE batch — which is what makes a
loaded clip a real input to a video graph. It defaults to `1`, the single image the node always
returned, so nothing already saved changes. The ceiling is a size rather than a count: past 4 GiB of
float32 the node refuses and says how many frames fit at that resolution, instead of running out of
VRAM. Frames of differing resolution cannot stack and are refused by name.

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

**Nothing has to change about where ComfyUI writes.** The frames land in ComfyUI's own output
directory as usual, and the node *copies* them into place under the root. The copy is what a failed
publish is recovered from, so the originals are never moved.

Two profile keys per project, beside every other per-show decision:

    "published_files": {
      "storage":       "primary",
      "path_template": "{entity.code}/{output}/v{version:03d}/{entity.code}_{output}_v{version:03d}.%04d.png",
      "colour_space":  "sRGB"
    }

`storage` is a LocalStorage `code` from your site. `path_template` is the same language as the name
template — Flow PT's dotted field paths and Python's format spec — with two rules of its own:

- `{version}` is the publish revision; `%04d` (or `####`, or `@@@@`) is the frame. They are different
  numbers, so in a *path* template the printf form always means the frame.
- The extension follows the files, not the template. The node writes PNG, so a template ending
  `.exr` registers `.png` and says so. Nothing is transcoded.

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
tools/qa_node.py --start --node FPTLoadVersion --drive drive.js --shot out.png
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
