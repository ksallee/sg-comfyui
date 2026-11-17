<script lang="ts" module>
	import type { PickerSummary } from 'sg-widgets-core';

	export type PickerControlSize = 'sm' | 'md' | 'lg';

	/** The row a press on the last row of a page carries, rather than an item key. */
	export const LOAD_MORE = '__load-more';

	/** Everything a picker built on this base takes. */
	export interface PickerControlProps {
		/** The `data-slot` prefix every part of this picker carries. */
		slot: string;
		/** The `data-picker` the popup carries. */
		picker: string;
		/** Several keys may be chosen at once. */
		multiple?: boolean;
		/** The chosen keys, in order. A single picker passes none or one. */
		keys: string[];
		/** The keys the primitive has settled on. `LOAD_MORE` never reaches it. */
		onSelect: (keys: string[]) => void;
		/** One label per chosen key: the summary, the title and the measured row read it. */
		labels: string[];
		/** A stable key per chip, so a removal does not redraw the row. Defaults to the label. */
		chipKeys?: string[];
		/** The `data-slot` of the chip row. Defaults to `<slot>-chips`. */
		chipsSlot?: string;
		/** What the control shows for the selection. */
		summary?: PickerSummary;
		/** Chips drawn before the rest becomes `+n`. `0` lets the row fit what it can. */
		max?: number;
		/** The value is a measured row of chips rather than the one chip of a single picker. */
		chipRow?: boolean;
		/** The control holds the caret. A summary control keeps it in the popup instead. */
		inline?: boolean;
		/** The caret gives its room to the chips. */
		tokenInput?: boolean;
		/** What the caret shows. */
		inputPlaceholder?: string;
		/** A summary control keeps a search row. A fixed set has nothing to search. */
		searchable?: boolean;
		/** The filled value is plain text, so the control keeps the reading inset in both states. */
		textValue?: boolean;
		/** The row keys on show, so a changed list follows the highlight. */
		rowCount?: number;
		/** What the chips look like, so a change to any of it re-measures the row. */
		rowKey?: string;
		size?: PickerControlSize;
		disabled?: boolean;
		/** The primitive takes no input. Wider than `disabled`: a loading picker is inert too. */
		inert?: boolean;
		readonly?: boolean;
		invalid?: boolean;
		clearable?: boolean;
		placeholder?: string;
		/** The combobox's accessible name, for a control whose placeholder is empty. */
		label?: string;
		searchPlaceholder?: string;
		/** Whether the popup is showing, two-way. */
		open?: boolean;
		onOpenChange?: (open: boolean) => void;
		/** What the caret holds, two-way. */
		query?: string;
		onQueryChange?: (query: string) => void;
		/** Remove the chip at `index`. Backspace walks the row through it. */
		onRemoveAt?: (index: number) => void;
		onClear?: () => void;
		/** The popup is as wide as the control it hangs off. */
		anchored?: boolean;
		loading?: boolean;
		/** Rows the list offers, which is what the live row counts. */
		count?: number;
		error?: string | null;
		empty?: boolean;
		emptyLabel?: string;
		loadingLabel?: string;
		errorLabel?: string;
		/** A further page is there to be read. */
		hasMore?: boolean;
		onLoadMore?: () => void;
		clearLabel?: string;
		triggerLabel?: string;
		overflowLabel?: string;
		/** Attributes the control carries on top of the shared ones. */
		controlProps?: Record<string, unknown>;
	}
</script>

