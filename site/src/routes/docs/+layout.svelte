<script>
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import { docs } from '$lib/site.js';

	let { children } = $props();
	let here = $derived(page.url.pathname.replace(/\/$/, ''));
</script>

<div class="page shell">
	<nav class="side" aria-label="Documentation">
		<a class="index" href="{base}/docs">Docs</a>
		<ul>
			{#each docs as doc (doc.slug)}
				<li>
					<a
						href="{base}/docs/{doc.slug}"
						aria-current={here.endsWith(`/docs/${doc.slug}`) ? 'page' : undefined}
					>
						{doc.title}
					</a>
				</li>
			{/each}
		</ul>
	</nav>
	<article class="doc">
		{@render children()}
	</article>
</div>

<style>
	.shell {
		display: grid;
		grid-template-columns: 210px minmax(0, 1fr);
		gap: clamp(2rem, 5vw, 4rem);
		padding-block: clamp(2.5rem, 5vw, 4rem) clamp(4rem, 8vw, 6rem);
		align-items: start;
	}

	.side {
		position: sticky;
		top: 96px;
	}

	.index {
		display: block;
		font-size: 0.8125rem;
		color: var(--muted);
		text-decoration: none;
		padding-bottom: 0.75rem;
		margin-bottom: 0.75rem;
		border-bottom: 1px solid var(--line);
	}

	.side ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.side li {
		margin-bottom: 0.15rem;
	}

	.side a[href] {
		display: block;
		padding: 0.3rem 0;
		color: var(--muted);
		text-decoration: none;
		font-size: 0.9375rem;
	}

	.side a:hover {
		color: var(--ink);
	}

	.side a[aria-current='page'] {
		color: var(--ink);
		font-weight: 520;
	}

	.doc :global(h1) {
		font-size: clamp(1.9rem, 1.2rem + 2.2vw, 2.6rem);
		margin-bottom: 1.25rem;
	}

	.doc :global(h2) {
		font-size: 1.3rem;
		margin: 2.75rem 0 0.9rem;
		padding-top: 1.5rem;
		border-top: 1px solid var(--line);
	}

	.doc :global(h3) {
		margin: 1.9rem 0 0.6rem;
	}

	.doc :global(.lede) {
		font-size: 1.125rem;
		max-width: 58ch;
	}

	@media (max-width: 860px) {
		.shell {
			grid-template-columns: minmax(0, 1fr);
		}

		.side {
			position: static;
		}

		.side ul {
			display: flex;
			flex-wrap: wrap;
			gap: 0.35rem 1.1rem;
		}
	}
</style>
