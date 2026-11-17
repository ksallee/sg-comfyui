<script lang="ts" module>
	import { LEAF_GLYPH, type LeafSize } from '$lib/components/leaf-classes.js';

	export type UserAvatarSize = LeafSize;

	/** Avatars follow the same ladder as thumbnails (`docs/design-rules.md`). */
	const BOX: Record<UserAvatarSize, string> = {
		sm: 'size-6 text-xs',
		md: 'size-8 text-sm',
		lg: 'size-10 text-sm'
	};
	/**
	 * Initials tint: a fixed hue from the name at a light and a dark lightness, so it
	 * reads the same under every theme. Like status colour, it is data, not a token.
	 */
	const TINT =
	  'bg-[oklch(0.93_0.05_var(--sg-hue))] text-[oklch(0.42_0.13_var(--sg-hue))] dark:bg-[oklch(0.32_0.06_var(--sg-hue))] dark:text-[oklch(0.86_0.09_var(--sg-hue))]';
</script>

<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import { initialsOf, nameHue } from 'sg-widgets-core';
	import Bot from '@lucide/svelte/icons/bot';
	import { cn, type WithElementRef } from '$lib/utils.js';

	type Props = WithElementRef<HTMLAttributes<HTMLSpanElement>, HTMLSpanElement> & {
		/** The person's display name, i.e. `cached_display_name` on a HumanUser (probe 060). */
		name: string;
		/** The user's `image` field, or null. Presigned and short-lived (field_types/image). */
		image?: string | null;
		size?: UserAvatarSize;
		/** For a HumanUser whose `sg_status_list` is `dis`: dim without hiding. */
		inactive?: boolean;
		/** Marks an ApiUser or a script account rather than a person. */
		apiUser?: boolean;
		/** `auto` tints the initials from the name, the same tint every time. */
		color?: 'auto' | 'none';
	};

	let {
		name,
		image = null,
		size = 'md',
		inactive = false,
		apiUser = false,
		color = 'none',
		class: className,
		ref = $bindable(null),
		...rest
	}: Props = $props();

	// Held as the failing URL, not a flag, so a new `image` retries on its own.
	let failed = $state<string | null>(null);
	const src = $derived(apiUser || (image !== null && image === failed) ? null : image);
	const initials = $derived(initialsOf(name));
	const tinted = $derived(color === 'auto' && !apiUser && !src && initials.length > 0);
</script>

<!--
	A person, as a round avatar.

	The initials fall out of the name in core (`initialsOf`) so React and Svelte cannot
	drift. An avatar never renders blank: an image that fails to load falls back to the
	initials, and with no name at all it is still a muted circle. An API user is a script
	account rather than a person, so the circle holds a bot glyph instead of a picture or
	initials and the tooltip says so.
-->
<span
	bind:this={ref}
	data-slot="user-avatar"
	data-inactive={inactive ? 'true' : undefined}
	data-api-user={apiUser ? 'true' : undefined}
	title={apiUser ? `${name} (API user)` : name}
	class={cn('relative inline-flex shrink-0 align-middle', BOX[size], className)}
	{...rest}
>
	<span
		class={cn(
			'bg-muted text-muted-foreground ring-border flex size-full items-center justify-center overflow-hidden rounded-full font-medium ring-1 select-none',
			apiUser && 'bg-secondary text-secondary-foreground',
			tinted && TINT,
			inactive && 'opacity-50 grayscale'
		)}
		style={tinted ? `--sg-hue: ${nameHue(name)}` : undefined}
	>
		{#if apiUser}
			<Bot aria-hidden="true" class={LEAF_GLYPH[size]} />
			<span class="sr-only">{name}</span>
		{:else if src}
			<img
				{src}
				alt={name}
				loading="lazy"
				decoding="async"
				onerror={() => (failed = src)}
				class="size-full object-cover"
			/>
		{:else}
			<span aria-hidden="true">{initials}</span>
			<span class="sr-only">{name}</span>
		{/if}
	</span>
</span>
