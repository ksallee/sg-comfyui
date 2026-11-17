<script lang="ts" module>
	import type { PickerSummary } from 'sg-widgets-core';

	export type StatusMultiPickerSize = 'sm' | 'md' | 'lg';
</script>

<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import type { FieldSchema, PickerRow, SgContext, StatusOption, StatusRecord } from 'sg-widgets-core';
	import {
		clearableForField,
		errorText,
		matchesEveryWord,
		NO_MATCH_LABEL,
		statusTableOptions
	} from 'sg-widgets-core';
	import { Combobox } from 'bits-ui';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { cn, type WithElementRef } from '$lib/utils.js';
	import { LEAF_GLYPH } from '$lib/components/leaf-classes.js';
	import PickerControl from '$lib/components/picker-control.svelte';
	import Row from '$lib/components/picker-row.svelte';
	import {
		PICKER_ARMED,
		PICKER_CHIP as BADGE,
		PICKER_ROW
	} from '$lib/components/picker-classes.js';
	import StatusBadge, { type StatusBadgeVariant } from '$lib/components/status-badge.svelte';
	import StatusGlyph from '$lib/components/status-glyph.svelte';

	type Props = WithElementRef<HTMLAttributes<HTMLDivElement>, HTMLDivElement> & {
		/** The widget context. The options and the status table are read through it, once per page. */
		context: SgContext;
		/** The type whose status field is offered. Without one, every status of the site is. */
		entityType?: string;
		/** Offer the codes this project allows. */
		projectId?: number;
		/** Offer the codes every one of these projects allows. */
		projectIds?: number[];
		/** A list or status field other than the type's own. Project's is `sg_status`. */
		field?: string;
		/** The selected codes. */
		value?: string[];
		onValueChange?: (value: string[]) => void;
		placeholder?: string;
		searchPlaceholder?: string;
		/** Shown when the search matches nothing. */
		emptyLabel?: string;
		/** The accessible name of the skeletons a read stands behind. */
		loadingLabel?: string;
		/** Shown in place of what the failed read said. */
		errorLabel?: string;
		/** Offer a control that clears the selection. A mandatory field is never clearable. */
		clearable?: boolean;
		readonly?: boolean;
		disabled?: boolean;
		invalid?: boolean;
		/** Draw the code as the row's right-aligned secondary, when it says more than the label. */
		showCode?: boolean;
		/** The muted line under a row's label. */
		subLabel?: (option: StatusOption) => string;
		/** A row's right-aligned value, of the caller's own making. Wins over the code. */
		secondary?: (option: StatusOption) => string;
		/** What the control shows for the selection. */
		summary?: PickerSummary;
		/** What one selected status is drawn as. Orthogonal to how many the control shows. */
		badge?: StatusBadgeVariant;
		/** Badges drawn before the rest becomes `+n`. `0` lets the row fit what it can. */
		max?: number;
		/** The site the stock sprite is served from, passed to every badge. Defaults to the context's. */
		siteUrl?: string;
		size?: StatusMultiPickerSize;
		/** Whether the popup is showing, two-way. */
		open?: boolean;
		onOpenChange?: (open: boolean) => void;
		class?: string;
	};

	let {
		context,
		entityType = undefined,
		projectId = undefined,
		projectIds = undefined,
		field = undefined,
		value = $bindable([]),
		onValueChange,
		placeholder = 'Select statuses',
		searchPlaceholder = 'Search statuses…',
		emptyLabel = NO_MATCH_LABEL,
		loadingLabel,
		errorLabel,
		clearable = undefined,
		readonly = false,
		disabled = false,
		invalid = false,
		showCode = true,
		subLabel,
		secondary,
		summary = 'ellipsis',
		badge = 'both',
		max = 0,
		siteUrl = undefined,
		size = 'md',
		open = $bindable(false),
		onOpenChange,
		class: className,
		ref = $bindable(null),
		...rest
	}: Props = $props();

	// The context's own services, so every widget on the page shares one schema read
	// and one status table.
	const schema = $derived(context.schema);
	const statusTable = $derived(context.statuses);
	const site = $derived(siteUrl ?? context.siteUrl);

	interface Loaded {
		loading: boolean;
		error: string | null;
		options: StatusOption[];
		/** The field the codes come from, which is what clause 8 reads `mandatory` off. */
		field: FieldSchema | null;
		statuses: ReadonlyMap<string, StatusRecord>;
	}

	function optionsFor(type: string, ids: number[], name: string | undefined): Promise<StatusOption[]> {
		const [first] = ids;
		if (first === undefined) return schema.statusOptions(type, undefined, name);
		return ids.length === 1
			? schema.statusOptions(type, first, name)
			: schema.statusOptionsForProjects(type, ids, name);
	}

	/**
	 * One load, as reactive state. The read hangs off the props through a derived and
	 * goes through the context's cache, so it is never an effect re-firing on
	 * a "last seen" key.
	 */
	function load(type: string | undefined, ids: number[], name: string | undefined): Loaded {
		const state = $state<Loaded>({
			loading: true,
			error: null,
			options: [],
			field: null,
			statuses: new Map()
		});
		// No type, no field: the Status table is the whole vocabulary (probe 010).
		if (type === undefined) {
			statusTable.byCode().then(
				(statuses) => {
					state.options = statusTableOptions([...statuses.values()]);
					state.statuses = statuses;
					state.loading = false;
				},
				(error: unknown) => {
					state.error = errorText(error);
					state.loading = false;
				}
			);
			return state;
		}
		// The field itself, for its display name and its `mandatory` flag.
		const named = name === undefined ? schema.statusField(type) : schema.field(type, name);
		Promise.all([optionsFor(type, ids, name), named, statusTable.byCode()]).then(
			([options, found, statuses]) => {
				state.options = options;
				state.field = typeof found === 'string' || found === undefined ? null : found;
				state.statuses = statuses;
				state.loading = false;
			},
			(error: unknown) => {
				state.error = errorText(error);
				state.loading = false;
			}
		);
		return state;
	}

	const projectKey = $derived((projectIds ?? (projectId === undefined ? [] : [projectId])).join(','));
	const query = $derived(
		load(entityType, projectKey === '' ? [] : projectKey.split(',').map(Number), field)
	);

	let search = $state('');

	// `display_values` is the only other source of a label, so the options carry it to the badge.
	const badgeField = $derived({
		displayValues: Object.fromEntries(query.options.map((option) => [option.code, option.label]))
	});
	// A stored code outside the usable set is legal, so it keeps a row of its own (probe 009).
	const rows = $derived([
		...query.options,
		...value
			.filter((code) => !query.options.some((option) => option.code === code))
			.map((code) => ({ code, label: code }))
	]);
	// A status list has no substring operator, so the vocabulary is read once and the
	// search box narrows it here (field_types/status_list).
	const shown = $derived(rows.filter((option) => matchesEveryWord(`${option.label} ${option.code}`, search)));
	const byCode = $derived(new Map(rows.map((option) => [option.code, option])));

	/**
	 * A chip control is a token field, with the caret beside the badges. A summary
	 * control is a trigger, and keeps its search box at the top of the popup instead.
	 */
	const inline = $derived(summary === 'chips');

	// Read-only wins over disabled and over the loading window.
	const inert = $derived(!readonly && (disabled || query.loading));
	const interactive = $derived(!readonly && !inert);

	/** A bare icon is half a badge wide, so a fixed cap fits twice as many. */
	const badgeMax = $derived(badge === 'icon' ? max * 2 : max);

	/** What the badges look like, so a change to any of it re-measures the row. */
	const rowKey = $derived(
		`${size}|${summary}|${badge}|${interactive}|${value.map((code) => byCode.get(code)?.label ?? code).join(', ')}`
	);

	function setSelected(next: string[]): void {
		value = next;
		onValueChange?.(value);
	}

	function remove(code: string): void {
		setSelected(value.filter((c) => c !== code));
	}

	function removeAt(index: number): void {
		const code = value[index];
		if (code !== undefined) remove(code);
	}

	/** The shared row a status is drawn as. There is no entity behind a code, so it carries no values. */
	function rowOf(option: StatusOption): PickerRow {
		return { type: 'Status', id: 0, name: option.label, values: {} };
	}

	/** The right-aligned value: the caller's, else the code when it says more than the label. */
	function secondaryOf(option: StatusOption): string | undefined {
		if (secondary) return secondary(option) || undefined;
		return showCode && option.code !== option.label ? option.code : undefined;
	}
