// Screenshots of the built page, numbered in review order.
//
//   npm run build
//   npm i --no-save playwright        # not a dependency of this site
//   npm run shots -- --out ~/Desktop/sg-comfyui-site-2026-09-10
//
// It serves build/ itself, so nothing else has to be running, and it prints every network request
// the page made. A request to any host other than the one it serves from is a failure.

import { createReadStream, existsSync, mkdirSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { extname, join, normalize } from 'node:path';
import { homedir } from 'node:os';
import { siteDir } from './readme-blocks.mjs';

const TYPES = {
	'.html': 'text/html',
	'.js': 'text/javascript',
	'.css': 'text/css',
	'.json': 'application/json',
	'.svg': 'image/svg+xml',
	'.png': 'image/png',
	'.jpg': 'image/jpeg',
	'.webm': 'video/webm',
	'.mp4': 'video/mp4',
	'.woff2': 'font/woff2'
};

function arg(name, fallback) {
	const at = process.argv.indexOf(`--${name}`);
	return at === -1 ? fallback : process.argv[at + 1];
}

const root = join(siteDir, 'build');
const out = (arg('out', join(homedir(), 'Desktop', 'sg-comfyui-site-2026-09-10')) ?? '').replace(
	/^~/,
	homedir()
);

if (!existsSync(root)) {
	console.error('No build/. Run: npm run build');
	process.exit(1);
}
mkdirSync(out, { recursive: true });

const server = createServer((request, response) => {
	const path = normalize(decodeURIComponent(new URL(request.url, 'http://x').pathname));
	let file = join(root, path);
	if (existsSync(file) && statSync(file).isDirectory()) file = join(file, 'index.html');
	if (!file.startsWith(root) || !existsSync(file)) {
		response.writeHead(404).end('not found');
		return;
	}
	response.writeHead(200, { 'content-type': TYPES[extname(file)] ?? 'application/octet-stream' });
	createReadStream(file).pipe(response);
});

await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;

let chromium;
try {
	({ chromium } = await import('playwright'));
} catch {
	console.error('playwright is not installed here. Run: npm i --no-save playwright');
	server.close();
	process.exit(1);
}

const SHOTS = [
	{ n: 1, page: '/', at: 'hero', width: 1440, height: 900, scheme: 'light' },
	{ n: 2, page: '/', at: 'provenance', width: 1440, height: 900, scheme: 'light' },
	{ n: 3, page: '/', at: 'hero', width: 1440, height: 900, scheme: 'dark' },
	{ n: 4, page: '/', at: 'provenance', width: 1440, height: 900, scheme: 'dark' },
	{ n: 5, page: '/', at: 'hero', width: 375, height: 780, scheme: 'light' },
	{ n: 6, page: '/', at: 'provenance', width: 375, height: 780, scheme: 'light' },
	{ n: 7, page: '/', at: 'hero', width: 375, height: 780, scheme: 'dark' },
	{ n: 8, page: '/', at: 'provenance', width: 375, height: 780, scheme: 'dark' },
	{ n: 9, page: '/', at: 'hero', width: 1440, height: 900, scheme: 'light', still: true },
	{ n: 10, page: '/', at: 'full', width: 1440, height: 900, scheme: 'light' },
	{ n: 11, page: '/', at: 'full', width: 1440, height: 900, scheme: 'dark' },
	{ n: 12, page: '/', at: 'full', width: 375, height: 780, scheme: 'light' },
	{ n: 13, page: '/docs/install/', at: 'full', width: 1440, height: 900, scheme: 'light' },
	{ n: 14, page: '/docs/install/', at: 'full', width: 375, height: 780, scheme: 'dark' }
];

const browser = await chromium.launch();
const requests = new Set();
const overflow = [];

for (const shot of SHOTS) {
	const context = await browser.newContext({
		viewport: { width: shot.width, height: shot.height },
		colorScheme: shot.scheme,
		reducedMotion: shot.still ? 'reduce' : 'no-preference',
		deviceScaleFactor: 2
	});
	const page = await context.newPage();
	page.on('request', (request) => requests.add(request.url()));
	await page.goto(origin + shot.page, { waitUntil: 'networkidle' });
	await page.waitForTimeout(500);

	if (shot.at === 'provenance') {
		await page.locator('#provenance').scrollIntoViewIfNeeded();
		await page.waitForTimeout(900);
	}

	if (shot.at === 'full') {
		// Sections fade in when they are scrolled to. Walk the page down and back so a full-page
		// screenshot holds the state a reader would have reached.
		const height = await page.evaluate(() => document.body.scrollHeight);
		for (let y = 0; y < height; y += shot.height) {
			await page.evaluate((to) => window.scrollTo(0, to), y);
			await page.waitForTimeout(180);
		}
		await page.evaluate(() => window.scrollTo(0, 0));
		await page.waitForTimeout(600);
	}

	const wide = await page.evaluate(
		() => document.documentElement.scrollWidth - document.documentElement.clientWidth
	);
	if (wide > 0) overflow.push(`${shot.page} at ${shot.width}px scrolls ${wide}px sideways`);

	const parts = [
		String(shot.n).padStart(2, '0'),
		shot.page === '/' ? 'home' : 'docs',
		shot.at,
		`${shot.width}`,
		shot.scheme
	];
	if (shot.still) parts.push('reduced-motion');
	await page.screenshot({
		path: join(out, `${parts.join('_')}.png`),
		fullPage: shot.at === 'full'
	});
	await context.close();
}

await browser.close();
server.close();

const foreign = [...requests].filter((url) => !url.startsWith(origin));
console.log(`\n${SHOTS.length} screenshots in ${out}`);
console.log(`\n${requests.size} network requests, all from the page itself:`);
for (const url of [...requests].sort()) console.log(`  ${url.replace(origin, '')}`);
if (foreign.length) {
	console.error(`\nRequests that left the origin:\n  ${foreign.join('\n  ')}`);
	process.exitCode = 1;
}
if (overflow.length) {
	console.error(`\nHorizontal scroll:\n  ${overflow.join('\n  ')}`);
	process.exitCode = 1;
}
