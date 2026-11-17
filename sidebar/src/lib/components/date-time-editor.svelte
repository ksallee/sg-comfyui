<script lang="ts" module>
	import type { DateValue } from '@internationalized/date';
	import type { ControlSize } from '$lib/components/control-classes.js';
	import { fromCalendarDate, toCalendarDate } from '$lib/components/editor-calendar.js';

	export type DateTimeEditorSize = ControlSize;

	/** The two halves of an instant, as the popover holds them. */
	interface InstantDraft {
		date: string;
		time: string;
	}
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import type { FieldSchema } from 'sg-widgets-core';
	import { fromApiDateTime, timeZoneName, toApiDateTime } from 'sg-widgets-core';
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
		/** The stored instant, UTC `YYYY-MM-DDTHH:MM:SSZ` at second resolution (field_types/date_time). */
		value?: string | null;
		onValueChange?: (value: string | null) => void;
		field?: Pick<FieldSchema, 'displayName' | 'mandatory'> | null;
		/** IANA zone the typed wall-clock time is read in. Defaults to the runtime's. */
		timeZone?: string;
		/** Name the zone under the button. */
		hint?: boolean;
		/** The row form: the button takes the width of its value and the zone line goes. */
		inline?: boolean;
		/** Seconds in the time input. The store keeps them; most fields do not need them. */
		showSeconds?: boolean;
		size?: DateTimeEditorSize;
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
		timeZone,
		hint = true,
		inline = false,
		showSeconds = false,
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

	const zoneOptions = $derived(timeZone === undefined ? {} : { timeZone });
	const zone = $derived(timeZoneName(timeZone));

	let dateInput = $state<HTMLInputElement | null>(null);

	function setOpen(next: boolean): void {
		const wanted = readonly || disabled ? false : next;
		if (wanted === open) return;
		open = wanted;
		onOpenChange?.(open);
	}

	const session = createValueSession<string | null, InstantDraft>({
		value: () => value,
		format: (stored) => {
			const local = fromApiDateTime(stored, zoneOptions);
			return {
				date: local?.date ?? '',
				time: local === null ? '' : showSeconds ? local.timeWithSeconds : local.time
			};
		},
		parse: (draft) => toApiDateTime(draft.date, draft.time, zoneOptions),
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

	const day = $derived(toCalendarDate(session.draft.date));
	// The button reads the stored instant, so it answers a commit and never a draft.
	const label = $derived.by(() => {
		const local = fromApiDateTime(value, zoneOptions);
		if (local === null) return null;
		return `${local.date} ${showSeconds ? local.timeWithSeconds : local.time}`;
	});

	// A picked day leaves the popover open: the time is the other half of the value.
	function pick(picked: DateValue | undefined): void {
		session.commit({ ...session.draft, date: fromCalendarDate(picked) });
	}
</script>

<!--
	A `date_time` field.

	The store is UTC `YYYY-MM-DDTHH:MM:SSZ`: a written offset is normalised away and a
	zoneless string is taken as UTC, not as site-local, so the wall-clock time typed
	here is converted before it is emitted and converted back to show
	(field_types/date_time). The zone that conversion uses is named under the button.

	One anatomy everywhere: a button carrying the stored instant, over a popover holding
	the typed day, the calendar and the time. `inline` only sizes the button to its value
	and drops the zone line.
-->
<ValueEditor
	bind:ref
	slotName="date-time-editor"
	{size}
	{inline}
	message={session.message}
	{errorMessage}
	class={className}
	{...rest}
>
	<Popover.Root bind:open={() => open, setOpen}>
		<Popover.Trigger
			data-slot="date-time-editor-trigger"
			aria-label={field?.displayName ?? 'Pick a date and time'}
			aria-invalid={session.invalid}
			aria-disabled={disabled ? 'true' : undefined}
			data-readonly={readonly ? 'true' : undefined}
			{disabled}
			title={value ?? undefined}
			class={cn(
				buttonVariants({ variant: 'outline' }),
				'w-full justify-start gap-1.5 font-normal tabular-nums',
				CONTROL_BOX[size],
				!label && 'text-muted-foreground'
			)}
		>
			<CalendarIcon aria-hidden="true" class={cn(CONTROL_GLYPH[size], 'shrink-0')} />
			<span class="truncate">{label ?? placeholder}</span>
		</Popover.Trigger>
		<Popover.Content
			strategy="fixed"
			align="start"
			class="flex w-auto flex-col gap-3 p-3"
			onOpenAutoFocus={(event) => {
				event.preventDefault();
				dateInput?.focus({ preventScroll: true });
			}}
		>
			<Input
				bind:ref={dateInput}
				bind:value={session.draft.date}
				type="text"
				data-slot="date-time-editor-date"
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
			<Input
				bind:value={session.draft.time}
				type="time"
				data-slot="date-time-editor-time"
				step={showSeconds ? 1 : undefined}
				{disabled}
				{readonly}
				class={cn('tabular-nums', CONTROL_BOX[size])}
				aria-invalid={session.invalid}
				aria-label="Time"
				onfocus={session.onfocus}
				onblur={session.onblur}
				onkeydown={session.onkeydown}
			/>
		</Popover.Content>
	</Popover.Root>
	{#if hint && !inline}
		<p data-slot="date-time-editor-zone" class="text-muted-foreground truncate text-xs">
			Local time in {zone}, stored as UTC.
		</p>
	{/if}
</ValueEditor>
