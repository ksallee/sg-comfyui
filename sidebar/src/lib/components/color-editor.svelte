<script lang="ts" module>
	import type { ControlSize } from '$lib/components/control-classes.js';

	export type ColorEditorSize = ControlSize;

	/** The swatch is the square of the control beside it. */
	const SWATCH: Record<ColorEditorSize, string> = {
		sm: 'size-8',
		md: 'size-9',
		lg: 'size-10'
	};
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import type { FieldSchema } from 'sg-widgets-core';
	import { COLOR_SENTINEL, colorToHex, parseBgColor, parseColorInput, rgbToCss } from 'sg-widgets-core';
	import { Input } from '$lib/components/ui/input/index.js';
	import { cn, type WithElementRef } from '$lib/utils.js';
	import { CONTROL_BOX } from '$lib/components/control-classes.js';
	import ValueEditor from '$lib/components/value-editor.svelte';
	import { createValueSession } from '$lib/components/value-editor.svelte.js';

	type Props = WithElementRef<Omit<HTMLAttributes<HTMLDivElement>, 'color'>, HTMLDivElement> & {
		/** The stored string: decimal `r,g,b`, or the pipeline-step token (field_types/color). */
		value?: string | null;
		onValueChange?: (value: string | null) => void;
		field?: Pick<FieldSchema, 'displayName' | 'mandatory'> | null;
		size?: ColorEditorSize;
		disabled?: boolean;
		readonly?: boolean;
		invalid?: boolean;
		error?: string | null;
		onErrorChange?: (error: string | null) => void;
		placeholder?: string;
		/** Explain the pipeline-step token under the control. */
		hint?: boolean;
		errorMessage?: Snippet<[string]>;
	};

	let {
		value = $bindable(null),
		onValueChange,
		field = null,
		size = 'md',
		disabled = false,
		readonly = false,
		invalid = false,
		error = null,
		onErrorChange,
		placeholder = '255,128,0',
		hint = true,
		errorMessage,
		class: className,
		ref = $bindable(null),
		...rest
	}: Props = $props();

	const session = createValueSession<string | null, string>({
		value: () => value,
		format: (stored) => stored ?? '',
		parse: parseColorInput,
		onValueChange: (next) => {
			value = next;
			onValueChange?.(next);
		},
		onErrorChange: (next) => onErrorChange?.(next),
		error: () => error,
		invalid: () => invalid
	});

	// The swatch follows the draft, so a typed hex shows its colour before it is committed.
	const preview = $derived(parseColorInput(session.draft));
	const rgb = $derived('error' in preview || preview.value === null ? null : parseBgColor(preview.value));
	const sentinel = $derived(!('error' in preview) && preview.value === COLOR_SENTINEL);

	// The native picker answers in hex; the store wants the decimal triple.
	function pick(event: Event): void {
		const result = parseColorInput((event.currentTarget as HTMLInputElement).value);
		if ('error' in result) return;
		session.apply(result.value);
	}
</script>

<!--
	A `color` field.

	The stored form is decimal `r,g,b` with no spaces and no `#`; hex is rejected on
	write and inside a filter, so a hex code typed here is converted before it is
	emitted. `Task.color` also takes the token `pipeline_step`, which is the only way
	to un-set it: a written null is a 400 (field_types/color).
-->
<ValueEditor
	bind:ref
	slotName="color-editor"
	{size}
	message={session.message}
	{errorMessage}
	class={className}
	{...rest}
>
	<div class="flex w-full min-w-0 items-center gap-2">
		<label
			data-slot="color-editor-swatch"
			title={disabled || readonly ? undefined : 'Pick a colour'}
			style={rgb ? `background-color:${rgbToCss(rgb)}` : undefined}
			class={cn(
				'border-input focus-within:ring-ring focus-within:ring-offset-background relative shrink-0 overflow-hidden rounded-lg border shadow-xs transition-shadow duration-150 focus-within:ring-2 focus-within:ring-offset-2',
				SWATCH[size],
				rgb ? undefined : 'bg-muted',
				disabled || readonly ? 'cursor-default' : 'cursor-pointer'
			)}
		>
			<input
				type="color"
				value={colorToHex(rgb ? `${rgb.r},${rgb.g},${rgb.b}` : null) ?? '#808080'}
				disabled={disabled || readonly}
				aria-label={field?.displayName ? `${field.displayName} colour` : 'Colour'}
				class="absolute inset-0 size-full cursor-[inherit] opacity-0"
				oninput={pick}
			/>
		</label>
		<Input
			bind:value={session.draft}
			type="text"
			{disabled}
			{readonly}
			{placeholder}
			class={cn('font-mono tabular-nums', CONTROL_BOX[size])}
			aria-invalid={session.invalid}
			aria-label={field?.displayName}
			aria-required={field?.mandatory}
			onfocus={session.onfocus}
			onblur={session.onblur}
			onkeydown={session.onkeydown}
		/>
	</div>
	{#if hint && sentinel}
		<p data-slot="color-editor-note" class="text-muted-foreground text-xs">
			Takes the colour of the linked pipeline step.
		</p>
	{/if}
</ValueEditor>
