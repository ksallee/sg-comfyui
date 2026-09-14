---
description: Measure one Flow Production Tracking project and write the profile every picker reads
---

Project: $ARGUMENTS

`profile.local.json` is what this show practices: what a Version links to, what it is called, and
which statuses it uses. Without it the pickers run on the site's own defaults, which suit a show that
links Versions to Shots. This command measures the show and writes the file.

The inspector is **not in this repo**. It is in the corpus checkout,
`../sg-groundtruth/inspect_site.py`, which is the repo that owns site measurement. Run it as it is.
Do not copy it, do not fork it, do not add a wrapper here.

    <comfy-python> ../sg-groundtruth/inspect_site.py                        list projects
    <comfy-python> ../sg-groundtruth/inspect_site.py --project 1180 --out <profile path>

Run it with the interpreter that has `sg_groundtruth` installed, which is the one ComfyUI runs on.

Credentials come from `../sg-groundtruth/.env.local`, not this repo's. The script loads them from its
own root (`sg_groundtruth.env.load`), layered over the environment. Same three keys either way
(`.env.local.example`). A missing key is named, never printed.

Always pass `--out`. Its default is `./profile.local.json` relative to the *working directory*, and
the file has to be written where the nodes read it. Ask the running ComfyUI for that path:

    curl http://127.0.0.1:8188/sg/paths

The answer is `{"profile": ..., "store": ...}`. Pass `profile` to `--out`. Use the address the
operator opens ComfyUI at where that is not the default. A ComfyUI started before this version of the
pack answers 404 there; restart ComfyUI, then ask again. With ComfyUI stopped, `tools/doctor.py`
prints the pack directory instead, which is read only while the protected user directory holds no
profile.

A profile in ComfyUI's protected user directory is read instead of one in the pack directory, so
writing to the wrong one leaves the report looking right and nothing changed.

1. **List first.** Run with no `--project` and read the ids and names back. Do not guess which
   show they meant from a partial name.
2. `--project <id> --out <profile path>`. It prints a report and then writes. Both matter; the
   report is the evidence for what it wrote.
3. **Read the report back in plain language, section by section.** It is measurement, not a decision:

   - **link**: which field a Version links to here, and what it points at, counted over the sample
     (probe 005). The chosen one is marked. Inference is least reliable here, and a wrong answer
     raises no error: on the sandbox project a Version-to-Version field (`image_source_entity`) is
     filled 31/33 and outranks `entity` at 30/33, so the inspector proposes linking Versions to
     Versions. Read the spread out loud, "it wants `image_source_entity` -> Version; `entity` is
     Shot 29, Asset 1", and ask which one they mean. The answer is `entity` on most shows.
   - **status**: usable is valid_values minus this project's hidden_values (probe 009), plus what the
     sample uses. The default is the schema's, which a project may hide.
   - **code**: the naming convention inferred from the codes the show already uses, with its
     coverage. Read the coverage number out. 80%+ is worth trusting, 40-79% means a large minority
     disagree, below that there is no convention to learn and the inspector guessed. A graph with
     several image outputs gives each stream its own root name, and the version name builds on
     `{root_name}`. A convention with no such token in the name puts every pass on one name, so say
     so before they accept it.
   - **fields**: filled, then distinct (probes 007, 020). "Identifier" and "no information" are both
     reasons not to expose a field: one value per row is not a choice, and one value site-wide is not
     either.
4. **What it will not infer, and you must ask about.**
   - `version_number_field`: a numeric field on Version, if this site has one. The report names
     candidates and refuses to pick, because a wrong guess misnumbers every publish with no error.
     Set it by hand or leave it out. Without it the version number is inside the Version name.
   - Whether the middle token of a code is a render pass or a pipeline step (`{task}`). The report
     says how many of them match a Task name on this project. The operator decides.
5. **Merging.** Keyed per project: inspecting a second show adds a block and leaves the first alone.
   A re-run keeps existing values and prints `(yours, kept)` beside each one it would have changed.
   `--overwrite` discards them. Never pass `--overwrite` without being asked.
6. Show them the block that was written, key by key, and say the file is theirs to edit. It is plain
   JSON and hand-editing it is the expected way to correct anything above. Then run `tools/doctor.py`
   again: it renders each template in the profile against a sample publish and names any token that
   comes back with nothing.

Then `/track-workflow <workflow.json>` puts the nodes into a graph they already use. The nine
provenance fields are a separate, optional step: Settings, then SG, SG Site Setup.

## Keys the profile reads that the inspector never writes

Hand-added, per project or at the top level. INSTALL.md lists every key with its default and who
writes it; DESIGN.md says why each one exists.

    link_types            override the entity types the link picker searches
    version_number_field  the site's numeric version-number field, if it has one
    provenance            {"mode": ..., "map": {...}}, which field each provenance fact is written to
    widgets               which fields are in the fold on each node
    show_all_projects     site-wide; include template, demo and archived projects in the picker

## Sample size

`--versions` (default 100) is the broad pass. `--shortlist` (default 10) is how many fields get a
`_summarize` at ~300ms each. Raise the first on a busy show where 100 Versions are one week's work.
Raising the second costs a round trip per field.
