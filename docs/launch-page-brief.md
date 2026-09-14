# Launch page brief

For the agent that builds `site/`. Read `RELEASE.md` first, then this.

## What it is

A static launch page for sg-comfyui: two ComfyUI nodes that publish generations to Flow Production
Tracking as Versions with the model, prompt, seed, sampler and workflow that made them, and read
that media back into a graph. The audience runs ComfyUI and has a Flow Production Tracking site.
They judge the page on the clips.

- SvelteKit 2.70, `adapter-static`, GitHub Pages from a `gh-pages` branch. No scroll-pinned section.
- Sources under `site/`.
- Fourteen sections, hero to footer, and nine docs pages.
- Four blocks copied from `README.md`, diffed in CI.

## The skill

`.claude/skills/taste-skill/`, copied verbatim from `github.com/leonxlnx/taste-skill` at `ccbc156`.
Invoke with `Skill(skill="taste-skill")`. Work through it in its order: the Design Read (section
0.B), the three dials (section 1), the layout, content and copy rules, the Pre-Flight Check
(section 14) before the page is done.

`.claude/skills/minimalist-skill/` is a reference for colour, type and spacing. Do not invoke it as
the process.

Design Read to confirm or argue with: a developer-tool launch for pipeline TDs and VFX artists,
restrained technical-editorial, native CSS in SvelteKit, self-hosted type, no pinned scroll section.
Dials: `DESIGN_VARIANCE 6`, `MOTION_INTENSITY 5`, `VISUAL_DENSITY 4`.

## Inputs

| input | where |
|---|---|
| Clips | `~/Desktop/sg-comfyui-clips-2026-09-10/`, seven clips as MP4, WebM, animated WebP |
| Screenshots | `~/Desktop/sg-comfyui-checkpoint-2026-09-10/`, eighteen numbered shots |
| README | `README.md`, source of the four diffed blocks; copy them |
| Product truth | `INSTALL.md`, `AGENTS.md`, `DESIGN.md`, `RELEASE.md` |

Nothing is fetched from a third party at runtime.

## Overrides to the skill

1. **Stack (section 3.A).** Not React, Next.js, Tailwind or Motion. SvelteKit and native CSS.
   `useReducedMotion()` maps to `matchMedia('(prefers-reduced-motion: reduce)')` and the CSS media
   query. Motion in leaf components with `onMount` and a teardown.
2. **Image sources (sections 4.8, 9.E).** No image-generation tool, no picsum, no simpleicons. Every
   image is a capture. No logo wall. Where the skill wants one, put the feedback list from
   `RELEASE.md`.
3. **Fonts (section 3.A).** Self-host with `@font-face` and `font-display: swap`. A real fallback stack.
   No external font host.
4. **Analytics.** None. No script, pixel, beacon, embed or consent banner.
5. **Copy.** CLAUDE.md's Writing and operator-message rules outrank the skill for any string that
   also appears in the product, the docs or a command. Keep the skill's own bans: no "Elevate",
   "Seamless", "Unleash", no invented numbers, no fake screenshots built from divs.

Keep unchanged: the Pre-Flight Check; section 6.B reduced motion; 5.D forbidden animation patterns; 4.7 layout
discipline; 4.9 content density; 6.C and 8 dark mode; 13 out of scope.

## Sections

1. Hero: what the pack does in one line, one clip, one install CTA.
2. The problem: a generation is a file with nothing attached.
3. SG Publish: a Version with model, prompt, seed, sampler, workflow. Clip.
4. SG Load: the media back into a graph, mask and format. Clip.
5. Provenance: the nine fields, and a site without them.
6. Formats: 8-bit PNG, 16-bit PNG, EXR 32-bit float, written by ComfyUI's encoder.
7. Templates, and `/track-workflow` on an existing graph.
8. Storage and paths: copy never move, the frame token, Windows notation.
9. Signing in: App Session Launcher, or a script name and key.
10. Install: ComfyUI Manager, the Registry, a checkout. Command blocks match `README.md`.
11. `tools/doctor.py`: the offline check.
12. Not in scope: no encoder, no decoder, no charts, no dashboards, no automations.
13. What's next, tell us: the feedback list from `RELEASE.md`, verbatim.
14. Footer: docs sitemap, licence, repository, Registry entry.

Docs pages: install, first run, the profile, the two nodes, the provenance fields, formats and colour
space, storage and paths, troubleshooting, the agent page.

## Done means

- Every Pre-Flight Check box ticked.
- `prefers-reduced-motion: reduce` gives no parallax and no autoplay.
- Every clip has a poster frame, `muted`, `playsinline`, a pause control.
- No network request leaves the origin on a cold load.
- The four README blocks are byte-identical to `README.md`, checked in CI.
- No horizontal scroll at 375px.
- Both colour schemes seen.
