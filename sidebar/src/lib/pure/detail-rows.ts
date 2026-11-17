/**
 * The rows a Version's detail lists: a label, the field it reads, and the type it renders by.
 */
import type { FieldSchema } from 'sg-widgets-core';

/** The fields every Version detail starts with. */
export const STANDARD_FIELDS = [
	'sg_status_list',
	'entity',
	'sg_task',
	'user',
	'created_at',
	'frame_range',
	'description'
];

export type DetailRow = { field: string; label: string; dataType: string };

/** One provenance concept and the field this project records it in (`/sg/provenance_fields`). */
export type ProvenanceField = { concept: string; label: string; field: string };

/** The concept whose field links a Version to the Versions it was generated from. */
export const LINEAGE_CONCEPT = 'generated_from';

/** `fields` the site has, under the site's own display names. */
export function detailRows(fields: string[], schema: Record<string, FieldSchema>): DetailRow[] {
	return fields
		.filter((name) => schema[name])
		.map((name) => ({ field: name, label: schema[name]!.displayName, dataType: schema[name]!.dataType }));
}

/** Concept labels that are acronyms, written as such. */
const ACRONYMS: Record<string, string> = { cfg: 'CFG' };

function sentence(label: string): string {
	return ACRONYMS[label] ?? label.charAt(0).toUpperCase() + label.slice(1);
}

/** The provenance fields the site has, each named by its concept. The lineage has its own section. */
export function provenanceRows(
	provenance: ProvenanceField[],
	schema: Record<string, FieldSchema>
): DetailRow[] {
	return provenance
		.filter((p) => schema[p.field] && p.concept !== LINEAGE_CONCEPT)
		.map((p) => ({
			field: p.field,
			label: sentence(p.label),
			dataType: schema[p.field]!.dataType
		}));
}

/** The field `concept` is recorded in, when the project records it in one the site has. */
export function conceptField(
	provenance: ProvenanceField[],
	schema: Record<string, FieldSchema>,
	concept: string
): string | null {
	const found = provenance.find((p) => p.concept === concept && schema[p.field]);
	return found ? found.field : null;
}

/** The field the lineage is read from. */
export function lineageField(
	provenance: ProvenanceField[],
	schema: Record<string, FieldSchema>
): string | null {
	return conceptField(provenance, schema, LINEAGE_CONCEPT);
}
