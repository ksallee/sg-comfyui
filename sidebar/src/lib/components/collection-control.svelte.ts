/**
 * The state and behaviour every collection shares.
 *
 * The table, the grid and the grouped list draw three different things over one
 * model: a source read through `collection-source`, a selection, a keyboard
 * cursor that skips disabled rows and asks for the next page at the end, a
 * virtualiser over the lines of that layout, and the scroll and load-more
 * triggers of the `paging` prop. That model lives here; a widget supplies its
 * layout and draws the markup.
 *
 * It is two calls, because a layout's lines are derived from the rows: the
 * control answers the source, the widget shapes its own lines out of the rows,
 * then the body wires the virtualiser and the cursor over them. A layout says
 * three things about its markup: how many lines it draws, which line a row sits
 * on, and which element takes the cursor.
 */
import { untrack } from 'svelte';
import type {
	EntityRef,
	EntityRow,
	SelectionAnchor,
	EntitySource,
	PagingMode,
	RowDisabledFn,
	RowIdFn,
	SortSpec,
	SourceFilters
} from 'sg-widgets-core';
import {
	collectionBottom,
	collectionView,
	describePaging,
	extendByStep,
	extendRange,
	firstEnabledIndex,
	gestureOf,
	hasFailedPage,
	loadsOnArrowDown,
	rowIdOf,
	rowIsDisabled,
	rowKey,
	sameRefs,
	selectableRefs,
	selectionState,
	setRefs,
	shouldLoadNext,
	stateLine,
	toggleRow
} from 'sg-widgets-core';
import { Virtualizer, elementScroll, observeElementOffset, observeElementRect } from '@tanstack/virtual-core';
import { bindSource, type Mirror, type SourceSnapshot } from '$lib/components/collection-source.svelte.js';

export type { Mirror, SourceSnapshot };

/** The root box and the regions beside it, worn by every collection. */
export const COLLECTION_ROOT = 'flex w-full min-w-0 flex-col gap-2';
export const COLLECTION_REGION = 'flex w-full min-w-0 flex-wrap items-center gap-2';

export interface CollectionControlOptions {
	source: () => EntitySource;
	/** How the set is walked. The source follows it rather than the other way round. */
	paging: () => PagingMode;
	sort?: Mirror<SortSpec[]>;
	filters?: Mirror<SourceFilters>;
	/** The selected rows. Left out where a widget holds its own selection. */
	selection?: Mirror<EntityRef[]>;
	getRowId?: () => RowIdFn | undefined;
	isRowDisabled?: () => RowDisabledFn | undefined;
	loadingLabel?: () => string | undefined;
}

export function createCollectionControl(options: CollectionControlOptions) {
	const { source, paging, selection } = options;

	const bound = bindSource({
		source,
		paging,
		...(options.sort ? { sort: options.sort } : {}),
		...(options.filters ? { filters: options.filters } : {})
	});

	const snapshot = $derived(bound.snapshot);
	const rows = $derived(snapshot.rows);
	const pager = $derived(describePaging(snapshot));
	/** A page that failed under rows already loaded, which the bottom block reports. */
	const pageError = $derived(hasFailedPage(snapshot));
	const loadingText = $derived(stateLine('loading', { loadingLabel: options.loadingLabel?.() }));

	const rowId = (row: EntityRow): string => rowIdOf(row, options.getRowId?.());
	const rowDisabled = (row: EntityRow): boolean => rowIsDisabled(row, options.isRowDisabled?.());
	const disabledAt = (index: number): boolean => {
		const row = rows[index];
		return row === undefined || rowDisabled(row);
	};

	/** The selection as keys, so a row asks whether it is in it in constant time. */
	const chosenKeys = $derived(new Set((selection?.get() ?? []).map(rowKey)));

	function setSelection(next: EntityRef[]): void {
		if (!selection || sameRefs(next, selection.get() ?? [])) return;
		selection.set(next);
	}

	/** Where the next Shift gesture ranges from. Not state: nothing draws it. */
	let anchor: SelectionAnchor | null = null;
	const indexOf = (row: EntityRow): number => rows.findIndex((entry) => rowKey(entry) === rowKey(row));

	return {
		source,
		paging,
		get snapshot(): SourceSnapshot {
			return snapshot;
		},
		get rows(): EntityRow[] {
			return rows;
		},
		get pager() {
			return pager;
		},
		get pageError(): boolean {
			return pageError;
		},
		get loadingText(): string {
			return loadingText;
		},
		/** Which of the four things the body shows, over the lines the layout drew. */
		view(lines: number) {
			return collectionView(snapshot, lines);
		},
		/** What sits under the last row: a failed page, a page on the way, a row or a sentinel. */
		get bottom() {
			return collectionBottom(snapshot, paging());
		},
		retry: bound.retry,
		rowId,
		rowDisabled,
		disabledAt,

		isSelected(row: EntityRow): boolean {
			return chosenKeys.has(rowKey(row));
		},
		/** Add or drop one row and anchor on it. A disabled row refuses. */
		toggle(row: EntityRow): void {
			if (!selection) return;
			const step = toggleRow(selection.get() ?? [], anchor, rows, indexOf(row), options.isRowDisabled?.());
			anchor = step.anchor;
			setSelection(step.selection);
		},
		/** A press on a row: Shift ranges from the anchor, anything else toggles. */
		press(row: EntityRow, event: { shiftKey?: boolean; metaKey?: boolean; ctrlKey?: boolean }): void {
			if (!selection) return;
			const range = gestureOf(event) === 'range' ? extendRange : toggleRow;
			const step = range(selection.get() ?? [], anchor, rows, indexOf(row), options.isRowDisabled?.());
			anchor = step.anchor;
			setSelection(step.selection);
		},
		/** Shift+arrow: the cursor moved from one loaded row to another, carrying the range. */
		extend(from: number, to: number): void {
			if (!selection) return;
			const step = extendByStep(selection.get() ?? [], anchor, rows, from, to, options.isRowDisabled?.());
			anchor = step.anchor;
			setSelection(step.selection);
		},
		/** The tri-state a header checkbox reads. */
		get allSelected() {
			return selectionState(rows, selection?.get() ?? [], options.isRowDisabled?.());
		},
		/** Take or drop every loaded row that is not disabled, keeping picks the loaded rows do not hold. */
		toggleAll(on: boolean): void {
			setSelection(setRefs(selection?.get() ?? [], selectableRefs(rows, options.isRowDisabled?.()), on));
		}
	};
}

