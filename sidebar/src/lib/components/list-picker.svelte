<script lang="ts" module>
	import type { StatusOption } from 'sg-widgets-core';

	export type ListPickerSize = 'sm' | 'md' | 'lg';

	/** One offered value: the string a write sends, and the label the schema gives it. */
	export type ListOption = StatusOption;

	/** A row stands for a value, not an entity, so it carries a type of its own and no values. */
	export const LIST_ROW_TYPE = 'ListValue';
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import type { FieldSchema } from 'sg-widgets-core';
	import {
		clearableForField,
		matchesEveryWord,
		NO_ROWS_LABEL,
		statusLabel,
		usableStatuses
	} from 'sg-widgets-core';
	import { Combobox } from 'bits-ui';
	import PickerControl from '$lib/components/picker-control.svelte';
	import Check from '@lucide/svelte/icons/check';
	import Row from '$lib/components/picker-row.svelte';
	import { PICKER_ROW } from '$lib/components/picker-classes.js';
	import { cn, type WithElementRef } from '$lib/utils.js';

	type Props = WithElementRef<Omit<HTMLAttributes<HTMLDivElement>, 'slot'>, HTMLDivElement> & {
		/** The stored string, one of the field's valid values, or null (field_types/list). */
		value?: string | null;
		onValueChange?: (value: string | null) => void;
		/** The field schema. Its valid values are the whole vocabulary a write may use. */
		field?: Pick<
			FieldSchema,
			'displayName' | 'mandatory' | 'validValues' | 'displayValues' | 'hiddenValues'
		> | null;
		/**
		 * The project the schema was read with. Given, the field's hidden values are
		 * subtracted; REST does not enforce them on write, so the subtraction is the
		 * client's (probe 009).
		 */
		projectId?: number;
		/** The set on offer, of the caller's own making. Wins over the field's. */
		options?: ListOption[];
		/** The `data-slot` prefix every part of this picker carries. */
		slot?: string;
		/** The `data-picker` the popup carries. */
		picker?: string;
		size?: ListPickerSize;
		disabled?: boolean;
		readonly?: boolean;
		invalid?: boolean;
		/** A message from the caller. The list has nothing of its own to fail on. */
		error?: string | null;
		onErrorChange?: (error: string | null) => void;
		placeholder?: string;
		/** Shown when the list offers nothing. */
		emptyLabel?: string;
		/** Offer a search box. The set is fixed, so it is off. */
		searchable?: boolean;
		searchPlaceholder?: string;
		/** Offer a control that clears the value. A mandatory field is never clearable. */
		clearable?: boolean;
		clearLabel?: string;
		triggerLabel?: string;
		/** Draw the stored string as a row's right-aligned secondary, where it says more than the label. */
		showCode?: boolean;
		/** The muted line under a row's label. */
		subLabel?: (option: ListOption) => string;
		/** A row's right-aligned value, of the caller's own making. Wins over the code. */
		secondary?: (option: ListOption) => string;
		/** A caller's read is in flight: the list stands behind skeletons and the control is inert. */
		loading?: boolean;
		/** What a caller's read failed with, drawn in place of the list. */
		loadError?: string | null;
		/** The accessible name of the skeletons a read stands behind. */
		loadingLabel?: string;
		/** Shown in place of what the failed read said. */
		errorLabel?: string;
		/** Whether the popup is showing, two-way. */
		open?: boolean;
		onOpenChange?: (open: boolean) => void;
		errorMessage?: Snippet<[string]>;
		/** A row's leading mark. Given, every row carries one. */
		mark?: Snippet<[ListOption]>;
		/** The control's value. Drawn as plain text when the caller passes none. */
		valueChip?: Snippet<[string]>;
	};

	let {
		value = $bindable(null),
		onValueChange,
		field = null,
		projectId,
		options: given,
		slot = 'list-picker',
		picker = 'list',
		size = 'md',
		disabled = false,
		readonly = false,
		invalid = false,
		error = null,
		onErrorChange,
		placeholder = 'Choose',
		emptyLabel = NO_ROWS_LABEL,
		searchable = false,
		searchPlaceholder = 'Search values…',
		clearable = undefined,
		clearLabel = 'Clear the value',
		triggerLabel = 'Show the values',
		showCode = false,
		subLabel,
		secondary,
		loading = false,
		loadError = null,
		loadingLabel,
		errorLabel,
		open = $bindable(false),
		onOpenChange,
		errorMessage,
		mark,
		valueChip,
		class: className,
		ref = $bindable(null),
		...rest
	}: Props = $props();

	let search = $state('');

	const options = $derived(
		given ??
			(projectId === undefined
				? (field?.validValues ?? []).map((code) => ({ code, label: statusLabel(field ?? {}, code) }))
				: usableStatuses(field ?? {}))
	);
	// A row may hold a value outside the offered set; that is a legal stored value, so it
	// keeps a row of its own, labelled with the value (probe 009).
	const rows = $derived(
		value && !options.some((option) => option.code === value)
			? [...options, { code: value, label: value }]
			: options
	);
	// The vocabulary is one read, so a search box narrows it here.
	const shown = $derived(
		searchable ? rows.filter((option) => matchesEveryWord(`${option.label} ${option.code}`, search)) : rows
	);
	const selected = $derived(value ? [value] : []);

	function labelOf(code: string): string {
		return rows.find((option) => option.code === code)?.label ?? code;
	}

	function pick(keys: string[]): void {
		const chosen = keys[0] ?? null;
		if (chosen === value) return;
		value = chosen;
		onErrorChange?.(null);
		onValueChange?.(chosen);
	}

	function clear(): void {
		value = null;
		onErrorChange?.(null);
		onValueChange?.(null);
	}

	/** The right-aligned value: the caller's, else the stored string where it says more. */
	function secondaryOf(option: ListOption): string | undefined {
		if (secondary) return secondary(option) || undefined;
		return showCode && option.code !== option.label ? option.code : undefined;
	}
