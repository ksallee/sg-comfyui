// Fails when a block under src/lib/readme/ differs from the README.md text it was copied from.
// Run with --write to copy the current README.md text into those files.

import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { relative } from 'node:path';
import { BLOCKS, blockDir, blockPath, cut, readReadme, repoDir } from './readme-blocks.mjs';

const write = process.argv.includes('--write');
const readme = readReadme();
let failed = 0;

if (write) mkdirSync(blockDir, { recursive: true });

for (const block of BLOCKS) {
	const wanted = cut(readme, block);
	const path = blockPath(block);
	if (write) {
		writeFileSync(path, wanted);
		console.log(`wrote ${relative(repoDir, path)}`);
		continue;
	}
	let found;
	try {
		found = readFileSync(path, 'utf8');
	} catch {
		console.error(`missing  ${relative(repoDir, path)}. Run: node site/scripts/check-readme-blocks.mjs --write`);
		failed += 1;
		continue;
	}
	if (found === wanted) {
		console.log(`ok       ${relative(repoDir, path)}`);
		continue;
	}
	failed += 1;
	console.error(`differs  ${relative(repoDir, path)} is not the README.md text between:`);
	console.error(`           "${block.start}"`);
	console.error(`           "${block.end}"`);
	const a = found.split('\n');
	const b = wanted.split('\n');
	for (let i = 0; i < Math.max(a.length, b.length); i += 1) {
		if (a[i] === b[i]) continue;
		console.error(`  line ${i + 1}`);
		console.error(`    page:   ${JSON.stringify(a[i] ?? null)}`);
		console.error(`    README: ${JSON.stringify(b[i] ?? null)}`);
	}
}

if (failed) {
	console.error(
		`\n${failed} block(s) differ. Copy README.md across with: node site/scripts/check-readme-blocks.mjs --write`
	);
	process.exit(1);
}
console.log(`\n${BLOCKS.length} blocks match README.md.`);
