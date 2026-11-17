<script lang="ts" module>
	import type { ChipSize } from '$lib/components/leaf-classes.js';

	export type EntityChipSize = ChipSize;
	export type EntityChipVariant = 'chip' | 'link' | 'text';

	/** A link or a bare label has no box, so only the type scale applies. */
	const TEXT: Record<EntityChipSize, string> = {
		xs: 'text-xs',
		sm: 'text-xs',
		md: 'text-sm',
		lg: 'text-sm'
	};
</script>

<script lang="ts">
	import type { HTMLAttributes, MouseEventHandler } from 'svelte/elements';
	import type { EntityRef, SgClient, SgContext } from 'sg-widgets-core';
	import { contextFromClient, entityDetailUrl } from 'sg-widgets-core';
	import X from '@lucide/svelte/icons/x';
	import * as HoverCard from '$lib/components/ui/hover-card/index.js';
	import { cn, type WithElementRef } from '$lib/utils.js';
	import { entityGlyph } from '$lib/components/entity-glyphs.js';
	import { CHIP_BOX, CHIP_CROSS, CHIP_GLYPH, CHIP_PAD, CHIP_SPACING, REMOVE_CONTROL } from '$lib/components/leaf-classes.js';
	import EntityCard from '$lib/components/entity-card.svelte';

	type Props = WithElementRef<HTMLAttributes<HTMLSpanElement>, HTMLSpanElement> & {
		/** `{type, id, name}` exactly as an entity field returns it under `relationships` (field_types/entity). */
		entity: EntityRef;
		/** A thumbnail URL for the linked row. Presigned and short-lived, so pass a fresh one (field_types/image). */
		thumbnail?: string | null;
		/** `chip` is the boxed default, `link` an inline link, `text` the bare name. */
		variant?: EntityChipVariant;
		/** A url, or a resolver. Left out, the row's own page on the site, opened in a new tab. */
		href?: string | ((entity: EntityRef) => string | null);
		/** The web app the row lives on. Defaults to the context's. */
		siteUrl?: string;
		/** Field paths shown in a hover card. Needs a context to read them through. */
		preview?: string[];
		/** The widget context, for the site url and for the hover card's read. */
		context?: SgContext;
		/** A client, for an app with no context. One context is built per client and shared. */
		client?: SgClient;
		onclick?: MouseEventHandler<HTMLButtonElement>;
		size?: EntityChipSize;
		removable?: boolean;
		onRemove?: (entity: EntityRef) => void;
		/** Accessible label for the remove control. */
		removeLabel?: string;
	};

	let {
		entity,
		thumbnail = null,
		variant = 'chip',
		href,
		siteUrl,
		preview,
		context,
		client,
		onclick,
		size = 'md',
		removable = false,
		onRemove,
		removeLabel,
		class: className,
		ref = $bindable(null),
		...rest
	}: Props = $props();

	const named = $derived(Boolean(entity.name && entity.name.length > 0));
	const label = $derived(named ? (entity.name as string) : `${entity.type} #${entity.id}`);
	const Glyph = $derived(entityGlyph(entity.type));

	// One context per client, so a chip handed a bare client shares the page's caches.
	const ctx = $derived(context ?? (client ? contextFromClient(client) : undefined));
	const site = $derived(siteUrl ?? ctx?.siteUrl ?? '');
	// The row's own page is on another origin, so it opens in a new tab; a url the
	// caller resolved belongs to the caller's app and stays in this one.
	const detail = $derived(href === undefined ? entityDetailUrl(site, entity) : null);
	const url = $derived(
		variant === 'text' ? null : typeof href === 'function' ? href(entity) : (href ?? detail)
	);
	const interactive = $derived(Boolean(url || onclick));
	const showGlyph = $derived(variant !== 'text');
	const innerClass = $derived(
		cn(
			'inline-flex min-w-0 items-center rounded-[inherit] outline-none',
			CHIP_SPACING[size].glyph,
			interactive &&
				'focus-visible:ring-ring focus-visible:ring-offset-background transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-offset-2 motion-safe:active:scale-[0.98]',
			variant === 'link' && url && 'underline-offset-2 hover:underline'
		)
	);
	const rootClass = $derived(
		cn(
			'inline-flex max-w-full min-w-0 items-center align-middle whitespace-nowrap',
			CHIP_SPACING[size].cross,
			variant === 'chip'
				? cn(
						'bg-secondary text-secondary-foreground rounded-md border',
						CHIP_BOX[size],
						CHIP_PAD[size].text,
						showGlyph && CHIP_PAD[size].lead,
						removable && CHIP_PAD[size].trail,
						interactive &&
							'hover:bg-accent hover:text-accent-foreground transition-colors duration-150'
					)
				: TEXT[size],
			className
		)
	);
</script>

<!--
	One linked row, as a chip, a link or bare text.

	`name` is the target's `cached_display_name` and is filled on every type measured,
	so a chip needs no second call (probe 060). When it is missing the chip shows
	`Type #id`, which is always addressable, in the mono/tabular treatment the design
	rules give ids. With no `href` the chip addresses the row's own page on the site,
	which core builds from the context's site url.
-->
{#snippet body()}
	{#if showGlyph}
		{#if thumbnail}
			<img
				src={thumbnail}
				alt=""
				aria-hidden="true"
				loading="lazy"
				decoding="async"
				class={cn('shrink-0 rounded-sm object-cover', CHIP_GLYPH[size])}
			/>
		{:else}
			<Glyph aria-hidden="true" class={cn('shrink-0 opacity-70', CHIP_GLYPH[size])} />
		{/if}
	{/if}
	<span class={cn('truncate', !named && 'font-mono tabular-nums')}>{label}</span>
{/snippet}

{#snippet chip()}
	<span
		bind:this={ref}
		data-slot="entity-chip"
		data-variant={variant}
		data-entity-type={entity.type}
		data-entity-id={entity.id}
		title={label}
		class={rootClass}
		{...rest}
	>
		{#if url}
			<a
				href={url}
				target={href === undefined ? '_blank' : undefined}
				rel={href === undefined ? 'noreferrer' : undefined}
				class={innerClass}>{@render body()}</a
			>
		{:else if onclick}
			<button type="button" {onclick} class={innerClass}>{@render body()}</button>
		{:else}
			<span class={innerClass}>{@render body()}</span>
		{/if}
		{#if removable}
			<button
				type="button"
				data-slot="entity-chip-remove"
				aria-label={removeLabel ?? `Remove ${label}`}
				onclick={() => onRemove?.(entity)}
				class={REMOVE_CONTROL}
			>
				<X aria-hidden="true" class={CHIP_CROSS[size]} />
			</button>
		{/if}
	</span>
{/snippet}

{#if preview && preview.length > 0 && ctx}
	<!-- The content mounts on open, so the card's read happens then and is cached on the context. -->
	<HoverCard.Root openDelay={200} closeDelay={100}>
		<HoverCard.Trigger>
			{#snippet child({ props })}
				<span
					{...props}
					data-slot="entity-chip-preview"
					class="inline-flex max-w-full min-w-0 align-middle"
				>
					{@render chip()}
				</span>
			{/snippet}
		</HoverCard.Trigger>
		<HoverCard.Content class="w-72 p-3">
			<EntityCard context={ctx} {entity} fields={preview} size="sm" siteUrl={site} />
		</HoverCard.Content>
	</HoverCard.Root>
{:else}
	{@render chip()}
{/if}
