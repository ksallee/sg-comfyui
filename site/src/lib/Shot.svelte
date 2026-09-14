<script>
	import { base } from '$app/paths';
	import { shotSize } from '$lib/site.js';

	/** A capture of the editor, with the sentence that says what is in it. */
	let { name, alt, caption = '' } = $props();

	let [width, height] = $derived(shotSize[name] ?? [1100, 950]);
</script>

<figure class="shot">
	<img src="{base}/media/{name}.png" {alt} {width} {height} loading="lazy" decoding="async" />
	{#if caption}<figcaption>{caption}</figcaption>{/if}
</figure>

<style>
	.shot {
		margin: 0;
	}

	img {
		width: 100%;
		height: auto;
		border: 1px solid var(--line);
		border-radius: var(--r);
		background: var(--sunk);
	}

	figcaption {
		margin-top: 0.7rem;
		color: var(--muted);
		font-size: 0.875rem;
	}
</style>
