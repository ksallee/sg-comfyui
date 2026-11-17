<script lang="ts" module>
	import type { PickerSummary, StatusOption } from 'sg-widgets-core';

	export type ListMultiPickerSize = 'sm' | 'md' | 'lg';

	/** One offered value: the string a write sends, and the label the schema gives it. */
	export type ListOption = StatusOption;

	/** A row stands for a value, not an entity, so it carries a type of its own and no values. */
	const LIST_ROW_TYPE = 'ListValue';
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
	import X from '@lucide/svelte/icons/x';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import PickerControl from '$lib/components/picker-control.svelte';
	import Row from '$lib/components/picker-row.svelte';
	import {
		PICKER_ARMED,
		PICKER_ROW,
		PICKER_TEXT_CHIP,
		PICKER_TEXT_CHIP_BOX,
		PICKER_TEXT_CHIP_CROSS
	} from '$lib/components/picker-classes.js';
	import { REMOVE_CONTROL } from '$lib/components/leaf-classes.js';
	import { cn, type WithElementRef } from '$lib/utils.js';

	type Props = WithElementRef<Omit<HTMLAttributes<HTMLDivElement>, 'slot'>, HTMLDivElement> & {
		/** The chosen values, each one of the field's valid values (field_types/list). */
		value?: string[];
		onValueChange?: (value: string[]) => void;
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
		size?: ListMultiPickerSize;
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
		/** Offer a control that clears the selection. A mandatory field is never clearable. */
		clearable?: boolean;
		clearLabel?: string;
		triggerLabel?: string;
		/** Draw the stored string as a row's right-aligned secondary, where it says more than the label. */
		showCode?: boolean;
		/** The muted line under a row's label. */
		subLabel?: (option: ListOption) => string;
		/** A row's right-aligned value, of the caller's own making. Wins over the code. */
		secondary?: (option: ListOption) => string;
		/** What the control shows for the selection. */
		summary?: PickerSummary;
		/** Chips drawn before the rest becomes `+n`. `0` lets the row fit what it can. */
		max?: number;
		/** Whether the popup is showing, two-way. */
		open?: boolean;
		onOpenChange?: (open: boolean) => void;
		errorMessage?: Snippet<[string]>;
	};

	let {
		value = $bindable([]),
		onValueChange,
		field = null,
		projectId,
		options: given,
		slot = 'list-multi-picker',
		picker = 'list',
		size = 'md',
		disabled = false,
		readonly = false,
		invalid = false,
		error = null,
		onErrorChange,
		placeholder = 'Select values',
		emptyLabel = NO_ROWS_LABEL,
		searchable = false,
		searchPlaceholder = 'Search values…',
		clearable = undefined,
		clearLabel = 'Clear the values',
		triggerLabel = 'Show the values',
		showCode = false,
		subLabel,
		secondary,
		summary = 'ellipsis',
		max = 0,
		open = $bindable(false),
		onOpenChange,
		errorMessage,
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
	const rows = $derived([
		...options,
		...value
			.filter((code) => !options.some((option) => option.code === code))
			.map((code) => ({ code, label: code }))
	]);
	// The vocabulary is one read, so a search box narrows it here.
	const shown = $derived(
		searchable ? rows.filter((option) => matchesEveryWord(`${option.label} ${option.code}`, search)) : rows
	);
	const interactive = $derived(!readonly && !disabled);

	function labelOf(code: string): string {
		return rows.find((option) => option.code === code)?.label ?? code;
	}

	function emit(next: string[]): void {
		value = next;
		onErrorChange?.(null);
		onValueChange?.(next);
	}

	function remove(code: string): void {
		emit(value.filter((c) => c !== code));
	}

	function removeAt(index: number): void {
		const code = value[index];
		if (code !== undefined) remove(code);
	}

	/** The right-aligned value: the caller's, else the stored string where it says more. */
	function secondaryOf(option: ListOption): string | undefined {
		if (secondary) return secondary(option) || undefined;
		return showCode && option.code !== option.label ? option.code : undefined;
	}
</script>

<!--
	Several values of a `list` field, picked from the set its schema declares.

	The vocabulary is the field's `valid_values`, byte for byte: a value outside it is a
	400 and the comparison is case-sensitive (field_types/list). With a project id the
	field's hidden values are subtracted, which REST does not do on write.

	The set is fixed and read once, so there is no search row unless a caller asks for
	one. The control is the base's summary trigger, and a chosen value is a plain chip.
-->
<div
	bind:this={ref}
	data-slot={slot}
	data-size={size}
	data-summary={summary}
	class={cn('flex w-full min-w-0 flex-col gap-2', className)}
	{...rest}
>
	<div class="relative flex w-full min-w-0 items-center">
		<PickerControl
			{slot}
			{picker}
			multiple
			anchored
			keys={value}
			onSelect={emit}
			labels={value.map(labelOf)}
			chipKeys={value}
			chipRow
			inline={false}
			{summary}
			{max}
			{searchable}
			rowCount={shown.length}
			{size}
			{disabled}
			{readonly}
			{invalid}
			clearable={clearableForField(clearable, field)}
			{placeholder}
			{searchPlaceholder}
			bind:open
			{onOpenChange}
			bind:query={search}
			onRemoveAt={removeAt}
			onClear={() => emit([])}
			count={shown.length}
			empty={shown.length === 0}
			{emptyLabel}
			{clearLabel}
			{triggerLabel}
			overflowLabel={`Show all ${value.length} values`}
			controlProps={{ 'aria-label': field?.displayName, 'aria-required': field?.mandatory }}
		>
			{#snippet chip(index: number, armed: boolean, hidden: boolean)}
				{@const code = value[index]!}
				<span
					data-slot={`${slot}-chip`}
					data-chip=""
					data-armed={armed ? 'true' : undefined}
					{hidden}
					class={cn(PICKER_TEXT_CHIP, PICKER_TEXT_CHIP_BOX[size], armed && PICKER_ARMED)}
				>
					<span class="truncate">{labelOf(code)}</span>
					{#if interactive}
						<button
							type="button"
							data-slot={`${slot}-remove`}
							aria-label={`Remove ${labelOf(code)}`}
							onclick={() => remove(code)}
							class={REMOVE_CONTROL}
						>
							<X aria-hidden="true" class={PICKER_TEXT_CHIP_CROSS[size]} />
						</button>
					{/if}
				</span>
			{/snippet}

			{#snippet rows()}
				{#each shown as option (option.code)}
					{@const chosen = value.includes(option.code)}
					<Combobox.Item
						data-slot={`${slot}-option`}
						data-option={option.code}
						data-checked={chosen ? 'true' : undefined}
						value={option.code}
						label={option.label}
						class={PICKER_ROW}
					>
						<Row
							row={{ type: LIST_ROW_TYPE, id: 0, name: option.label, values: {} }}
							query={searchable ? search : ''}
							thumbnail={false}
							subLabel={subLabel?.(option)}
							secondary={secondaryOf(option)}
							{size}
							indicatorSlot={`${slot}-check`}
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
	{#if error}
		{#if errorMessage}
			{@render errorMessage(error)}
		{:else}
			<p data-slot="field-editor-error" class="text-destructive text-xs">{error}</p>
		{/if}
	{/if}
</div>
