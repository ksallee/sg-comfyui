import { describe, expect, it } from 'vitest';
import { condition, emptyFilter, group, toApi3Hash } from 'sg-widgets-core';
import { versionFilter } from './version-filter';

const PROJECT = { type: 'Project', id: 70 };

describe('versionFilter', () => {
	it('scopes to the project when nothing else is set', () => {
		expect(toApi3Hash(versionFilter(PROJECT, emptyFilter(), ''))).toEqual(
			toApi3Hash(group('and', [condition('project', 'is', PROJECT)]))
		);
	});

	it('adds one code condition per word of the search', () => {
		expect(toApi3Hash(versionFilter(PROJECT, emptyFilter(), '  sh010  comp '))).toEqual(
			toApi3Hash(
				group('and', [
					condition('project', 'is', PROJECT),
					condition('code', 'contains', 'sh010'),
					condition('code', 'contains', 'comp')
				])
			)
		);
	});

	it('keeps the filter bar as its own group', () => {
		const bar = group('and', [condition('sg_status_list', 'in', ['rev', 'apr'])]);
		expect(toApi3Hash(versionFilter(PROJECT, bar, ''))).toEqual(
			toApi3Hash(group('and', [condition('project', 'is', PROJECT), bar]))
		);
	});
});