export type CollectionControl = ReturnType<typeof createCollectionControl>;

/**
 * What a layout tells the base about its own markup.
 *
 * `lines` is what the virtualiser walks: rows for a table, lines of tiles for a
 * grid, headers and rows as one stream for a grouped list. The two maps carry a
 * row index to and from a line, so the base can scroll to a row and say which
 * row the viewport ends on without knowing what a line holds.
 */
export interface CollectionLayout {
	/** Lines the virtualiser walks. */
	lines: () => number;
	/** What `virtualizeAfter` is measured against: rows, where a line holds several. */
	measured: () => number;
	/** A line's height in pixels, before it is drawn. */
	lineHeight: () => number;
	/** Lines drawn outside the viewport. */
	overscan: number;
	/** Rows above which the body is virtualised. */
	virtualizeAfter: () => number;
	/** The line a row sits on. -1 when the row is not drawn. */
	lineOfRow: (index: number, row: EntityRow, id: string) => number;
	/** The last row the viewport reaches, given the last line it drew. */
	lastRowOfLine: (line: number) => number;
	/** The element the cursor lands on. `extra` is the table's column, if any. */
	cursorTarget: (index: number, row: EntityRow, id: string, extra: string | null) => HTMLElement | null | undefined;
}

/** The window the virtualiser leaves, in lines, with the space above and below it. */
export interface CollectionWindow {
	before: number;
	after: number;
	from: number;
	to: number;
}

