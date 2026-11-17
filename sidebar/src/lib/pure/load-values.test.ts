import { describe, expect, it } from 'vitest';
import type { EntityRow } from 'sg-widgets-core';
import { LOAD_NODE, NONE, VERSION_FIELDS, loadValues } from './load-values';

const row = (relationships: EntityRow['relationships']): EntityRow => ({
	type: 'Version',
	id: 6012,
	attributes: { code: 'sh010_comp_v003' },
	relationships
});

describe('loadValues', () => {
	it('pins the Version and names its project, link and task as SG Load lists them', () => {
		const values = loadValues(
			row({
				project: { data: { type: 'Project', id: 70, name: 'Demo: Animation' } },
				entity: { data: { type: 'Shot', id: 1180, name: 'sh010' } },
				sg_task: { data: { type: 'Task', id: 5541, name: 'Comp' } }
			})
		);
		expect(values).toEqual({
			project: 'Demo: Animation',
			link: 'sh010 (Shot)',
			task: 'Comp',
			pin_version_id: 6012
		});
	});

	it('writes the visible no-value for a Version with no link and no task', () => {
		const values = loadValues(
			row({
				project: { data: { type: 'Project', id: 70, name: 'Demo: Animation' } },
				entity: { data: null },
				sg_task: { data: null }
			})
		);
		expect(values.link).toBe(NONE);
		expect(values.task).toBe(NONE);
		expect(values.pin_version_id).toBe(6012);
	});

	it('reads each relationship it needs from the fields the sidebar asks for', () => {
		for (const field of ['project', 'entity', 'sg_task']) expect(VERSION_FIELDS).toContain(field);
	});

	it('names the node class ComfyUI registers', () => {
		expect(LOAD_NODE).toBe('SGLoadVersion');
	});
});