</script>

<!--
	Several statuses, picked from the codes a project offers.

	Without an entity type the options are every status of the site, which is what the
	valid values of a status field are chosen from. With one, the options are `valid_values` minus the project's `hidden_values`, read with
	`project_id`; over several projects they are the intersection of those sets. REST
	does not enforce `hidden_values` on write, so the subtraction is the client's job
	(probe 009). A selected code the option set does not carry keeps a row of its own,
	labelled with the code, so a selection is never dropped from the display.

	A status list has no substring operator, so there is no server-side type-ahead over
	it: the vocabulary is read once and the query input narrows it in the browser
	(field_types/status_list).

	A row is the shared picker row of rule 9, after its checkbox: the status glyph as the
	leading mark, the display label with the matched runs bold, and the code
	right-aligned. The badge stays in the control, where a status is a value rather than
	an option.
-->
<div
	bind:this={ref}
	data-slot="status-multi-picker"
	data-size={size}
	data-summary={summary}
	data-badge={badge}
	data-loading={query.loading ? 'true' : undefined}
	class={cn('relative flex w-full min-w-0 items-center', className)}
	{...rest}
>
	<PickerControl
		slot="status-multi-picker"
		picker="status"
		multiple
		anchored
		keys={value}
		onSelect={setSelected}
		labels={value.map((code) => byCode.get(code)?.label ?? code)}
		chipKeys={value}
		chipsSlot="status-multi-picker-badges"
		{summary}
		max={badgeMax}
		chipRow
		{inline}
		{rowKey}
		rowCount={shown.length}
		{size}
		{disabled}
		{inert}
		{readonly}
		{invalid}
		clearable={clearableForField(clearable, query.field)}
		controlProps={{ 'aria-label': query.field?.displayName, 'aria-required': query.field?.mandatory }}
		{placeholder}
		{searchPlaceholder}
		bind:open
		{onOpenChange}
		bind:query={search}
		onRemoveAt={removeAt}
		onClear={() => setSelected([])}
		loading={query.loading}
		error={query.error}
		count={shown.length}
		empty={shown.length === 0}
		{emptyLabel}
		{loadingLabel}
		{errorLabel}
		clearLabel="Clear the statuses"
		triggerLabel="Show the statuses"
		overflowLabel={`Show all ${value.length} statuses`}
	>
		{#snippet chip(index: number, armed: boolean, hidden: boolean)}
			{@const code = value[index]!}
			<span
				data-slot="status-multi-picker-chip"
				data-chip=""
				data-armed={armed ? 'true' : undefined}
				{hidden}
				class={cn('flex min-w-0 shrink-0 items-center', armed && cn(PICKER_ARMED, 'rounded-md'))}
			>
				<StatusBadge
					{code}
					status={query.statuses.get(code) ?? null}
					field={badgeField}
					variant={badge}
					size={BADGE[size]}
					siteUrl={site}
					removable={interactive}
					onRemove={remove}
					removeLabel={`Remove ${byCode.get(code)?.label ?? code}`}
					class="min-w-0"
				/>
			</span>
		{/snippet}

		{#snippet rows()}
			{#each shown as option (option.code)}
				{@const chosen = value.includes(option.code)}
				<Combobox.Item
					data-slot="status-multi-picker-option"
					data-status-code={option.code}
					data-selected-status={chosen ? 'true' : undefined}
					value={option.code}
					label={option.label}
					class={PICKER_ROW}
				>
					<Row
						row={rowOf(option)}
						query={search}
						subLabel={subLabel?.(option)}
						secondary={secondaryOf(option)}
						{size}
						{context}
						indicatorSlot="status-multi-picker-check"
					>
						{#snippet indicator()}
							<Checkbox checked={chosen} tabindex={-1} aria-hidden="true" class="pointer-events-none" />
						{/snippet}
						{#snippet glyph()}
							<StatusGlyph
								status={query.statuses.get(option.code) ?? null}
								siteUrl={site}
								fallback
								class={LEAF_GLYPH[size]}
							/>
						{/snippet}
					</Row>
				</Combobox.Item>
			{/each}
		{/snippet}
	</PickerControl>
</div>
