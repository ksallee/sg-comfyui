<script>
	import { base } from '$app/paths';
	import { onMount } from 'svelte';

	/**
	 * A screen recording. WebM first, MP4 second, a poster frame under both. It plays on entering
	 * the viewport and never on its own under `prefers-reduced-motion: reduce`.
	 */
	let { name, caption, ratio = '1600 / 1382' } = $props();

	let node = $state(null);
	let playing = $state(false);
	let ready = $state(false);

	onMount(() => {
		ready = true;
		const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		if (still || !node) return;

		const seen = new IntersectionObserver(
			(entries) => {
				for (const entry of entries) {
					if (entry.isIntersecting) node?.play().catch(() => {});
					else node?.pause();
				}
			},
			{ threshold: 0.35 }
		);
		seen.observe(node);
		return () => seen.disconnect();
	});

	function toggle() {
		if (!node) return;
		if (node.paused) node.play().catch(() => {});
		else node.pause();
	}
</script>

<figure class="clip">
	<div class="frame" style="aspect-ratio: {ratio}">
		<!-- svelte-ignore a11y_media_has_caption -->
		<video
			bind:this={node}
			poster="{base}/media/{name}.jpg"
			preload="metadata"
			muted
			loop
			playsinline
			onplay={() => (playing = true)}
			onpause={() => (playing = false)}
		>
			<source src="{base}/media/{name}.webm" type="video/webm" />
			<source src="{base}/media/{name}.mp4" type="video/mp4" />
		</video>
		{#if ready}
			<button type="button" class="control" onclick={toggle}>
				{playing ? 'Pause' : 'Play'}
			</button>
		{/if}
	</div>
	<figcaption>{caption}</figcaption>
</figure>

<style>
	.clip {
		margin: 0;
	}

	.frame {
		position: relative;
		background: var(--sunk);
		border: 1px solid var(--line);
		border-radius: var(--r);
		overflow: hidden;
	}

	video {
		width: 100%;
		height: 100%;
	}

	.control {
		position: absolute;
		right: 0.6rem;
		bottom: 0.6rem;
		font-family: var(--mono);
		font-size: 0.75rem;
		color: #f1efea;
		background: rgb(14 14 13 / 0.72);
		border: 1px solid rgb(241 239 234 / 0.28);
		border-radius: var(--r-sm);
		padding: 0.3rem 0.6rem;
		cursor: pointer;
		min-width: 3.6rem;
	}

	.control:hover {
		background: rgb(14 14 13 / 0.9);
	}

	figcaption {
		margin-top: 0.7rem;
		color: var(--muted);
		font-size: 0.875rem;
		max-width: 58ch;
	}
</style>
