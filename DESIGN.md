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

## Nodes (v0)

- `FPT Publish Version` — image in, Version created on a Task/Asset/Shot, media uploaded, provenance attached
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
