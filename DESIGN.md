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

No wrapper over `fpt-api` or `shotgun_api3`. A ComfyUI node ships into someone else's Python env; every dependency is a support burden. `requests` only.

## Site profile

Every site is different: custom fields, custom entity types, different mandatory fields, different status lists,
and no agreement on whether a Version hangs off a Task, a Shot, an Asset or a playlist. Integrations here fail
because they hardcode one studio's conventions, or expose every field and become unusable.

Instead the operator's agent inspects their site and writes a profile the node consumes.

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
