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
- Slash commands in `.claude/commands/` for the recurring jobs (add a node, write a probe)
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

Site access goes through `fpt_llm_api`, the sibling corpus repo's client. This repo holds node code only.

The root `__init__.py` is not optional and not decoration: ComfyUI imports `custom_nodes/<dir>/__init__.py`
directly (`nodes.py:2263`) and a `src/` layout is invisible to it. Any module importing `fpt_llm_api` must
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
with the client — `python -m fpt_llm_api.schema field Version sg_task`, `python -m fpt_llm_api.schema entities
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

- `FPT Publish Version` — image in, Version created, media uploaded, provenance attached. Inputs are built from
  the site profile: link target and exposed fields are resolved, not hardcoded.
- `Flow PT Fetch Version` — a Version's media back into the graph, and the link recorded

`av` (PyAV) joins `requests` and `Pillow` as a dependency ComfyUI already ships — it backs ComfyUI's own
video nodes. Imported lazily inside the movie branch, so an install without it still loads every node and
fails only when someone actually asks for a movie frame.

## Media comes back the same way it went out

A fetched Version is an ancestor, not just pixels. `version_id` is a plain widget, so it is already in the
prompt graph — the branch walk that scopes provenance answers "what did this come from" for free, and the
operator never types an id. A plate becomes a previs; several Versions become one output; the chain lives in
Flow PT.

Which media a Version can deliver is a property of that Version, not of the site (probe 021), so the editor
asks per pick and offers only tiers that resolve to a real file. Published files are not a tier yet: on the
only site available, the types a graph wants carry no path at all. That is recorded as unproven, not as
absent — `docs/quirks.md` in the corpus repo names what would close it.

## Version naming is a convention, never a field

A Version has **no version-number field** — `PublishedFile` has `version_number`, `Version` does not —
so the version lives inside `code`. It is a naming convention, it differs per site and per show, and
nothing here may hardcode one.

So the convention is inferred from the codes a show already uses, shown to the operator with its
coverage, and stored in the profile as data:

    "code_template":   "{link}_{task}_v{version}",
    "code_regex":      "^(?P<link>.+)_(?P<task>[A-Za-z]+)_v(?P<version>\\d+)$",
    "approved_status": "apr"

Measured on three real projects: the reference show scores 100/100, this sandbox 2/3, and a project of
ad-hoc test names 0/53. **The coverage number is the point** — 0% is the honest answer, and the
operator sees it rather than getting a confident wrong guess.

`approved_status` is separate because status vocabularies are per project (probe 009); which code
means approved cannot be assumed.

### Which makes two nodes a pipeline

`code = auto` numbers per link, from the codes already on that link. `select = latest` resolves at run
time, ordering by the convention's version number rather than by id — a re-published v002 is newer by
id but older by intent. So step N publishes and step N+1 consumes it, with no id copied between graphs,
and the lineage field records the join by itself.

A Version resolved at run time is not in the prompt graph, so `lineage.py` records what each Fetch node
actually resolved and the publish node reads back only its own ancestors' entries.

## Provenance

Captured per publish:

| field | source |
|---|---|
| model, prompt, seed, sampler | ComfyUI prompt graph |
| workflow JSON | attachment — best effort, see below |
| submitting client | `COMFY_USAGE_SOURCE` |
| input Version ids | upstream `Flow PT Fetch Version` nodes, or typed by hand |
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

### Media comes back the same way it went out

A fetched Version is an ancestor, not just pixels. `version_id` is a plain widget, so it is already in the
prompt graph — the branch walk that scopes provenance answers "what did this come from" for free, and the
operator never types an id. A plate becomes a previs; several Versions become one output; the chain lives in
Flow PT.

Which media a Version can deliver is a property of that Version, not of the site (probe 021), so the editor
asks per pick and offers only tiers that resolve to a real file. Published files are not a tier yet: on the
only site available, the types a graph wants carry no path at all. That is recorded as unproven, not as
absent — `docs/quirks.md` in the corpus repo names what would close it.

## Version naming is a convention, never a field

A Version has **no version-number field** — `PublishedFile` has `version_number`, `Version` does not —
so the version lives inside `code`. It is a naming convention, it differs per site and per show, and
nothing here may hardcode one.

So the convention is inferred from the codes a show already uses, shown to the operator with its
coverage, and stored in the profile as data:

    "code_template":   "{link}_{task}_v{version}",
    "code_regex":      "^(?P<link>.+)_(?P<task>[A-Za-z]+)_v(?P<version>\\d+)$",
    "approved_status": "apr"

Measured on three real projects: the reference show scores 100/100, this sandbox 2/3, and a project of
ad-hoc test names 0/53. **The coverage number is the point** — 0% is the honest answer, and the
operator sees it rather than getting a confident wrong guess.

`approved_status` is separate because status vocabularies are per project (probe 009); which code
means approved cannot be assumed.

### Which makes two nodes a pipeline

`code = auto` numbers per link, from the codes already on that link. `select = latest` resolves at run
time, ordering by the convention's version number rather than by id — a re-published v002 is newer by
id but older by intent. So step N publishes and step N+1 consumes it, with no id copied between graphs,
and the lineage field records the join by itself.

A Version resolved at run time is not in the prompt graph, so `lineage.py` records what each Fetch node
actually resolved and the publish node reads back only its own ancestors' entries.

## Provenance is per branch, not per graph

One graph holds several independent branches — three lookdev variants off a shared depth pass. The
publish node takes `UNIQUE_ID` and walks back through its own inputs (`provenance.ancestors`), so each
Version describes only what produced *its* image. Without it every Version carries every other variant's
prompt and seed, and a depth AOV claims sampler settings it never used.

Tracing conditioning respects the input it started from: `ControlNetApplyAdvanced` takes both `positive`
and `negative`, so following every link merges the two prompts into one.

C2PA where the writer supports it; custom fields plus attachment otherwise. Field names are decided by probe, not by the docs.

## Non-goals

Charts, dashboards, reports, webhooks, automations — see `CLAUDE.md`. Video and OTIO. Inpainting UI. three.js. Browser extension.

## Later

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
        CATEGORY = "Flow PT"
        OUTPUT_NODE = True         # terminal node: always executes

    NODE_CLASS_MAPPINGS = {"FPTPublishVersion": FPTPublishVersion}
    NODE_DISPLAY_NAME_MAPPINGS = {"FPTPublishVersion": "Publish Version to Flow PT"}

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

### The dependency problem

`_deps.py` resolves `fpt_llm_api` from a sibling checkout. That works here and is **not distributable** — a
registry install gets this repo and nothing else, and `fpt-llm-api` is private.

Three ways out, in order of preference:

1. Publish the *client* half of `fpt-llm-api` to PyPI as a slim package and depend on it normally. The corpus
   stays private; only the client ships.
2. Vendor the client into this repo. It is about sixty lines. Cheap, but it forks.
3. Declare a git dependency. Fragile, and impossible while the repo is private.

Decide before publishing, not after — `[project].name` on the Registry is immutable.
