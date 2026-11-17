<script lang="ts" module>
	export type FieldPickerSize = 'sm' | 'md' | 'lg';
</script>

<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import type { FieldHop, FieldOption, FieldPathOption, FieldSchema, SgContext } from 'sg-widgets-core';
	import {
		currentType,
		deriveFieldOptions,
		errorText,
		friendlyFieldPath,
		iconNameFor,
		NO_MATCH_LABEL,
		pickerKeyIntent,
		repeatedLabels,
		resolveFieldPathOptions,
		searchFieldOptions,
		searchFieldPathOptions,
		stateLine
	} from 'sg-widgets-core';
	import Braces from '@lucide/svelte/icons/braces';
	import Calendar from '@lucide/svelte/icons/calendar';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import CircleDollarSign from '@lucide/svelte/icons/circle-dollar-sign';
	import CircleDot from '@lucide/svelte/icons/circle-dot';
	import FileText from '@lucide/svelte/icons/file-text';
	import Fingerprint from '@lucide/svelte/icons/fingerprint';
	import Globe from '@lucide/svelte/icons/globe';
	import Hash from '@lucide/svelte/icons/hash';
	import Image from '@lucide/svelte/icons/image';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import Link from '@lucide/svelte/icons/link';
	import Link2 from '@lucide/svelte/icons/link-2';
	import List from '@lucide/svelte/icons/list';
	import Palette from '@lucide/svelte/icons/palette';
	import Percent from '@lucide/svelte/icons/percent';
	import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
	import Ruler from '@lucide/svelte/icons/ruler';
	import SearchX from '@lucide/svelte/icons/search-x';
	import Shapes from '@lucide/svelte/icons/shapes';
	import Sigma from '@lucide/svelte/icons/sigma';
	import SquareCheck from '@lucide/svelte/icons/square-check';
	import Tag from '@lucide/svelte/icons/tag';
	import Timer from '@lucide/svelte/icons/timer';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Type from '@lucide/svelte/icons/type';
	import X from '@lucide/svelte/icons/x';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { cn, type WithElementRef } from '$lib/utils.js';
	import StateLine from '$lib/components/state-line.svelte';
	import {
		PICKER_CONTROL,
		PICKER_GLYPH,
		PICKER_ICON_BUTTON,
		PICKER_TEXT_BOX,
		PICKER_TRAILING
	} from '$lib/components/picker-classes.js';

	type Props = WithElementRef<HTMLAttributes<HTMLDivElement>, HTMLDivElement> & {
		/** The widget context. The schema is read through it, once per page. */
		context: SgContext;
		/** The type the path starts on. */
		entityType: string;
		/** A fixed list of paths, offered flat. The list restrictions do not apply to it. */
		options?: string[];
		/** The dotted path, `field` or `field.Type.field…`. Empty when nothing is chosen. */
		value?: string;
		onValueChange?: (value: string) => void;
		/** Allow descending through entity fields. */
		deepLinks?: boolean;
		/** Show the programmatic name beside the display name. */
		showCode?: boolean;
		/** How many hops a path may take. */
		maxDepth?: number;
		/** Data types a field must have to be selected. Traversal ignores this. */
		dataTypes?: string | string[];
		/** A field is selectable only if it links one of these. Traversal ignores this. */
		validTypes?: string[];
		/** Full dotted paths to drop. */
		exclude?: string[];
		/** Dotted prefixes to drop, along with everything beneath them. */
		hidePaths?: string[];
		/** Drop the data types the API refuses in a filter. */
		filterableOnly?: boolean;
		/** Synthetic entries offered at the root only. */
		extraFields?: { name: string; displayName?: string }[];
		/** Caller's own visibility test over the schema and the candidate's full path. */
		filter?: (field: FieldSchema, path: string) => boolean;
		/** Close the popover on a selection. Off keeps it open for the next pick. */
		closeOnSelect?: boolean;
		placeholder?: string;
		searchPlaceholder?: string;
		/** Shown when the search matches nothing. */
		emptyLabel?: string;
		/** The accessible name of the skeletons a read stands behind. */
		loadingLabel?: string;
		/** Shown in place of what the failed read said. */
		errorLabel?: string;
		clearable?: boolean;
		readonly?: boolean;
		disabled?: boolean;
		invalid?: boolean;
		size?: FieldPickerSize;
		/** Whether the popover is showing, two-way. */
		open?: boolean;
		onOpenChange?: (open: boolean) => void;
		class?: string;
	};

	let {
		context,
		entityType,
		options,
		value = $bindable(''),
		onValueChange,
		deepLinks = false,
		showCode = false,
		maxDepth = 2,
		dataTypes,
		validTypes,
		exclude,
		hidePaths,
		filterableOnly = false,
		extraFields,
		filter,
		closeOnSelect = true,
		placeholder = 'Select a field',
		searchPlaceholder = 'Search fields…',
		emptyLabel = NO_MATCH_LABEL,
		loadingLabel,
		errorLabel,
		clearable = true,
		readonly = false,
		disabled = false,
		invalid = false,
		size = 'md',
		open = $bindable(false),
		onOpenChange,
		class: className,
		ref = $bindable(null),
		...rest
	}: Props = $props();

	// The context's own service, so every widget on the page shares one schema read.
	const schema = $derived(context.schema);

