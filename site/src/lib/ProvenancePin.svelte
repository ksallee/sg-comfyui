<script>
	import Shot from '$lib/Shot.svelte';
	import { provenance } from '$lib/site.js';
	import { onMount } from 'svelte';

	// The one pinned section on the page. It keeps the section in place and steps the highlight down
	// the nine fields, so each field name and its source is read before the next arrives.

	let wrap = $state(null);
	let active = $state(0);
	let pinned = $state(false);

	onMount(() => {
		if (!wrap) return;
		if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
		if (window.matchMedia('(max-width: 900px)').matches) return;

		let context;
		let cancelled = false;

		(async () => {
			const { gsap } = await import('gsap');
			const { ScrollTrigger } = await import('gsap/ScrollTrigger');
			if (cancelled || !wrap) return;
			gsap.registerPlugin(ScrollTrigger);
			pinned = true;

			context = gsap.context(() => {
				ScrollTrigger.create({
					trigger: wrap,
					start: 'top top',
					end: () => `+=${provenance.length * 240}`,
					pin: true,
					scrub: true,
					invalidateOnRefresh: true,
					onUpdate(self) {
						const step = Math.floor(self.progress * provenance.length);
						active = Math.min(provenance.length - 1, Math.max(0, step));
					}
				});
			}, wrap);
		})();

		return () => {
			cancelled = true;
			context?.revert();
			pinned = false;
		};
	});
</script>

<section class="band" class:stepping={pinned} id="provenance" bind:this={wrap}>
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
			{#each provenance as [label, name, from], index (name)}
				<li class:on={!pinned || index === active}>
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

	.stepping {
		min-height: 100dvh;
		display: grid;
		align-items: center;
		padding-block: 4rem;
	}

	.stepping li {
		opacity: 0.32;
		transition: opacity 0.35s var(--ease), border-color 0.35s var(--ease);
	}

	.stepping li.on {
		opacity: 1;
		border-left-color: var(--accent);
	}

	@media (max-width: 900px) {
		.grid {
			grid-template-columns: minmax(0, 1fr);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.stepping li {
			opacity: 1;
			transition: none;
		}
	}
</style>
