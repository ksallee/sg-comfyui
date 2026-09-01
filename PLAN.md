# Plan

## State

Scaffolded. Auth proved (probe 001). Nothing built yet.

**Big Buck Bunny (70) is the inference sample, and stays read-only.** Probes 004/005 measure which fields are
actually filled; writing test Versions into it would skew the statistics the inspector reads.

Writes go to our own project, created in Phase 3 and seeded with our own generated media — which also keeps the
public demo clear of anyone else's asset licensing.

## Phase 0 — prove the API

No product code. Read-only. Every finding cited later by the code that depends on it.

- [x] 001 auth, token lifetime
- [ ] 002 schema read: entity types, Version fields, types, which are mandatory
- [ ] 003 query shape: deep-linked and bubbled fields on Versions (`sg_task.Task.content`), filters, paging
- [ ] 004 link usage: on BBB, what do Versions actually attach to, and at what rate
- [ ] 005 fill rates: which Version fields are populated on recent entries
- [ ] 006 upload: how media actually attaches to a Version, step by step
- [ ] 007 attachments: arbitrary file (workflow JSON) on a Version
- [ ] 008 custom fields: can a script create schema fields over REST, or is that admin-only

008 decides where provenance lives: real custom fields, or a JSON blob in an existing text field plus an
attachment. Do not design provenance storage before it lands.

## Phase 1 — inspector

- `inspect.py` turns 002–005 into `profile.local.json` for one project
- `/inspect-site` command: agent runs it, explains findings in plain language, operator edits and confirms

## Phase 2 — node

- `provenance.py`: model, prompt, seed, sampler, graph, input Version ids, out of the ComfyUI prompt object
- `FPT Publish Version`, inputs built from the profile
- Install into ComfyUI, publish end to end from a real graph

## Phase 3 — own project, loop, showcase

- Create our project; seed shots, tasks and media generated with nano banana 2 via the higgsfield MCP
- First write probes land here
- `FPT Fetch Media`, round trip
- Recorded demo; publish repo, `probes/findings/` becomes the public cookbook

## Open

- Does ComfyUI re-evaluate `INPUT_TYPES` on refresh, or does a profile change need a restart? Decides whether
  re-inspection is live or requires a bounce.
