<script lang="ts" module>
	import type {
		EntityRef,
		FieldSpec,
		FilterGroup,
		PickerRow,
		PickerSummary,
		SearchFieldSpec,
		SgContext,
		WireGroup
	} from 'sg-widgets-core';

	export type EntityMultiPickerSize = 'sm' | 'md' | 'lg';

	/** Everything both entity pickers take. They differ only in the shape of the value. */
	export interface EntityMultiPickerBaseProps {
		/** Types to search. One for a homogeneous picker, several for a polymorphic one. */
		entityTypes: string[];
		/** The widget context. Every read goes through it, so widgets on a page share one cache. */
		context: SgContext;
		/** Field holding the row label. Defaults to the display-name chain. */
		labelField?: string;
		/**
		 * Extra fields the query is matched against, on top of the display-name chain. A
		 * function is called with the query, so a field is searched only when it suits it.
		 */
		searchFields?: SearchFieldSpec[] | ((query: string) => SearchFieldSpec[]);
		/** Field shown right-aligned, drawn by its data type. A path, or a resolved column. */
		secondaryField?: FieldSpec | null;
		/** Right-aligned text of the caller's own making. Wins over `secondaryField`. */
		secondary?: (row: PickerRow) => string;
		/** Field shown under the label: a path, or a resolved column. */
		subLabelField?: FieldSpec | null;
		/** The muted line of the caller's own making. Wins over `subLabelField`. */
		subLabel?: (row: PickerRow) => string;
		/** Field holding the thumbnail URL. `false` hides the leading slot. */
		thumbnail?: string | false;
		roundThumbnail?: boolean;
		/** Show the row's `code` beside the label when the two differ. */
		showCode?: boolean;
		/** The site the status sprite is served from, for a secondary that is a status. Defaults to the context's. */
		siteUrl?: string;
		/** Extra fields to request, so a caller's own sub-label or secondary can be read. */
		fields?: string[];
		/** Pre-filter merged into every search with `and`. */
		filters?: FilterGroup | WireGroup | null;
		/** Sugar for a project condition. Skipped on a type with no project link. */
		projectId?: number;
		/** Rows to keep out of the results. Pushed into the server filter as `id not_in`. */
		exclude?: EntityRef[];
		minQueryLength?: number;
		pageSize?: number;
		placeholder?: string;
		searchPlaceholder?: string;
		/** Shown when the query matches nothing. */
		emptyLabel?: string;
		/** The accessible name of the skeletons a read stands behind. */
		loadingLabel?: string;
		/** Shown in place of what the failed read said. */
		errorLabel?: string;
		/** What the control shows for the selection. */
		summary?: PickerSummary;
		/** Chips drawn before the rest becomes `+n`. `0` draws every chip. */
		max?: number;
		size?: EntityMultiPickerSize;
		disabled?: boolean;
		readonly?: boolean;
		invalid?: boolean;
		clearable?: boolean;
		debounceMs?: number;
		/** Whether the popup is showing, two-way. */
		open?: boolean;
		onOpenChange?: (open: boolean) => void;
		onError?: (error: Error) => void;
		class?: string;
	}
</script>