</script>

<!--
	One value of a `list` field, picked from the set its schema declares.

	Despite the name the value is one bare string, and a write outside `valid_values` is
	a 400 and case-sensitive, so the schema's vocabulary is the whole set a picker may
	offer (field_types/list). With a project id the field's hidden values are subtracted,
	which REST does not do on write.

	The set is fixed and read once, so there is no search row unless a caller asks for
	one, and the control is the base's summary trigger: the value reads as plain text,
	the way a select does.
-->
<div
	bind:this={ref}
	data-slot={slot}
	data-size={size}
	data-loading={loading ? 'true' : undefined}
	class={cn('flex w-full min-w-0 flex-col gap-2', className)}
	{...rest}
>
	<div class="relative flex w-full min-w-0 items-center">
		<PickerControl
			{slot}
			{picker}
			anchored
			keys={selected}
			onSelect={pick}
			labels={selected.map(labelOf)}
			inline={false}
			textValue={!valueChip}
			{searchable}
			rowCount={shown.length}
			{size}
			{disabled}
			inert={!readonly && (disabled || loading)}
			{readonly}
			{invalid}
			clearable={clearableForField(clearable, field)}
			{placeholder}
			{searchPlaceholder}
			bind:open
			{onOpenChange}
			bind:query={search}
			onRemoveAt={clear}
			onClear={clear}
			{loading}
			error={loadError}
			count={shown.length}
			empty={shown.length === 0}
			{emptyLabel}
			{loadingLabel}
			{errorLabel}
			{clearLabel}
			{triggerLabel}
			controlProps={{ 'aria-label': field?.displayName, 'aria-required': field?.mandatory }}
		>
			{#snippet chip()}
				{#if valueChip}
					{@render valueChip(value ?? '')}
				{:else}
					<span data-slot={`${slot}-text`} class="truncate">{labelOf(value ?? '')}</span>
				{/if}
			{/snippet}

			{#snippet rows()}
				{#each shown as option (option.code)}
					<Combobox.Item
						data-slot={`${slot}-option`}
						data-option={option.code}
						data-checked={option.code === value ? 'true' : undefined}
						value={option.code}
						label={option.label}
						class={PICKER_ROW}
					>
						<Row
							row={{ type: LIST_ROW_TYPE, id: 0, name: option.label, values: {} }}
							query={searchable ? search : ''}
							thumbnail={mark ? 'image' : false}
							subLabel={subLabel?.(option)}
							secondary={secondaryOf(option)}
							{size}
							indicatorAt="end"
						>
							{#snippet indicator()}
								{#if option.code === value}<Check aria-hidden="true" class="size-4" />{/if}
							{/snippet}
							{#snippet glyph()}
								{@render mark?.(option)}
							{/snippet}
						</Row>
					</Combobox.Item>
				{/each}
			{/snippet}
		</PickerControl>
	</div>
	{#if error}
		{#if errorMessage}
			{@render errorMessage(error)}
		{:else}
			<p data-slot="field-editor-error" class="text-destructive text-xs">{error}</p>
		{/if}
	{/if}
</div>
