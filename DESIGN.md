# Design

## Thesis

Studios generate in ComfyUI. Output lands in Slack and Dropbox with no version history, no review, no record of model, prompt, seed, or source. Clients are starting to require AI disclosure and nobody can answer.

This is not a generation tool. It is the provenance and review path for generation that already happens.

Consequence: never pitch or build a feature that makes images. Build the trail.

## Local first, agent operable

The tool runs on the operator's machine against their own site. No service, no account, no telemetry.

The operator is not expected to read the code. They fork, point an agent at the repo, and change the node or the design. That is the product, equally with the node itself.

Requirements this imposes:
- Every convention discoverable from `CLAUDE.md` alone
- Slash commands in `.claude/commands/` for the recurring jobs: `/inspect-site` measures a project and
  writes the profile, `/track-workflow` puts the nodes into a graph, `/task` does a job against the API
- Probes runnable by an agent to learn the API before editing
- No framework, no plugin system, no dynamic dispatch

## Architecture

    __init__.py      re-exports the mappings; ComfyUI reads this file and no other
    src/comfyui_fpt/
      site.py        .env.local, profile.local.json, a connected client
      publish.py     create Version, three-step upload, attach — one probe citation per call
      provenance.py  extract model/prompt/seed/graph from the ComfyUI prompt object
      nodes/         one file per node
      __init__.py    NODE_CLASS_MAPPINGS

Site access goes through `sg_groundtruth`, the sibling corpus repo's client. This repo holds node code only.

The root `__init__.py` is not optional and not decoration: ComfyUI imports `custom_nodes/<dir>/__init__.py`
directly (`nodes.py:2263`) and a `src/` layout is invisible to it. Any module importing `sg_groundtruth` must
import `_deps` first — import order inside the package decides whether the path is set up yet.

### Two paths

**Publish path** — the node at runtime. REST and `requests` only, no exceptions. A ComfyUI node ships into
someone else's Python env; every dependency is a support burden, and `shotgun_api3` is heavyweight.

**Setup path** — schema cache, inspector, field creation. Runs on the operator's machine at configuration time
with an agent present, so it may use the Python API where that is genuinely better. If REST cannot create
schema fields but `shotgun_api3` can, provenance-as-typed-fields survives as a setup step.

Same line as "LLM at configuration time, never in the publish path".

Probes exercise REST, always — their job is to prove the *node's* behaviour, and the two APIs differ in filter
syntax, return shape and upload flow. Findings carry a Python equivalent where the mapping is non-obvious; TDs
read Python, and REST-and-Python-side-by-side-both-verified does not exist anywhere else.

### Cheap index, expensive body

The pattern repeats, and it is deliberate: `probes/findings/INDEX.md` over the findings, the schema digest over
the raw schema. An agent reads the index, then opens only what it needs. An agent that must read the corpus to
answer one question burns its context on the first call and is useless for the rest of the session.

Findings are therefore tagged, and a verdict is one actionable sentence — often the only thing read.

## Schema cache

The schema is the only source of truth for what a site calls things: which `CustomEntityNN` are enabled and
their display names, which fields exist, their types, per-project status lists. It changes when anyone adds a
field, so it is cached and refreshable, never assumed.

Two layers, because a real studio site has hundreds of entity types by hundreds of fields:

- **raw** — full JSON, per site and per project, on disk, timestamped, gitignored. Refresh explicitly; the node
  never refreshes on the publish path.
- **digest** — compact, generated from raw: entity types actually in use, display name to programmatic name,
  fields with type and mandatory flag.

"Consultable by the LLM" means a query CLI over the cache, not a blob in context. It lives in the corpus repo
with the client — `python -m sg_groundtruth.schema field Version sg_task`, `python -m sg_groundtruth.schema entities
--custom`. An agent that has to read the raw dump to answer one question will burn its context on the first
call and be useless for the rest of the session.

Per site *and* per project: some field configuration and every status list is project-scoped.

## Site profile

Every site is different: custom fields, custom entity types, different mandatory fields, different status lists,
and no agreement on whether a Version hangs off a Task, a Shot, an Asset or a playlist. Integrations here fail
because they hardcode one studio's conventions, or expose every field and become unusable.