const ICONS: Record<string, typeof Type> = {
		braces: Braces,
		calendar: Calendar,
		'calendar-clock': CalendarClock,
		'circle-dollar-sign': CircleDollarSign,
		'circle-dot': CircleDot,
		'file-text': FileText,
		fingerprint: Fingerprint,
		globe: Globe,
		hash: Hash,
		image: Image,
		'key-round': KeyRound,
		link: Link,
		'link-2': Link2,
		list: List,
		palette: Palette,
		percent: Percent,
		ruler: Ruler,
		shapes: Shapes,
		sigma: Sigma,
		'square-check': SquareCheck,
		tag: Tag,
		timer: Timer,
		type: Type
	};

	function setOpen(next: boolean): void {
		const wanted = readonly || disabled ? false : next;
		// The query goes with the list, so the next open starts on the whole set.
		if (!wanted) {
			search = '';
			highlighted = '';
		}
		if (wanted === open) return;
		open = wanted;
		onOpenChange?.(open);
	}

	let inputEl = $state<HTMLInputElement | null>(null);
	let search = $state('');
	let highlighted = $state('');
	let hops = $state<FieldHop[]>([]);
	/** The field whose target type is being chosen, when it declares more than one. */
	let choosing = $state<FieldOption | null>(null);
	let loaded = $state<{ type: string; fields: Record<string, FieldSchema> } | null>(null);
	/** The caller's fixed list, resolved. Keyed on what was asked for, so a change re-reads. */
	let fixed = $state<{ key: string; rows: FieldPathOption[] } | null>(null);
	let resolved = $state<{ path: string; label: string } | null>(null);
	let failure = $state<string | null>(null);

	const type = $derived(currentType(entityType, hops));
	const fixedKey = $derived(options ? `${entityType}|${options.join(',')}` : null);

	// Every path of the fixed list is resolved through the types it travels, once per list.
	$effect(() => {
		const service = schema;
		const key = fixedKey;
		const paths = options;
		if (key === null || paths === undefined) return;
		let live = true;
		void resolveFieldPathOptions(service, entityType, paths).then((rows) => {
			if (live) fixed = { key, rows };
		});
		return () => {
			live = false;
		};
	});

	// `/schema/<Type>/fields` is 48KB and ~330ms (probe 002); the schema service caches
	// it, so a hop back to a type already visited costs nothing.
	$effect(() => {
		const service = schema;
		const wanted = type;
		if (options) return;
		let live = true;
		service
			.fields(wanted)
			.then((fields) => {
				if (live) loaded = { type: wanted, fields };
			})
			.catch((error: unknown) => {
				if (live) failure = errorText(error);
			});
		return () => {
			live = false;
		};
	});

	// The closed control shows the friendly path, never the raw one, so the label is
	// resolved through the schema of every type the path travels.
	$effect(() => {
		const service = schema;
		const root = entityType;
		const wanted = value;
		if (!wanted || extraFields?.some((extra) => extra.name === wanted)) return;
		let live = true;
		service
			.resolvePath(root, wanted)
			.then((segments) => {
				if (live) resolved = { path: wanted, label: friendlyFieldPath(segments) };
			})
			// A path the schema no longer holds still has to be readable, so it stays as it is.
			.catch(() => {
				if (live) resolved = { path: wanted, label: wanted };
			});
		return () => {
			live = false;
		};
	});

	const fixedRows = $derived(fixed?.key === fixedKey ? fixed.rows : null);
	const fields = $derived(loaded?.type === type ? loaded.fields : null);
	const nested = $derived(
		fields
			? deriveFieldOptions(fields, {
					rootType: entityType,
					hops,
					deepLinks,
					maxDepth,
					dataTypes,
					validTypes,
					exclude,
					hidePaths,
					filterableOnly,
					extraFields,
					filter
				})
			: []
	);
	/** One shape for both lists, so a fixed row and a schema row draw the same. */
	const rows = $derived(
		fixedRows
			? searchFieldPathOptions(fixedRows, search).map((row) => ({
					path: row.path,
					label: row.label,
					code: row.name,
					sub: row.subLabel,
					dataType: row.dataType,
					field: null as FieldOption | null
				}))
			: choosing
				? []
				: searchFieldOptions(nested, search).map((row) => ({
						path: row.path,
						label: row.displayName,
						code: row.name,
						sub: row.computed ? 'computed' : row.dataType,
						dataType: row.dataType,
						field: row as FieldOption | null
					}))
	);
	/** Labels two rows share, over the whole list so a search never changes a row. Such a row shows its code. */
	const repeated = $derived(
		repeatedLabels(fixedRows ? fixedRows.map((row) => row.label) : nested.map((row) => row.displayName))
	);
	const targets = $derived(choosing ? choosing.targets.filter((t) => matchesType(t)) : []);
	/** Every row's value, in the order they are drawn: what the arrow keys walk. */
	const values = $derived(choosing ? targets : rows.map((row) => row.path));
	const cursor = $derived(values.includes(highlighted) ? highlighted : (values[0] ?? ''));
	const computed = $derived(extraFields?.find((extra) => extra.name === value));
	const offered = $derived(fixedRows?.find((row) => row.path === value));
	const label = $derived(
		computed
			? (computed.displayName ?? computed.name)
			: offered
				? offered.label
				: resolved?.path === value
					? resolved.label
					: null
	);
	const ready = $derived(options ? fixedRows !== null : fields !== null);
	const showClear = $derived(clearable && value !== '' && !readonly && !disabled);
	const breadcrumb = $derived(!options && (hops.length > 0 || choosing !== null));

	function matchesType(target: string): boolean {
		return target.toLowerCase().includes(search.trim().toLowerCase());
	}

	function emit(next: string): void {
		value = next;
		onValueChange?.(next);
	}

	/** Every hop clears the search box; nothing is remounted, so focus stays in the input. */
	function descend(field: FieldOption, through: string): void {
		hops = [...hops, { name: field.name, displayName: field.displayName, through }];
		choosing = null;
		search = '';
		highlighted = '';
	}

	function activate(row: { path: string; field: FieldOption | null }): void {
		if (row.field?.traversable && !row.field.selectable) {
			descendInto(row.field);
			return;
		}
		emit(row.path);
		// The search box clears on every selection as it does on every hop, so a caller
		// adding one field after another never has to reach for the mouse.
		search = '';
		highlighted = '';
		if (closeOnSelect) setOpen(false);
	}

	function descendInto(row: FieldOption): void {
		if (!row.traversable) return;
		if (row.targets.length === 1) descend(row, row.targets[0] as string);
		else {
			choosing = row;
			search = '';
			highlighted = '';
		}
	}

	function back(): void {
		if (choosing) choosing = null;
		else hops = hops.slice(0, -1);
		search = '';
		highlighted = '';
	}

	function reset(): void {
		hops = [];
		choosing = null;
		search = '';
		highlighted = '';
	}

	function onKeys(event: KeyboardEvent): void {
		// One value, so an empty query takes Backspace down to nothing in a press.
		const intent = pickerKeyIntent(event.key, {
			open,
			query: search,
			count: value === '' ? 0 : 1,
			focused: null,
			editable: !readonly && !disabled,
			multiple: false
		});
		if (intent.kind === 'remove') {
			event.preventDefault();
			emit('');
			return;
		}
		if (event.key === 'ArrowRight') {
			if (choosing) {
				const target = cursor;
				if (target) {
					event.preventDefault();
					descend(choosing, target);
				}
				return;
			}
			const row = rows.find((r) => r.path === cursor)?.field;
			if (row?.traversable) {
				event.preventDefault();
				descendInto(row);
			}
			return;
		}
		if (event.key === 'ArrowLeft' && breadcrumb) {
			event.preventDefault();
			back();
		}
	}
