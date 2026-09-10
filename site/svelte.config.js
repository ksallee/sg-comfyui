import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

// GitHub Pages serves a project site under /<repo>. BASE_PATH overrides it for a custom domain.
const base = process.env.BASE_PATH ?? '/sg-comfyui';

/** @type {import('@sveltejs/kit').Config} */
export default {
	preprocess: vitePreprocess(),
	kit: {
		adapter: adapter({ pages: 'build', assets: 'build', fallback: undefined, strict: true }),
		paths: { base: base === '/' ? '' : base, relative: true },
		prerender: { handleHttpError: 'fail' }
	}
};
