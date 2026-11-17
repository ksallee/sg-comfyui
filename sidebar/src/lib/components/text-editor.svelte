<script lang="ts" module>
	import type { ControlSize } from '$lib/components/control-classes.js';

	export type TextEditorSize = ControlSize;
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import type { FieldSchema } from 'sg-widgets-core';
	import { parseTextInput } from 'sg-widgets-core';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import type { WithElementRef } from '$lib/utils.js';
	import { CONTROL_BOX, CONTROL_PAD } from '$lib/components/control-classes.js';
	import ValueEditor from '$lib/components/value-editor.svelte';
	import { createValueSession } from '$lib/components/value-editor.svelte.js';

	type Props = WithElementRef<Omit<HTMLAttributes<HTMLDivElement>, 'oninput'>, HTMLDivElement> & {
		/** The stored string, or null. There is no empty string in the store (field_types/text). */
		value?: string | null;
		onValueChange?: (value: string | null) => void;
		/** The field schema, for the label and the placeholder. */
		field?: Pick<FieldSchema, 'displayName' | 'mandatory'> | null;
		/** A textarea instead of a single-line input. Newlines survive a one-line field either way. */
		multiline?: boolean;
		rows?: number;
		size?: TextEditorSize;
		disabled?: boolean;
		readonly?: boolean;
		/** Forced invalid state. A failed parse sets it on its own. */
		invalid?: boolean;
		/** A message from the caller, shown in place of the parse error. */
		error?: string | null;
		onErrorChange?: (error: string | null) => void;
		placeholder?: string;
		/** Renders the message. Default is a small destructive line under the control. */
		errorMessage?: Snippet<[string]>;
	};

	let {
		value = $bindable(null),
		onValueChange,
		field = null,
		multiline = false,
		rows = 3,
		size = 'md',
		disabled = false,
		readonly = false,
		invalid = false,
		error = null,
		onErrorChange,
		placeholder,
		errorMessage,
		class: className,
		ref = $bindable(null),
		...rest
	}: Props = $props();

	const session = createValueSession<string | null, string>({
		value: () => value,
		format: (stored) => stored ?? '',
		parse: parseTextInput,
		onValueChange: (next) => {
			value = next;
			onValueChange?.(next);
		},
		onErrorChange: (next) => onErrorChange?.(next),
		error: () => error,
		invalid: () => invalid,
		// A newline is what Enter means in a textarea.
		commitOnEnter: () => !multiline
	});
</script>

<!--
	A `text` field.

	Both ends of the value are stripped on write and an empty string is stored as null,
	so clearing the input and clearing the field are the same act; there is no "set but
	blank" state to round-trip (field_types/text).
-->
<ValueEditor
	bind:ref
	slotName="text-editor"
	{size}
	message={session.message}
	{errorMessage}
	class={className}
	{...rest}
>
	{#if multiline}
		<Textarea
			bind:value={session.draft}
			{rows}
			{disabled}
			{readonly}
			{placeholder}
			class={CONTROL_PAD[size]}
			aria-invalid={session.invalid}
			aria-label={field?.displayName}
			aria-required={field?.mandatory}
			onfocus={session.onfocus}
			onblur={session.onblur}
			onkeydown={session.onkeydown}
		/>
	{:else}
		<Input
			bind:value={session.draft}
			type="text"
			{disabled}
			{readonly}
			{placeholder}
			class={CONTROL_BOX[size]}
			aria-invalid={session.invalid}
			aria-label={field?.displayName}
			aria-required={field?.mandatory}
			onfocus={session.onfocus}
			onblur={session.onblur}
			onkeydown={session.onkeydown}
		/>
	{/if}
</ValueEditor>
