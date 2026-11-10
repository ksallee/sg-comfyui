<script>
	import Head from '$lib/Head.svelte';
	import { base } from '$app/paths';
	import Shot from '$lib/Shot.svelte';
	import { author, licence, repo } from '$lib/site.js';
	import { reveal } from '$lib/reveal.js';

	const recorded = [
		['Model', 'the checkpoints the graph loaded'],
		['Prompt and negative prompt', 'the text encoded into the conditioning on this branch'],
		['Seed, sampler, steps, CFG', 'the last sampler on the branch'],
		['Workflow', 'the graph, attached when the ComfyUI editor sends it'],
		['Built from', 'the earlier versions this generation was made from']
	];
</script>

<svelte:head>
	<Head
		title="Provenance for generative pipelines. SG ComfyUI"
		description="sg-comfyui records which model, prompt and input versions made each ComfyUI generation, when the generation is made. Open source, MIT."
	/>
</svelte:head>

<!-- 1. The problem -->
<section class="hero">
	<div class="page">
		<h1>Provenance for generative pipelines</h1>
		<p class="lede">
			A generative pipeline makes thousands of images and clips. A month later someone asks which
			model made the shot that shipped, with which prompt, from which input images. Most studios
			cannot answer.
		</p>
	</div>
</section>

<!-- 2. The answer -->
<section class="band" use:reveal>
	<div class="page answer">
		<div>
			<h2>sg-comfyui records the answer when the generation is made.</h2>
			<p class="lede">
				One node at the end of a ComfyUI graph, SG Publish, writes the model, prompt, negative
				prompt, seed, sampler, steps and CFG, the workflow, and the versions the generation was built
				from.
			</p>
			<p>
				Each record is also a <code>.provenance.json</code> file, attached to the published media. An
				input is linked as a version when a second node, SG Load, read it into the graph. Each
				output records only the branch of the graph that made it.
			</p>
			<ol class="fields">
				{#each recorded as [label, from] (label)}
					<li>
						<span class="label">{label}</span>
						<span class="from">{from}</span>
					</li>
				{/each}
			</ol>
		</div>
		<div class="answer-shot">
			<Shot
				name="load-provenance-rows"
				alt="The SG Load panel listing a version's provenance: model, prompt, seed, sampler, steps and cfg"
				caption="SG Load showing the provenance a published version records."
			/>
		</div>
	</div>
</section>

<!-- 3. Queryable -->
<section class="band" use:reveal>
	<div class="page">
		<h2>The records are queryable.</h2>
		<p class="lede wide">
			Each fact is a typed field on the version. Find every output of one model, or follow a final
			shot back through the versions it was built from.
		</p>
		<div class="contrast">
			<div class="cell">
				<h3>A file in the output folder</h3>
				<ul>
					<li>A file name.</li>
					<li>A size and a date.</li>
					<li>Whatever the artist typed into the name.</li>
				</ul>
			</div>
			<div class="cell">
				<h3>A version published by sg-comfyui</h3>
				<ul>
					<li>Nine typed fields, queryable in a filter.</li>
					<li>A link to each version it was built from.</li>
					<li>A <code>.provenance.json</code> record, attached.</li>
					<li>The workflow, attached when the ComfyUI editor sends it.</li>
					<li>Review media that plays in a browser.</li>
				</ul>
			</div>
		</div>
	</div>
</section>

<!-- 4. Where it is stored -->
<section class="band" use:reveal>
	<div class="page">
		<h2>Stored in Flow Production Tracking.</h2>
		<p class="lede wide">
			Today the records are stored in Flow Production Tracking, the production tracker many film and
			animation studios use. It was formerly called ShotGrid. Each generation becomes a Version
			there, linked to a shot or an asset.
		</p>
	</div>
</section>

<!-- 5. Who built it, and where to go -->
<section class="band" use:reveal>
	<div class="page about">
		<div>
			<h2>Open source, MIT.</h2>
			<p class="lede">
				Built by Kevin Sallée: 12 years of film pipelines, then Product Manager at Autodesk.
			</p>
			<p class="contact">
				Contact Kevin on <a href={author} rel="external">LinkedIn</a>.
			</p>
		</div>
		<ul class="links">
			<li><a class="button" href={repo} rel="external">The GitHub repository</a></li>
			<li><a class="button quiet" href="{base}/docs/install">Install</a></li>
			<li><a class="button quiet" href="{base}/docs/provenance">The provenance fields</a></li>
			<li><a class="button quiet" href={licence} rel="external">MIT licence</a></li>
		</ul>
	</div>
</section>

<style>
	.hero {
		padding-block: clamp(3rem, 6vw, 5.5rem);
	}

	.hero h1 {
		font-size: clamp(2.15rem, 1rem + 2.8vw, 3.4rem);
		max-width: 18ch;
	}

	.hero .lede {
		margin-top: 1.5rem;
		max-width: 52ch;
		font-size: 1.125rem;
	}

	.answer {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: clamp(2rem, 5vw, 4.5rem);
		align-items: start;
	}

	.answer h2 {
		margin-bottom: 1rem;
	}

	.answer .lede {
		margin-bottom: 0.9rem;
	}

	.fields {
		list-style: none;
		margin: 1.5rem 0 0;
		padding: 0;
		max-width: none;
	}

	.fields li {
		display: grid;
		gap: 0.15rem;
		padding: 0.68rem 0 0.68rem 0.95rem;
		border-left: 2px solid var(--line);
		margin: 0;
	}

	.label {
		font-weight: 560;
		letter-spacing: -0.012em;
	}

	.from {
		color: var(--muted);
		font-size: 0.875rem;
	}

	.lede.wide {
		max-width: 58ch;
		margin-top: 1rem;
	}

	.contrast {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: 1.25rem;
		margin-top: 2.75rem;
	}

	.cell {
		border: 1px solid var(--line);
		border-radius: var(--r);
		background: var(--surface);
		padding: clamp(1.25rem, 2.4vw, 1.9rem);
	}

	.cell h3 {
		margin-bottom: 0.85rem;
		color: var(--muted);
		font-size: 0.8125rem;
		font-weight: 560;
		letter-spacing: 0.01em;
	}

	.cell ul {
		margin: 0;
	}

	.cell li:last-child {
		margin-bottom: 0;
	}

	.about {
		display: grid;
		grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);
		gap: clamp(2rem, 5vw, 4rem);
		align-items: center;
	}

	.about h2 {
		margin-bottom: 1.1rem;
	}

	.about .lede {
		margin: 0;
		font-size: 1.125rem;
		max-width: 46ch;
	}

	.contact {
		margin: 1rem 0 0;
	}

	.links {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.links li {
		margin: 0;
	}

	@media (max-width: 900px) {
		.answer,
		.contrast,
		.about {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
