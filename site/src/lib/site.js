export const repo = 'https://github.com/ksallee/sg-comfyui';
export const issues = `${repo}/issues/new`;
export const registry = 'https://registry.comfy.org/';
export const licence = `${repo}/blob/main/LICENSE`;
export const author = 'https://www.linkedin.com/in/kevinsallee/';

/** The nine documentation pages, in reading order. The footer and /docs both list these. */
export const docs = [
	{ slug: 'install', title: 'Install', blurb: 'The interpreter, the four local files, the doctor.' },
	{ slug: 'first-run', title: 'First run', blurb: 'Settings to the example workflow, in eight steps.' },
	{ slug: 'profile', title: 'The profile', blurb: 'profile.local.json, key by key.' },
	{ slug: 'nodes', title: 'The two nodes', blurb: 'What SG Publish writes and what SG Load reads.' },
	{ slug: 'provenance', title: 'Provenance fields', blurb: 'The nine fields, and a site without them.' },
	{ slug: 'formats', title: 'Formats and colour space', blurb: 'PNG, EXR, review media, what is recorded.' },
	{ slug: 'storage', title: 'Storage and paths', blurb: 'Local File Storage roots, templates, tokens.' },
	{ slug: 'troubleshooting', title: 'Troubleshooting', blurb: 'The symptom, then the fix.' },
	{ slug: 'agent', title: 'For an agent', blurb: 'The entry point, the procedures, the commands.' }
];

/** The nine provenance fields, from README.md. */
export const provenance = [
	['AI Generator', 'sg_ai_generator', 'ComfyUI, and the name the submitting client gave itself'],
	['AI Model', 'sg_ai_model', 'the checkpoints the graph loaded'],
	['AI Prompt', 'sg_ai_prompt', 'positive conditioning on this branch'],
	['AI Negative Prompt', 'sg_ai_negative_prompt', 'negative conditioning on this branch'],
	['AI Seed', 'sg_ai_seed', 'text, not a number: seeds reach 2**64-1'],
	['AI Sampler', 'sg_ai_sampler', 'sampler and scheduler'],
	['AI Steps', 'sg_ai_steps', 'the last sampler on the branch'],
	['AI CFG', 'sg_ai_cfg', 'the last sampler on the branch'],
	['AI Generated From', 'sg_ai_generated_from', 'the Versions this was made from']
];

/** Pixel size of every capture under static/media, so a page reserves its space before it loads. */
export const shotSize = {
	'01_publish_before_run_exr': [1100, 950],
	'04_publish_storage_alert': [1100, 950],
	'05_publish_provenance_into_description': [1100, 950],
	'07_load_exr': [1400, 1000],
	'12_settings_site_setup_9_of_9': [1100, 950],
	'18_template_00_example': [1600, 1000],
	'19_template_01_concept_and_style': [1600, 1000],
	'20_template_02_style_from_a_reference': [1600, 1000],
	'example-workflow': [1540, 903],
	'load-provenance-rows': [870, 660],
	'settings-sign-in': [2304, 1440],
	'settings-storage-paths': [1900, 750],
	'sg-load-info': [1560, 2536],
	'sg-load-node': [1050, 800],
	'sg-publish-info': [1560, 2104],
	'sg-publish-node': [765, 855]
};