<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import {
		createEntitySearch,
		entityKey,
		NO_MATCH_LABEL,
		pathOf,
		placeholderName,
		rowThumbnail,
		withSelectedPinned
	} from 'sg-widgets-core';
	import { Combobox } from 'bits-ui';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import EntityChip from '$lib/components/entity-chip.svelte';
	import PickerControl from '$lib/components/picker-control.svelte';
	import Row from '$lib/components/picker-row.svelte';
	import { PICKER_ARMED, PICKER_CHIP, PICKER_ROW } from '$lib/components/picker-classes.js';
	import { cn, type WithElementRef } from '$lib/utils.js';

	type Props = WithElementRef<HTMLAttributes<HTMLDivElement>, HTMLDivElement> &
		EntityMultiPickerBaseProps & {
			/** The chosen rows, two-way. Bare `{type, id}` members are resolved on mount. */
			value?: EntityRef[];
			onValueChange?: (value: EntityRef[], rows: PickerRow[]) => void;
		};

	let {
		entityTypes,
		context,
		value = $bindable([]),
		labelField,
		searchFields,
		secondaryField,
		secondary,
		subLabelField,
		subLabel,
		thumbnail = 'image',
		roundThumbnail = false,
		showCode = false,
		siteUrl,
		fields,
		filters = null,
		projectId,
		exclude,
		minQueryLength = 0,
		pageSize = 20,
		placeholder = 'Search for entities',
		searchPlaceholder = 'Search…',
		emptyLabel = NO_MATCH_LABEL,
		loadingLabel,
		errorLabel,
		summary = 'ellipsis',
		max = 0,
		size = 'md',
		disabled = false,
		readonly = false,
		invalid = false,
		clearable = true,
		debounceMs = 250,
		open = $bindable(false),
		onOpenChange,
		onValueChange,
		onError,
		class: className,
		ref = $bindable(null),
		...rest
	}: Props = $props();

	// The context's own services, so every widget on the page shares one schema read
	// and one status table.
	const schema = $derived(context.schema);
	const site = $derived(siteUrl ?? context.siteUrl);

	// svelte-ignore state_referenced_locally
	const search = createEntitySearch({
		client: context.client,
		schema,
		entityTypes,
		labelField,
		searchFields,
		secondaryField,
		subLabelField,
		thumbnail,
		fields,
		filters,
		projectId,
		exclude,
		minQueryLength,
		pageSize,
		debounceMs,
		onError: (error: Error) => onError?.(error)
	});

	let snap = $state(search.state);
	let query = $state('');

	$effect(() => search.subscribe((next) => (snap = next)));
	$effect(() => () => search.dispose());

	$effect(() => {
		search.update({
			client: context.client,
			schema,
			entityTypes,
			labelField,
			searchFields,
			secondaryField,
			subLabelField,
			thumbnail,
			fields,
			filters,
			projectId,
			exclude,
			minQueryLength,
			pageSize,
			debounceMs,
			onError: (error: Error) => onError?.(error)
		});
	});

	// The search runs for an open picker only: the list is what the popup shows, and
	// a closed one has nobody to show it to.
	$effect(() => {
		if (open) search.setQuery(query);
	});

	// Bare references are resolved by one batched read per type, latched on the
	// references themselves, so a later set of bare ones resolves too.
	$effect(() => {
		if (value.length > 0) search.hydrate(value);
	});

	const selectedKeys = $derived(value.map(entityKey));
	const selected = $derived(new Set(selectedKeys));
	const chips = $derived.by(() => {
		void snap;
		return value.map((ref) => {
			const row = search.known.get(entityKey(ref));
			return {
				ref,
				entity: { type: ref.type, id: ref.id, name: row?.name || ref.name || placeholderName(ref) },
				thumbnail: row ? rowThumbnail(row.values, { thumbnail }) : null
			};
		});
	});
	/**
	 * A chip control is a token field, with the caret beside the chips. A summary
	 * control is a trigger, and keeps its search box at the top of the popup instead.
	 */
	const inline = $derived(summary === 'chips');
	/** What the chips look like, so a change to any of it re-measures the row. */
	const rowKey = $derived(
		`${size}|${summary}|${chips.map((chip) => `${chip.entity.name}:${chip.thumbnail ?? ''}`).join(', ')}`
	);
	// Search results first, selected rows appended, so a selection stays deselectable
	// whatever the query, and even when a search returns nothing at all.
	const options = $derived(withSelectedPinned(snap.rows, value, search.known));
	const polymorphic = $derived(entityTypes.length > 1);
	const interactive = $derived(!disabled && !readonly);

	/** The caller's own sub-label. Absent, the row reads `subLabelField` itself. */
	function subLabelOf(row: PickerRow): string | undefined {
		return subLabel ? subLabel(row) : undefined;
	}

	/** The caller's own secondary, and the type on a polymorphic list that names no field. */
	function customSecondary(row: PickerRow): string | undefined {
		if (secondary) return secondary(row);
		return !pathOf(secondaryField) && polymorphic ? row.type : undefined;
	}

	function rowFor(key: string): PickerRow | null {
		return options.find((option) => entityKey(option) === key) ?? search.known.get(key) ?? null;
	}

	function emit(next: EntityRef[]): void {
		value = next;
		onValueChange?.(
			next,
			next.map(
				(ref) =>
					search.known.get(entityKey(ref)) ?? {
						type: ref.type,
						id: ref.id,
						name: ref.name || placeholderName(ref),
						values: {}
					}
			)
		);
	}

	function setSelected(keys: string[]): void {
		const rows = keys.map(rowFor).filter((row): row is PickerRow => row !== null);
		search.remember(rows);
		emit(rows.map((row) => ({ type: row.type, id: row.id, name: row.name })));
	}

	function remove(ref: EntityRef): void {
		emit(value.filter((other) => entityKey(other) !== entityKey(ref)));
	}

	function removeAt(index: number): void {
		const chip = value[index];
		if (chip) remove(chip);
	}
