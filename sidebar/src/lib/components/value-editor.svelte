<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import { cn, type WithElementRef } from '$lib/utils.js';
	import type { ControlSize } from '$lib/components/control-classes.js';
	import FieldError from '$lib/components/field-error.svelte';
	import { VALUE_EDITOR_ROOT } from '$lib/components/value-editor.svelte.js';

	type Props = WithElementRef<HTMLAttributes<HTMLDivElement>, HTMLDivElement> & {
		/** The editor's own `data-slot` name. */
		slotName: string;
		size?: ControlSize;
		/** The row form: the control takes the width of its value. */
		inline?: boolean;
		/** The message under the control, or null when there is nothing to say. */
		message?: string | null;
		errorMessage?: Snippet<[string]>;
		/** The control and whatever sits beside or under it. */
		children?: Snippet;
	};

	let {
		slotName,
		size = 'md',
		inline = false,
		message = null,
		errorMessage,
		children,
		class: className,
		ref = $bindable(null),
		...rest
	}: Props = $props();
</script>

<!--
	The box a value editor stands in: the control and its extras, then the error
	line. The session those controls run on is `value-editor.svelte.ts`.
-->
<div
	bind:this={ref}
	data-slot={slotName}
	data-size={size}
	data-inline={inline ? 'true' : undefined}
	class={cn(VALUE_EDITOR_ROOT, inline && 'w-fit', className)}
	{...rest}
>
	{@render children?.()}
	<FieldError {message} {errorMessage} />
</div>