<script lang="ts">
	import { tick, type Snippet } from 'svelte';
	import {
		focusChip,
		listStatus,
		NO_MATCH_LABEL,
		pickerKeyIntent,
		stateLine,
		summariseSelection,
		watchHighlight,
		watchOverflow
	} from 'sg-widgets-core';
	import { Combobox } from 'bits-ui';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Search from '@lucide/svelte/icons/search';
	import SearchX from '@lucide/svelte/icons/search-x';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import X from '@lucide/svelte/icons/x';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import StateLine from '$lib/components/state-line.svelte';
	import {
		CHIP_GAP,
		LIST_STATUS,
		OVERFLOW_RESERVE,
		PICKER_ANCHORED_POPUP,
		PICKER_BOX,
		PICKER_CONTROL,
		PICKER_GLYPH,
		PICKER_ICON_BUTTON,
		PICKER_INPUT,
		PICKER_LIST,
		PICKER_PILL,
		PICKER_POPUP,
		PICKER_ROW,
		PICKER_SEARCH,
		PICKER_SEARCH_ROW,
		PICKER_TEXT_BOX,
		PICKER_TOKEN_INPUT,
		PICKER_TRAILING
	} from '$lib/components/picker-classes.js';
	import { cn } from '$lib/utils.js';

	type Props = PickerControlProps & {
		/** One chip: its index, whether the caret is on it, whether the row hides it. */
		chip?: Snippet<[number, boolean, boolean]>;
		/** The rows of the list, as items of the primitive. */
		rows?: Snippet;
	};

	let {
		slot,
		picker,
		multiple = false,
		keys,
		onSelect,
		labels,
		chipKeys,
		chipsSlot,
		summary = 'chips',
		max = 0,
		chipRow = false,
		inline = true,
		tokenInput = true,
		inputPlaceholder,
		searchable = true,
		textValue = false,
		rowCount = 0,
		rowKey,
		size = 'md',
		disabled = false,
		inert = disabled,
		readonly = false,
		invalid = false,
		clearable = true,
		placeholder = '',
		label,
		searchPlaceholder = 'Search…',
		open = $bindable(false),
		onOpenChange,
		query = $bindable(''),
		onQueryChange,
		onRemoveAt,
		onClear,
		anchored = false,
		loading = false,
		count = 0,
		error = null,
		empty = false,
		emptyLabel = NO_MATCH_LABEL,
		loadingLabel,
		errorLabel,
		hasMore = false,
		onLoadMore,
		clearLabel = 'Clear the selection',
		triggerLabel = 'Show the options',
		overflowLabel,
		controlProps,
		chip,
		rows
	}: Props = $props();

	let controlEl = $state<HTMLElement | null>(null);
	let listEl = $state<HTMLElement | null>(null);
	// The list writes the overflow variables the fade reads, which are Base UI's own.
	$effect(() => watchOverflow(listEl));
	let inputEl = $state<HTMLInputElement | null>(null);
	let triggerEl = $state<HTMLElement | null>(null);
	let chipsEl = $state<HTMLElement | null>(null);
	/** The chip holding the caret. Backspace and Delete take it. */
	let armed = $state<number | null>(null);
	/** A press on the load-more row is not a selection, and must not close the popup. */
	let paging = false;
	/** The search box is being put back after a pick, which is not typing. */
	let restoring = false;

	const loadingText = $derived(stateLine('loading', { loadingLabel }));
	/** The caret is a combobox, so it is named even when the control shows no placeholder. */
	const inputLabel = $derived(label || placeholder || triggerLabel);
	const interactive = $derived(!readonly && !inert);
	const showClear = $derived(clearable && labels.length > 0 && !readonly && !disabled);
	/** Only a multi control's row weighs itself; a single one draws its chip and stops. */
	const fitted = $derived(chipRow && multiple && summary === 'ellipsis');
	const measureKey = $derived(rowKey ?? `${size}|${summary}|${labels.join(', ')}`);

	let available = $state(0);
	let widths = $state<number[]>([]);
	let measured = $state(false);
	/** True once the row knows its own widths and its room, so it may be drawn. */
	const ready = $derived(!fitted || (measured && available > 0));

	/** Every chip laid out, so a hidden one still reports the width it would take. */
	function measure(row: HTMLElement): number[] {
		const drawn = [...row.querySelectorAll<HTMLElement>('[data-chip]')];
		const was = drawn.map((one) => one.hidden);
		for (const one of drawn) one.hidden = false;
		const out = drawn.map((one) => Math.ceil(one.getBoundingClientRect().width) + CHIP_GAP);
		drawn.forEach((one, i) => (one.hidden = was[i] ?? false));
		return out;
	}

	/** The room the chips have: the control's box, less the padding its affordances take. */
	function roomIn(control: HTMLElement): number {
		const style = getComputedStyle(control);
		return control.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
	}

	$effect(() => {
		const control = controlEl;
		if (!control || !fitted) return;
		const observer = new ResizeObserver(() => (available = roomIn(control)));
		observer.observe(control);
		available = roomIn(control);
		return () => observer.disconnect();
	});

	$effect(() => {
		void measureKey;
		const row = chipsEl;
		if (!row || !fitted) return;
		widths = measure(row);
		measured = true;
		let live = true;
		// A chip drawn in the fallback font is not the chip the row ends up with.
		void document.fonts?.ready.then(() => {
			if (live && chipsEl) widths = measure(chipsEl);
		});
		return () => {
			live = false;
		};
	});

	const plan = $derived(
		summariseSelection(labels, (label) => label, {
			summary,
			max,
			fit: fitted && measured && available > 0 ? { widths, available, reserve: OVERFLOW_RESERVE } : undefined
		})
	);
	const counted = $derived(summary === 'count' && chipRow && multiple);

	/** The caret's text, written back and announced, as `setOpen` is to `open`. */
	function setQuery(next: string): void {
		if (next === query) return;
		query = next;
		onQueryChange?.(next);
	}

	/** A press anywhere in the field opens the list, and a token field takes the caret. */
	/** Typing asks for the list: a press may have closed it a moment ago. */
	function typed(next: string): void {
		// The search box put back after a pick is not typing: a single pick has just
		// closed the list, and reading the write as a keystroke would open it again.
		if (restoring) return;
		setQuery(next);
		if (interactive && !open) setOpen(true);
	}

	function openFromControl(event: PointerEvent): void {
		if (!interactive) return;
		const target = event.target as HTMLElement | null;
		// The chip's remove control, the clear control and the chevron own their own press.
		if (target?.closest('button')) return;
		// The press's own default would move focus to the body and off whichever caret
		// takes it: the field's, or the popup's once the effect below focuses it.
		const onCaret = target === inputEl;
		if (!onCaret) event.preventDefault();
		armed = null;
		if (inline && !onCaret) inputEl?.focus({ preventScroll: true });
		// A press anywhere on the control toggles the list, the caret included; typing opens it again.
		setOpen(!open);
	}

	// A summary trigger has no caret of its own, so the popup's search box takes it.
	$effect(() => {
		if (!open || inline) return;
		inputEl?.focus({ preventScroll: true });
	});

	function setOpen(next: boolean): void {
		// The load-more row is a press on an item, which the primitive reads as a
		// selection. Paging is not a selection, and must not close the popup.
		if (!next && paging) {
			paging = false;
			return;
		}
		const wanted = interactive ? next : false;
		if (!wanted) setQuery('');
		if (wanted === open) return;
		const handBack = !wanted && !inline && inputEl !== null && document.activeElement === inputEl;
		open = wanted;
		onOpenChange?.(open);
		if (handBack) void tick().then(toTrigger);
	}

	/** The chevron opens the list on the arrow, as it does on Enter and Space. */
	function openOnArrow(event: KeyboardEvent): void {
		if (event.key !== 'ArrowDown' || open || !interactive) return;
		event.preventDefault();
		setOpen(true);
	}

	/**
	 * A summary control's caret is in the popup and goes with it, so the chevron takes
	 * it back: the next key is the picker's, and Tab leaves from where the picker stands.
	 */
	function toTrigger(): void {
		const active = document.activeElement;
		if (active && active !== document.body && active !== inputEl) return;
		triggerEl?.focus({ preventScroll: true });
	}

	// A chip removed from under the caret takes it with it.
	$effect(() => {
		if (armed !== null && armed >= labels.length) armed = null;
	});

	// The caret sits on one chip of the row at a time, and the row keeps it out of the
	// tab order, so Tab still leaves the control.
	$effect(() => {
		void labels.length;
		focusChip(chipsEl, armed);
	});

	// A chip is not a control, so its keys reach this handler through the row rather
	// than through markup a reader would have to read as interactive.
	$effect(() => {
		const row = chipsEl;
		if (!row) return;
		row.addEventListener('keydown', onKey);
		return () => row.removeEventListener('keydown', onKey);
	});

	/** The caret leaves the chips when it leaves the widget, and not before. */
	function releaseChips(): void {
		setTimeout(() => {
			const active = document.activeElement;
			if (active === inputEl || controlEl?.contains(active)) return;
			armed = null;
		}, 0);
	}

	/** The caret back in the input, and the chip row released. */
	function toInput(): void {
		armed = null;
		inputEl?.focus({ preventScroll: true });
	}

	/**
	 * The chip keys, Escape and the arrows, from the input or from a chip. The
	 * primitive's own handler runs after this one, so a key this picker owns is
	 * prevented rather than shared.
	 */
	function onKey(event: KeyboardEvent): void {
		// A link or a remove control inside a chip owns its own keys.
		if ((event.target as HTMLElement | null)?.closest('a,button')) return;
		const intent = pickerKeyIntent(event.key, {
			open,
			query,
			count: labels.length,
			focused: armed,
			editable: interactive,
			multiple
		});
		switch (intent.kind) {
			case 'dismiss':
				if (armed !== null) toInput();
				setOpen(false);
				return;
			case 'focus':
				event.preventDefault();
				if (intent.index === null) toInput();
				else armed = intent.index;
				return;
			case 'remove':
				event.preventDefault();
				armed = intent.then;
				onRemoveAt?.(intent.index);
				if (intent.then === null) inputEl?.focus({ preventScroll: true });
				return;
			case 'type':
				event.preventDefault();
				toInput();
				typed(query + intent.key);
				return;
			case 'open':
				event.preventDefault();
				toInput();
				setOpen(true);
				return;
			case 'follow':
				// The key belongs to the list, and the list's own watcher follows the highlight.
				return;
			default:
				return;
		}
	}

	// A load-more page appends rows under the highlighted one, and a new query
	// replaces them all; either way the list follows the highlight.
	$effect(() => {
		void rowCount;
		return watchHighlight(listEl);
	});

	function choose(next: string[]): void {
		if (next.includes(LOAD_MORE)) {
			paging = true;
			onLoadMore?.();
			return;
		}
		onSelect(next);
		restoreSearchBox();
		// A press on a row leaves the caret in the list; the next key belongs to the
		// control, so the input takes it back and the chip row is released. A pick made
		// with a chip armed would otherwise keep that chip, and the next Backspace would
		// take it rather than the one just added.
		toInput();
	}

	/**
	 * The primitive writes the chosen item's label into the search box. The box holds the
	 * query and nothing else, so the write is put back as a write the primitive reads:
	 * an unchanged query is not a new search. Only the primitive reads it: the picker's
	 * own handler would take it for typing and open the list a single pick just closed.
	 */
	function restoreSearchBox(): void {
		void tick().then(() => {
			if (!inputEl || inputEl.value === query) return;
			inputEl.value = query;
			restoring = true;
			try {
				inputEl.dispatchEvent(new Event('input', { bubbles: true }));
			} finally {
				restoring = false;
			}
		});
	}

	function clear(): void {
		onClear?.();
		// The clear control goes with the value, and the caret stays on the picker.
		if (inline) inputEl?.focus({ preventScroll: true });
		else triggerEl?.focus({ preventScroll: true });
	}