/** The virtualiser, the cursor and the scroll trigger over one layout's lines. */
export function bindCollectionBody(control: CollectionControl, layout: CollectionLayout) {
	const { source, paging } = control;

	let scrollEl = $state<HTMLElement | null>(null);
	let sentinel = $state<HTMLElement | null>(null);
	// The virtualizer notifies from inside an effect, so the counter it bumps is written
	// and never read there: `ticks += 1` would make the effect depend on its own write.
	let tickCount = 0;
	let ticks = $state(0);
	const virtualized = $derived(layout.measured() > layout.virtualizeAfter());

	function bump(): void {
		tickCount += 1;
		ticks = tickCount;
	}

	const virtualizer = new Virtualizer<HTMLElement, HTMLElement>({
		count: 0,
		getScrollElement: () => scrollEl,
		estimateSize: () => layout.lineHeight(),
		overscan: layout.overscan,
		observeElementRect,
		observeElementOffset,
		scrollToFn: elementScroll,
		onChange: bump
	});

	$effect(() => virtualizer._didMount());
	$effect(() => {
		// Read every dependency before the call, so the effect tracks the line count and
		// the height and not the tick the virtualizer's own notification writes.
		const count = virtualized ? layout.lines() : 0;
		const size = layout.lineHeight();
		const element = scrollEl;
		virtualizer.setOptions({
			count,
			getScrollElement: () => element,
			estimateSize: () => size,
			overscan: layout.overscan,
			observeElementRect,
			observeElementOffset,
			scrollToFn: elementScroll,
			onChange: bump
		});
		// The observers attach to whichever element `getScrollElement` now answers; without
		// this the virtualizer keeps the one it had when it mounted, which was none.
		virtualizer._willUpdate();
		virtualizer.measure();
	});

	/** The lines on screen, with the space the ones above and below take. */
	const window_ = $derived.by<CollectionWindow | null>(() => {
		void ticks;
		if (!virtualized) return null;
		const items = virtualizer.getVirtualItems();
		const first = items[0];
		const last = items[items.length - 1];
		if (!first || !last) return { before: 0, after: 0, from: 0, to: -1 };
		return {
			before: first.start,
			after: virtualizer.getTotalSize() - last.end,
			from: first.index,
			to: last.index
		};
	});

	/* the cursor ----------------------------------------------------------- */

	const rows = $derived(control.rows);

	/** The one tab stop of a roving layout, which never lands on a disabled row. */
	let cursor = $state(0);
	const active = $derived(
		rows.length === 0 ? -1 : firstEnabledIndex(rows.length, Math.min(cursor, rows.length - 1), 1, control.disabledAt)
	);

	/** The row a cursor is waiting on, until the page it asked for lands. */
	let wanted = $state<{ index: number; extra: string | null } | null>(null);

	/** Put the cursor on one row, drawing it first where it is outside the window. */
	function focusRow(index: number, extra: string | null = null): void {
		const at = Math.max(0, Math.min(index, rows.length - 1));
		const row = rows[at];
		if (!row) return;
		cursor = at;
		const id = control.rowId(row);
		const put = (): void => {
			const target = layout.cursorTarget(at, row, id, extra);
			if (!target) return;
			target.focus({ preventScroll: true });
			target.scrollIntoView({ block: 'nearest' });
		};
		if (virtualized) {
			const line = layout.lineOfRow(at, row, id);
			if (line >= 0) virtualizer.scrollToIndex(line);
			requestAnimationFrame(put);
		} else put();
	}

	/**
	 * Ask for the next page where the cursor has run past the loaded rows, and hold it
	 * where it is until those rows arrive. False when the step is an ordinary move.
	 */
	function askForPage(index: number, extra: string | null = null): boolean {
		if (!loadsOnArrowDown(control.snapshot, paging(), index)) return false;
		wanted = { index, extra };
		void source().loadMore();
		return true;
	}

	$effect(() => {
		const held = wanted;
		if (!held) return;
		if (control.snapshot.status === 'error') wanted = null;
		else if (rows.length > held.index) {
			wanted = null;
			untrack(() => focusRow(held.index, held.extra));
		}
	});

	/* scroll paging -------------------------------------------------------- */

	$effect(() => {
		// The virtualiser's own range says which line the viewport ends on, and the layout
		// says which row that is: a group header only ever makes the scroller ask later.
		void ticks;
		if (!virtualized || paging() !== 'scroll') return;
		const items = virtualizer.getVirtualItems();
		const last = items[items.length - 1];
		if (!last) return;
		if (shouldLoadNext(control.snapshot, { paging: paging(), lastVisible: layout.lastRowOfLine(last.index) })) {
			void source().loadMore();
		}
	});

	$effect(() => {
		// A body short enough not to be virtualised has no range to read, so the last row
		// carries a sentinel instead.
		const root = scrollEl;
		const target = sentinel;
		if (!root || !target || paging() !== 'scroll') return;
		const observer = new IntersectionObserver(
			(entries) => {
				if (!entries.some((entry) => entry.isIntersecting)) return;
				if (shouldLoadNext(control.snapshot, { paging: paging(), lastVisible: rows.length - 1 })) {
					void source().loadMore();
				}
			},
			{ root, rootMargin: '200px' }
		);
		observer.observe(target);
		return () => observer.disconnect();
	});

	return {
		get virtualized(): boolean {
			return virtualized;
		},
		get window(): CollectionWindow | null {
			return window_;
		},
		get active(): number {
			return active;
		},
		setCursor(index: number): void {
			cursor = index;
		},
		focusRow,
		askForPage,
		/** The scrolling body. The virtualiser and the sentinel both watch it. */
		setScroller(element: HTMLElement | null): void {
			scrollEl = element;
		},
		/** The row a short body hangs its scroll trigger on. */
		setSentinel(element: HTMLElement | null): void {
			sentinel = element;
		}
	};
}

export type CollectionBody = ReturnType<typeof bindCollectionBody>;
