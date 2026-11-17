<script lang="ts" module>
	import type {
		EntityRef,
		FieldSpec,
		FilterGroup,
		PickerRow,
		SearchFieldSpec,
		SgContext,
		WireGroup
	} from 'sg-widgets-core';

	export type EntityPickerSize = 'sm' | 'md' | 'lg';

	/** Everything both entity pickers take. They differ only in the shape of the value. */
	export interface EntityPickerBaseProps {
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
		size?: EntityPickerSize;
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
	import EntityChip from '$lib/components/entity-chip.svelte';
	import PickerControl from '$lib/components/picker-control.svelte';
	import Check from '@lucide/svelte/icons/check';
	import Row from '$lib/components/picker-row.svelte';
	import { PICKER_ARMED, PICKER_CHIP, PICKER_ROW } from '$lib/components/picker-classes.js';
	import { cn, type WithElementRef } from '$lib/utils.js';

	type Props = WithElementRef<HTMLAttributes<HTMLDivElement>, HTMLDivElement> &
		EntityPickerBaseProps & {
			/** The chosen row, two-way. A bare `{type, id}` is resolved on mount. */
			value?: EntityRef | null;
			onValueChange?: (value: EntityRef | null, row: PickerRow | null) => void;
		};

	let {
		entityTypes,
		context,
		value = $bindable(null),
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
		placeholder = 'Search for an entity',
		searchPlaceholder = 'Search…',
		emptyLabel = NO_MATCH_LABEL,
		loadingLabel,
		errorLabel,
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

	// A bare reference is resolved by one batched read, latched on the reference
	// itself, so swapping in a different bare one resolves that one too.
	$effect(() => {
		if (value) search.hydrate([value]);
	});

	const selectedRow = $derived.by(() => {
		void snap;
		return value ? (search.known.get(entityKey(value)) ?? null) : null;
	});
	const chipEntity = $derived(
		value
			? {
					type: value.type,
					id: value.id,
					name: selectedRow?.name || value.name || placeholderName(value)
				}
			: null
	);
	const options = $derived(withSelectedPinned(snap.rows, value ? [value] : [], search.known));
	const polymorphic = $derived(entityTypes.length > 1);
	const selectedKey = $derived(value ? entityKey(value) : '');

	/** The caller's own sub-label. Absent, the row reads `subLabelField` itself. */
	function subLabelOf(row: PickerRow): string | undefined {
		return subLabel ? subLabel(row) : undefined;
	}

	/** The caller's own secondary, and the type on a polymorphic list that names no field. */
	function customSecondary(row: PickerRow): string | undefined {
		if (secondary) return secondary(row);
		return !pathOf(secondaryField) && polymorphic ? row.type : undefined;
	}

	function setSelected(keys: string[]): void {
		const row = options.find((option) => entityKey(option) === keys[0]);
		if (!row) return;
		// The primitive writes the item's label into its own copy of the input value;
		// mirroring it here makes the clear on close a change the input sees.
		query = row.name ?? '';
		search.remember([row]);
		value = { type: row.type, id: row.id, name: row.name };
		onValueChange?.(value, row);
	}

	function clear(): void {
		value = null;
		onValueChange?.(null, null);
	}
</script>

<!--
	One entity, chosen by server-side search.

	A query past `minQueryLength` becomes one `contains` condition per word, `or`'d
	across the type's display-name fields, and goes to `POST /entity/<type>/_search`
	once per searched type. Under it the same search runs without the name condition,
	so an open picker lists the rows worked on most recently. The combobox does no
	filtering of its own: the server is the only authority on what matches. A response
	from an abandoned query is dropped rather than shown, reads come from the query
	cache, and every row is held under `Type:id` because a numeric id alone collides
	across types.

	The secondary column is drawn by the field's data type through FieldValue, so a
	status is a badge and a date is formatted.
-->
<div
	bind:this={ref}
	data-slot="entity-picker"
	data-size={size}
	data-multiple="false"
	class={cn('relative flex w-full min-w-0 items-center', disabled && 'pointer-events-none opacity-50', className)}
	{...rest}
>
	<PickerControl
		slot="entity-picker"
		picker="entity"
		keys={value ? [selectedKey] : []}
		onSelect={setSelected}
		labels={chipEntity ? [chipEntity.name] : []}
		summary="chips"
		tokenInput={false}
		inputPlaceholder={chipEntity ? searchPlaceholder : placeholder}
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
		onRemoveAt={clear}
		onClear={clear}
		loading={snap.loading && options.length === 0}
		error={snap.error?.message ?? null}
		count={options.length}
		empty={options.length === 0}
		{emptyLabel}
		{loadingLabel}
		{errorLabel}
		hasMore={snap.hasMore}
		onLoadMore={() => search.loadMore()}
	>
		{#snippet chip(_index: number, armed: boolean)}
			<EntityChip
				entity={chipEntity!}
				thumbnail={selectedRow ? rowThumbnail(selectedRow.values, { thumbnail }) : null}
				size={PICKER_CHIP[size]}
				{context}
				siteUrl={site}
				data-armed={armed ? 'true' : undefined}
				class={armed ? PICKER_ARMED : undefined}
			/>
		{/snippet}

		{#snippet rows()}
			{#each options as row (entityKey(row))}
				{@const chosen = selectedKey === entityKey(row)}
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
						indicatorAt="end"
					>
						{#snippet indicator()}
							{#if chosen}<Check aria-hidden="true" class="size-4" />{/if}
						{/snippet}
					</Row>
				</Combobox.Item>
			{/each}
		{/snippet}
	</PickerControl>
</div>
