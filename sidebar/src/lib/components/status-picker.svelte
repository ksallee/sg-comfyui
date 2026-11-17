<script lang="ts" module>
	export type StatusPickerSize = 'sm' | 'md' | 'lg';
</script>

<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import type { FieldSchema, SgContext, StatusOption, StatusRecord } from 'sg-widgets-core';
	import { errorText, NO_ROWS_LABEL } from 'sg-widgets-core';
	import { LEAF_GLYPH } from '$lib/components/leaf-classes.js';
	import ListPicker from '$lib/components/list-picker.svelte';
	import { PICKER_CHIP as BADGE } from '$lib/components/picker-classes.js';
	import StatusBadge from '$lib/components/status-badge.svelte';
	import StatusGlyph from '$lib/components/status-glyph.svelte';
	import type { WithElementRef } from '$lib/utils.js';

	type Props = WithElementRef<Omit<HTMLAttributes<HTMLDivElement>, 'slot'>, HTMLDivElement> & {
		/** The widget context. The options and the status table are read through it, once per page. */
		context: SgContext;
		entityType: string;
		/** Offer the codes this project allows. */
		projectId?: number;
		/** Offer the codes every one of these projects allows. */
		projectIds?: number[];
		/** A list or status field other than the type's own. Project's is `sg_status`. */
		field?: string;
		/** The selected code, or `null` when nothing is chosen. */
		value?: string | null;
		onValueChange?: (value: string | null) => void;
		placeholder?: string;
		/** Shown when the field offers nothing. */
		emptyLabel?: string;
		/** The accessible name of the skeletons a read stands behind. */
		loadingLabel?: string;
		/** Shown in place of what the failed read said. */
		errorLabel?: string;
		/** Offer a control that clears the value. A mandatory field is never clearable. */
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
		/** The site the stock sprite is served from, passed to every badge. Defaults to the context's. */
		siteUrl?: string;
		size?: StatusPickerSize;
		/** Whether the popup is showing, two-way. */
		open?: boolean;
		onOpenChange?: (open: boolean) => void;
		class?: string;
	};

	let {
		context,
		entityType,
		projectId = undefined,
		projectIds = undefined,
		field = undefined,
		value = $bindable(null),
		onValueChange,
		placeholder = 'Select a status',
		emptyLabel = NO_ROWS_LABEL,
		loadingLabel,
		errorLabel,
		clearable = undefined,
		readonly = false,
		disabled = false,
		invalid = false,
		showCode = true,
		subLabel,
		secondary,
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
	function load(type: string, ids: number[], name: string | undefined): Loaded {
		const state = $state<Loaded>({
			loading: true,
			error: null,
			options: [],
			field: null,
			statuses: new Map()
		});
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

	// `display_values` is the only other source of a label, so the options carry it to the badge.
	const badgeField = $derived({
		displayValues: Object.fromEntries(query.options.map((option) => [option.code, option.label]))
	});

	// The first option set is not a change: it is what the widget was mounted to show.
	let seen: string | null = null;
	$effect(() => {
		if (query.loading || query.error !== null) return;
		const codes = query.options.map((option) => option.code).join(',');
		const dropped =
			seen !== null && seen !== codes && Boolean(value) && !query.options.some((o) => o.code === value);
		seen = codes;
		if (dropped) {
			value = null;
			onValueChange?.(null);
		}
	});

	function pick(next: string | null): void {
		value = next;
		onValueChange?.(value);
	}
</script>

<!--
	One status, picked from the codes a project offers.

	The clear follows clause 8 of the picker contract: the field's own schema decides,
	and a site that flags its status field mandatory gets no cross.

	The list picker with a status row and a badge for its value. The options are
	`valid_values` minus the project's `hidden_values`, read with `project_id`; over
	several projects they are the intersection of those sets. REST does not enforce
	`hidden_values` on write, so the subtraction is the client's job (probe 009). A code
	the option set does not carry still renders, as itself: a row may legally hold one
	(field_types/status_list). When a later option set drops the selected code, the
	picker clears it and emits once.

	A row is the shared picker row of rule 9: the status glyph as the leading mark, the
	display label as the row's text, and the code right-aligned. The badge stays in the
	control, where a status is a value rather than an option.
-->
<ListPicker
	bind:ref
	slot="status-picker"
	picker="status"
	options={query.options}
	value={value ?? null}
	onValueChange={pick}
	{placeholder}
	{emptyLabel}
	{loadingLabel}
	{errorLabel}
	loading={query.loading}
	loadError={query.error}
	field={query.field}
	{clearable}
	clearLabel="Clear the status"
	triggerLabel="Show the statuses"
	{readonly}
	{disabled}
	{invalid}
	{showCode}
	{subLabel}
	{secondary}
	{size}
	bind:open
	{onOpenChange}
	class={className}
	{...rest}
>
	{#snippet valueChip(code: string)}
		<StatusBadge
			{code}
			status={query.statuses.get(code) ?? null}
			field={badgeField}
			size={BADGE[size]}
			siteUrl={site}
			class="min-w-0"
		/>
	{/snippet}

	{#snippet mark(option: StatusOption)}
		<StatusGlyph
			status={query.statuses.get(option.code) ?? null}
			siteUrl={site}
			fallback
			class={LEAF_GLYPH[size]}
		/>
	{/snippet}
</ListPicker>
