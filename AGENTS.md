# For an agent

This repo is two ComfyUI nodes. SG Publish sends a generation to Flow Production Tracking as a
Version with the model, prompt, seed, sampler and workflow that produced it. SG Load reads a Version's
media back into a graph. Nothing here makes images.

Run this first:

```sh
<comfy-python> tools/doctor.py            # the interpreter, the paths, the profile
<comfy-python> tools/doctor.py --site     # also the connection, the fields, the storage, the links
```

It prints one line per thing a publish needs, with the fix appended where it fails. It exits non-zero
on anything that would stop a publish.

## Which document

| job | read |
|---|---|
| What the nodes do, and a first run | `README.md` |
| A local file, an interpreter, a command, a profile key, a fix | `INSTALL.md` |
| Changing this code | `CLAUDE.md`, then `DESIGN.md` |

## The procedures

`.claude/commands/` holds three procedures. They are plain markdown with no Claude Code in them.
Follow the file whether or not your harness has slash commands.

| file | does |
|---|---|
| `.claude/commands/setup.md` | a first run, from the connection to the example workflow |
| `.claude/commands/inspect-site.md` | measure one project and write `profile.local.json` |
| `.claude/commands/track-workflow.md` | put the nodes into a graph the operator already uses |

## The launch page

The page under `site/` is written under `taste-skill`, in `.claude/skills/taste-skill/`. It is copied
verbatim from `github.com/leonxlnx/taste-skill` at `ccbc156` and pinned here, so a review reads what
the agent read. It is the only skill in that marketplace built for a landing page rather than for
generating images or for another vendor's tool. `minimalist-skill` sits beside it as an aesthetic
reference, pulled from and never followed whole.

`RELEASE.md` wins where the skill collides with this repo.

| the skill says | this repo |
|---|---|
| React, Next.js, Tailwind and Motion (3.A) | SvelteKit 2.70 with `adapter-static` |
| `picsum.photos` and Simple Icons (4.8) | captures of the nodes, served from the site itself |
| fonts through `next/font` | fonts self-hosted, with a real fallback stack |
| nothing about analytics | there are none |

A page on GitHub Pages fetches nothing from a third party. The skill's reduced-motion rule and its
GSAP ScrollTrigger skeletons stand as written. Every string a person reads follows CLAUDE.md, which
outranks the skill's marketing register.