</script>

<!--
	One field of one entity type, as a searchable combobox that descends through links.

	The value is ShotGrid's dotted path: a root field is its own code, and every hop
	names the field followed and the type it landed on. Only a single `entity` field
	is descended into - a dotted path through a `multi_entity` field reads back
	nothing, 200 with the key absent (probe 016). A link declaring several target
	types asks which one first. `dataTypes` and `validTypes` bind what may be chosen,
	not what may be walked through, so a picker restricted to dates still reaches a
	date behind a link.

	`options` replaces the schema list with a caller's own paths, flat: no links, no
	descending, no breadcrumb, and the list restrictions do not apply.
-->
<div
	bind:this={ref}
	data-slot="field-picker"
	data-size={size}
	data-depth={hops.length}
	class={cn('relative flex w-full min-w-0 items-center', className)}
	{...rest}
>
	<Popover.Root bind:open={() => open, setOpen}>
		<Popover.Trigger
			data-slot="field-picker-trigger"
			role="combobox"
			aria-expanded={open}
			aria-invalid={invalid ? 'true' : undefined}
			aria-disabled={disabled ? 'true' : undefined}
			data-readonly={readonly ? 'true' : undefined}
			data-value={value || undefined}
			data-empty={value === '' ? '' : undefined}
			{disabled}
			title={label ?? placeholder}
			class={cn(
				PICKER_CONTROL,
				/* The trigger is the focusable element itself, not a box round an input. */
				'focus-visible:ring-ring focus-visible:ring-offset-background aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 aria-invalid:ring-2',
				PICKER_TEXT_BOX[size],
				readonly ? 'pr-3' : showClear ? 'pr-14' : 'pr-8'
			)}
		>
			{#if value === ''}
				<span class="text-muted-foreground truncate">{placeholder}</span>
			{:else if label === null}
				<Skeleton class="h-4 w-32" />
			{:else}
				<span data-slot="field-picker-label" class="truncate">{label}</span>
			{/if}
		</Popover.Trigger>

		<!-- Fixed: the Command list scrolls its highlighted row into view on mount, and an absolute wrapper
		     still at the page origin would drag the page there with it. -->
		<Popover.Content
			strategy="fixed"
			data-picker="field"
			onOpenAutoFocus={(e) => {
				e.preventDefault();
				inputEl?.focus({ preventScroll: true });
			}}
			align="start"
			onkeydown={onKeys}
			class="w-96 max-w-[calc(100vw-2rem)] gap-0 overflow-hidden p-0"
		>
			{#if breadcrumb}
				<div
					data-slot="field-picker-breadcrumb"
					class="border-border flex items-center gap-1.5 border-b px-2 py-1.5"
				>
					<button
						type="button"
						data-slot="field-picker-back"
						aria-label="Go back one level"
						title="Back (Left arrow)"
						onclick={back}
						class={PICKER_ICON_BUTTON}
					>
						<ChevronLeft aria-hidden="true" class="size-4" />
					</button>
					<nav
						aria-label="Field path"
						class="text-muted-foreground flex min-w-0 flex-1 items-center gap-1 overflow-hidden text-xs"
					>
						<span class="shrink-0">{entityType}</span>
						{#each hops as hop (hop.name + hop.through)}
							<ChevronRight aria-hidden="true" class="size-3 shrink-0" />
							<span class="truncate">{hop.displayName}</span>
						{/each}
						{#if choosing}
							<ChevronRight aria-hidden="true" class="size-3 shrink-0" />
							<span class="truncate italic">{choosing.displayName}</span>
						{/if}
					</nav>
					<button
						type="button"
						data-slot="field-picker-reset"
						aria-label="Back to the root type"
						title="Reset"
						onclick={reset}
						class={PICKER_ICON_BUTTON}
					>
						<RotateCcw aria-hidden="true" class="size-4" />
					</button>
				</div>
			{/if}

			<Command.Root
				shouldFilter={false}
				loop
				value={cursor}
				onValueChange={(next) => (highlighted = next)}
			>
				<Command.Input
					bind:ref={inputEl}
					bind:value={search}
					placeholder={choosing ? 'Which type?' : searchPlaceholder}
				/>
				<Command.List>
					{#if failure}
						<StateLine
							state="error"
							slotName="field-picker-error"
							icon={TriangleAlert}
							label={stateLine('error', { errorLabel }, failure)}
						/>
					{:else if choosing}
						<Command.Empty>
							<StateLine state="empty" icon={SearchX} label={emptyLabel} pad="none" />
						</Command.Empty>
						{#each targets as target (target)}
							<Command.Item
								value={target}
								onSelect={() => choosing && descend(choosing, target)}
								class="items-start"
							>
								<Link aria-hidden="true" class="mt-0.5 size-4 shrink-0 opacity-70" />
								<span class="flex min-w-0 flex-1 flex-col">
									<span class="truncate">{target}</span>
									<span class="text-muted-foreground truncate text-xs">entity type</span>
								</span>
								<ChevronRight aria-hidden="true" class="size-4 shrink-0 opacity-50" />
							</Command.Item>
						{/each}
					{:else if !ready}
						<div
							data-slot="field-picker-loading"
							class="flex flex-col"
							aria-busy="true"
							aria-label={stateLine('loading', { loadingLabel })}
						>
							{#each [0, 1, 2] as row (row)}
								<div class="flex flex-col gap-1 px-2 py-1.5">
									<Skeleton class="h-5 w-2/3" />
									<Skeleton class="h-3 w-1/4" />
								</div>
							{/each}
						</div>
					{:else}
						<Command.Empty>
							<StateLine state="empty" icon={SearchX} label={emptyLabel} pad="none" />
						</Command.Empty>
						{#each rows as row (row.path)}
							{@const Glyph = ICONS[iconNameFor(row.dataType)] ?? FileText}
							<Command.Item
								value={row.path}
								onSelect={() => activate(row)}
								data-checked={row.path === value ? 'true' : undefined}
								data-traversable={row.field?.traversable ? 'true' : undefined}
								title={row.path}
								class="items-start"
							>
								<Glyph aria-hidden="true" class="mt-0.5 size-4 shrink-0 opacity-70" />
								<span class="flex min-w-0 flex-1 flex-col">
									<span class="flex min-w-0 items-center gap-1.5">
										<span class="truncate">{row.label}</span>
										{#if (showCode || repeated.has(row.label)) && row.code !== '' && row.code !== row.label}
											<span class="text-muted-foreground shrink-0 font-mono text-xs">{row.code}</span>
										{/if}
									</span>
									<span class="text-muted-foreground truncate text-xs">
										{row.sub}
									</span>
								</span>
								{#if row.field?.traversable}
									<button
										type="button"
										tabindex={-1}
										data-slot="field-picker-descend"
										aria-label={`Open ${row.label}`}
										title="Open (Right arrow)"
										onmousedown={(event) => event.preventDefault()}
										onclick={(event) => {
											event.stopPropagation();
											if (row.field) descendInto(row.field);
										}}
										class={PICKER_ICON_BUTTON}
									>
										<ChevronRight aria-hidden="true" class="size-4" />
									</button>
								{/if}
							</Command.Item>
						{/each}
					{/if}
				</Command.List>
			</Command.Root>
		</Popover.Content>
	</Popover.Root>

	{#if !readonly}
		<div class={cn('pointer-events-none absolute top-0 right-2 flex items-center gap-1', PICKER_TRAILING[size])}>
			{#if showClear}
				<button
					type="button"
					data-slot="field-picker-clear"
					aria-label="Clear the field"
					onclick={() => emit('')}
					class={PICKER_ICON_BUTTON}
				>
					<X aria-hidden="true" class={PICKER_GLYPH[size]} />
				</button>
			{/if}
			<ChevronDown aria-hidden="true" class={cn('shrink-0 opacity-50', PICKER_GLYPH[size])} />
		</div>
	{/if}
</div>