Instead the operator's agent inspects their site and writes a profile the node consumes.

The schema cache says what *exists*. The profile says what is *practiced* and what to expose.
Different lifetimes: the cache refreshes when the schema changes, the profile is inference plus
operator edits layered on top.

- Schema says what is *possible*; recent Versions say what is *practiced*. Rank fields by fill rate over the
  project's last N Versions, not by what the schema permits — sites carry hundreds of dead legacy fields.
- Keyed per project, not per site. One studio runs shows with different conventions.

`Version.entity` is not one type. The schema lists **15** valid ones — Asset, Level, MocapTake, Reel,
ShootDay, Shot, Sequence, Delivery, Launch, Camera, Slate, SourceClip and three `CustomEntity` slots —
identical on every project. So a single `link_type` was never Flow PT's model: one show hangs Versions
off Shots, another off Assets, and plenty use several at once (the reference show links 99 Shots and 1
Asset; another links Assets, Shots and Sequences).

The picker therefore offers **every type the show actually uses**, each option carrying its own type
(`bunny_030_0090 (Shot)`), and the type written to the Version comes from what was picked rather than
from a default. Which types to search is observed from recent Versions, because searching all 15 would
be slow and mostly empty — with Shot, Asset and Sequence added regardless, since observation alone is
circular: a brand new Asset cannot be picked while no Version points at one. `link_types` in the
profile overrides the lot.

Top-level keys are the site default; a `projects` block overrides them per show. Nothing is global that a
show can disagree about:

    {
      "default_project": 1180,
      "projects": {
        "1180": {"name": "sandbox",   "link_type": "Shot",  "link_field": "entity", "code_prefix": "corridor_v001"},
        "91":   {"name": "Kids Room", "link_type": "Asset", "link_field": "entity", "code_prefix": "comfy_v001"}
      }
    }

This is what lets two graphs open in one ComfyUI publish into two shows that link Versions differently. The
node resolves `link_type` from the project the operator picked on that node, and `/fpt/profile` tells the
editor the same thing so the link picker searches the right entity type. One ComfyUI, one profile, many shows.
- Plain JSON, human-editable, regenerable. Operator edits win over inference.
- Gitignored. Field naming and pipeline conventions are potentially confidential — unlike `probes/findings/`,
  which document the API itself and are safe to publish.

**The LLM runs at configuration time, never in the publish path.** It probes, then writes data. Publishing is
deterministic, offline, and costs no tokens.

## Nodes (v0)

- `Flow PT Publish Version` — image in, Version created, media uploaded, provenance attached. Inputs are built from
  the site profile: link target and exposed fields are resolved, not hardcoded.
- `Flow PT Load Version` — a Version's media back into the graph, and the link recorded

`av` (PyAV) joins `requests` and `Pillow` as a dependency ComfyUI already ships — it backs ComfyUI's own
video nodes. Imported lazily on both sides of the movie branch, decoding a frame in `media.py` and encoding a
batch in `movie.py`, so an install without it still loads every node and fails only when someone actually
asks for a movie frame or publishes a batch. Nothing shells out to ffmpeg.

## Output is always a movie

A run is one Version. One frame publishes as it always did; more than one becomes ONE Version carrying an
h264 movie, uploaded to `sg_uploaded_movie`, with frame 1 also going to `image` so there is a thumbnail
before the transcode lands.

The rule comes from probe 022: a Version's media is single-valued, so a sequence cannot BE media. The node
used to loop, and a two-second camera move produced 33 Versions and 33 one-frame transcodes while the real
`.mp4` the graph wrote never reached the site.

`sg_first_frame`, `sg_last_frame`, `frame_count` and `frame_range` are ours, and are written where the site
has them. `sg_uploaded_movie_mp4`, `_frame_rate` and `_transcoding_status` are the transcoder's and are never
written: probe 022 measured `_mp4` still serving a transcode of a replaced file while status read 1, and
writing them ourselves manufactures that same desync in any player that trusts them.

