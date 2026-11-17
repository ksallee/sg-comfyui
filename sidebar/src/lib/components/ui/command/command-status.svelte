<script lang="ts">
	import { cn, type WithElementRef } from "$lib/utils.js";
	import type { HTMLAttributes } from "svelte/elements";

	let {
		ref = $bindable(null),
		class: className,
		children,
		...restProps
	}: WithElementRef<HTMLAttributes<HTMLDivElement>> = $props();
</script>

<!-- The list's live region: what a reader hears, beside what the state line shows. -->
<div
	bind:this={ref}
	data-slot="command-status"
	role="status"
	aria-live="polite"
	aria-atomic="true"
	class={cn("sr-only", className)}
	{...restProps}
>
	{@render children?.()}
</div>
