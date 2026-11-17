<script lang="ts" module>
	import type { StatusBadgeSize } from '$lib/components/status-badge.svelte';
	import type { ThumbnailSize } from '$lib/components/thumbnail.svelte';

	export type EntityCardSize = 'sm' | 'md' | 'lg';
	/** `card` is the stacked surface; `tile` is the thumbnail-first cell a grid lays out. */
	export type EntityCardVariant = 'card' | 'tile';

	/** Cards and detail panes take the top of the thumbnail ladder (`docs/design-rules.md`). */
	const THUMB: Record<EntityCardSize, ThumbnailSize> = { sm: 'xl', md: 'xl', lg: '2xl' };
	/** A badge sits one step under the card it is in (`docs/design-rules.md` rule 3). */
	const BADGE: Record<EntityCardSize, StatusBadgeSize> = { sm: 'xs', md: 'sm', lg: 'md' };
	const HEADER: Record<EntityCardSize, string> = { sm: 'gap-2', md: 'gap-3', lg: 'gap-3' };
	const STACK: Record<EntityCardSize, string> = { sm: 'gap-2', md: 'gap-3', lg: 'gap-4' };
	const NAME: Record<EntityCardSize, string> = { sm: 'text-sm', md: 'text-sm', lg: 'text-base' };
	const ROWS: Record<EntityCardSize, string> = { sm: 'gap-y-1.5', md: 'gap-y-2', lg: 'gap-y-2' };
	const BODY: Record<EntityCardSize, string> = { sm: 'p-3', md: 'p-3', lg: 'p-4' };
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import type {
		EntityCardColumn,
		EntityCardModel,
		EntityRef,
		EntityRow,
		FieldSpec,
		FieldTextOptions,
		SgClient,
		SgContext,
		StatusRecord
	} from 'sg-widgets-core';
	import {
		cellValue,
		contextFromClient,
		describeEntityCard,
		entityCardSlot,
		entityDetailUrl,
		errorText,
		fieldText,
		imageState,
		isEmptyValue,
		loadEntityCard,
		pathOf,
		preferencesOf,
		renderKindFor,
		stateLine,
		urlLink
	} from 'sg-widgets-core';
	import CircleAlert from '@lucide/svelte/icons/circle-alert';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { cn, type WithElementRef } from '$lib/utils.js';
	import { entityGlyph } from '$lib/components/entity-glyphs.js';
	import StateLine from '$lib/components/state-line.svelte';
	import StatusBadge from '$lib/components/status-badge.svelte';
	import Thumbnail from '$lib/components/thumbnail.svelte';

	type Props = WithElementRef<Omit<HTMLAttributes<HTMLDivElement>, 'children'>, HTMLDivElement> & {
		/** The cached client, the schema service, the site url and the preferences the card reads through. */
		context?: SgContext;
		/** A client, for an app with no context. One context is built per client and shared. */
		client?: SgClient;
		/** The row to show. Given, nothing is read. */
		row?: EntityRow | null;
		/** The row to read, when no `row` is given. */
		entity?: EntityRef | null;
		/** Dotted field paths for the grid, in order. `card` only. */
		fields?: string[];
		variant?: EntityCardVariant;
		size?: EntityCardSize;
		/** The `image` field the thumbnail comes from. */
		imagePath?: string;
		/** Field shown as the name. Defaults to the type's own display name. `tile` only. */
		labelField?: string | null;
		/** The left of the tile's metadata line: a path, or a resolved column so it renders by type. */
		subLabelField?: FieldSpec | null;
		/** The caller's own sub-label. Wins over `subLabelField`. */
		subLabel?: (row: EntityRow) => string;
		/** The right of the tile's metadata line: a path, or a resolved column so it renders by type. */
		secondaryField?: FieldSpec | null;
		/** The caller's own text on the right of the metadata line. Wins over `secondaryField`. */
		secondary?: (row: EntityRow) => string;
		/** Show the row's `code` beside the name when the two differ. `tile` only. */
		showCode?: boolean;
		/** `Status` rows by code (probe 010). Read through the context when not given. */
		statuses?: Record<string, StatusRecord> | null;
		/** Draws the tile's selection checkbox and gives the tile a focus ring. */
		selectable?: boolean;
		selected?: boolean;
		onSelectedChange?: (selected: boolean) => void;
		/** Controls in the thumbnail's top-right corner, on hover or focus. `tile` only. */
		actions?: Snippet;
		/** The web app the row lives on. Defaults to the context's. */
		siteUrl?: string;
		/** The site's `hours_per_day` from `GET /preferences`; durations then render in days. Defaults to the context's. */
		hoursPerDay?: number;
		locale?: string;
		/** IANA zone a `date_time` is shown in. Defaults to the context's. */
		timeZone?: string;
		/** Frames a second, for a timecode. Defaults to the context's. */
		frameRate?: number;
		/** What a field with no value shows. */
		emptyLabel?: string;
		/** Shown in place of what the failed read said. */
		errorLabel?: string;
	};

	let {
		context,
		client,
		row = null,
		entity = null,
		fields = [],
		variant = 'card',
		size = 'md',
		imagePath = 'image',
		labelField = null,
		subLabelField = null,
		subLabel,
		secondaryField = null,
		secondary,
		showCode = false,
		statuses = null,
		selectable = false,
		selected = false,
		onSelectedChange,
		actions,
		siteUrl,
		hoursPerDay,
		locale,
		timeZone,
		frameRate,
		emptyLabel = 'empty',
		errorLabel,
		class: className,
		ref = $bindable(null),
		...rest
	}: Props = $props();

	// One context per client, so a card handed a bare client shares the page's caches.
	const ctx = $derived(context ?? (client ? contextFromClient(client) : undefined));
	// The site's preferences, with anything the caller named winning over them.
	const prefs = $derived<FieldTextOptions>({
		...preferencesOf(ctx),
		...(hoursPerDay === undefined ? {} : { hoursPerDay }),
		...(locale === undefined ? {} : { locale }),
		...(timeZone === undefined ? {} : { timeZone }),
		...(frameRate === undefined ? {} : { frameRate })
	});

	interface Loaded {
		card: EntityCardModel;
		statuses: Record<string, StatusRecord>;
	}

	async function build(
		source: { row: EntityRow | null; entity: EntityRef | null },
		wanted: string[],
		table: Record<string, StatusRecord> | null
	): Promise<Loaded> {
		if (!ctx) throw new Error('An entity card needs a context or a client.');
		const options = { fields: wanted, imagePath };
		const card = source.row
			? await describeEntityCard(ctx, source.row, options)
			: source.entity
				? await loadEntityCard(ctx, source.entity, options)
				: null;
		if (!card) throw new Error('An entity card needs a row or a reference.');
		return { card, statuses: table ?? Object.fromEntries(await ctx.statuses.byCode()) };
	}

	const subPath = $derived(pathOf(subLabelField));
	const secondaryPath = $derived(pathOf(secondaryField));
	// A tile draws one metadata line, so the paths it resolves are the row anatomy's,
	// not the caller's field grid.
	const paths = $derived(
		variant === 'tile' ? [...new Set([subPath, secondaryPath].filter((p) => p.length > 0))] : fields
	);

	// The read hangs off the props through a derived, so a new row or a new path
	// list is a new promise and no effect has to guard against the last one.
	const loaded = $derived(build({ row, entity }, paths, statuses));
	const site = $derived(siteUrl ?? ctx?.siteUrl ?? '');
	const linkClass =
		'focus-visible:ring-ring focus-visible:ring-offset-background truncate underline-offset-2 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-offset-2';
	/** Chrome over the thumbnail: absent until it is wanted, then a fade and a small rise. */
	const revealClass = 'transition-[opacity,transform] duration-150 ease-out motion-reduce:transition-opacity';
	const hiddenClass =
		'opacity-0 group-hover/tile:opacity-100 group-focus-within/tile:opacity-100 motion-safe:-translate-y-0.5 motion-safe:group-hover/tile:translate-y-0 motion-safe:group-focus-within/tile:translate-y-0';

	/** An entity value and a multi_entity value are the same shape, one boxed (field_types/multi_entity). */
	function refsOf(value: unknown): EntityRef[] {
		return Array.isArray(value) ? (value as EntityRef[]) : [value as EntityRef];
	}

	function textOf(column: EntityCardColumn): string {
		return fieldText(column.value, column.dataType, {
			...prefs,
			...(column.field?.displayValues === undefined ? {} : { displayValues: column.field.displayValues })
		});
	}

	function nameOf(card: EntityCardModel): string {
		if (!labelField) return card.name;
		return String(cellValue(card.row, labelField) ?? '');
	}

	/** The programmatic name, when it says something the label does not. */
	function codeOf(card: EntityCardModel): string {
		if (!showCode) return '';
		const raw = cellValue(card.row, 'code');
		return typeof raw === 'string' && raw.length > 0 && raw !== nameOf(card) ? raw : '';
	}
