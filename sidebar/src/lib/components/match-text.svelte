<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import { matchRuns } from 'sg-widgets-core';
	import { cn, type WithElementRef } from '$lib/utils.js';

	type Props = WithElementRef<Omit<HTMLAttributes<HTMLSpanElement>, 'children'>, HTMLSpanElement> & {
		/** The label to draw. */
		text: string;
		/** What was searched for. Its whitespace-separated words are the ones marked. */
		query?: string;
	};

	let { text, query = '', class: className, ref = $bindable(null), ...rest }: Props = $props();
</script>

<!--
	A label with the query's matched runs at the weight `docs/design-rules.md` rule 6
	gives them.

	`POST /entity/_text_search` matches a row when every word of the query appears in
	it, so every word is marked wherever it occurs and overlapping words merge into one
	run (053_text_search_matching). Emphasis is weight and never colour, so a row that
	carries its own colour still reads. The runs are text: nothing here sets HTML from
	a row, and they rebuild the label exactly, so a label with no match draws as itself.
-->
<span data-slot="match-text" bind:this={ref} class={cn(className)} {...rest}
	>{#each matchRuns(text, query) as run, i (i)}<span
			class={run.match ? 'font-semibold' : undefined}>{run.text}</span
		>{/each}</span
>
