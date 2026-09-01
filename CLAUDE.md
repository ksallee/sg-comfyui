# comfyui-fpt

ComfyUI nodes that publish generations to Flow Production Tracking with provenance.

## Clean room

Never read: `~/dev/fpt-ai`, `~/dev/flow-data-api-docs`, `~/dev/flow-data-sdk-python`, `~/dev/tk-*`.
Derive only from public Flow PT REST docs and this repo's probe findings.

Out of scope, permanently: charts, dashboards, scheduled reports, webhooks, automations. Do not add them.

## Probes are the source of truth

The REST docs are incomplete and sometimes wrong. Never code against documented behaviour — probe it, record it, code against the finding.

- One question per probe: `probes/NNN_slug.py`
- Each writes `probes/findings/NNN_slug.md`: endpoint, doc claim, actual, verdict
- Read-only by default; writes require `--write`
- Sanitize before commit: no tokens, no site URL, no real names
- Code cites findings: `# probe 004`

Run: `python probes/004_slug.py`

## Stack

Python 3.11. Only what ComfyUI already ships: `requests`, `Pillow`. A new dependency needs a line in DESIGN.md justifying it.

## Secrets

`.env.local`, gitignored, never printed or logged. Auth is `client_credentials`: script name + key.

## Agent-operable

Forkers drive this repo with an agent, not by reading it. Small files, explicit names, no magic, no indirection. Conventions live here or in DESIGN.md — once, in one place.

## Style

Terse. Comments explain why, never what. Docstrings only for non-obvious behaviour or a probe citation.
