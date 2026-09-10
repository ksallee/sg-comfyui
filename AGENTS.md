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

`.claude/commands/` has four procedures. They are plain markdown with no Claude Code in them.
Follow the file whether or not your harness has slash commands.

| file | does |
|---|---|
| `.claude/commands/setup.md` | a first run, from the connection to the example workflow |
| `.claude/commands/inspect-site.md` | measure one project and write `profile.local.json` |
| `.claude/commands/track-workflow.md` | put the nodes into a graph the operator already uses |
| `.claude/commands/task.md` | do a job against the API, grounded in the corpus |

## The launch page

The page under `site/` is written under `taste-skill`, in `.claude/skills/taste-skill/`. It is copied
verbatim from `github.com/leonxlnx/taste-skill` at `ccbc156` and pinned here, so a review reads what
the agent read. `minimalist-skill` is an aesthetic reference, read in part and not followed.

`RELEASE.md` takes precedence over the skill.

| the skill says | this repo |
|---|---|
| React, Next.js, Tailwind and Motion (3.A) | SvelteKit 2.70 with `adapter-static` |
| `picsum.photos` and Simple Icons (4.8) | captures of the nodes, served from the site itself |
| fonts through `next/font` | fonts self-hosted, with a fallback stack |
| nothing about analytics | there are none |

A page on GitHub Pages fetches nothing from a third party. The skill's reduced-motion rule applies
as written. No section is pinned to the scroll. Strings a person reads follow CLAUDE.md, not the
skill's marketing register.
