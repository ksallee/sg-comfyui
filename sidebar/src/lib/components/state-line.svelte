<script lang="ts" module>
	import type { WidgetState } from 'sg-widgets-core';

	/** Where the line sits: `docs/design-rules.md` rule 5 gives each its own inset. */
	export type StateLinePad = 'popover' | 'table' | 'none';

	const LINE = 'flex items-center justify-center gap-1.5 text-center text-sm';
	const TONE: Record<Exclude<WidgetState, 'loading' | 'rows'>, string> = {
		empty: 'text-muted-foreground',
		error: 'text-destructive'
	};
	const PAD: Record<StateLinePad, string> = { popover: 'py-6', table: 'py-10', none: '' };
</script>

<script lang="ts">
	import type { Component, Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import type { LucideIcon } from '@lucide/svelte';
	import { cn, type WithElementRef } from '$lib/utils.js';

	type Props = WithElementRef<HTMLAttributes<HTMLDivElement>> & {
		/** Which state this is. An error is destructive, an empty state muted. */
		state: Exclude<WidgetState, 'loading' | 'rows'>;
		/** The line to show. */
		label: string;
		/** The glyph in front of it. */
		icon?: LucideIcon | Component | null;
		/** `popover` for a list, `table` for a body, `none` under loaded rows. */
		pad?: StateLinePad;
		/** The `data-slot` this block carries. Defaults to `state-line`. */
		slotName?: string;
		/** Anything after the line: a retry control. */
		children?: Snippet;
	};

	let {
		state,
		label,
		icon: Icon = null,
		pad = 'popover',
		slotName,
		class: className,
		children,
		ref = $bindable(null),
		...rest
	}: Props = $props();
</script>

<!--
	The empty and error line of `docs/design-rules.md` rule 5, drawn once for every
	widget in this registry. Loading is skeletons shaped like the rows they stand in
	for, so it stays with the widget that knows that shape.
-->
<div
	bind:this={ref}
	data-slot={slotName ?? 'state-line'}
	data-state={state}
	class={cn(LINE, TONE[state], PAD[pad], className)}
	{...rest}
>
	{#if Icon}
		<Icon aria-hidden="true" class="size-4 shrink-0" />
	{/if}
	<span class="min-w-0 truncate" title={label}>{label}</span>
	{@render children?.()}
</div>
