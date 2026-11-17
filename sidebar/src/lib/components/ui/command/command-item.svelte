<script lang="ts">
	import { Command as CommandPrimitive } from "bits-ui";
	import CheckIcon from '@lucide/svelte/icons/check';
	import { cn } from "$lib/utils.js";

	let {
		ref = $bindable(null),
		class: className,
		children,
		...restProps
	}: CommandPrimitive.ItemProps = $props();
</script>

<CommandPrimitive.Item
	bind:ref
	data-slot="command-item"
	class={cn(
		"group/command-item relative flex cursor-default items-center gap-2 rounded-sm px-2 py-1.5 has-[[data-slot=picker-row-sub-label]]:py-1 text-sm outline-hidden select-none in-data-[slot=dialog-content]:rounded-lg! data-disabled:pointer-events-none data-disabled:opacity-50 data-highlighted:bg-muted data-highlighted:text-foreground [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4 data-highlighted:*:[svg]:text-foreground",
		className
	)}
	{...restProps}
>
	{#snippet child({ props })}
		<!-- The row under the cursor is `data-highlighted` here as it is on the picker base, so one class string and one query serve both registries. -->
		<div {...props} data-highlighted={props['data-selected'] !== undefined ? '' : undefined}>
			{@render children?.()}
			<CheckIcon
				class="cn-command-item-indicator ml-auto opacity-0 group-has-[[data-slot=command-shortcut]]/command-item:hidden group-data-[checked=true]/command-item:opacity-100"
			/>
		</div>
	{/snippet}
</CommandPrimitive.Item>
