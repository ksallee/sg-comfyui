/**
 * The second line of a lineage row: the model that made the source, and its link when that is not
 * the opened Version's.
 */
import type { EntityRef, EntityRow } from 'sg-widgets-core';

// The provenance record joins several models with " | " (provenance.py).
const SEPARATOR = /\s*\|\s*/;
const EXTENSION = /\.(safetensors|ckpt|pt|pth|bin|gguf|sft)$/i;

/** The first model without its extension, and `+n` for the others. */
export function shortModel(value: unknown): string {
	const models = String(value ?? '')
		.split(SEPARATOR)
		.map((m) => m.trim())
		.filter(Boolean);
	if (!models.length) return '';
	const first = models[0]!.replace(EXTENSION, '');
	return models.length > 1 ? `${first} +${models.length - 1}` : first;
}

export type LineageInfo = { model: string; elsewhere: string | null };

export function lineageInfo(
	row: EntityRow,
	modelField: string | null,
	openedLink: Pick<EntityRef, 'type' | 'id'> | null
): LineageInfo {
	const data = row.relationships.entity?.data;
	const link = data && !Array.isArray(data) ? data : null;
	const same = link && openedLink && link.type === openedLink.type && link.id === openedLink.id;
	return {
		model: modelField ? shortModel(row.attributes[modelField]) : '',
		elsewhere: link && !same ? (link.name ?? null) : null
	};
}
