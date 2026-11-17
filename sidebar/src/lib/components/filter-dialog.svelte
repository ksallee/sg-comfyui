<script lang="ts" module>
	import type { ControlSize } from '$lib/components/control-classes.js';
	import { CHIP_BOX, CHIP_PAD, type ChipSize } from '$lib/components/leaf-classes.js';

	export type FilterDialogSize = ControlSize;

	/** The icon-button step beside a control of each height. */
	const ICON: Record<FilterDialogSize, 'icon-sm' | 'icon' | 'icon-lg'> = {
		sm: 'icon-sm',
		md: 'icon',
		lg: 'icon-lg'
	};
	/** The count beside the label is a chip, so it takes the step under the control. */
	const COUNT: Record<FilterDialogSize, ChipSize> = { sm: 'xs', md: 'sm', lg: 'md' };
	/** A text chip wears the entity chip's surface, as a picker's code chip does. */
	const COUNT_CHIP =
		'bg-secondary text-secondary-foreground inline-flex shrink-0 items-center rounded-md border tabular-nums';
</script>

<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import type { Snippet } from 'svelte';
	import FilterIcon from '@lucide/svelte/icons/list-filter';
	import PencilIcon from '@lucide/svelte/icons/pencil';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import type { FilterGroup, SgContext } from 'sg-widgets-core';
	import { countActiveConditions, emptyFilter, isEmptyFilter } from 'sg-widgets-core';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { cn, type WithElementRef } from '$lib/utils.js';
	import { CONTROL_BOX, CONTROL_GLYPH } from '$lib/components/control-classes.js';
	import FilterEditor, {
		type FieldChooserArgs,
		type ValueEditorArgs
	} from '$lib/components/filter-editor.svelte';

	type Props = WithElementRef<HTMLAttributes<HTMLDivElement>, HTMLDivElement> & {
		entityType: string;
		/** The widget context. Every read goes through it, so widgets on a page share one cache. */
		context: SgContext;
		value: FilterGroup;
		hidePaths?: string[];
		size?: FilterDialogSize;
		disabled?: boolean;
		/** Replaces both button labels. Otherwise Add filters, then Edit filters. */
		label?: string;
		title?: string;
		onValueChange?: (value: FilterGroup) => void;
		/** Whether the dialog is showing, two-way. */
		open?: boolean;
		onOpenChange?: (open: boolean) => void;
		fieldChooser?: Snippet<[FieldChooserArgs]>;
		valueEditor?: Snippet<[ValueEditorArgs]>;
		entityEditor?: Snippet<[ValueEditorArgs]>;
		class?: string;
	};

	let {
		entityType,
		context,
		value = $bindable(emptyFilter()),
		hidePaths = [],
		size = 'md',
		disabled = false,
		label,
		title = 'Filters',
		onValueChange,
		open = $bindable(false),
		onOpenChange,
		fieldChooser,
		valueEditor,
		entityEditor,
		class: className,
		ref = $bindable(null),
		...rest
	}: Props = $props();

	let draft = $state<FilterGroup>(value);

	const active = $derived(countActiveConditions(value));

	function commit(next: FilterGroup): void {
		value = next;
		onValueChange?.(next);
	}

	function apply(): void {
		// A tree of blank rows is not a filter; it applies as no filter at all.
		commit(isEmptyFilter(draft) ? emptyFilter() : draft);
		setOpen(false);
	}

	function clearAll(): void {
		commit(emptyFilter());
		setOpen(false);
	}

	function setOpen(next: boolean): void {
		if (next === open) return;
		open = next;
		if (next) draft = value;
		onOpenChange?.(next);
	}
</script>

<!--
	The launcher for the filter editor.

	Empty, it is one Add filters button. With filters applied it is an Edit filters
	button carrying the count, plus a control that clears them without opening
	anything. Edits inside the dialog are staged: only Apply emits, Cancel drops
	them, and Clear all emits an empty filter.
-->
<div
	bind:this={ref}
	data-slot="filter-dialog"
	class={cn('inline-flex items-center gap-2', className)}
	{...rest}
>
	<!-- The draft starts from the applied value every time the dialog opens, so a cancelled edit leaves nothing behind. -->
	<Dialog.Root bind:open={() => open, setOpen}>
		<Dialog.Trigger
			{disabled}
			data-slot="filter-launch"
			data-size={size}
			class={cn(
				'border-border bg-background hover:bg-muted focus-visible:border-ring focus-visible:ring-ring/50 inline-flex shrink-0 items-center gap-1.5 rounded-lg border text-sm font-medium shadow-xs outline-none focus-visible:ring-3 disabled:pointer-events-none disabled:opacity-50',
				CONTROL_BOX[size]
			)}
		>
			{#if active > 0}
				<PencilIcon class={CONTROL_GLYPH[size]} />
				{label ?? 'Edit filters'}
				<span
					data-slot="filter-count"
					class={cn(COUNT_CHIP, CHIP_BOX[COUNT[size]], CHIP_PAD[COUNT[size]].text)}
				>{active}</span>
			{:else}
				<FilterIcon class={CONTROL_GLYPH[size]} />
				{label ?? 'Add filters'}
			{/if}
		</Dialog.Trigger>
		<!-- A condition row wants room: the dialog takes the viewport up to 64rem. -->
		<Dialog.Content class="w-[min(96vw,64rem)] sm:max-w-none">
			<Dialog.Header>
				<Dialog.Title>{title}</Dialog.Title>
				<Dialog.Description>Rows match on {entityType}. Nothing applies until you press Apply.</Dialog.Description>
			</Dialog.Header>
			<FilterEditor
				{entityType}
				{context}
				{hidePaths}
				{size}
				bind:value={draft}
				{fieldChooser}
				{valueEditor}
				{entityEditor}
			/>
			<Dialog.Footer class="sm:justify-between">
				<Button variant="ghost" data-slot="filter-clear-all" onclick={clearAll}>Clear all</Button>
				<div class="flex items-center gap-2">
					<Button variant="outline" data-slot="filter-cancel" onclick={() => setOpen(false)}>Cancel</Button>
					<Button data-slot="filter-apply" onclick={apply}>Apply</Button>
				</div>
			</Dialog.Footer>
		</Dialog.Content>
	</Dialog.Root>

	{#if active > 0}
		<Button
			variant="ghost"
			size={ICON[size]}
			{disabled}
			aria-label="Clear filters"
			data-slot="filter-clear"
			onclick={() => commit(emptyFilter())}
		>
			<Trash2Icon />
		</Button>
	{/if}
</div>
