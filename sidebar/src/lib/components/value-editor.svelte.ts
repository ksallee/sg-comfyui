/**
 * The session every leaf value editor runs on.
 *
 * Text, number, url, colour, date and date-time differ in what they parse, what
 * they write back into their control, and what sits beside it. Everything else is
 * the same in all six and lives here: the draft, the commit on blur and on Enter,
 * the Escape that restores, the parse error and the message it becomes, and the
 * invalid reading the control wears. An editor supplies a parse and a format for
 * its own type and draws its own control and extras.
 *
 * The checkbox is not one of them: it has no draft, so it writes on the toggle.
 */
import { untrack } from 'svelte';
import type { ParseResult } from 'sg-widgets-core';

/** The root box every value editor wears. */
export const VALUE_EDITOR_ROOT = 'flex w-full min-w-0 flex-col gap-2';

export interface ValueSessionOptions<TValue, TDraft> {
	/** The stored value. */
	value: () => TValue;
	/** The stored value as the draft the control shows. */
	format: (value: TValue) => TDraft;
	/** The draft as a stored value, or the reason it was refused. */
	parse: (draft: TDraft) => ParseResult<TValue>;
	/** Writes a committed value out. Called only when it differs from the stored one. */
	onValueChange?: (value: TValue) => void;
	onErrorChange?: (error: string | null) => void;
	/** A message from the caller, shown in place of the parse error. */
	error?: () => string | null;
	/** Forced invalid state. A failed parse sets it on its own. */
	invalid?: () => boolean;
	/** Whether a value is the stored one and so is not emitted. Default is `Object.is`. */
	same?: (next: TValue, current: TValue) => boolean;
	/** Enter commits. False where a newline is what Enter means. */
	commitOnEnter?: () => boolean;
	/** Stop Enter and Escape going up the tree, for a control drawn in a portal. */
	stopKeys?: boolean;
	/** After Enter, with whether the parse held. */
	onEnter?: (committed: boolean) => void;
	/** After Escape. */
	onEscape?: () => void;
}

export function createValueSession<TValue, TDraft>(options: ValueSessionOptions<TValue, TDraft>) {
	const same = options.same ?? ((next: TValue, current: TValue) => Object.is(next, current));

	let draft = $state<TDraft>(options.format(options.value()));
	let parseError = $state<string | null>(null);
	// The control is uncontrolled while it has focus, so typing is never fought by an
	// incoming value; an outside change lands as soon as the control is left.
	let editing = $state(false);

	// Keyed on the incoming value alone: a commit that clears the focus flag must not
	// re-run this, or a refused draft is overwritten while its message still stands.
	$effect(() => {
		const incoming = options.format(options.value());
		if (!untrack(() => editing)) draft = incoming;
	});

	const message = $derived(options.error?.() ?? parseError);
	const isInvalid = $derived((options.invalid?.() ?? false) || message !== null);

	function clear(): void {
		parseError = null;
		options.onErrorChange?.(null);
	}

	/** Takes a value that needs no parse: a picked colour, a picked day, a step. */
	function apply(next: TValue): void {
		clear();
		draft = options.format(next);
		if (same(next, options.value())) return;
		options.onValueChange?.(next);
	}

	/** Parses the draft and takes it. Answers whether it parsed, so Enter knows. */
	function commit(override?: TDraft): boolean {
		if (override !== undefined) draft = override;
		const result = options.parse(draft);
		if ('error' in result) {
			parseError = result.error;
			options.onErrorChange?.(result.error);
			return false;
		}
		apply(result.value);
		return true;
	}

	/** Back to the stored value, with nothing left to report. */
	function reset(): void {
		draft = options.format(options.value());
		clear();
	}

	return {
		get draft(): TDraft {
			return draft;
		},
		set draft(next: TDraft) {
			draft = next;
		},
		get editing(): boolean {
			return editing;
		},
		set editing(next: boolean) {
			editing = next;
		},
		get message(): string | null {
			return message;
		},
		get invalid(): boolean {
			return isInvalid;
		},
		apply,
		commit,
		reset,
		onfocus(): void {
			editing = true;
		},
		// Losing focus because the control was removed from the page is not a commit.
		onblur(event: FocusEvent): void {
			if (!(event.currentTarget as HTMLElement | null)?.isConnected) return;
			editing = false;
			commit();
		},
		onkeydown(event: KeyboardEvent): void {
			if (event.key !== 'Enter' && event.key !== 'Escape') return;
			// A portalled control replays its keys up the owner's tree, so a key the
			// editor answers is stopped where it is answered.
			if (options.stopKeys) event.stopPropagation();
			if (event.key === 'Enter') {
				if (options.commitOnEnter?.() === false) return;
				const committed = commit();
				options.onEnter?.(committed);
				return;
			}
			reset();
			options.onEscape?.();
		}
	};
}

export type ValueSession<TValue, TDraft> = ReturnType<typeof createValueSession<TValue, TDraft>>;