**The frame rate is stated, never assumed.** The node's own `fps` widget wins; at 0 the graph is asked — any
node with an `fps` or `frame_rate` widget, the branch first and the whole graph second, because a movie node
is usually a sibling of the publish node rather than an ancestor — and two conflicting rates leave the graph
treated as silent. Only then does 24 apply, and the panel names which of the three answered, before the run
and after it. A supervisor reading timing off the player can tell a measured rate from a default one.

Image sequences stay supported as *input*: the Load node's `frames` tier is untouched.

## Media comes back the same way it went out

A fetched Version is an ancestor, not just pixels. `version_id` is a plain widget, so it is already in the
prompt graph — the branch walk that scopes provenance answers "what did this come from" for free, and the
operator never types an id. A plate becomes a previs; several Versions become one output; the chain lives in
Flow PT.

Which media a Version can deliver is a property of that Version, not of the site (probe 021), so the editor
asks per pick and offers only tiers that resolve to a real file. Published files are not a tier yet: on the
only site available, the types a graph wants carry no path at all. That is recorded as unproven, not as
absent — `docs/quirks.md` in the corpus repo names what would close it.

## Where the version number lives is site-specific

A Toolkit-driven site usually carries a real numeric field on Version — `sg_version_number` or
similar — and that is authoritative when present, so `version_number_field` names it in the profile
and the node writes it. Many sites have none (this one has none; `PublishedFile.version_number` is a
different entity), and then the version lives inside `code` as a freeform convention that differs per
show. Both paths are supported and neither is assumed.

So the convention is inferred from the codes a show already uses, shown to the operator with its
coverage, and stored in the profile as data:

    "code_template":   "{entity.code}_{output}_v{version:03d}",
    "code_regex":      "^(?P<entity>.+)_(?P<output>[A-Za-z]+)_v(?P<version>\\d+)$",
    "approved_status": "apr"

Measured on three real projects: the reference show scores 100/100, this sandbox 2/3, and a project of
ad-hoc test names 0/53. **The coverage number is the point** — 0% is the honest answer, and the
operator sees it rather than getting a confident wrong guess.

There is deliberately **no "approved" concept**. Flow PT has no such thing — approved is one status
code among many, the codes differ per project (probe 009), and a show may care about `rev`, `ip`, a
custom code, or none. So a Load node takes a status the operator picks from that project's real list,
and empty means any. An earlier version of this hardcoded "latest approved", which was this project
inventing vocabulary the API does not have.

### Which makes two nodes a pipeline

`code = auto` numbers per link. `select = newest matching` resolves at run time using Flow PT's own
rule — order newest-first (`id` or `created_at`), optionally require a status, optionally require a
substring in the code. Ordering by the convention's version number is offered as a third option,
because a re-published v002 is newer by id but older by intent. So step N publishes and step N+1
consumes it, with no id copied between graphs, and the lineage field records the join by itself.

A Version resolved at run time is not in the prompt graph, so `lineage.py` records what each Load node
actually resolved and the publish node reads back only its own ancestors' entries.

## Provenance

Captured per publish:

| field | source |
|---|---|
| model, prompt, seed, sampler | ComfyUI prompt graph |
| workflow JSON | attachment — best effort, see below |
| submitting client | `COMFY_USAGE_SOURCE` |
| input Version ids | upstream `Flow PT Load Version` nodes, or typed by hand |
| user, timestamp | client |

### The workflow attachment is best effort

`PROMPT` is guaranteed — execution cannot happen without it. `EXTRA_PNGINFO` is not: it is whatever the
client put in `extra_data`, and `None` otherwise (`execution.py:199`). The standard frontend sends it; the
`comfy` CLI, the ComfyUI MCP server, and every wrapper UI that builds its own API-format prompt do not.

So a publish must never depend on the workflow, and must say when it is missing rather than quietly
omitting it. `COMFY_USAGE_SOURCE` records which client submitted the prompt, which is exactly the
information needed to explain an absent workflow later.

This is also the reason the demo drives ComfyUI over plain HTTP rather than through its MCP server:
an MCP-submitted prompt exercises the degraded provenance path.

### Where each piece lands is the operator's, not ours

