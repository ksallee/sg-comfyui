<script>
	import Shot from '$lib/Shot.svelte';
	import { provenance } from '$lib/site.js';
</script>
<section class="band" id="provenance">
	<div class="page grid">
		<div class="side">
			<h2>Provenance</h2>
			<p class="lede">
				AI provenance is recorded in Version fields: <code>sg_ai_generator</code>,
				<code>sg_ai_model</code>, <code>sg_ai_prompt</code>, and so on. A site without them gets the
				same facts in the Version's description.
			</p>
			<p>
				SG Publish shows what it will record. SG Load shows what a Version records. An agent sets
				the fields up and remaps them (<code>/setup</code>, SG Site Setup).
			</p>
			<div class="side-shot">
				<Shot
					name="load-provenance-rows"
					alt="The SG Load panel listing a Version's provenance: model, prompt, seed, sampler, steps and cfg"
					caption="SG Load on a pinned Version, before the graph runs."
				/>
			</div>
		</div>

		<ol class="fields">
			{#each provenance as [label, name, from] (name)}
				<li>
					<span class="head">
						<span class="label">{label}</span>
						<code>{name}</code>
					</span>
					<span class="from">{from}</span>
				</li>
			{/each}
		</ol>
	</div>
</section>

<style>
	.grid {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: clamp(2rem, 5vw, 4.5rem);
		align-items: start;
	}

	.side h2 {
		margin-bottom: 1rem;
	}

	.side-shot {
		margin-top: 1.5rem;
	}

	.side h2 + .lede {
		margin-bottom: 0.9rem;
	}

	.fields {
		list-style: none;
		margin: 0;
		padding: 0;
		max-width: none;
	}

	li {
		display: grid;
		gap: 0.15rem;
		padding: 0.68rem 0 0.68rem 0.95rem;
		border-left: 2px solid var(--line);
		margin: 0;
	}

	.head {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.6rem;
	}

	.label {
		font-weight: 560;
		letter-spacing: -0.012em;
	}

	code {
		font-size: 0.75rem;
		background: none;
		border: 0;
		padding: 0;
		color: var(--accent);
	}

	.from {
		color: var(--muted);
		font-size: 0.875rem;
	}

	@media (max-width: 900px) {
		.grid {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
