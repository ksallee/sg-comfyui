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

    src/comfyui_fpt/
      client.py      thin REST client: token, refresh, request
      provenance.py  extract model/prompt/seed/graph from the ComfyUI prompt object
      nodes/         one file per node
      __init__.py    NODE_CLASS_MAPPINGS

Site access goes through `fpt_llm_api`, the sibling corpus repo's client. This repo holds node code only.

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

"Consultable by the LLM" means a query CLI over the cache, not a blob in context — `python schema.py field
Version sg_task`, `python schema.py entities --enabled`. An agent that has to read the raw dump to answer one
question will burn its context on the first call and be useless for the rest of the session.

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
- Plain JSON, human-editable, regenerable. Operator edits win over inference.
- Gitignored. Field naming and pipeline conventions are potentially confidential — unlike `probes/findings/`,
  which document the API itself and are safe to publish.

**The LLM runs at configuration time, never in the publish path.** It probes, then writes data. Publishing is
deterministic, offline, and costs no tokens.

## Nodes (v0)

- `FPT Publish Version` — image in, Version created, media uploaded, provenance attached. Inputs are built from
  the site profile: link target and exposed fields are resolved, not hardcoded.
- `FPT Fetch Media` — Version or Attachment out as an image, to feed a graph

## Provenance

Captured per publish:

| field | source |
|---|---|
| model, prompt, seed, sampler | ComfyUI prompt graph |
| workflow JSON | attachment |
| input Version ids | node inputs |
| user, timestamp | client |

C2PA where the writer supports it; custom fields plus attachment otherwise. Field names are decided by probe, not by the docs.

## Non-goals

Charts, dashboards, reports, webhooks, automations — see `CLAUDE.md`. Video and OTIO. Inpainting UI. three.js. Browser extension.

## Later

React review surface showing iteration lineage, extracted into an MIT component registry. Not in this repo.
