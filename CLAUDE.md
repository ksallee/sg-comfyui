# comfyui-flow-production-tracking

ComfyUI nodes that publish generations to Flow Production Tracking with provenance.

## Clean room

Never read: `~/dev/fpt-ai`, `~/dev/flow-data-api-docs`, `~/dev/flow-data-sdk-python`, `~/dev/tk-*`.
Derive only from public Flow PT REST docs and this repo's probe findings.

Out of scope, permanently: charts, dashboards, scheduled reports, webhooks, automations. Do not add them.

## The corpus lives next door

`../sg-groundtruth` holds every verified truth about the API, and the client. This repo probes nothing and
duplicates nothing.

Read `../sg-groundtruth/corpus/INDEX.md` first, always. Never code against behaviour no entry covers — that is a
gap, and the probe that closes it belongs in `sg-groundtruth`. Code cites entries: `# probe 004`.

Plan for both repos: `../sg-groundtruth/PLAN.md`.

## Stack

Python 3.11. `sg_groundtruth` for all site access, plus what ComfyUI already ships: `requests`, `Pillow`. Never
`shotgun_api3`, never `fpt-api` — it is AGPL. A new dependency needs a line in DESIGN.md justifying it.

The sibling checkout (`sg-groundtruth/`, package `sg_groundtruth`) is expected; override with `SG_GROUNDTRUTH_PATH`.

## Secrets

`.env.local`, gitignored, never printed or logged. Auth is `client_credentials`: script name + key.

## ComfyUI

Node classes register through `NODE_CLASS_MAPPINGS` in `__init__.py`. `INPUT_TYPES` is a classmethod evaluated
at load — that is the hook the site mapping drives. Provenance comes from the hidden `PROMPT` and
`EXTRA_PNGINFO` inputs, never from asking the user.

Where each piece of provenance lands in Flow PT is the operator's mapping, not a default. See DESIGN.md.

## Agent-operable

Forkers drive this repo with an agent, not by reading it. Small files, explicit names, no magic, no indirection. Conventions live here or in DESIGN.md — once, in one place.

## Style

Terse. Comments explain why, never what. Docstrings only for non-obvious behaviour or a probe citation.
