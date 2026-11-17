import { describe, expect, it } from 'vitest';
import { startProject } from './start-project';

const ITEMS = [
	{ id: 70, label: 'Kids Room' },
	{ id: 122, label: 'sg-comfyui Sandbox' }
];

describe('startProject', () => {
	it('opens on the project picked last', () => {
		expect(startProject(ITEMS, 122, 70)).toEqual({ type: 'Project', id: 122, name: 'sg-comfyui Sandbox' });
	});

	it('falls back to the profile’s default when the saved project is gone', () => {
		expect(startProject(ITEMS, 999, 70)).toEqual({ type: 'Project', id: 70, name: 'Kids Room' });
	});

	it('falls back to the first project when nothing names one', () => {
		expect(startProject(ITEMS, 0, 0)).toEqual({ type: 'Project', id: 70, name: 'Kids Room' });
	});

	it('is null on a site with no project', () => {
		expect(startProject([], 122, 70)).toBeNull();
	});
});
