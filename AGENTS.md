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

## The launch page

The launch page under `site/` is written under `taste-skill`, in `.claude/skills/taste-skill/`. It is
copied verbatim from `github.com/leonxlnx/taste-skill` at `ccbc156` and pinned here so a review reads
what the agent read. Of the thirteen skills in that marketplace it is the only one built for a
landing page rather than for generating images or for another vendor's tool, and its layout, copy
and pre-flight rules hold up away from the stack it assumes. `minimalist-skill` sits beside it as an
aesthetic reference and is pulled from, never followed whole.

Four of its instructions do not apply and `RELEASE.md` wins where they collide. Its section 3.A
assumes React, Next.js, Tailwind and Motion; the page is SvelteKit 2.70 with `adapter-static`. Its
section 4.8 reaches for `picsum.photos` and Simple Icons; every image and clip on this page is a
capture of the nodes, served from the site itself, because a page on GitHub Pages fetches nothing
from a third party. It says to load fonts through `next/font`; fonts are self-hosted with a real
fallback stack. It says nothing about analytics; there are none. Its reduced-motion rule and its
GSAP ScrollTrigger skeletons stand as written. Every string a person reads follows CLAUDE.md, which
outranks the skill's marketing register.
