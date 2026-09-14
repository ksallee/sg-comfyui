<script>
	import { base } from '$app/paths';
	import { repo } from '$lib/site.js';
</script>

<header>
	<nav class="page" aria-label="Main">
		<a class="wordmark" href="{base}/">
			<span class="mark" aria-hidden="true">SG</span>
			<span>SG ComfyUI</span>
		</a>
		<ul>
			<li><a href="{base}/#install">Install</a></li>
			<li><a href="{base}/docs">Docs</a></li>
			<li><a href={repo} rel="external">GitHub</a></li>
		</ul>
	</nav>
</header>

<style>
	header {
		position: sticky;
		top: 0;
		z-index: 20;
		background: color-mix(in srgb, var(--paper) 88%, transparent);
		backdrop-filter: blur(10px);
		border-bottom: 1px solid var(--line);
	}

	nav {
		height: 64px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1.5rem;
	}

	.wordmark {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		color: var(--ink);
		text-decoration: none;
		font-size: 0.9375rem;
		font-weight: 520;
		letter-spacing: -0.012em;
		white-space: nowrap;
		min-width: 0;
	}

	.wordmark span:last-child {
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.mark {
		display: grid;
		place-items: center;
		width: 26px;
		height: 26px;
		flex: none;
		border-radius: var(--r-sm);
		background: var(--ink);
		color: var(--paper);
		font-family: var(--mono);
		font-size: 0.6875rem;
		letter-spacing: 0;
	}

	ul {
		display: flex;
		align-items: center;
		gap: 1.4rem;
		list-style: none;
		margin: 0;
		padding: 0;
		flex: none;
	}

	li {
		margin: 0;
	}

	ul a {
		color: var(--muted);
		text-decoration: none;
		font-size: 0.9375rem;
	}

	ul a:hover {
		color: var(--ink);
	}

	@media (max-width: 640px) {
		.wordmark span:last-child {
			display: none;
		}

		ul {
			gap: 1.05rem;
		}
	}
</style>