</script>

<!--
	Several entities, chosen by server-side search.

	The same request model as the single picker: one `contains` condition per word,
	`or`'d across the type's display-name fields, one `POST /entity/<type>/_search`
	per searched type, no filtering in the browser, abandoned responses dropped, and
	the same search without the name condition while nothing is typed. The option list
	is the results followed by any selected row they do not hold, so a selection is
	always there to be unticked, and every row is held under `Type:id`.

	The secondary column is drawn by the field's data type through FieldValue, so a
	status is a badge and a date is formatted.
-->
<div
	bind:this={ref}
	data-slot="entity-picker"
	data-size={size}
	data-multiple="true"
	data-summary={summary}
	class={cn('relative flex w-full min-w-0 items-center', disabled && 'pointer-events-none opacity-50', className)}
	{...rest}
>
	<PickerControl
		slot="entity-picker"
		picker="entity-multi"
		multiple
		keys={selectedKeys}
		onSelect={setSelected}
		labels={chips.map((chip) => chip.entity.name)}
		chipKeys={selectedKeys}
		{summary}
		{max}
		chipRow
		{inline}
		{rowKey}
		rowCount={snap.rows.length}
		{size}
		{disabled}
		{readonly}
		{invalid}
		{clearable}
		{placeholder}
		{searchPlaceholder}
		bind:open
		{onOpenChange}
		bind:query
		onRemoveAt={removeAt}
		onClear={() => emit([])}
		loading={snap.loading && options.length === 0}
		error={snap.error?.message ?? null}
		count={options.length}
		empty={options.length === 0}
		{emptyLabel}
		{loadingLabel}
		{errorLabel}
		hasMore={snap.hasMore}
		onLoadMore={() => search.loadMore()}
		overflowLabel={`Show all ${chips.length} selected`}
	>
		{#snippet chip(index: number, armed: boolean, hidden: boolean)}
			{@const one = chips[index]!}
			<EntityChip
				entity={one.entity}
				thumbnail={one.thumbnail}
				size={PICKER_CHIP[size]}
				{context}
				siteUrl={site}
				removable={interactive}
				onRemove={() => remove(one.ref)}
				data-chip=""
				data-armed={armed ? 'true' : undefined}
				{hidden}
				class={cn('shrink-0', armed && PICKER_ARMED)}
			/>
		{/snippet}

		{#snippet rows()}
			{#each options as row (entityKey(row))}
				{@const chosen = selected.has(entityKey(row))}
				<Combobox.Item
					data-slot="entity-picker-option"
					data-entity-type={row.type}
					data-entity-id={row.id}
					data-checked={chosen ? 'true' : undefined}
					value={entityKey(row)}
					label={row.name}
					class={PICKER_ROW}
				>
					<Row
						{row}
						query={snap.query}
						{thumbnail}
						{roundThumbnail}
						{showCode}
						{subLabelField}
						subLabel={subLabelOf(row)}
						{secondaryField}
						secondary={customSecondary(row)}
						{size}
						{context}
						siteUrl={site}
						indicatorSlot="entity-picker-check"
					>
						{#snippet indicator()}
							<Checkbox checked={chosen} tabindex={-1} aria-hidden="true" class="pointer-events-none" />
						{/snippet}
					</Row>
				</Combobox.Item>
			{/each}
		{/snippet}
	</PickerControl>
</div>
