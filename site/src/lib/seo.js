import { docs, registry, repo } from '$lib/site.js';

/** The canonical origin. The sitemap, llms.txt and the share tags use absolute URLs. */
export const origin = 'https://sg-comfyui.vercel.app';

export const siteName = 'SG ComfyUI';

/** The base path a local build and GitHub Pages serve under; svelte.config.js defaults to it. */
export const localBase = '/sg-comfyui';

/** The share card. 1200 by 630, the size LinkedIn, Slack and X read. */
export const shareImage = `${origin}/media/og.png`;

/** Every page, as served: the landing page, the docs index, the nine docs pages. */
export function pages() {
	return ['/', '/docs/', ...docs.map((d) => `/docs/${d.slug}/`)];
}

export function sitemap() {
	const urls = pages()
		.map((path) => `\t<url><loc>${origin}${path}</loc></url>`)
		.join('\n');
	return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;
}

export function robots() {
	return `User-agent: *
Allow: /

Sitemap: ${origin}/sitemap.xml
`;
}

/** What an LLM client reads first: what the pack is, then one line per page. */
export function llmsTxt() {
	const lines = [
		'# SG ComfyUI',
		'',
		'Two ComfyUI nodes that record a generation in Flow Production Tracking, formerly ShotGrid.',
		'SG Publish creates a Version from an IMAGE or a VIDEO, uploads the media, and attaches the',
		'model, prompt, seed, sampler and workflow that made it. SG Load reads a Version\'s media back',
		'into a graph as image, video and mask. Nothing here generates, encodes or decodes.',
		'',
		`Requires ComfyUI 0.34.0 and Python 3.11. On the Comfy Registry as sg-comfyui: ${registry}.`,
		`Source, MIT: ${repo}. Issues: ${repo}/issues.`,
		'',
		'## Docs',
		'',
		...docs.map((d) => `- [${d.title}](${origin}/docs/${d.slug}/): ${d.blurb}`),
		'',
		'## For an agent',
		'',
		`- AGENTS.md in the repository is the entry point: ${repo}/blob/main/AGENTS.md`,
		`- README.md: ${repo}/blob/main/README.md`,
		`- INSTALL.md, every path and the profile key by key: ${repo}/blob/main/INSTALL.md`,
		''
	];
	return lines.join('\n');
}
