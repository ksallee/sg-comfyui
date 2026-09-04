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

Plan for both repos: `../sg-groundtruth/PLAN.md` — older, and stale where this repo has moved past it.

`RELEASE.md` is what is being built now, what was decided and why, and what is still open. Read it
before starting work.

## Stack

Python 3.11. `sg_groundtruth` for all site access, plus what ComfyUI already ships: `requests`, `Pillow`. Never
`shotgun_api3`, never `fpt-api` — it is AGPL. A new dependency needs a line in DESIGN.md justifying it.

The sibling checkout (`sg-groundtruth/`, package `sg_groundtruth`) is expected; override with `SG_GROUNDTRUTH_PATH`.

## Running it

Everything runs from the repo root. Every `-m comfyui_fpt.*` needs `PYTHONPATH=src` — the package
lives under `src/` and nothing installs it. `instrument.py` is run as a file on purpose: `-m` would
import the package `__init__` and therefore torch, and a graph must stay analysable on a machine with
neither torch nor a route to the site.

Operation is `README.md`. The recurring jobs are slash commands: `/inspect-site` writes
`profile.local.json`, which is gitignored and which every picker reads, so nothing works before it;
`/track-workflow` puts the nodes into a graph the operator already uses.

## Secrets

`.env.local`, gitignored, never printed or logged. Auth is `client_credentials`: script name + key.

## ComfyUI

Node classes register through `NODE_CLASS_MAPPINGS` in `__init__.py`. `INPUT_TYPES` is a classmethod evaluated
at load — that is the hook the site mapping drives. Provenance comes from the hidden `PROMPT` and
`EXTRA_PNGINFO` inputs, never from asking the user.

Where each piece of provenance lands in Flow PT is the operator's mapping, not a default. See DESIGN.md.

**`widgets_values` is positional.** A widget inserted, removed or reordered displaces every value below it
in every graph already saved, silently — so append, never insert, and never remove. One declared order is
shared by `INPUT_TYPES`, `instrument.PUBLISH_WIDGETS`/`LOAD_WIDGETS`, `web/fpt_entity_picker.js` `DECLARED`
and every `*.json` under `example_workflows/` and `tools/workflows/`; all five move together or none do.
`tools/smoke.py` is what proves it, because only loading a saved graph in a real ComfyUI shows the shift.
An input *slot* is different: adding one is additive and safe.

**This node records; it does not make media.** Review media is derived and may be transcoded; a deliverable
file is never transformed. Nothing here encodes — `VideoInput.save_to()` is ComfyUI's own encoder and owns
that side.

## Agent-operable

Forkers drive this repo with an agent, not by reading it. Small files, explicit names, no magic, no indirection. Conventions live here or in DESIGN.md — once, in one place.

## Style

Terse. Comments explain why, never what. Docstrings only for non-obvious behaviour or a probe citation.
