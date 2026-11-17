<script lang="ts" module>
	import type { DateValue } from '@internationalized/date';
	import type { ControlSize } from '$lib/components/control-classes.js';
	import { fromCalendarDate, toCalendarDate } from '$lib/components/editor-calendar.js';

	export type DateEditorSize = ControlSize;
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import type { FieldSchema } from 'sg-widgets-core';
	import { toApiDate } from 'sg-widgets-core';
	import CalendarIcon from '@lucide/svelte/icons/calendar';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import { Calendar } from '$lib/components/ui/calendar/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import { cn, type WithElementRef } from '$lib/utils.js';
	import { CONTROL_BOX, CONTROL_GLYPH } from '$lib/components/control-classes.js';
	import ValueEditor from '$lib/components/value-editor.svelte';
	import { createValueSession } from '$lib/components/value-editor.svelte.js';

	type Props = WithElementRef<HTMLAttributes<HTMLDivElement>, HTMLDivElement> & {
		/** The stored day, exactly `YYYY-MM-DD`, with no time and no zone (field_types/date). */
		value?: string | null;
		onValueChange?: (value: string | null) => void;
		field?: Pick<FieldSchema, 'displayName' | 'mandatory'> | null;
		/** The row form: the button takes the width of its value. */
		inline?: boolean;
		size?: DateEditorSize;
		disabled?: boolean;
		readonly?: boolean;
		invalid?: boolean;
		error?: string | null;
		onErrorChange?: (error: string | null) => void;
		placeholder?: string;
		/** Whether the calendar popover is showing, two-way. */
		open?: boolean;
		onOpenChange?: (open: boolean) => void;
		errorMessage?: Snippet<[string]>;
	};

	let {
		value = $bindable(null),
		onValueChange,
		field = null,
		inline = false,
		size = 'md',
		disabled = false,
		readonly = false,
		invalid = false,
		error = null,
		onErrorChange,
		placeholder = 'YYYY-MM-DD',
		open = $bindable(false),
		onOpenChange,
		errorMessage,
		class: className,
		ref = $bindable(null),
		...rest
	}: Props = $props();

	let dayInput = $state<HTMLInputElement | null>(null);

	function setOpen(next: boolean): void {
		const wanted = readonly || disabled ? false : next;
		if (wanted === open) return;
		open = wanted;
		onOpenChange?.(open);
	}

	const session = createValueSession<string | null, string>({
		value: () => value,
		format: (stored) => stored ?? '',
		parse: toApiDate,
		onValueChange: (next) => {
			value = next;
			onValueChange?.(next);
		},
		onErrorChange: (next) => onErrorChange?.(next),
		error: () => error,
		invalid: () => invalid,
		stopKeys: true,
		onEnter: (committed) => {
			if (!committed) return;
			session.editing = false;
			setOpen(false);
		},
		onEscape: () => {
			session.editing = false;
		}
	});

	const day = $derived(toCalendarDate(value));

	function pick(picked: DateValue | undefined): void {
		session.editing = false;
		setOpen(false);
		session.apply(fromCalendarDate(picked) || null);
	}
</script>

<!--
	A `date` field.

	The value is exactly `YYYY-MM-DD`: no time, no zone, and the API validates the day
	rather than only parsing it, so `2026-02-30` is refused here too. A timestamp is
	never a date on this type (field_types/date).

	One anatomy everywhere: a button carrying the stored day, over a popover holding the
	typed day and the calendar. `inline` only sizes the button to its value.
-->
<ValueEditor
	bind:ref
	slotName="date-editor"
	{size}
	{inline}
	message={session.message}
	{errorMessage}
	class={className}
	{...rest}
>
	<Popover.Root bind:open={() => open, setOpen}>
		<Popover.Trigger
			data-slot="date-editor-trigger"
			aria-label={field?.displayName ?? 'Pick a date'}
			aria-invalid={session.invalid}
			aria-disabled={disabled ? 'true' : undefined}
			data-readonly={readonly ? 'true' : undefined}
			{disabled}
			title={value ?? undefined}
			class={cn(
				buttonVariants({ variant: 'outline' }),
				'w-full justify-start gap-1.5 font-normal tabular-nums',
				CONTROL_BOX[size],
				!value && 'text-muted-foreground'
			)}
		>
			<CalendarIcon aria-hidden="true" class={cn(CONTROL_GLYPH[size], 'shrink-0')} />
			<span class="truncate">{value ?? placeholder}</span>
		</Popover.Trigger>
		<Popover.Content
			strategy="fixed"
			align="start"
			class="flex w-auto flex-col gap-3 p-3"
			onOpenAutoFocus={(event) => {
				event.preventDefault();
				dayInput?.focus({ preventScroll: true });
			}}
		>
			<Input
				bind:ref={dayInput}
				bind:value={session.draft}
				type="text"
				data-slot="date-editor-day"
				{disabled}
				{readonly}
				{placeholder}
				class={cn('tabular-nums', CONTROL_BOX[size])}
				aria-invalid={session.invalid}
				aria-label={field?.displayName ?? 'Date'}
				aria-required={field?.mandatory}
				onfocus={session.onfocus}
				onblur={session.onblur}
				onkeydown={session.onkeydown}
			/>
			<Calendar type="single" class="p-0" value={day} onValueChange={pick} />
		</Popover.Content>
	</Popover.Root>
</ValueEditor>
