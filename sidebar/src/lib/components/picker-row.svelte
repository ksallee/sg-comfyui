<script lang="ts" module>
	import type { FieldSpec, PickerRow as PickerRowData, SgContext } from 'sg-widgets-core';

	export type PickerRowSize = 'sm' | 'md' | 'lg';

	/** The leading slot follows the thumbnail ladder of `docs/design-rules.md`. */
	const LEAD: Record<PickerRowSize, string> = { sm: 'size-6', md: 'size-8', lg: 'size-10' };
	/** The indicator column is as tall as the leading slot, so a checkbox centres on the picture. */
	const LEAD_HEIGHT: Record<PickerRowSize, string> = { sm: 'h-6', md: 'h-8', lg: 'h-10' };
	const GLYPH: Record<PickerRowSize, string> = { sm: 'size-3.5', md: 'size-4', lg: 'size-5' };
	/** A row's text, on the leaf ladder of `docs/design-rules.md`. */
	const TEXT: Record<PickerRowSize, string> = { sm: 'text-xs', md: 'text-sm', lg: 'text-base' };

	const PEOPLE = ['HumanUser', 'ApiUser', 'ClientUser'];

	/** Everything rule 9 of `docs/design-rules.md` gives a row, as one props object. */
	export interface PickerRowProps {
		/** The row to draw: the reference, its label and the values a read answered. */
		row: PickerRowData;
		/** The query whose matched runs are bold. */
		query?: string;
		/** Crumbs drawn before the label, muted and separated by `›`. */
		crumbs?: string[];
		/** Field holding the thumbnail URL. `false` hides the leading slot. */
		thumbnail?: string | false;
		roundThumbnail?: boolean;
		/** Show the row's `code` beside the label when the two differ. */
		showCode?: boolean;
		/** The muted line under the label: a path, or a resolved column. */
		subLabelField?: FieldSpec | null;
		/** The muted line of the caller's own making. Wins over `subLabelField`. */
		subLabel?: string;
		/** The right-aligned value: a path, or a resolved column so it renders by type. */
		secondaryField?: FieldSpec | null;
		/** Right-aligned text of the caller's own making. Wins over `secondaryField`. */
		secondary?: string;
		size?: PickerRowSize;
		/** The widget context. The two fields' schemas and the status table are read through it. */
		context?: SgContext;
		/** The site the status sprite is served from. Defaults to the context's. */
		siteUrl?: string;
		/** The `data-slot` the indicator column carries. Defaults to `picker-row-indicator`. */
		indicatorSlot?: string;
		/**
		 * Where the indicator column sits. A checkbox leads; a single picker's tick trails, where an
		 * unticked row leaves no gap before its label.
		 */
		indicatorAt?: 'start' | 'end';
	}
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { RowAnatomy, RowFieldPlan } from 'sg-widgets-core';
	import {
		isEmptyValue,
		pathOf,
		resolveRowFields,
		rowCode,
		rowSecondary,
		rowSubLabel,
		rowThumbnail,
		secondaryType,
		subLabelType
	} from 'sg-widgets-core';
	import { cn } from '$lib/utils.js';
	import { PICKER_ROW_INDICATOR } from '$lib/components/picker-classes.js';
	import FieldValue from '$lib/components/field-value.svelte';
	import MatchText from '$lib/components/match-text.svelte';
	import Thumbnail from '$lib/components/thumbnail.svelte';
	import UserAvatar from '$lib/components/user-avatar.svelte';

	type Props = PickerRowProps & {
		/** Drawn in the leading slot when the row carries no picture. */
		glyph?: Snippet;
		/** What the indicator column holds: a tick, a checkbox, or nothing while the row is not taken. */
		indicator?: Snippet;
	};

	let {
		row,
		query = '',
		crumbs = [],
		thumbnail = 'image',
		roundThumbnail = false,
		showCode = false,
		subLabelField = null,
		subLabel,
		secondaryField = null,
		secondary,
		size = 'md',
		context,
		siteUrl,
		glyph,
		indicator,
		indicatorSlot,
		indicatorAt = 'start'
	}: Props = $props();

	const anatomy = $derived({ thumbnail, subLabelField, secondaryField, showCode });
	const site = $derived(siteUrl ?? context?.siteUrl);
	const picture = $derived(rowThumbnail(row.values, anatomy));
	const code = $derived(rowCode(row.values, row.name, showCode));
	const raw = $derived(rowSecondary(row, anatomy));
	const secondaryPath = $derived(pathOf(secondaryField));
	/** An id is a code, and codes are the mono treatment of `docs/design-rules.md`. */
	const secondaryIsId = $derived(secondaryPath === 'id');
	const person = $derived(PEOPLE.includes(row.type));
	const title = $derived([...crumbs, row.name].join(' › '));

	/**
	 * What the sub-label and the secondary draw with: their fields and, when either is a
	 * status, the one status table behind both. The read hangs off the props through a
	 * derived rather than an effect with a "last seen" key.
	 */
	function loadFields(type: string, shape: RowAnatomy, ctx: SgContext | undefined): RowFieldPlan {
		const column = (spec: FieldSpec | null | undefined) =>
			spec && typeof spec !== 'string' ? spec.field : null;
		const plan = $state<RowFieldPlan>({
			subLabel: column(shape.subLabelField),
			secondary: column(shape.secondaryField),
			statuses: null
		});
		if (!ctx) return plan;
		void resolveRowFields(ctx.schema, ctx.statuses, type, shape).then((found) => {
			plan.subLabel = found.subLabel;
			plan.secondary = found.secondary;
			plan.statuses = found.statuses;
		}, () => {
			// A field the schema cannot answer renders as text, which is always readable.
		});
		return plan;
	}

	const plan = $derived(loadFields(row.type, anatomy, context));
	const dataType = $derived(secondaryType(anatomy, plan.secondary?.dataType));
	const sub = $derived(
		subLabel ??
			rowSubLabel(row.values, anatomy, {
				dataType: subLabelType(anatomy, plan.subLabel?.dataType),
				statuses: plan.statuses
			})
	);