The nine fields are a default, not a schema. A studio that already records seeds in `sg_render_seed`,
or that wants nothing but a readable paragraph, should not have to fork the node — so the mapping is
data, per project, beside every other per-show decision:

    "provenance": {
      "mode": "fields",
      "map": {
        "seed":   "sg_render_seed",
        "prompt": "description",
        "cfg":    null
      }
    }

`mode` is the fallback for concepts the map does not name: `fields` uses the defaults, `description`
folds everything into the note. That is the difference between one word and nine null entries, and
"put it all in the description" is a real request.

The concepts — generator, model, prompt, negative_prompt, seed, sampler, steps, cfg,
generated_from — are what the graph knows. `fields.concepts` produces them, `fields.targets`
resolves the operator's decision once, and both the publish path and `/fpt/preview_publish` read
that same resolution, so the panel shows where a value will actually land rather than where this
repo would have put it.

A target the site does not have is **reported, not dropped**: a typo in a profile would otherwise
hide behind a Version that looks fine.

Pointing at a field the studio already has is the preferred move, and cheaper than it looks —
`fields.ensure` only creates what `FIELDS` names, and every name it spends is spent site-wide
forever (probe 019).

### Typed fields, not a JSON blob

`fields.py` defines nine fields on Version and creates them idempotently (`python -m comfyui_fpt.fields`).
`description` is then the operator's note, and the complete structure still rides up as a
`.provenance.json` attachment — the fields are the queryable summary, the attachment is the record.

Three constraints came out of probe 019 and are not negotiable:

- **Seed is `text`.** A `number` field takes 2**31-1 but 400s at 2**63; ComfyUI seeds reach 2**64-1.
- **`ensure()` reads `/schema` first.** Re-POSTing an existing display name does not error, it silently
  creates `<name>_1`, so a POST-and-hope ensure quietly multiplies fields on every run.
- **Field names are permanent.** DELETE frees the field but never its name, and trashed fields cannot be
  enumerated, so the collision is invisible. Adding to `FIELDS` spends a name site-wide, forever.

Lineage is `sg_ai_generated_from`, a `multi_entity` of Version — probe 019 confirms multi_entity
round-trips `{type, id}` hashes and takes exactly one `valid_types` element.

Not "source versions": the sources need not be AI, and a scanned plate feeding a previs is the ordinary
case. The `AI` describes this Version's generation, not its inputs. Display and programmatic names are
kept in step — a TD reading `sg_ai_generated_from` should find "AI Generated From" in the UI — so a
rename means a new field, never a relabel.

## Provenance is per branch, not per graph

One graph holds several independent branches — three lookdev variants off a shared depth pass. The
publish node takes `UNIQUE_ID` and walks back through its own inputs (`provenance.ancestors`), so each
Version describes only what produced *its* image. Without it every Version carries every other variant's
prompt and seed, and a depth AOV claims sampler settings it never used.

Tracing conditioning respects the input it started from: `ControlNetApplyAdvanced` takes both `positive`
and `negative`, so following every link merges the two prompts into one.

C2PA where the writer supports it; custom fields plus attachment otherwise. Field names are decided by probe, not by the docs.

## Coverage, measured

"Works on any workflow" is a claim, so it is measured rather than asserted. The corpus is 680 real
graphs: the 629 ComfyUI template workflows every user sees in the template browser, plus the three
most-starred public collections (ZHO, Yolain, `comfyanonymous/ComfyUI_examples`).

Re-measured 2026-09-03, after `instrument.py` learned to see through subgraphs:

                                    before   after
    analysed without error         680/680  680/680
    finds a publishable stream     509/680  546/680   75% → 80%
    finds a loader to replace      428/680  430/680
    publishable streams, in total      977     1419

**The count is the small half of it.** 246 of the 680 graphs put their work inside a subgraph, and of
those, 200 already reported *something* — the instance's own output slot, or a plate feeding it. What
they reported was the wrong thing. 297 streams moved from a subgraph instance's output onto the node
that actually makes the picture, which is where the name lives: `video_ltx2_i2v` used to offer
`scale_dimensions`, a node feeding the block, and now offers the `VAEDecode` inside it;
`3d_moge_perspective_to_mesh` now offers `normal_opengl` and `normal_directx` by those names, which
existed only inside. 215 graphs have a stream that exists nowhere else. So a TD opening a current
template and running `/track-workflow` is no longer told there is nothing to do on a graph full of
work.

