<script lang="ts" module>
	import type { ChipSize } from '$lib/components/leaf-classes.js';

	/** How much of the status to show. `glyph` is the bare icon, with no pill around it. */
	export type StatusBadgeVariant = 'both' | 'icon' | 'text' | 'glyph';
	export type StatusBadgeSize = ChipSize;
	/** Which of the two names the badge puts on show; the other one goes in the tooltip. */
	export type StatusBadgeLabel = 'name' | 'code';
</script>

<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import type { FieldSchema, StatusRecord } from 'sg-widgets-core';
	import { statusGlyph, statusLabel, statusPaint } from 'sg-widgets-core';
	import X from '@lucide/svelte/icons/x';
	import { cn, type WithElementRef } from '$lib/utils.js';
	import { CHIP_BOX, CHIP_CROSS, CHIP_GLYPH, CHIP_PAD, CHIP_SPACING, LEAF_GLYPH, REMOVE_CONTROL } from '$lib/components/leaf-classes.js';
	import StatusGlyph from '$lib/components/status-glyph.svelte';

	// `color` is a deprecated HTML attribute Svelte types as `never`, so it is dropped
	// before the badge's own prop of that name is declared.
	type Props = WithElementRef<Omit<HTMLAttributes<HTMLSpanElement>, 'color'>, HTMLSpanElement> & {
		/** The stored code, e.g. `ip`. A row may hold a code outside the usable set; that is legal (probe 009). */
		code: string;
		/** The resolved `Status` row, when the app has read `GET /entity/statuses` (probe 010). */
		status?: StatusRecord | null;
		/** The field schema, whose `display_values` is the only other source of a label (field_types/status_list). */
		field?: Pick<FieldSchema, 'displayValues'> | null;
		variant?: StatusBadgeVariant;
		size?: StatusBadgeSize;
		/** Paint the badge in the status colour instead of the neutral surface. */
		color?: boolean;
		label?: StatusBadgeLabel;
		/** The site the stock sprite is served from, for icons the package does not bundle. */
		siteUrl?: string;
		/** Draw a remove control inside the pill. The icon-only variant has no room for it and ignores this. */
		removable?: boolean;
		onRemove?: (code: string) => void;
		/** Accessible label for the remove control. */
		removeLabel?: string;
	};

	let {
		code,
		status = null,
		field = null,
		variant = 'both',
		size = 'md',
		color = false,
		label = 'name',
		siteUrl = undefined,
		removable = false,
		onRemove,
		removeLabel,
		class: className,
		ref = $bindable(null),
		...rest
	}: Props = $props();

	const known = $derived(Boolean(status) || field?.displayValues?.[code] !== undefined);
	const name = $derived(status?.name || (field ? statusLabel(field, code) : code) || code);
	const text = $derived(label === 'code' ? code : name);
	const other = $derived(label === 'code' ? name : code);
	const paint = $derived(color ? statusPaint(status) : null);
	const style = $derived(
		paint ? `background-color:${paint.background};color:${paint.foreground}` : undefined
	);
	// An `html` icon carries the label itself, so it replaces the text rather than
	// preceding it, and such a status has no image to show in icon-only mode
	// (010_status_icons).
	const glyph = $derived(statusGlyph(status, siteUrl));
	const textIcon = $derived(glyph.kind === 'html' ? glyph.html || text : null);
	const showGlyph = $derived(variant !== 'text' && glyph.kind !== 'none' && textIcon === null);
	const showText = $derived(variant !== 'icon' || textIcon !== null);
	// The bare glyph has no pill, so no colour, no text and no room for a cross.
	const bare = $derived(variant === 'glyph');
	// A bare icon is the glyph and nothing else, so there is no room for a cross.
	const showRemove = $derived(removable && variant !== 'icon' && !bare);
</script>

<!--
	One status, as a badge.

	The label comes from the `Status` row's `name`, else from the field's
	`display_values`, else it is the raw code: a status_list value is a bare code with
	no entity behind it, so a dotted read gives nothing (field_types/status_list). An
	unknown code is therefore never blank - it renders as itself. Whichever of the name
	and the code is not on show is the tooltip, so a code is always one hover away from
	its name. The badge is neutral by default; `color` paints it in `bg_color`,
	comma-separated decimal RGB and never hex (probe 010), the one raw colour the design
	rules allow.

	`display_type` picks one of three icon renderings (010_status_icons): `image` is a
	self-contained data URI, `html` is the label itself and so replaces the text rather
	than preceding it, and `image_map` names a cell of the stock sprite. Cells of the
	shipped statuses are bundled in core and draw with no site access; any other stock
	icon draws from the site's own copy of the sprite, so it needs `siteUrl`. The key
	stays on the element as `data-status-icon`.

	`removable` draws a cross inside the pill, after the label, in the badge's own
	foreground: under `color` that is the readable black or white the status colour
	gives, so the cross keeps its contrast on every colour. Its hover is a translucent
	wash of that foreground rather than the destructive tint the entity chip uses, since
	the pill already carries a colour of its own.

	`glyph` is the icon alone, in its own colour, with no pill around it: no border, no
	background, no inset, sized like a row glyph. It is the leading mark of a row whose
	label is an entity's name, where a bordered pill would read as a second surface; a
	status listed as an option is the glyph and its name. The label stays as the
	accessible name and the tooltip, `color` has nothing to paint, and there is no room
	for a cross. A status with no icon to draw takes the neutral dot, so a row always
	carries a leading mark.
-->
{#snippet content()}
	{#if showGlyph}
		<StatusGlyph {status} {siteUrl} onColor={Boolean(paint)} class={CHIP_GLYPH[size]} />
	{/if}
	<span class={cn('truncate', !showText && 'sr-only')}>{textIcon ?? text}</span>
{/snippet}

{#if code}
	<span
		bind:this={ref}
		data-slot="status-badge"
		data-status-code={code}
		data-status-known={known ? 'true' : 'false'}
		data-variant={variant}
		title={other}
		style={bare ? undefined : style}
		class={cn(
			bare
				? cn('inline-flex shrink-0 items-center justify-center align-middle', LEAF_GLYPH[size === 'xs' ? 'sm' : size])
				: cn(
						/* A badge paints no surface of its own: it wears the card, popover or page it sits on. */
						'border-border inline-flex max-w-full min-w-0 items-center rounded-md border align-middle',
						showRemove ? CHIP_SPACING[size].cross : CHIP_SPACING[size].glyph,
						CHIP_BOX[size],
						variant === 'icon'
							? cn('justify-center', CHIP_PAD[size].icon)
							: cn(CHIP_PAD[size].text, showGlyph && CHIP_PAD[size].lead, showRemove && CHIP_PAD[size].trail),
						paint && 'border-transparent ring-1 ring-current/10 ring-inset',
						color && !paint && 'bg-muted text-muted-foreground border-transparent'
					),
			className
		)}
		{...rest}
	>
		{#if bare}
			<StatusGlyph {status} {siteUrl} fallback class={LEAF_GLYPH[size === 'xs' ? 'sm' : size]} />
			<span class="sr-only">{text}</span>
		{:else if showRemove}
			<span class={cn('flex min-w-0 items-center', CHIP_SPACING[size].glyph)}>{@render content()}</span>
			<button
				type="button"
				data-slot="status-badge-remove"
				aria-label={removeLabel ?? `Remove ${text}`}
				onclick={() => onRemove?.(code)}
				class={cn(REMOVE_CONTROL, 'pointer-events-auto')}
			>
				<X aria-hidden="true" class={CHIP_CROSS[size]} />
			</button>
		{:else}
			{@render content()}
		{/if}
	</span>
{/if}
