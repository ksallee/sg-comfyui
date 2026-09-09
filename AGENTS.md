# For an agent

This repo is two ComfyUI nodes. SG Publish sends a generation to Flow Production Tracking as a
Version with the model, prompt, seed, sampler and workflow that produced it. SG Load reads a Version's
media back into a graph. Nothing here makes images.

Run this first. It prints one line per thing a publish needs, with the fix appended where it fails,
and exits non-zero on anything that would stop a publish:

```sh
<comfy-python> tools/doctor.py            # the interpreter, the paths, the profile
<comfy-python> tools/doctor.py --site     # also the connection, the fields, the storage, the links
```

Then read `README.md` for what the nodes do, and `INSTALL.md` for where the local files live, which
interpreter runs which command, the profile key by key, and what to do when something does not answer.

Three procedures live in `.claude/commands/`. They are plain markdown with no Claude Code in them, so
follow the file whether or not your harness has slash commands:

- `.claude/commands/setup.md` — a first run, from the connection to the example workflow.
- `.claude/commands/inspect-site.md` — measure one project and write `profile.local.json`.
- `.claude/commands/track-workflow.md` — put the nodes into a graph the operator already uses.

Which document is yours depends on the job:

- **Working for an operator**, setting this up or putting the nodes into their graph: `README.md`,
  `INSTALL.md`, and the procedure above that matches the job.
- **Changing this code**: `CLAUDE.md` first, which holds the conventions this repo is held to, then
  `DESIGN.md`, which is why each decision is the one that was made.