</script>

<!--
	One row as a card, or as a tile.

	Given a reference the card reads the row itself: one search asking for the
	type's identity chain, its thumbnail, its status field and the caller's paths
	at once, through the context's cache, so a second card on the same row costs
	nothing. Every path is labelled through the schema, and a hop names the type it
	travels through only when the field could have gone somewhere else, which is
	the same ambiguity the projection resolves (probe 059).

	Values are drawn here rather than through FieldValue: FieldValue draws a linked
	row as a chip, and a chip's own hover card is this card, so the two would
	depend on each other and neither registry CLI can install a cycle. A card is a
	compact surface, so a linked row is a link and the rest is one line of text
	through core's `fieldText`.

	A tile is the same row read picture first: the thumbnail fills the top, the
	status sits on it as an icon, and the row-anatomy props draw one metadata line
	under the name. A Version with media carries the play overlay the desktop
	tk-framework-qtwidgets label uses. Selection and activation belong to whoever
	lays the tiles out, so the tile takes its selected state and spreads the
	listbox attributes and handlers a collection puts on it.
-->
{#snippet cell(column: EntityCardColumn, table: Record<string, StatusRecord>)}
	{@const kind = renderKindFor(column.dataType)}
	{#if kind === 'empty' || isEmptyValue(column.value)}
		<span class="text-muted-foreground text-xs italic select-none">{emptyLabel}</span>
	{:else if kind === 'status'}
		<StatusBadge
			code={String(column.value)}
			status={table[String(column.value)] ?? null}
			field={column.field}
			size={BADGE[size]}
			siteUrl={site}
		/>
	{:else if kind === 'image'}
		<Thumbnail src={String(column.value)} size="sm" alt="" />
	{:else if kind === 'entity' || kind === 'multi_entity'}
		<span class="flex min-w-0 flex-wrap items-center gap-2">
			{#each refsOf(column.value) as target (`${target.type}:${target.id}`)}
				{@const url = entityDetailUrl(site, target)}
				{@const name = fieldText(target, 'entity')}
				{#if url}
					<a href={url} target="_blank" rel="noreferrer" title={name} class={linkClass}>{name}</a>
				{:else}
					<span title={name} class="truncate">{name}</span>
				{/if}
			{/each}
		</span>
	{:else if kind === 'url'}
		{@const link = urlLink(column.value)}
		{#if link?.href}
			<a href={link.href} rel="noreferrer" title={link.label} class={linkClass}>{link.label}</a>
		{:else}
			<span title={link?.label} class="truncate">{link?.label}</span>
		{/if}
	{:else if kind === 'text'}
		<!-- `text` keeps its newlines: a description is free text and often multi-line. -->
		<span class="min-w-0 break-words whitespace-pre-wrap">{textOf(column)}</span>
	{:else}
		{@const text = textOf(column)}
		<span title={text} class={cn('truncate', kind === 'number' && 'tabular-nums')}>{text}</span>
	{/if}
{/snippet}

{#if variant === 'tile'}
	<div
		bind:this={ref}
		data-slot="entity-card"
		data-variant="tile"
		data-size={size}
		data-state={selected ? 'selected' : undefined}
		class={cn(
			'group/tile border-border bg-card focus-visible:ring-ring focus-visible:ring-offset-background relative flex w-full min-w-0 flex-col overflow-hidden rounded-lg border text-left outline-none transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-offset-2',
			selected && 'bg-accent text-accent-foreground',
			className
		)}
		{...rest}
	>
		{#await loaded}
			<Skeleton class="aspect-video w-full rounded-none" />
			<div class={cn('flex min-w-0 flex-col gap-1.5', BODY[size])}>
				<Skeleton class="h-4 w-3/4" />
				<Skeleton class="h-3 w-1/2" />
			</div>
		{:then { card, statuses: table }}
			{@const name = nameOf(card)}
			{@const code = codeOf(card)}
			{@const sub = subLabel ? subLabel(card.row) : ''}
			{@const right = secondary ? secondary(card.row) : ''}
			{@const subColumn = entityCardSlot(card, subLabelField)}
			{@const secondaryColumn = entityCardSlot(card, secondaryField)}
			<div data-slot="entity-card-media" class="relative w-full">
				<Thumbnail
					src={card.thumbnail}
					size={THUMB[size]}
					alt=""
					entityType={card.entity.type}
					playable={card.entity.type === 'Version' && imageState(card.thumbnail) === 'ready'}
					class="h-auto w-full rounded-none border-0"
				/>
				<span
					data-slot="entity-card-overlay"
					class="absolute top-2 left-2 flex max-w-[calc(100%-1rem)] items-center gap-1.5"
				>
					{#if selectable}
						<span
							data-slot="entity-card-selection"
							class={cn('flex items-center', revealClass, selected ? 'opacity-100' : hiddenClass)}
						>
							<Checkbox
								aria-label="Select {name}"
								checked={selected}
								onCheckedChange={(value) => onSelectedChange?.(value === true)}
								class="bg-background/80 border-transparent shadow-sm"
							/>
						</span>
					{/if}
				</span>
				<!-- The status keeps the right corner; the actions appear beside it, never over it. -->
				{#if actions || card.status}
					<span
						data-slot="entity-card-overlay-end"
						class="absolute top-2 right-2 flex max-w-[calc(100%-1rem)] items-center gap-1.5"
					>
						{#if actions}
							<span
								data-slot="entity-card-actions"
								class={cn('flex items-center gap-1.5', revealClass, hiddenClass)}
							>
								{@render actions()}
							</span>
						{/if}
						{#if card.status}
							<StatusBadge
								code={card.status.code}
								status={table[card.status.code] ?? null}
								field={card.status.field}
								variant="icon"
								size={BADGE[size]}
								siteUrl={site}
								class="bg-background/80 border-transparent shadow-sm"
							/>
						{/if}
					</span>
				{/if}
			</div>
			<div data-slot="entity-card-body" class={cn('flex min-w-0 flex-col gap-1.5', BODY[size])}>
				<span data-slot="entity-card-name" class="flex min-w-0 items-center gap-1.5">
					<span title={name} class={cn('min-w-0 truncate font-medium', NAME[size])}>{name}</span>
					{#if code}
						<span class="text-muted-foreground shrink-0 font-mono text-xs">{code}</span>
					{/if}
				</span>
				{#if sub || subColumn || right || secondaryColumn}
					<span
						data-slot="entity-card-meta"
						class="text-muted-foreground flex min-w-0 items-center gap-1.5 text-xs"
					>
						<span data-slot="entity-card-sub" class="flex min-w-0 flex-1 items-center truncate">
							{#if sub}
								<span title={sub} class="truncate">{sub}</span>
							{:else if subColumn}
								{@render cell(subColumn, table)}
							{/if}
						</span>
						<span data-slot="entity-card-secondary" class="flex shrink-0 items-center justify-end">
							{#if right}
								<span title={right} class="truncate">{right}</span>
							{:else if secondaryColumn}
								{@render cell(secondaryColumn, table)}
							{/if}
						</span>
					</span>
				{/if}
			</div>
		{:catch error}
			<StateLine
				state="error"
				icon={CircleAlert}
				label={stateLine('error', { errorLabel }, errorText(error))}
			/>
		{/await}
	</div>
{:else}
	<div
		bind:this={ref}
		data-slot="entity-card"
		data-variant="card"
		data-size={size}
		class={cn('flex w-full min-w-0 flex-col', STACK[size], className)}
		{...rest}
	>
		{#await loaded}
			<div class={cn('flex min-w-0 items-start', HEADER[size])}>
				<Skeleton class={cn('aspect-video shrink-0', size === 'lg' ? 'h-24' : 'h-16')} />
				<div class="flex min-w-0 flex-1 flex-col gap-2">
					<Skeleton class="h-4 w-3/4" />
					<Skeleton class="h-3 w-1/2" />
				</div>
			</div>
			<div class={cn('grid min-w-0 grid-cols-[minmax(0,auto)_minmax(0,1fr)] gap-x-3', ROWS[size])}>
				{#each fields as path (path)}
					<Skeleton class="h-3 w-16" />
					<Skeleton class="h-3 w-full" />
				{/each}
			</div>
		{:then { card, statuses: table }}
			{@const Glyph = entityGlyph(card.entity.type)}
			{@const url = entityDetailUrl(site, card.entity)}
			<div class={cn('flex min-w-0 items-start', HEADER[size])}>
				<Thumbnail src={card.thumbnail} size={THUMB[size]} alt="" entityType={card.entity.type} />
				<div class="flex min-w-0 flex-1 flex-col gap-1.5">
					{#if url}
						<a
							href={url}
							target="_blank"
							rel="noreferrer"
							title={card.name}
							class={cn(linkClass, 'font-medium', NAME[size])}>{card.name}</a
						>
					{:else}
						<span title={card.name} class={cn('truncate font-medium', NAME[size])}>{card.name}</span>
					{/if}
					<div class="flex min-w-0 flex-wrap items-center gap-2">
						<span class="text-muted-foreground inline-flex min-w-0 items-center gap-1.5 text-xs">
							<Glyph aria-hidden="true" class="size-4 shrink-0 opacity-70" />
							<span class="truncate">{card.typeLabel}</span>
						</span>
						{#if card.status}
							<StatusBadge
								code={card.status.code}
								status={table[card.status.code] ?? null}
								field={card.status.field}
								size={BADGE[size]}
								siteUrl={site}
							/>
						{/if}
					</div>
				</div>
			</div>
			{#if card.columns.length > 0}
				<!-- The label is a size under the value, so a stretched row hangs it above the first line; one baseline holds them level. -->
				<dl
					class={cn(
						'grid min-w-0 grid-cols-[minmax(0,auto)_minmax(0,1fr)] items-baseline gap-x-3',
						ROWS[size]
					)}
				>
					{#each card.columns as column (column.path)}
						<dt class="text-muted-foreground truncate text-xs" title={column.label}>{column.label}</dt>
						<dd data-data-type={column.dataType} class="flex min-w-0 items-center text-sm">
							{@render cell(column, table)}
						</dd>
					{/each}
				</dl>
			{/if}
		{:catch error}
			<StateLine
				state="error"
				icon={CircleAlert}
				label={stateLine('error', { errorLabel }, errorText(error))}
			/>
		{/await}
	</div>
{/if}
