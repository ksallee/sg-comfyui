// The four blocks this page copies out of README.md, and how to cut them out of it.
// `start` and `end` are matched as whole lines. The block is everything between them, trimmed;
// `keepStart` keeps the start line itself, for a block that begins with a heading.
// check-readme-blocks.mjs compares the cut against src/lib/readme/*.md and fails on any difference.

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const siteDir = dirname(dirname(fileURLToPath(import.meta.url)));
export const repoDir = dirname(siteDir);
export const blockDir = join(siteDir, 'src', 'lib', 'readme');

export const BLOCKS = [
	{
		name: 'requirements',
		title: 'Requirements',
		start: '## Install',
		end: '### Which install'
	},
	{
		name: 'install-commands',
		title: 'Install commands',
		start: '### Which install',
		keepStart: true,
		end: 'Paths, the command-line tools, the profile key by key and the fixes are in [INSTALL.md](INSTALL.md).'
	},
	{
		name: 'first-run',
		title: 'First run',
		start: '## First run',
		end: 'A farm enters a Script name and Application key under Script Authentication instead of step 3.'
	},
	{
		name: 'whats-next',
		title: "What's next",
		start: "## What's next",
		end: '## Known limits'
	}
];

export function readReadme() {
	return readFileSync(join(repoDir, 'README.md'), 'utf8');
}

/** Cut one block out of README.md. Throws when an anchor is missing or out of order. */
export function cut(readme, block) {
	const lines = readme.split('\n');
	const from = lines.indexOf(block.start);
	if (from === -1) throw new Error(`README.md has no line "${block.start}"`);
	const to = lines.indexOf(block.end, from + 1);
	if (to === -1) throw new Error(`README.md has no line "${block.end}" after "${block.start}"`);
	return lines.slice(block.keepStart ? from : from + 1, to).join('\n').trim() + '\n';
}

export function blockPath(block) {
	return join(blockDir, `${block.name}.md`);
}