</script>

{#snippet caret()}
	<Combobox.Input
		bind:ref={inputEl}
		data-slot={`${slot}-input`}
		aria-invalid={invalid ? 'true' : undefined}
		aria-label={inputLabel}
		readonly={readonly || undefined}
		placeholder={inputPlaceholder ?? (labels.length > 0 ? '' : placeholder)}
		oninput={(e) => typed(e.currentTarget.value)}
		onkeydown={onKey}
		class={tokenInput ? PICKER_TOKEN_INPUT : PICKER_INPUT}
	/>
{/snippet}

{#snippet control()}
	<div
		bind:this={controlEl}
		data-slot={`${slot}-control`}
		onpointerdown={openFromControl}
		onfocusout={releaseChips}
		role="group"
		aria-disabled={inert ? 'true' : undefined}
		data-multiple={multiple ? 'true' : undefined}
		data-invalid={invalid && !inline ? 'true' : undefined}
		data-readonly={readonly ? 'true' : undefined}
		data-empty={labels.length === 0 ? '' : undefined}
		title={plan.title || placeholder}
		class={cn(
			PICKER_CONTROL,
			(textValue ? PICKER_TEXT_BOX : PICKER_BOX)[size],
			plan.oneLine && 'flex-nowrap',
			readonly ? 'pr-3' : showClear ? 'pr-14' : 'pr-8'
		)}
		{...controlProps}
	>
		{#if labels.length > 0}
			<span data-slot={`${slot}-value`} class="flex min-w-0 items-center gap-1.5">
				{#if counted}
					<span data-slot={`${slot}-count`} class="truncate">{plan.countLabel}</span>
				{:else if chipRow}
					<!--
						Whole chips only: the row measures itself and hides the ones that do not
						fit, so nothing is ever cut in half. `+n` follows the last one drawn.
						No stylesheet here gives `[hidden]` a display rule, so the row does.
					-->
					<span
						bind:this={chipsEl}
						data-slot={chipsSlot ?? `${slot}-chips`}
						class={cn(
							'flex min-w-0 items-center gap-1.5 [&>[hidden]]:hidden',
							plan.oneLine ? 'flex-nowrap overflow-hidden' : 'flex-wrap',
							ready ? undefined : 'invisible'
						)}
					>
						{#each labels as label, index (chipKeys?.[index] ?? `${index}:${label}`)}
							{@render chip?.(index, armed === index, ready && index >= plan.shown.length)}
						{/each}
						{#if plan.overflow > 0}
							<button
								type="button"
								data-slot={`${slot}-overflow`}
								title={plan.title}
								aria-label={overflowLabel ?? `Show all ${labels.length} selected`}
								onclick={() => setOpen(true)}
								class={PICKER_PILL}>+{plan.overflow}</button
							>
						{/if}
					</span>
				{:else}
					{@render chip?.(0, armed === 0, false)}
				{/if}
			</span>
		{:else if !inline}
			<span data-slot={`${slot}-placeholder`} class="text-muted-foreground truncate">{placeholder}</span>
		{/if}
		{#if inline}
			{@render caret()}
		{/if}
	</div>
{/snippet}

{#snippet popup()}
	<!--
		Fixed, and anchored to the whole control rather than to the input: the list
		scrolls its highlighted row into view on mount, and an absolute wrapper still
		at the page origin would drag the page there with it.
	-->
	<Combobox.Portal>
		<Combobox.Content
			data-picker={picker}
			data-slot={`${slot}-content`}
			strategy="fixed"
			customAnchor={controlEl}
			align="start"
			sideOffset={4}
			class={anchored ? PICKER_ANCHORED_POPUP : PICKER_POPUP}
		>
			{#if !inline && searchable}
				<div data-slot={`${slot}-search`} class={PICKER_SEARCH_ROW}>
					<Search aria-hidden="true" class="size-4 shrink-0 opacity-50" />
					<Combobox.Input
						bind:ref={inputEl}
						data-slot={`${slot}-input`}
						aria-label={searchPlaceholder}
						placeholder={searchPlaceholder}
						oninput={(e) => typed(e.currentTarget.value)}
						onkeydown={onKey}
						class={PICKER_SEARCH}
					/>
				</div>
			{:else if !inline}
				<!-- Nothing to search, and still the one caret: it holds the focus and the keys. -->
				<Combobox.Input
					bind:ref={inputEl}
					data-slot={`${slot}-input`}
					aria-label={inputLabel}
					readonly
					onkeydown={onKey}
					class="sr-only"
				/>
			{/if}
			<div
				data-slot={`${slot}-status`}
				role="status"
				aria-live="polite"
				aria-atomic="true"
				class={LIST_STATUS}
			>
				{listStatus({ loading, count, error, asked: true }, { emptyLabel, loadingLabel, errorLabel })}
			</div>
			<div bind:this={listEl} data-slot={`${slot}-list`} class={PICKER_LIST}>
				{#if error !== null && error !== ''}
					<StateLine
						state="error"
						slotName={`${slot}-error`}
						icon={TriangleAlert}
						label={stateLine('error', { errorLabel }, error)}
					/>
				{:else if loading}
					<div
						data-slot={`${slot}-loading`}
						class="flex flex-col"
						aria-busy="true"
						aria-label={loadingText}
					>
						{#each [0, 1, 2] as row (row)}
							<div class="flex items-center px-2 py-1.5">
								<Skeleton class="h-5 w-full" />
							</div>
						{/each}
					</div>
				{:else if empty}
					<StateLine state="empty" slotName={`${slot}-empty`} icon={SearchX} label={emptyLabel} />
				{:else}
					{@render rows?.()}
					{#if hasMore}
						<Combobox.Item
							data-slot={`${slot}-more`}
							value={LOAD_MORE}
							label={loading ? loadingText : 'Load more'}
							class={cn(PICKER_ROW, 'text-muted-foreground justify-center text-xs')}
						>
							{loading ? loadingText : 'Load more'}
						</Combobox.Item>
					{/if}
				{/if}
			</div>
		</Combobox.Content>
	</Combobox.Portal>
{/snippet}

{#snippet actions()}
	{#if !readonly}
		<div class={cn('pointer-events-none absolute top-0 right-2 flex items-center gap-1', PICKER_TRAILING[size])}>
			{#if showClear}
				<button
					type="button"
					data-slot={`${slot}-clear`}
					aria-label={clearLabel}
					onclick={clear}
					class={PICKER_ICON_BUTTON}
				>
					<X aria-hidden="true" class={PICKER_GLYPH[size]} />
				</button>
			{/if}
			<Combobox.Trigger
				bind:ref={triggerEl}
				data-slot={`${slot}-trigger`}
				aria-label={triggerLabel}
				disabled={inert}
				onkeydown={openOnArrow}
				class={PICKER_ICON_BUTTON}
			>
				<ChevronDown aria-hidden="true" class={PICKER_GLYPH[size]} />
			</Combobox.Trigger>
		</div>
	{/if}
{/snippet}

<!--
	The control and the popup every picker in this registry wears.

	The box and its states, the press rule (a press anywhere on the control toggles the
	list, the caret included), where the caret lands on open, the keyboard model
	of core's `pickerKeyIntent`, the inline token field against the summary trigger with
	its chip row, and the popup shell: the search row, the list, the empty, loading and
	error block, and the load-more row. A picker supplies its rows, its row renderer and
	its chip and nothing else.
-->
{#if multiple}
	<Combobox.Root
		type="multiple"
		disabled={inert}
		inputValue={query}
		bind:open={() => open, setOpen}
		bind:value={() => keys, choose}
	>
		{@render control()}
		{@render popup()}
		{@render actions()}
	</Combobox.Root>
{:else}
	<Combobox.Root
		type="single"
		allowDeselect={false}
		disabled={inert}
		inputValue={query}
		bind:open={() => open, setOpen}
		bind:value={() => keys[0] ?? '', (key) => choose(key === '' ? [] : [key])}
	>
		{@render control()}
		{@render popup()}
		{@render actions()}
	</Combobox.Root>
{/if}
