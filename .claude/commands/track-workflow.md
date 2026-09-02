---
description: Add Flow PT tracking to a ComfyUI workflow the operator already uses
---

Workflow: $ARGUMENTS

Their graph already works. You are adding tracking to it, not redesigning it. The script does the
graph surgery; you ask the questions and explain the result.

1. `python src/comfyui_fpt/instrument.py <workflow.json>` — analysis only, writes nothing.
2. Read the two lists back in plain language:
   - **publishable streams** — each becomes a Version. Say what feeds it and what consumes it, so they
     recognise it: "the normal_directx output that currently only goes to a Preview".
   - **image inputs a Fetch could replace** — each is a place the graph could take its input from Flow
     PT instead of disk. This is what makes two graphs a pipeline.
3. **Propose the naming, do not leave it to them from nothing.** You have just read what each stream
   is — `depth`, `normal_opengl`, `mask` — so say what each Version would be called under this show's
   convention and let them correct it. `--template` prints the proposed codes beside each stream.
   A graph with several image outputs needs `{output}` in the template, or every pass collapses onto
   one name; a graph with one output does not.
4. Ask, and do not guess:
   - Which streams are worth a Version? Publishing every pass is usually wrong.
   - Which project, and which entity do these hang off? Read `profile.local.json`; if the project has
     no block yet, that is `/inspect-site`'s job first.
   - Should any loader read from Flow PT? Only if something upstream publishes there.
   - Which Task, if any. `{task}` is the pipeline step the Version hangs off and is the operator's
     call; `{output}` is what the stream is. They are different, and three passes may share one Task.
5. Check the naming convention exists for that project — `code_template` and `code_regex` in the
   profile. Without them `code = auto` fails loudly, which is correct: there is no version-number
   field on Version by default, so a convention cannot be assumed. `/inspect-site` infers it and
   reports its coverage.
6. Re-run the same script with `--out`, `--publish NODE:SLOT` and `--fetch NODE`. **Never overwrite the original.**
7. Say what changed in one line per node, and that the original is untouched.

Publishing is additive: tapping a stream leaves whatever already consumed it connected. Replacing a
loader rewires its consumers and leaves the loader in place but unwired, so they can see what was
swapped and put it back.

Validated against the 544 workflow templates ComfyUI ships: 528 parse, 0 errors, 268 have a
publishable stream and 177 have both. A workflow built from custom nodes this project has never heard
of still analyses correctly, because the rule is structural — an IMAGE link into a sink — not a list
of node names.

Run it as a file, not `-m`: the analyser needs no client, no site and no torch, so a graph can be
analysed on a machine that cannot reach Flow PT at all.