29 old addresses are gone rather than moved, and all 29 were wrong: 27 were an IMAGE feeding a
subgraph that only *looked* like a video sink because the instance declares a VIDEO output — the
input plate reported as an output — and 2 were an instance output slot nothing inside ever fed. **No
graph that used to find a stream finds none now.**

14 of the 37 newly-covered graphs came from a second, smaller correction in the same pass: a save
node is an end even when it also hands the picture on. `SaveImage` feeding an `ImageCompare` so the
operator can see before and after is the shape, and it hid every SeedVR2 int8 upscaler.

Instrumenting is measured too, not just analysis: all 586 corpus graphs that have anything to
instrument were tapped and had their loader replaced, and all 586 came out with unique node and link
ids across the document, no dangling endpoint, every instance's output count matching its
definition's, and the publish node fed by exactly the stream that was asked for.

The 134 that still find nothing are mostly 3D, audio and text graphs with no image output at all,
correctly out of scope.

Before the sink rule learned that frames assembled into another medium end an image stream too
(`instrument._is_sink`) the number was 57%. That one fix moved 124 workflows, nearly all of them
video. Those frames now publish as one Version carrying one movie — see "Output is always a movie".

### Subgraphs

`instrument.py` analyses a flattened view (`_flatten`), because a subgraph instance is a relay rather
than a node: what the definition's `inputNode` hands on is whatever the instance's input was fed, and
what its `outputNode` receives is what the instance's output emits. Splicing those pairs gives the
graph ComfyUI itself executes — confirmed against `graphToPrompt`, which addresses the same interior
node as `306:296` where this addresses it `306/296`. Nesting comes out for free and does occur: 76
places in the corpus instantiate a definition inside another, one level deep, never more.

Tapping crosses the boundary at the instance's output: the stream is **promoted** to an output slot,
exactly as dragging an interior output onto the subgraph's output panel does in the editor, so the
publish node itself stays at the top level with its pickers rather than being buried a level down. If
the stream already leaves through an output — as a template's own `depth` pass does — that slot is
reused and nothing is added at all.

Promotion is additive and safe. The reverse is not: a definition's interior is shared by every
instance of it, so rewiring an interior input to feed it from outside would break the other
instances. A loader inside a subgraph is therefore replaced *inside* that same subgraph. Only 3
corpus graphs have one, and no corpus graph instantiates a definition twice — but the file is
someone else's, so the rule is the rule and not the measurement.

The naming rule is unchanged in spirit and needed one addition: what a stream is called still comes
from what the graph already says, and inside a subgraph the graph says one more thing — the
subgraph's own name. Its useful half is the *opposite* half from a sink label's. "Preview Image
(normal_opengl)" says what the stream is inside the brackets; "Depth Estimation (Depth Anything 3)"
says it before them and names a model inside. So the trailing bracket is dropped, and the name is
tried only after everything nearer the stream.

## Non-goals

Charts, dashboards, reports, webhooks, automations — see `CLAUDE.md`. Video and OTIO. Inpainting UI. three.js. Browser extension.

## Later

Publishing a sequence AS a sequence, rather than as the movie made from it. That wants `PublishedFile` —
probe 022's own verdict, since media is single-valued and Attachments are storage rather than review — plus
shared storage for `sg_path_to_frames` to point at. `PublishedFile` is still unproven: probe 021 found the
types a graph wants carrying no `path` at all on the one site available, so the probe that closes it belongs
in `sg-groundtruth`, not here.

React review surface showing iteration lineage, extracted into an MIT component registry. Not in this repo.

## Node anatomy

