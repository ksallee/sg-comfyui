/**
 * The Versions a Version was generated from, and theirs, as a tree.
 *
 * A dotted path through a multi-entity field reads back nothing (probe 016), so the tree is read
 * one level per request, with `id in [...]` (probe 017).
 */
import type { EntityRef, EntityRow } from 'sg-widgets-core';

export type LineageNode = {
	row: EntityRow;
	/** The Versions this one was generated from, in the order the field lists them. */
	parents: LineageNode[];
	/** Already in the tree. Its own sources are listed where it first appears. */
	repeat: boolean;
	/** Has sources below the depth limit. They are not read. */
	more: boolean;
	/** Not readable: retired, or out of the reader's reach. Named from the link. */
	stub: boolean;
};

/** Reads Versions by id. A row it cannot read is left out of the answer. */
export type ReadMany = (ids: number[]) => Promise<EntityRow[]>;

/** Levels read below the Version, by default. */
export const LINEAGE_DEPTH = 4;

function sources(row: EntityRow, field: string): EntityRef[] {
	const data = row.relationships[field]?.data;
	return Array.isArray(data) ? data : data ? [data] : [];
}

function node(row: EntityRow, flags: Partial<LineageNode> = {}): LineageNode {
	return { row, parents: [], repeat: false, more: false, stub: false, ...flags };
}

function stubRow(ref: EntityRef): EntityRow {
	return { type: ref.type, id: ref.id, attributes: { code: ref.name ?? String(ref.id) }, relationships: {} };
}

export async function readLineage(
	root: EntityRow,
	field: string,
	readMany: ReadMany,
	depth = LINEAGE_DEPTH
): Promise<LineageNode> {
	const top = node(root);
	const known = new Map<number, EntityRow>([[root.id, root]]);
	let level = [top];

	for (let d = 0; d < depth && level.length; d++) {
		const wanted = [...new Set(level.flatMap((n) => sources(n.row, field).map((s) => s.id)))].filter(
			(id) => !known.has(id)
		);
		const read = new Map((wanted.length ? await readMany(wanted) : []).map((r) => [r.id, r]));
		const next: LineageNode[] = [];
		for (const n of level) {
			for (const ref of sources(n.row, field)) {
				const seen = known.get(ref.id);
				if (seen) {
					n.parents.push(node(seen, { repeat: true }));
					continue;
				}
				const row = read.get(ref.id);
				if (!row) {
					known.set(ref.id, stubRow(ref));
					n.parents.push(node(stubRow(ref), { stub: true }));
					continue;
				}
				known.set(row.id, row);
				const child = node(row);
				n.parents.push(child);
				next.push(child);
			}
		}
		level = next;
	}

	for (const n of level) {
		n.more = sources(n.row, field).some((s) => !known.has(s.id));
	}
	return top;
}
