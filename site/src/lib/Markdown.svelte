<script>
	import { render } from '$lib/markdown.js';

	/** One of the four blocks copied out of README.md. */
	let { source } = $props();
	let html = $derived(render(source));
</script>

<div class="md">
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{@html html}
</div>

<style>
	.md :global(h3) {
		margin: 1.8rem 0 0.7rem;
		font-size: 0.9375rem;
		font-weight: 560;
		color: var(--muted);
	}

	.md :global(h3:first-child) {
		margin-top: 0;
	}

	.md :global(p:last-child),
	.md :global(pre:last-child),
	.md :global(ul:last-child),
	.md :global(ol:last-child),
	.md :global(table:last-child) {
		margin-bottom: 0;
	}
</style>
