/**
 * What an SG Load node is set to when a Version is dragged or added from the sidebar.
 *
 * The node is pinned to the Version by id. Project, link and task are filled in with the labels
 * SG Load's own pickers list, so setting `pin_version_id` to 0 loads the newest Version of that
 * task.
 */
import type { EntityRef, EntityRow } from 'sg-widgets-core';

/** The node class `NODE_CLASS_MAPPINGS` registers. */
export const LOAD_NODE = 'SGLoadVersion';

/** SG Load's visible "no value". */
export const NONE = '(none)';

/** The Version fields the sidebar reads: the tile's, then the node's. */
export const VERSION_FIELDS = [
	'code',
	'image',
	'sg_status_list',
	'user',
	'created_at',
	'project',
	'entity',
	'sg_task'
];

/** SG Load's widget values by name. */
export type LoadValues = {
	project: string;
	link: string;
	task: string;
	pin_version_id: number;
};

function ref(row: EntityRow, field: string): EntityRef | null {
	const data = row.relationships[field]?.data;
	return data && !Array.isArray(data) ? data : null;
}

/** `name (Type)`, the link label SG Load lists (`site.label_for`). */
function linkLabel(link: EntityRef | null): string {
	return link?.name ? `${link.name} (${link.type})` : NONE;
}

export function loadValues(row: EntityRow): LoadValues {
	return {
		project: ref(row, 'project')?.name ?? '',
		link: linkLabel(ref(row, 'entity')),
		task: ref(row, 'sg_task')?.name ?? NONE,
		pin_version_id: row.id
	};
}
