<script lang="ts">
	import { Command as CommandPrimitive } from "bits-ui";
	import { watchOverflow } from "sg-widgets-core";
	import { cn } from "$lib/utils.js";

	let {
		ref = $bindable(null),
		class: className,
		...restProps
	}: CommandPrimitive.ListProps = $props();

	// Bits UI publishes no overflow distances, so the list measures its own and writes
	// the variables the fade reads, which are the ones Base UI writes on the React side.
	$effect(() => watchOverflow(ref));
</script>

<CommandPrimitive.List
	bind:ref
	data-slot="command-list"
	class={cn(
		"no-scrollbar max-h-72 scroll-py-1 outline-none overflow-x-hidden overflow-y-auto",
		"[scrollbar-gutter:stable] [--fade-size:1.5rem] mask-t-from-[calc(100%-min(var(--fade-size),var(--scroll-area-overflow-y-start,0px)))] mask-b-from-[calc(100%-min(var(--fade-size),var(--scroll-area-overflow-y-end,0px)))]",
		className
	)}
	{...restProps}
/>