A custom node is a Python class registered from `__init__.py`. Verified against docs.comfy.org, 2026-09-02.

    class FPTPublishVersion:
        @classmethod
        def INPUT_TYPES(cls):
            return {
                "required": {"images": ("IMAGE", {})},
                "optional": {"description": ("STRING", {"multiline": True})},
                "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
            }
        RETURN_TYPES = ()          # trailing comma matters when there is one
        FUNCTION = "publish"
        CATEGORY = "Flow Production Tracking"
        OUTPUT_NODE = True         # terminal node: always executes

    NODE_CLASS_MAPPINGS = {"FPTPublishVersion": FPTPublishVersion}
    NODE_DISPLAY_NAME_MAPPINGS = {"FPTPublishVersion": "Flow PT Publish Version"}

`INPUT_TYPES` is a classmethod evaluated at load, which is what lets the mapping drive the inputs.

There is a second, newer schema — `io.ComfyNode` with `define_schema()` returning an `io.Schema`, which is
how the stock `comfy_extras/*` nodes are now written; `execution.py` branches on `is_v3`. Both are live and
v1 is not deprecated. **This repo targets v1**, because a registry node should load on the older ComfyUI a
studio actually has installed, and because the dict form is the one a forker's agent can read without
learning a second vocabulary. The cost is that v1 hidden inputs are raw dict lookups, where v3's
`HiddenHolder` returns `None` for anything absent (`_io.py:1545`) — so we handle the `None` cases ourselves.

### Where provenance comes from

The hidden inputs are the whole provenance mechanism. `PROMPT` is the executing prompt graph — model, seed,
sampler, steps, cfg all live in its node widget values. `EXTRA_PNGINFO` carries the workflow as saved, which is
what gets attached as a file. `UNIQUE_ID` identifies this node instance.

Nothing else needs to be asked of the user; the graph already knows.

## Distribution

Two ways in, and they are not the same thing:

- **Git clone into `ComfyUI/custom_nodes/`** — what a developer does. `requirements.txt` is installed by
  ComfyUI-Manager.
- **The Comfy Registry** — what everyone else does, reached through ComfyUI-Manager or `comfy node install`.
  Publishing needs a `pyproject.toml` with a PEP 621 `[project]` block plus `[tool.comfy]` carrying
  `PublisherId`, `DisplayName` and `Icon`. Publish with `comfy node publish`, or a GitHub Action on
  `REGISTRY_ACCESS_TOKEN` triggered by a version bump.

### Names

`[project].name` on the Registry is immutable, so it is decided here rather than in passing:

    [project].name                comfyui-flow-production-tracking   permanent
    [tool.comfy].DisplayName      Flow Production Tracking
    repo, custom_nodes directory  comfyui-flow-production-tracking
    CATEGORY                      Flow Production Tracking
    node titles                   Flow PT Publish Version, Flow PT Load Version
    Python package                comfyui_fpt

The long form goes in the slots that are searched — a TD looks for the product, not an abbreviation, and
half of them still search "shotgrid", which belongs in the registry keywords and the README where it can
be changed later. Node titles stay short because they render on the node body. The Python package stays
`comfyui_fpt`: it is internal, every import is relative, and `python -m comfyui_fpt.fields` has to be
typable.

`Publish`/`Load` is both vocabularies at once — `tk-multi-publish2`/`tk-multi-loader2` on the Flow PT
side, and on the ComfyUI side `Load` is what a node is called when it is where the pixels come from.
`Fetch` was neither.

`NODE_CLASS_MAPPINGS` keys are written into every saved workflow, so they are permanent from the moment
anyone outside this repo saves a graph: `FPTPublishVersion`, `FPTLoadVersion`.

### The dependency problem

`_deps.py` resolves `sg_groundtruth` from a sibling checkout. That works here and is **not distributable** — a
registry install gets this repo and nothing else, and `sg-groundtruth` is private.

Three ways out, in order of preference:

1. Publish the *client* half of `sg-groundtruth` to PyPI as a slim package and depend on it normally. The corpus
   stays private; only the client ships.
2. Vendor the client into this repo. It is about sixty lines. Cheap, but it forks.
3. Declare a git dependency. Fragile, and impossible while the repo is private.

Decide before publishing, not after — `[project].name` on the Registry is immutable.
