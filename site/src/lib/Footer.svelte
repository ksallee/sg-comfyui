<script>
	import { base } from '$app/paths';
	import { docs, licence, registry, repo } from '$lib/site.js';

	const half = Math.ceil(docs.length / 2);
	const columns = [docs.slice(0, half), docs.slice(half)];
</script>

<footer id="footer">
	<div class="page inner">
		<div class="about">
			<h2>Flow Production Tracking for ComfyUI</h2>
			<p>
				Two ComfyUI nodes that record a generation in Flow Production Tracking, formerly ShotGrid.
			</p>
		</div>

		{#each columns as column, index (index)}
			<nav aria-label={index === 0 ? 'Documentation, first half' : 'Documentation, second half'}>
				<ul>
					{#each column as doc (doc.slug)}
						<li><a href="{base}/docs/{doc.slug}">{doc.title}</a></li>
					{/each}
				</ul>
			</nav>
		{/each}

		<nav aria-label="Project">
			<ul>
				<li><a href={repo} rel="external">Repository</a></li>
				<li><a href={registry} rel="external">Comfy Registry</a></li>
				<li><a href={licence} rel="external">MIT licence</a></li>
			</ul>
		</nav>
	</div>
	<div class="page rule">
		<p class="mono-label">
			The pack is not on the Comfy Registry yet. Install it from a checkout until it is.
		</p>
	</div>
</footer>

<style>
	footer {
		border-top: 1px solid var(--line);
		background: var(--sunk);
		padding-block: clamp(3rem, 6vw, 5rem) 2.5rem;
	}

	.inner {
		display: grid;
		grid-template-columns: minmax(0, 1.6fr) repeat(3, minmax(0, 1fr));
		gap: 2.5rem;
		align-items: start;
	}

	.about h2 {
		font-size: 1.0625rem;
		letter-spacing: -0.012em;
	}

	.about p {
		margin: 0.6rem 0 0;
		color: var(--muted);
		font-size: 0.9375rem;
		max-width: 34ch;
	}

	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	li {
		margin-bottom: 0.55rem;
	}

	a {
		color: var(--muted);
		text-decoration: none;
		font-size: 0.9375rem;
	}

	a:hover {
		color: var(--ink);
		text-decoration: underline;
	}

	.rule {
		margin-top: 2.75rem;
		padding-top: 1.5rem;
	}

	.rule p {
		margin: 0;
		border-top: 1px solid var(--line);
		padding-top: 1.5rem;
		max-width: none;
	}

	@media (max-width: 900px) {
		.inner {
			grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
			gap: 2rem;
		}

		.about {
			grid-column: 1 / -1;
		}
	}
</style>
