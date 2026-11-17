import { describe, expect, it } from 'vitest';
import type { FieldSchema } from 'sg-widgets-core';
import { detailRows, lineageField, provenanceRows, STANDARD_FIELDS } from './detail-rows';

const field = (name: string, displayName: string, dataType: string) =>
	({ name, displayName, dataType, entityType: 'Version' }) as FieldSchema;

const SCHEMA: Record<string, FieldSchema> = {
	sg_status_list: field('sg_status_list', 'Status', 'status_list'),
	entity: field('entity', 'Link', 'entity'),
	user: field('user', 'Artist', 'entity'),
	description: field('description', 'Description', 'text'),
	sg_ai_model: field('sg_ai_model', 'AI Model', 'text'),
	sg_ai_cfg: field('sg_ai_cfg', 'AI CFG', 'float'),
	sg_ai_generated_from: field('sg_ai_generated_from', 'AI Generated From', 'multi_entity')
};

describe('detailRows', () => {
	it('lists the fields the site has, in the order asked, under the site’s own names', () => {
		expect(detailRows(['entity', 'sg_task', 'user'], SCHEMA)).toEqual([
			{ field: 'entity', label: 'Link', dataType: 'entity' },
			{ field: 'user', label: 'Artist', dataType: 'entity' }
		]);
	});

	it('starts from the status, the link and the task', () => {
		expect(STANDARD_FIELDS.slice(0, 3)).toEqual(['sg_status_list', 'entity', 'sg_task']);
	});
});

describe('provenanceRows', () => {
	const MAPPED = [
		{ concept: 'model', label: 'model', field: 'sg_ai_model' },
		{ concept: 'seed', label: 'seed', field: 'sg_ai_seed' },
		{ concept: 'cfg', label: 'cfg', field: 'sg_ai_cfg' },
		{ concept: 'generated_from', label: 'generated from', field: 'sg_ai_generated_from' }
	];

	it('names each field by its concept, skips a field the site lacks, and leaves the lineage out', () => {
		expect(provenanceRows(MAPPED, SCHEMA)).toEqual([
			{ field: 'sg_ai_model', label: 'Model', dataType: 'text' },
			{ field: 'sg_ai_cfg', label: 'CFG', dataType: 'float' }
		]);
	});

	it('reads the lineage from the generated-from field when the site has it', () => {
		expect(lineageField(MAPPED, SCHEMA)).toBe('sg_ai_generated_from');
		const { sg_ai_generated_from: _, ...without } = SCHEMA;
		expect(lineageField(MAPPED, without)).toBeNull();
	});
});
