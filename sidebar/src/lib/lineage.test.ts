import { describe, expect, it } from 'vitest';
import type { EntityRow } from 'sg-widgets-core';
import { readLineage, type LineageNode } from './lineage';

const FIELD = 'sg_ai_generated_from';

function version(id: number, from: number[] = []): EntityRow {
	return {
		type: 'Version',
		id,
		attributes: { code: `v${id}` },
		relationships: { [FIELD]: { data: from.map((f) => ({ type: 'Version', id: f, name: `v${f}` })) } }
	};
}

/** A site of Versions by id, and the id lists each read asked for. */
function site(rows: EntityRow[]) {
	const byId = new Map(rows.map((r) => [r.id, r]));
	const asked: number[][] = [];
	const readMany = async (ids: number[]) => {
		asked.push([...ids]);
		return ids.flatMap((id) => (byId.has(id) ? [byId.get(id)!] : []));
	};
	return { readMany, asked };
}

/** The tree as `id` strings, `*` for a repeat, `+` for a branch cut at the depth limit, `?` for a stub. */
function shape(node: LineageNode): unknown {
	const mark = node.repeat ? '*' : node.more ? '+' : node.stub ? '?' : '';
	const label = `${node.row.id}${mark}`;
	return node.parents.length ? { [label]: node.parents.map(shape) } : label;
}

describe('readLineage', () => {
	it('reads one level per request, in the order the field lists the sources', async () => {
		const { readMany, asked } = site([version(2, [4]), version(3), version(4)]);
		const tree = await readLineage(version(1, [2, 3]), FIELD, readMany);
		expect(shape(tree)).toEqual({ '1': [{ '2': ['4'] }, '3'] });
		expect(asked).toEqual([[2, 3], [4]]);
	});

	it('marks a Version already in the tree and does not read it again', async () => {
		const { readMany, asked } = site([version(2, [4]), version(3, [4]), version(4)]);
		const tree = await readLineage(version(1, [2, 3]), FIELD, readMany);
		expect(shape(tree)).toEqual({ '1': [{ '2': ['4'] }, { '3': ['4*'] }] });
		expect(asked).toEqual([[2, 3], [4]]);
	});

	it('stops at a cycle', async () => {
		const { readMany } = site([version(2, [1])]);
		const tree = await readLineage(version(1, [2]), FIELD, readMany);
		expect(shape(tree)).toEqual({ '1': [{ '2': ['1*'] }] });
	});

	it('cuts a branch at the depth limit and says there is more', async () => {
		const { readMany, asked } = site([version(2, [3]), version(3, [4]), version(4)]);
		const tree = await readLineage(version(1, [2]), FIELD, readMany, 2);
		expect(shape(tree)).toEqual({ '1': [{ '2': ['3+'] }] });
		expect(asked).toEqual([[2], [3]]);
	});

	it('keeps a source it cannot read, named from the link', async () => {
		const { readMany } = site([]);
		const tree = await readLineage(version(1, [9]), FIELD, readMany);
		expect(shape(tree)).toEqual({ '1': ['9?'] });
		expect(tree.parents[0]!.row.attributes.code).toBe('v9');
	});

	it('reads nothing for a Version generated from nothing', async () => {
		const { readMany, asked } = site([]);
		const tree = await readLineage(version(1), FIELD, readMany);
		expect(shape(tree)).toBe('1');
		expect(asked).toEqual([]);
	});
});
