<script>
	import { base } from '$app/paths';
	import { docs } from '$lib/site.js';
</script>

<svelte:head>
	<title>Docs. SG ComfyUI</title>
	<meta name="description" content="Nine pages: install, first run, the profile, the two nodes, provenance, formats, storage, troubleshooting, and the agent entry point." />
</svelte:head>

<h1>Docs</h1>
<p class="lede">
	The same text is in <code>README.md</code>, <code>INSTALL.md</code>
	and <code>AGENTS.md</code>.
</p>

<ul class="cards">
	{#each docs as doc (doc.slug)}
		<li>
			<a href="{base}/docs/{doc.slug}">
				<span class="title">{doc.title}</span>
				<span class="blurb">{doc.blurb}</span>
			</a>
		</li>
	{/each}
</ul>

<style>
	.cards {
		list-style: none;
		margin: 2.5rem 0 0;
		padding: 0;
		max-width: none;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 1rem;
	}

	li {
		margin: 0;
	}

	a {
		display: grid;
		gap: 0.35rem;
		height: 100%;
		border: 1px solid var(--line);
		border-radius: var(--r);
		background: var(--surface);
		padding: 1.15rem 1.25rem;
		text-decoration: none;
		color: var(--ink);
		transition: border-color 0.2s var(--ease);
	}

	a:hover {
		border-color: var(--muted);
	}

	.title {
		font-weight: 560;
		letter-spacing: -0.012em;
	}

	.blurb {
		color: var(--muted);
		font-size: 0.9375rem;
	}
</style>
