import { describe, expect, it } from 'vitest';
import type { EntityRow } from 'sg-widgets-core';
import { lineageInfo, shortModel } from './lineage-info';

describe('shortModel', () => {
	it('drops the extension of a checkpoint', () => {
		expect(shortModel('flux1-dev-fp8.safetensors')).toBe('flux1-dev-fp8');
	});

	it('names the first model and counts the rest', () => {
		expect(
			shortModel('flux1-dev-fp8.safetensors | flux1-redux-dev.safetensors | sigclip_vision_patch14_384.safetensors')
		).toBe('flux1-dev-fp8 +2');
	});

	it('is empty for no model', () => {
		expect(shortModel(null)).toBe('');
		expect(shortModel('  ')).toBe('');
	});
});

describe('lineageInfo', () => {
	const row = (link: { type: string; id: number; name: string } | null, model: string | null): EntityRow => ({
		type: 'Version',
		id: 2,
		attributes: { code: 'v2', sg_ai_model: model },
		relationships: { entity: { data: link } }
	});
	const SH010 = { type: 'Shot', id: 10, name: 'sh010' };

	it('names the link when the source comes from another one', () => {
		expect(lineageInfo(row(SH010, 'sd15.ckpt'), 'sg_ai_model', { type: 'Shot', id: 20 })).toEqual({
			model: 'sd15',
			elsewhere: 'sh010'
		});
	});

	it('names no link when the source shares the opened Version’s', () => {
		expect(lineageInfo(row(SH010, null), 'sg_ai_model', { type: 'Shot', id: 10 })).toEqual({
			model: '',
			elsewhere: null
		});
	});

	it('reads no model when the project records none', () => {
		expect(lineageInfo(row(null, 'sd15.ckpt'), null, null).model).toBe('');
	});
});
