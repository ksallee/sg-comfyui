---
description: Add Flow Production Tracking tracking to a ComfyUI workflow the operator already uses
---

Workflow: $ARGUMENTS

Their graph already works. You are adding tracking to it, not redesigning it. The script does the
graph surgery; you ask the questions and explain the result.

1. `python src/comfyui_sg/instrument.py <workflow.json>` — analysis only, writes nothing. Run from
   the pack directory; this one needs no `PYTHONPATH`, no credentials and no profile (see the last
   paragraph for why).
2. Read the two lists back in plain language:
   - **publishable streams** — each becomes a Version. Say what feeds it and what consumes it, so they
     recognise it: "the normal_directx output that currently only goes to a Preview".
     A node printed as `306/296` is inside the subgraph the line names; pass that whole path to
     `--publish`, and say which subgraph it is in, because that is how the operator finds it on the
     canvas.
   - **image inputs a Load could replace** — each is a place the graph could take its input from SG
     instead of disk. This is what makes two graphs a pipeline.
3. **Propose the naming, do not leave it to them from nothing.** You have just read what each stream
   is — `depth`, `normal_opengl`, `mask` — and the report prints the root name it derived for each
   one, plus the Version name that follows from it. Say both back and let them correct it.
   `--template` prints the proposed names beside each stream. One root name per stream is what keeps
   several passes out of one another's numbering.
4. Ask, and do not guess:
   - Which streams are worth a Version? Publishing every pass is usually wrong.
   - Which project, and which entity do these hang off? Give `--link` the typed form the picker
     uses, `sh010 (Shot)` or `charA (Asset)` — a bare name still works but falls back to the
     project's default type, which may not be the one meant.
   - Should any loader read from Flow Production Tracking? If something upstream already publishes
     there, point it at that. If nothing does — the ordinary case for the first graph in a chain —
     offer to put the file the loader *already reads* into Flow Production Tracking first, and then
     replace it. Do not skip the loaders just because nothing has published yet; that is the
     chicken-and-egg, and step 4b is the way out of it.
   - Which Task, if any. A Task is the pipeline step the Version hangs off and is the operator's
     call; the root name is what the stream is. They are different, and three passes may share one
     Task.
4b. **If they said yes to seeding an input**, ask the same questions once more for it — project,
   link, and what the stream IS. The root name is written the way the node's root name widget is
   written, as a template: `{entity}_plate`, not the file's name.

       PYTHONPATH=src python -m comfyui_sg.seed <file> --project P --link "sh010 (Shot)" \
           --root-name "{entity}_plate" --note "..."

   `PYTHONPATH=src` and the pack directory are required for every `-m comfyui_sg.*`: the package
   lives under `src/` and nothing installs it. This one also needs `.env.local` and
   `profile.local.json`. `<file>` is a path on disk, so join ComfyUI's `input/` directory to whatever
   `LoadImage` names, and check the file is there: corpus graphs rarely ship the image they were
   built on. Print the Version name it produced and use that when you wire the Load node.

   A new Shot or Asset reaches the link picker only once a Version points at it, and the editor's
   lookups are cached for 600 seconds. After seeding, press **Sync from SG** on the node, or reload
   the page, before saying it did not work.

   Say plainly that a seeded Version carries **no generation record** — the Load panel will show it
   as such — because a file on disk does not say how it was made. If they know it was AI generated
   elsewhere, that belongs in `--note`, not in the AI fields, which are for what this graph did.

5. Check the naming convention for that project — `root_name` and `code_template` in the profile,
   which Settings, then SG, SG Publish Defaults writes. Both have defaults, so a show that has said
   nothing still numbers correctly: the matcher for previous versions is derived from the version
   name template itself. `code_regex` in the profile is only for SG Load, which reads it to rank
   Versions by the number in the name.
6. Re-run the same script with `--out`, `--publish NODE:SLOT` and `--load NODE`. **Never overwrite the original.**
7. Say what changed in one line per node, and that the original is untouched.

Publishing is additive: tapping a stream leaves whatever already consumed it connected. Replacing a
loader rewires its consumers and leaves the loader in place but unwired, so they can see what was
swapped and put it back.

A stream inside a subgraph is tapped at the subgraph's output: an existing output slot if the stream
already leaves through one, otherwise a new one named after the stream — the same thing dragging an
interior output onto the output panel does — so the publish node still sits at the top level. The
script prints which of the two happened; say so in step 7. A loader inside a subgraph is replaced
inside it instead, because adding an output to a definition is additive and rewiring its interior is
not.

Measured over the full 680-graph corpus (the ComfyUI templates plus three public collections): 0
errors, 546 have a publishable stream, 430 have a loader. See DESIGN.md, "Coverage, measured", for
what the stream count means and why it matters more than the graph count.

A workflow built from custom nodes this project has never heard of still analyses correctly, because
the rule is structural — an IMAGE link into a sink — not a list of node names.

Run it as a file, not `-m`: `-m` imports the package `__init__`, which imports the nodes and therefore
torch. As a file the analyser needs no client, no site and no torch, so a graph can be analysed on a
machine that cannot reach Flow Production Tracking at all.
