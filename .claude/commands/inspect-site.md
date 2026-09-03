---
description: Measure one Flow PT project and write the profile every picker reads
---

Project: $ARGUMENTS

Nothing in this repo works until `profile.local.json` exists. It is gitignored, so a fresh clone has
none, and both nodes read it to decide what a Version hangs off, what it is called and which statuses
exist. This command produces it.

The inspector is **not in this repo**. It lives in the corpus checkout, `../sg-groundtruth/inspect_site.py`,
because it is the corpus repo that owns site measurement. Drive it. Do not copy it, do not fork it, do
not add a wrapper here.

    python ../sg-groundtruth/inspect_site.py                        list projects
    python ../sg-groundtruth/inspect_site.py --project 1180 --out profile.local.json

Credentials come from `../sg-groundtruth/.env.local`, not this repo's — the script loads them from its
own root (`sg_groundtruth.env.load`), layered over the environment. Same three keys either way
(`.env.local.example`). A missing key is named, never printed.

`--out` is not optional in practice: the default is `./profile.local.json` relative to the *working
directory*, so run from this repo's root and pass it explicitly, or the profile lands next to the
inspector where nothing reads it.

1. **List first, always.** Run with no `--project` and read the ids and names back. Do not guess which
   show they meant from a partial name.
2. `--project <id> --out profile.local.json`. It prints a report and then writes. Both matter; the
   report is the evidence for what it wrote.
3. **Read the report back in plain language, section by section.** It is measurement, not a decision:

   - **link** — which field a Version actually hangs off here, and what it points at, counted over the
     sample (probe 005). The chosen one is marked. **This is where inference most often gets it wrong**,
     and it fails quietly: on the sandbox project a Version-to-Version field (`image_source_entity`) is
     filled 31/33 and outranks `entity` at 30/33, so the inspector proposes linking Versions to Versions.
     Read the spread out loud — "it wants `image_source_entity` -> Version; `entity` is Shot 29, Asset 1"
     — and ask which one they mean. Nearly always `entity`.
   - **status** — usable is valid_values minus this project's hidden_values (probe 009), plus what the
     sample actually uses. The default is the schema's, which a project may hide.
   - **code** — the naming convention inferred from the codes the show already uses, with its coverage.
     **The coverage number is the point.** 80%+ is worth trusting, 40-79% means a large minority
     disagree, below that there is no convention to learn and the honest answer is that it guessed.
     A graph with several image outputs needs `{output}` in the template or every pass collapses onto
     one name — say so before they accept it.
   - **fields** — filled, then distinct (probes 007, 020). "Identifier" and "no information" are both
     reasons not to expose a field: one value per row is not a choice, and one value site-wide is not
     either.
4. **What it will not infer, and you must ask about.**
   - `version_number_field` — a real numeric field on Version, if this site has one. The report names
     candidates and refuses to pick, because guessing wrong misnumbers every publish silently. Set it
     by hand or leave it out; without it the version lives inside `code`.
   - Whether the middle token of a code is a render pass (`{output}`) or a pipeline step (`{task}`).
     The report says how many of them match a Task name on this project. That count is the argument;
     the operator decides.
5. **Merging.** Keyed per project: inspecting a second show adds a block and leaves the first alone.
   Operator edits win — a re-run keeps existing values and prints `(yours, kept)` beside each one it
   would have changed. `--overwrite` discards them. Never pass `--overwrite` without being asked.
6. Show them the block that was written, key by key, and say the file is theirs to edit. It is plain
   JSON and hand-editing it is the expected way to correct anything above.

Then, in order:

    PYTHONPATH=src python -m comfyui_fpt.fields     create the nine provenance fields on Version
    /track-workflow <workflow.json>                 put the nodes into a graph

## Keys the profile carries that the inspector never writes

Hand-added, per project or at the top level, all documented in DESIGN.md:

    link_types            override the entity types the link picker searches
    version_number_field  the site's real version-number field, if it has one
    provenance            {"mode": ..., "map": {...}} — where each piece of provenance lands
    show_all_projects     site-wide; include template, demo and archived projects in the picker

## Sample size

`--versions` (default 100) is the broad pass; `--shortlist` (default 10) is how many fields get a
`_summarize` at ~300ms each. Raise the first on a busy show where 100 Versions are all one week's
work. Raising the second costs a round trip per field and rarely changes the answer.