</script>

<!--
	One entity row, the anatomy of rule 9 in `docs/design-rules.md`: a picture, the
	label with the matched runs bold, a muted sub-label and a right-aligned secondary
	rendered by its data type. Every picker, search and tree row is this one row, so a
	caller learns the six props once.

	The component draws the row's contents, not its box: the caller owns the list item,
	its selection state and anything it puts in front, such as a checkbox.
-->
{#snippet indicatorCell()}
	<!-- Fixed whether or not the row is ticked, so the labels, or the secondaries before a trailing tick, sit at one x. -->
	<span
		data-slot={indicatorSlot ?? 'picker-row-indicator'}
		class={cn(PICKER_ROW_INDICATOR, thumbnail !== false && LEAD_HEIGHT[size])}
	>
		{@render indicator?.()}
	</span>
{/snippet}

{#if indicator && indicatorAt === 'start'}
	{@render indicatorCell()}
{/if}

{#if thumbnail !== false}
	<span data-slot="picker-row-leading" class={cn('flex shrink-0 items-center justify-center', LEAD[size])}>
		{#if person}
			<UserAvatar
				name={row.name}
				image={picture}
				{size}
				color="auto"
				apiUser={row.type === 'ApiUser'}
				inactive={row.values['sg_status_list'] === 'dis'}
			/>
		{:else if picture === null && glyph}
			<span class={cn('text-muted-foreground flex items-center justify-center', GLYPH[size])}>
				{@render glyph()}
			</span>
		{:else}
			<Thumbnail
				src={picture}
				aspect="square"
				{size}
				entityType={row.type}
				class={roundThumbnail ? 'rounded-full' : undefined}
			/>
		{/if}
	</span>
{/if}

<span data-slot="picker-row-text" class={cn('flex min-w-0 flex-1 flex-col', TEXT[size])}>
	<span data-slot="picker-row-label" class="flex min-w-0 items-center gap-1.5" {title}>
		<span class="truncate"
			>{#each crumbs as crumb, i (i)}<span class="text-muted-foreground">{crumb}</span><span
					aria-hidden="true"
					class="text-muted-foreground">{' › '}</span
				>{/each}<MatchText
				data-slot="picker-row-name"
				text={row.name}
				{query}
				class={crumbs.length > 0 ? 'font-medium' : undefined}
			/></span
		>
		{#if code}
			<span data-slot="picker-row-code" class="text-muted-foreground shrink-0 font-mono text-xs">{code}</span>
		{/if}
	</span>
	{#if sub}
		<!-- Highlighted too, so a row matched on its login or its email shows why. -->
		<MatchText
			data-slot="picker-row-sub-label"
			text={sub}
			{query}
			class="text-muted-foreground truncate text-xs"
			title={sub}
		/>
	{/if}
</span>

{#if secondary}
	<span data-slot="picker-row-secondary" class="text-muted-foreground shrink-0 text-xs">{secondary}</span>
{:else if secondaryPath && !isEmptyValue(raw)}
	<span
		data-slot="picker-row-secondary"
		class={cn(
			'text-muted-foreground flex shrink-0 items-center text-xs',
			secondaryIsId && 'font-mono tabular-nums'
		)}
	>
		<FieldValue
			value={raw}
			{dataType}
			field={plan.secondary}
			statuses={plan.statuses}
			{context}
			siteUrl={site}
			class="w-auto justify-end text-xs"
		/>
	</span>
{/if}

{#if indicator && indicatorAt === 'end'}
	{@render indicatorCell()}
{/if}
