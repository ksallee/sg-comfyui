/**
 * The Versions the sidebar lists: one project, the filter bar's conditions, and the search words.
 *
 * Each word is a `contains` on `code`, so `sh010 comp` finds `sh010_comp_v003`.
 */
import { condition, group, isEmptyFilter, type EntityRef, type FilterGroup } from 'sg-widgets-core';

export function versionFilter(project: EntityRef, bar: FilterGroup, text: string): FilterGroup {
	const words = text.split(/\s+/).filter(Boolean);
	return group('and', [
		condition('project', 'is', { type: project.type, id: project.id }),
		...(isEmptyFilter(bar) ? [] : [bar]),
		...words.map((word) => condition('code', 'contains', word))
	]);
}
