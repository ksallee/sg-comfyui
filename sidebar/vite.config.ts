import { fileURLToPath } from 'node:url';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

// One ES module under ../web/sidebar/. ComfyUI imports every .js under web/ as an extension, so
// the build is one file with no chunks, and importing it has no side effects.
export default defineConfig({
	// Component styles are injected next to the component, which is inside the shadow root.
	plugins: [tailwindcss(), svelte({ compilerOptions: { css: 'injected' } })],
	// Library mode leaves `process.env.NODE_ENV` in dependencies' code, and a browser has no `process`.
	define: { 'process.env.NODE_ENV': JSON.stringify('production') },
	resolve: { alias: { $lib: fileURLToPath(new URL('./src/lib', import.meta.url)) } },
	build: {
		outDir: '../web/sidebar',
		emptyOutDir: true,
		minify: true,
		lib: { entry: 'src/main.ts', formats: ['es'], fileName: () => 'sg_sidebar_app.js' },
		rollupOptions: { output: { codeSplitting: false } }
	},
	test: { include: ['src/**/*.test.ts'] }
});
