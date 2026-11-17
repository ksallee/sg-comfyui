<script lang="ts" module>
	import type { ControlSize } from '$lib/components/control-classes.js';

	export type CheckboxEditorSize = ControlSize;

	/** The switch primitive carries two sizes; the third reuses the larger one. */
	const SWITCH: Record<CheckboxEditorSize, 'sm' | 'default'> = {
		sm: 'sm',
		md: 'default',
		lg: 'default'
	};
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import type { FieldSchema } from 'sg-widgets-core';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { cn, type WithElementRef } from '$lib/utils.js';
	import { CONTROL_HEIGHT } from '$lib/components/control-classes.js';
	import FieldError from '$lib/components/field-error.svelte';

	type Props = WithElementRef<HTMLAttributes<HTMLDivElement>, HTMLDivElement> & {
		/** Two-state and never null: an untouched row already reads false (field_types/checkbox). */
		value?: boolean;
		onValueChange?: (value: boolean) => void;
		field?: Pick<FieldSchema, 'displayName' | 'mandatory'> | null;
		size?: CheckboxEditorSize;
		disabled?: boolean;
		readonly?: boolean;
		invalid?: boolean;
		/** A message from the caller. The switch has nothing of its own to fail on. */
		error?: string | null;
		onErrorChange?: (error: string | null) => void;
		placeholder?: string;
		/** The two words shown beside the switch. */
		labels?: { on: string; off: string };
		errorMessage?: Snippet<[string]>;
	};

	let {
		value = $bindable(false),
		onValueChange,
		field = null,
		size = 'md',
		disabled = false,
		readonly = false,
		invalid = false,
		error = null,
		onErrorChange,
		placeholder,
		labels = { on: 'Yes', off: 'No' },
		errorMessage,
		class: className,
		ref = $bindable(null),
		...rest
	}: Props = $props();

	const checked = $derived(value === true);
	const label = $derived(checked ? labels.on : labels.off);

	function toggle(next: boolean): void {
		// `false` is the only off state: null is unwritable on this type (field_types/checkbox).
		if (readonly || disabled) return;
		value = next;
		onErrorChange?.(null);
		onValueChange?.(next);
	}
</script>

<!--
	A `checkbox` field.

	The type is two-state and never null: a row that was never touched already reads
	false, a written null is a 400, and `false` is the only off state there is
	(field_types/checkbox). So this control has no empty state and no clear affordance.
-->
<div
	bind:this={ref}
	data-slot="checkbox-editor"
	data-size={size}
	class={cn('flex w-full min-w-0 flex-col gap-2', className)}
	{...rest}
>
	<div class={cn('flex w-full min-w-0 items-center gap-2', CONTROL_HEIGHT[size])}>
		<!-- Disabled wins over readonly, so a control that is both still reads inert. -->
		<Switch
			size={SWITCH[size]}
			{checked}
			disabled={disabled || readonly}
			aria-readonly={readonly}
			aria-invalid={invalid}
			aria-label={field?.displayName ?? placeholder ?? label}
			onCheckedChange={toggle}
			class={readonly && !disabled ? 'data-disabled:cursor-default data-disabled:opacity-100' : undefined}
		/>
		<span aria-hidden="true" class="truncate text-sm select-none">{label}</span>
	</div>
	<FieldError message={error} {errorMessage} />
</div>
