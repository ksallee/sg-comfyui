/**
 * The binding between a collection and the source behind it.
 *
 * The table, the grid and the grouped list each hold a source, follow its
 * snapshot, load it when it is idle, keep its mode on the `paging` prop and
 * mirror its sort and its filter out as two-way props. That is one model, so it
 * lives here and each widget keeps only what it draws.
 */
import { untrack } from 'svelte';
import type { EntitySource, PagingMode, SortSpec, SourceFilters } from 'sg-widgets-core';
import { sameFilters, sameSort, sourceModeFor } from 'sg-widgets-core';

/** The value a source publishes, as the template reads it. */
export type SourceSnapshot = ReturnType<EntitySource['snapshot']>;

/** One side of a two-way prop: what the caller holds, and where a change goes. */
export interface Mirror<T> {
	get: () => T | undefined;
	set: (value: T) => void;
}

export interface CollectionSourceOptions {
	source: () => EntitySource;
	/** How the set is walked. The source follows it rather than the other way round. */
	paging: () => PagingMode;
	sort?: Mirror<SortSpec[]>;
	filters?: Mirror<SourceFilters>;
}

export interface CollectionSource {
	/** The last snapshot the source published. */
	readonly snapshot: SourceSnapshot;
	/** Read the page that failed again: the one a pager is on, or the one that was appended. */
	retry: () => void;
}

export function bindSource(options: CollectionSourceOptions): CollectionSource {
	const { source, paging, sort, filters } = options;

	// The source is the store; the snapshot is the value a template reads.
	let snapshot = $state(untrack(source).snapshot());
	$effect(() => source().subscribe(() => (snapshot = source().snapshot())));
	$effect(() => {
		if (source().status === 'idle') void source().load();
	});
	$effect(() => {
		// Setting a mode the source already holds is a no-op.
		void source().setMode(sourceModeFor(paging()));
	});

	/*
	 * Two-way state.
	 *
	 * Each pair is one effect out of the source and one into it, each reading the
	 * other side untracked, so a change travels once and the two never write to
	 * each other.
	 */
	if (sort) {
		$effect(() => {
			const wanted = sort.get();
			if (wanted === undefined || sameSort(wanted, untrack(() => snapshot.sort))) return;
			void source().setSort([...wanted]);
		});
		$effect(() => {
			const current = snapshot.sort;
			if (sameSort(current, untrack(() => sort.get() ?? []))) return;
			sort.set([...current]);
		});
	}

	if (filters) {
		$effect(() => {
			const wanted = filters.get();
			if (wanted === undefined || sameFilters(wanted, untrack(() => snapshot.filters))) return;
			void source().setFilters(wanted);
		});
		$effect(() => {
			const current = snapshot.filters;
			if (sameFilters(current, untrack(() => filters.get() ?? null))) return;
			filters.set(current);
		});
	}

	return {
		get snapshot() {
			return snapshot;
		},
		retry() {
			const held = source();
			if (paging() === 'pages') void held.setPage(snapshot.page);
			else void held.loadMore();
		}
	};
}
