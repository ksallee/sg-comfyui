# The launch page

For Jeremy. This folder is the launch page and the docs pages. Everything here is yours to redesign.
The facts on the page are not: they come from the product and from `README.md` at the repo root.

## Run it

Requires node 22.

```sh
cd site
npm install
npm run dev
```

Open http://localhost:5173/sg-comfyui/ (the base path matches the GitHub Pages URL). Edits reload
in place.

## Where things are

| path | what |
|---|---|
| `src/app.css` | Tokens: colours for light and dark, type, radius, gutter, page width, band spacing, easing. Start here. |
| `src/routes/+page.svelte` | The landing page, one section per `<section class="band">`, styles at the bottom of the file. |
| `src/routes/docs/` | The docs pages, one folder each, sharing `+layout.svelte`. |
| `src/lib/Nav.svelte`, `Footer.svelte` | Nav and footer. |
| `src/lib/Clip.svelte` | A clip: MP4 and WebM sources, poster, pause control. |
| `src/lib/Shot.svelte` | A screenshot with a caption. Sizes are in `src/lib/site.js`. |
| `src/lib/Provenance.svelte` | The provenance section. |
| `src/lib/site.js` | Links, the nine provenance fields, image sizes. |
| `src/lib/readme/*.md` | Four blocks copied from the root `README.md`. Do not edit these; see below. |
| `static/media/` | Every clip, poster and screenshot. |
| `static/fonts/` | Geist and Geist Mono, self-hosted. |

## Rules that CI checks

- `npm run check` passes (svelte-check).
- `npm run build` passes.
- `npm run check:readme` passes. The four blocks under `src/lib/readme/` must match `README.md` at
  the repo root byte for byte. Change the root README, then run
  `node scripts/check-readme-blocks.mjs --write`.

## Rules that nothing checks

- No analytics, no tracking, no consent banner.
- No request to a third party at runtime: no external fonts, scripts, images or embeds.
- Dark only. There is no light scheme and no toggle.
- `prefers-reduced-motion: reduce` disables parallax and autoplay.
- No horizontal scroll at 375px.
- Every image and clip is a capture of the real product. Nothing is mocked in HTML.
- Copy follows `CLAUDE.md` at the repo root, section Writing. Short, exact, no selling, no em dashes.
  Change the words with Kevin.

## Captures

`npm run shots` serves the build and screenshots each section at 1440 and 375, both schemes, into
`~/Desktop/sg-comfyui-site-<date>/`. It needs `npm i --no-save playwright` once.

New product screenshots and clips are made by the harness under `tools/` at the repo root, not by
hand. Ask Kevin for a new capture.

## Ship

Branch off `dev`. Open a pull request onto `dev`. CI runs the three checks above. Kevin merges.
Publishing to GitHub Pages is a separate step Kevin runs.
