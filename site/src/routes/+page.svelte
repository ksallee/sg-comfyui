<script>
	import { base } from '$app/paths';
	import Clip from '$lib/Clip.svelte';
	import Markdown from '$lib/Markdown.svelte';
	import Provenance from '$lib/Provenance.svelte';
	import Shot from '$lib/Shot.svelte';
	import { author, issues } from '$lib/site.js';
	import { reveal } from '$lib/reveal.js';
	import { onDestroy } from 'svelte';

	import firstRun from '$lib/readme/first-run.md?raw';
	import installCommands from '$lib/readme/install-commands.md?raw';
	import requirements from '$lib/readme/requirements.md?raw';
	import whatsNext from '$lib/readme/whats-next.md?raw';

	const doctor = `ok    Python 3.11.11 at /Users/you/ComfyUI/venv/bin/python.
ok    sg_groundtruth imports here.
ok    requests imports here.
ok    Pillow imports here.
ok    This is the interpreter ComfyUI runs on, /Users/you/ComfyUI/venv/bin/python.`;

	const templates = [
		{
			name: '18_template_00_example',
			title: '00_example',
			alt: 'The 00_example template open in ComfyUI, an image into SG Publish and SG Load reading it back'
		},
		{
			name: '19_template_01_concept_and_style',
			title: '01_concept_and_style',
			alt: 'The 01_concept_and_style template open in ComfyUI'
		},
		{
			name: '20_template_02_style_from_a_reference',
			title: '02_style_from_a_reference',
			alt: 'The 02_style_from_a_reference template open in ComfyUI'
		}
	];

	const firstRunGraph = {
		name: 'example-workflow',
		title: '00_example',
		alt: 'The 00_example template open in ComfyUI after a Run'
	};

	// A graph is unreadable at thumbnail size. The full PNG opens in a modal dialog, which Escape
	// and the backdrop both close.
	let shown = $state(null);
	let box = $state(null);

	function enlarge(template) {
		shown = template;
		box?.showModal();
	}

	const agentPrompt = `Clone https://github.com/ksallee/sg-comfyui into ComfyUI's custom_nodes directory.
Install its requirements.txt into the interpreter ComfyUI runs on.
Restart ComfyUI.
Welcome me.
Ask me before you run tools/doctor.py.
Then offer to run /setup.`;

	let copied = $state(false);
	let said;

	async function copyPrompt() {
		try {
			await navigator.clipboard.writeText(agentPrompt);
		} catch {
			return;
		}
		copied = true;
		clearTimeout(said);
		said = setTimeout(() => (copied = false), 3000);
	}

	onDestroy(() => clearTimeout(said));
</script>

<svelte:head>
	<title>Flow Production Tracking for ComfyUI</title>
	<meta
		name="description"
		content="Two ComfyUI nodes. SG Publish creates a Version with the model, prompt, seed, sampler and workflow that made it. SG Load reads that media back into a graph."
	/>
</svelte:head>

<!-- 1. Hero -->
<section class="hero">
	<div class="page hero-grid">
		<h1>Publish generations to Flow Production Tracking.</h1>
		<div class="hero-copy">
			<p class="lede">
				SG Publish creates a Version with the model, prompt, seed, sampler and workflow that made it.
			</p>
			<div class="actions">
				<a class="button" href="#install">Install</a>
				<a class="button quiet" href="{base}/docs">Read the docs</a>
			</div>
		</div>
		<div class="hero-media">
			<Clip
				name="02_publish_run"
				caption="One Run. The node reports the Version it created and the files it registered."
			/>
		</div>
	</div>
</section>

<!-- 2. The problem -->
<section class="band" use:reveal>
	<div class="page problem">
		<h2>A generation is a file with nothing attached.</h2>
		<p class="lede">
			The checkpoint, the prompt, the seed and the sampler are in a graph on one machine. The file
			that leaves it has a name and a date.
		</p>
		<div class="contrast">
			<div class="cell sunk">
				<h3>In the output directory</h3>
				<ul>
					<li>A file name.</li>
					<li>A size and a date.</li>
					<li>Whatever the artist typed into the name.</li>
				</ul>
			</div>
			<div class="cell">
				<h3>On the Version</h3>
				<ul>
					<li>Nine typed fields, queryable in a filter or a page layout.</li>
					<li>The workflow, attached, when the submitting client sent one.</li>
					<li>A <code>.provenance.json</code> record.</li>
					<li>Review media that plays in a browser.</li>
				</ul>
			</div>
		</div>
	</div>
</section>

<!-- 3. SG Publish -->
<section class="band" id="publish" use:reveal>
	<div class="page">
		<h2>SG Publish creates the Version and uploads the media.</h2>
		<p class="lede wide">
			Pick the project and the link on the node. The pickers read them from your site.
		</p>
		<div class="wide-media">
			<Clip
				name="01_publish_pick"
				caption="Project, link, Task and status, read live from the site. Sync from SG forces a read past the 600 second cache."
			/>
		</div>
		<div class="facts">
			<div>
				<h3>Linked the way your site links</h3>
				<p>A Shot, an Asset, or whatever else this project's Versions already use.</p>
			</div>
			<div>
				<h3>Named by a template</h3>
				<p>Root name and version name come from the profile. Settings writes both.</p>
			</div>
			<div>
				<h3>Files registered on request</h3>
				<p>Frames or the movie become PublishedFiles when Create Published Files is ticked.</p>
			</div>
		</div>
	</div>
</section>

<!-- 4. SG Load -->
<section class="band" id="load" use:reveal>
	<div class="page">
		<h2>SG Load reads the media back into the graph.</h2>
		<p class="lede wide">
			Find a Version by project, link, Task, status and name. <code>pin_version_id</code> takes an id
			instead. 16-bit PNG and EXR are read at full precision.
		</p>
		<div class="wide-media">
			<Clip
				name="06_load_image_mask"
				caption="An RGBA Version read back. Alpha becomes the mask output, on ComfyUI's convention."
			/>
		</div>
		<dl class="outputs">
			<dt>Outputs</dt>
			<dd>
				<code>image</code> <code>video</code> <code>mask</code> <code>version_id</code>
				<code>code</code> <code>colour_space</code>
			</dd>
			<dt>Recorded downstream</dt>
			<dd>The Version it read, on anything published from the same graph.</dd>
		</dl>
	</div>
</section>

<!-- 5. Provenance -->
<Provenance />

<!-- 6. Formats -->
<section class="band" id="formats" use:reveal>
	<div class="page">
		<h2>Three frame formats, written by ComfyUI's encoder.</h2>
		<p class="lede wide">
			Pick one on the node's format widget. A VIDEO read from a file is uploaded as that file, byte
			for byte.
		</p>
		<div class="bento">
			<div class="cell">
				<h3>8-bit PNG</h3>
				<p>The plain case. Review media is 8-bit whatever the frames are.</p>
			</div>
			<div class="cell">
				<h3>16-bit PNG</h3>
				<p>SG Load reads it back at full precision.</p>
			</div>
			<div class="cell sunk">
				<h3>EXR 32-bit float</h3>
				<p>
					Pixels are written unchanged. The declared colour space goes in the PublishedFile's
					description and is never applied.
				</p>
			</div>
			<div class="cell image">
				<Shot
					name="07_load_exr"
					alt="SG Load on an EXR Version in ComfyUI, showing the format line and the colour space output"
					caption="SG Load reports the format before a run, and returns the colour space as an output."
				/>
			</div>
		</div>
	</div>
</section>

<!-- 7. Templates -->
<section class="band" id="templates" use:reveal>
	<div class="page">
		<div class="split">
			<div class="split-copy">
				<h2>Three demo templates to test the nodes.</h2>
				<p>
					Open the Templates browser, category <code>sg-comfyui</code>. <code>00_example</code>
					publishes one image and reads it back.
				</p>
				<p>
					For a graph you already use, <code>/track-workflow</code> adds the nodes to it. Fill from
					SG defaults then puts your publish defaults on the node.
				</p>
			</div>
			<div class="split-media">
				<Clip
					name="04_fill_defaults"
					caption="Fill from SG defaults writes the storage, the paths and the status onto the node."
				/>
			</div>
		</div>
		<div class="gallery" role="group" aria-label="The shipped templates">
			{#each templates as template (template.name)}
				<figure>
					<button
						type="button"
						class="thumb"
						aria-label="Open {template.title} at full size"
						onclick={() => enlarge(template)}
					>
						<img
							src="{base}/media/{template.name}.png"
							alt={template.alt}
							width="1600"
							height="1000"
							loading="lazy"
							decoding="async"
						/>
					</button>
					<figcaption><code>{template.title}</code> <span>Open the full graph</span></figcaption>
				</figure>
			{/each}
		</div>
	</div>
</section>

<!-- 8. Storage -->
<section class="band" id="storage" use:reveal>
	<div class="page">
		<h2>Files are copied to the storage location.</h2>
		<p class="lede wide">
			The nodes use only the filesystem roots defined on your SG site (Local File Storage) and
			relative path templates similar to SG Toolkit's.
		</p>
		<div class="wide-media">
			<Shot
				name="settings-storage-paths"
				alt="The SG page of ComfyUI settings, showing the storage, the sequence and movie path templates, and the Path to Frames and Path to Movie toggles"
				caption="Settings, then SG. Each template shows what it renders to under the root."
			/>
		</div>
		<div class="storage">
			<div>
				<figure class="path">
					<figcaption class="mono-label">
						Sequence path, and what one publish rendered it to
					</figcaption>
					<pre><code>{'{entity}/{root_name}/{version_name}/{version_name}.%04d{ext}'}

/Volumes/FPT/sh010/verify_pub_rows/verify_pub_rows_v003/verify_pub_rows_v003.%04d.exr</code></pre>
				</figure>
				<p>
					ComfyUI writes the frames to its own output directory and the node copies them under the
					root. A publish that fails after the copy names the copies it left. A re-run overwrites
					the same paths.
				</p>
				<p>
					A PublishedFile path is stored against the storage root, so the site resolves it on every
					operating system the root is mapped for. Path to Frames and Path to Movie are optional
					Version fields, one string each, written in the notation of the operating system picked
					under Settings, then SG.
				</p>
			</div>
			<table>
				<thead>
					<tr>
						<th scope="col">token</th>
						<th scope="col">what it is</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<td><code>{'{version}'}</code></td>
						<td>the publish revision</td>
					</tr>
					<tr>
						<td><code>%04d</code> <code>####</code> <code>@@@@</code></td>
						<td>the frame number</td>
					</tr>
					<tr>
						<td><code>{'{entity.Shot.code}'}</code></td>
						<td>a dotted field path, to any depth</td>
					</tr>
					<tr>
						<td><code>[optional blocks]</code></td>
						<td>dropped when the fields inside are empty</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</section>

<!-- 9. Signing in -->
<section class="band" id="signing-in" use:reveal>
	<div class="page">
		<h2>Sign in as yourself, or as a script.</h2>
		<div class="paths">
			<div>
				<h3>A person, at a workstation</h3>
				<p>
					Press Log in under Log In As Yourself. Approve the request in the browser tab. The nodes
					publish as you.
				</p>
			</div>
			<div>
				<h3>A script, on a farm</h3>
				<p>
					Make the script under Admin, then Scripts. Enter its Script name and Application key under
					Script Authentication.
				</p>
			</div>
		</div>
		<p class="wide">
			Press Test either way. It reports who the nodes publish as. Both are stored in ComfyUI's
			protected user directory, never in the settings store.
		</p>
		<div class="wide-media">
			<Shot
				name="settings-sign-in"
				alt="The SG page of ComfyUI settings, showing Log In As Yourself above Script Authentication"
				caption="Settings, then SG. Log In As Yourself is one button. Script Authentication takes the Script name and the Application key."
			/>
		</div>
	</div>
</section>

<!-- 10. Install -->
<section class="band" id="install" use:reveal>
	<div class="page install">
		<div class="install-copy">
			<h2>Install</h2>
			<Markdown source={requirements} />
			<Markdown source={installCommands} />
			<div class="agent-install">
				<button type="button" class="button" onclick={copyPrompt} aria-live="polite">
					{copied ? 'Prompt copied' : 'Install with your LLM'}
				</button>
				<details>
					<summary>The prompt</summary>
					<pre><code>{agentPrompt}</code></pre>
				</details>
			</div>
		</div>
		<div class="install-run">
			<h3 class="run-title">First run</h3>
			<Markdown source={firstRun} />
			<p class="note">
				Restart ComfyUI to install or upgrade the pack. A profile edit is read on a browser refresh.
			</p>
			<figure class="run-shot">
				<button
					type="button"
					class="thumb"
					aria-label="Open the 00_example graph at full size"
					onclick={() => enlarge(firstRunGraph)}
				>
					<img src="{base}/media/example-workflow.png" alt={firstRunGraph.alt} width="1540" height="903" loading="lazy" />
				</button>
				<figcaption>Step 6 opens this graph. Click it for full size.</figcaption>
			</figure>
		</div>
	</div>
</section>

<!-- 11. The doctor -->
<section class="band" id="doctor" use:reveal>
	<div class="page doctor">
		<div>
			<h2><code class="big">tools/doctor.py</code> checks the install offline.</h2>
			<p>
				It prints one line per thing a publish needs, with the fix appended where it fails, and
				exits non-zero on anything that would stop a publish. <code>--site</code> adds the
				connection, the provenance fields, the storage roots and the link types.
			</p>
			<p>
				It needs no site, no ComfyUI and no torch. Run it with the interpreter ComfyUI runs on: when
				two interpreters differ, it names both.
			</p>
		</div>
		<pre class="terminal"><code>{doctor}</code></pre>
	</div>
</section>

<!-- 12. Agents -->
<section class="band tight" id="agents" use:reveal>
	<div class="page agents">
		<h2>An agent adds the nodes to your workflow.</h2>
		<p>
			Point your agent at a graph you already use. <code>/track-workflow</code> adds SG Publish and
			SG Load where the graph needs them, wired and filled in, and leaves the original untouched.
			<code>/setup</code> connects the site and creates the provenance fields. <code>AGENTS.md</code>
			is the entry point, written for any harness. An agent runs <code>tools/doctor.py</code> first.
		</p>
		<p class="commands">
			<code>/setup</code>
			<code>/inspect-site</code>
			<code>/track-workflow</code>
			<code>/task</code>
			<a href="{base}/docs/agent">The agent page</a>
		</p>
	</div>
</section>

<!-- 13. Not in scope -->
<section class="band" id="scope" use:reveal>
	<div class="page">
		<h2>What this pack does not do.</h2>
		<div class="scope">
			<p>No encoder, no decoder, no generation. ComfyUI writes and reads the pixels.</p>
			<p>No charts, no dashboards, no scheduled reports, no automations.</p>
			<p>Review media is derived and may be transcoded. A deliverable file is never transformed.</p>
			<p>Colour space is recorded, never applied. Core ComfyUI has no colour management.</p>
		</div>
	</div>
</section>

<!-- 14. What is next -->
<section class="band" id="next" use:reveal>
	<div class="page next">
		<h2>What's next</h2>
		<Markdown source={whatsNext} />
	</div>
</section>

<!-- 15. The state of it -->
<section class="band" id="state" use:reveal>
	<div class="page state">
		<div>
			<h2>The pack is alpha, and it is built to be forked.</h2>
			<p class="lede">
				Adjust the nodes for your pipeline, or send the change back. Tell Kevin what breaks and what
				is missing.
			</p>
		</div>
		<div class="state-cta">
			<a class="button" href={issues} rel="external">Open an issue</a>
			<a class="button quiet" href={author} rel="external">Message Kevin</a>
		</div>
	</div>
</section>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
<dialog
	class="viewer"
	bind:this={box}
	onclose={() => (shown = null)}
	onclick={(event) => {
		if (event.target === box) box.close();
	}}
>
	{#if shown}
		<p class="viewer-foot">
			<code>{shown.title}</code>
			<button type="button" class="button quiet" onclick={() => box.close()}>Close</button>
		</p>
		<div class="viewer-scroll">
			<img src="{base}/media/{shown.name}.png" alt={shown.alt} />
		</div>
	{/if}
</dialog>

<style>
	/* 1. Hero */
	.hero {
		padding-block: clamp(2.5rem, 4vw, 3.5rem) clamp(3rem, 6vw, 5.5rem);
	}

	.hero-grid {
		display: grid;
		grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr);
		column-gap: clamp(2rem, 5vw, 4rem);
		row-gap: clamp(2rem, 4vw, 3rem);
		align-items: start;
	}

	.hero-grid h1 {
		grid-column: 1 / -1;
		max-width: 20ch;
	}

	.hero-copy .lede {
		max-width: 34ch;
		font-size: 1.125rem;
	}

	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		margin-top: 1.75rem;
	}

	/* 2. The problem */
	.problem .lede {
		margin-top: 1rem;
		font-size: 1.125rem;
		max-width: 52ch;
	}

	.contrast {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1.25fr);
		gap: 1.25rem;
		margin-top: 2.75rem;
	}

	.cell {
		border: 1px solid var(--line);
		border-radius: var(--r);
		background: var(--surface);
		padding: clamp(1.25rem, 2.4vw, 1.9rem);
	}

	.cell.sunk {
		background: var(--sunk);
	}

	.cell h3 {
		margin-bottom: 0.85rem;
		color: var(--muted);
		font-size: 0.8125rem;
		font-weight: 560;
		letter-spacing: 0.01em;
	}

	.cell ul {
		margin: 0;
	}

	.cell li:last-child {
		margin-bottom: 0;
	}

	/* 3. SG Publish */
	.lede.wide,
	p.wide {
		max-width: 58ch;
		margin-top: 1rem;
	}

	.wide-media {
		margin-top: 2.25rem;
	}

	.facts {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 2rem;
		margin-top: 2.5rem;
		padding-top: 2rem;
		border-top: 1px solid var(--line);
	}

	.facts h3 {
		margin-bottom: 0.5rem;
	}

	.facts p {
		margin: 0;
		color: var(--muted);
		font-size: 0.9375rem;
	}

	/* 4. SG Load */
	.outputs {
		margin: 2rem 0 0;
		padding-top: 1.25rem;
		border-top: 1px solid var(--line);
		display: grid;
		grid-template-columns: max-content minmax(0, 1fr);
		gap: 0.6rem 2rem;
		align-items: baseline;
	}

	.outputs dt {
		color: var(--muted);
		font-size: 0.8125rem;
	}

	.outputs dd {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
	}

	/* 7. Templates */
	.split {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: clamp(2rem, 5vw, 4rem);
		align-items: center;
	}

	.split-copy h2 {
		margin-bottom: 1.1rem;
	}

	/* 6. Formats */
	.bento {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 1.25rem;
		margin-top: 2.5rem;
	}

	.bento .cell h3 {
		color: var(--ink);
		font-family: var(--mono);
		font-size: 0.9375rem;
		letter-spacing: -0.01em;
	}

	.bento .cell p {
		margin: 0;
		color: var(--muted);
		font-size: 0.9375rem;
	}

	.bento .cell.image {
		grid-column: 1 / -1;
		padding: 0;
		border: 0;
		background: none;
	}

	/* 7. Templates */
	.gallery {
		display: grid;
		grid-auto-flow: column;
		grid-auto-columns: minmax(280px, 1fr);
		gap: 1.25rem;
		margin-top: 3rem;
		overflow-x: auto;
		scroll-snap-type: x mandatory;
		padding-bottom: 0.75rem;
	}

	.gallery figure {
		margin: 0;
		scroll-snap-align: start;
	}

	.run-shot {
		margin: 1.5rem 0 0;
	}

	.run-shot figcaption,
	.gallery figcaption {
		margin-top: 0.7rem;
		color: var(--muted);
		font-size: 0.875rem;
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.6rem;
	}

	.gallery figcaption span {
		font-size: 0.8125rem;
	}

	.thumb {
		display: block;
		width: 100%;
		padding: 0;
		border: 1px solid var(--line);
		border-radius: var(--r);
		background: var(--sunk);
		overflow: hidden;
		cursor: pointer;
		transition: border-color 0.18s var(--ease);
	}

	.thumb:hover {
		border-color: var(--muted);
	}

	.thumb img {
		width: 100%;
		height: auto;
	}

	/* The full graph, over the page. The image is shown at its own size and scrolls under a footer
	   that keeps Close in reach. */
	.viewer {
		width: min(96vw, 1640px);
		max-width: none;
		max-height: 92vh;
		padding: 0;
		border: 1px solid var(--line);
		border-radius: var(--r);
		background: var(--surface);
		color: var(--ink);
		overflow: hidden;
	}

	.viewer[open] {
		display: flex;
		flex-direction: column;
	}

	.viewer::backdrop {
		background: rgb(14 14 13 / 0.72);
	}

	.viewer-scroll {
		overflow: auto;
		padding: 0 0.75rem 0.75rem;
	}

	.viewer img {
		width: 100%;
		height: auto;
		border-radius: var(--r-sm);
	}

	.viewer-foot {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		margin: 0;
		max-width: none;
		padding: 0.75rem;
		border-bottom: 1px solid var(--line);
	}

	/* 8. Storage */
	.storage {
		display: grid;
		grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr);
		gap: clamp(2rem, 5vw, 4rem);
		align-items: start;
		margin-top: 2.75rem;
		padding-top: 2rem;
		border-top: 1px solid var(--line);
	}

	.path {
		margin: 0 0 1.5rem;
	}

	.path figcaption {
		margin-bottom: 0.6rem;
	}

	.path pre {
		margin: 0;
		font-size: 0.75rem;
		white-space: pre;
	}

	/* 9. Signing in */
	.paths {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: clamp(1.5rem, 4vw, 3rem);
		margin-top: 2.25rem;
		padding-top: 2rem;
		border-top: 1px solid var(--line);
	}

	.paths h3 {
		margin-bottom: 0.6rem;
	}

	.paths p {
		margin: 0;
		color: var(--muted);
	}

	/* 10. Install */
	.install {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: clamp(2rem, 5vw, 4rem);
		align-items: start;
	}

	.install h2 {
		margin-bottom: 1.5rem;
	}

	.run-title {
		font-size: clamp(1.65rem, 1.05rem + 2vw, 2.5rem);
		font-weight: 560;
		letter-spacing: -0.022em;
		margin-bottom: 1.5rem;
	}

	.install-run .note {
		color: var(--muted);
		font-size: 0.9375rem;
		margin-top: 1.5rem;
	}

	.install-run :global(figure) {
		margin-top: 1.5rem;
	}

	.agent-install {
		margin-top: 1.75rem;
		padding-top: 1.5rem;
		border-top: 1px solid var(--line);
	}

	.agent-install summary {
		margin-top: 1rem;
		color: var(--muted);
		font-size: 0.875rem;
		cursor: pointer;
	}

	.agent-install pre {
		margin: 0.75rem 0 0;
		font-size: 0.75rem;
	}

	.agent-install pre code {
		white-space: pre-wrap;
	}

	/* 11. The doctor */
	.doctor {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr);
		gap: clamp(2rem, 5vw, 4rem);
		align-items: center;
	}

	.doctor h2 {
		margin-bottom: 1.1rem;
	}

	code.big {
		font-size: 0.78em;
		background: none;
		border: 0;
		padding: 0;
		color: var(--accent);
	}

	.terminal {
		margin: 0;
		font-size: 0.75rem;
		background: var(--surface);
	}

	/* 12. Not in scope */
	.scope {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: 1.5rem 3rem;
		margin-top: 1.5rem;
	}

	.scope p {
		margin: 0;
		color: var(--muted);
		max-width: 44ch;
	}

	/* 12. Agents */
	.agents p {
		margin-top: 1.1rem;
	}

	.commands {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.4rem 0.9rem;
		margin-bottom: 0;
	}

	/* 14. What is next */
	.next h2 {
		margin-bottom: 1.25rem;
	}

	/* Ten entries stack into a column too long to scan. */
	.next :global(ul) {
		columns: 2;
		column-gap: clamp(2rem, 5vw, 4rem);
		max-width: none;
		margin-bottom: 0;
	}

	.next :global(li) {
		break-inside: avoid;
		margin-bottom: 0.6rem;
	}

	/* 15. The state of it */
	.state {
		display: grid;
		grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);
		gap: clamp(2rem, 5vw, 4rem);
		align-items: center;
	}

	.state h2 {
		margin-bottom: 1.1rem;
	}

	.state .lede {
		margin: 0;
		font-size: 1.125rem;
		max-width: 46ch;
	}

	.state-cta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
	}

	@media (max-width: 900px) {
		.hero-grid,
		.contrast,
		.split,
		.storage,
		.paths,
		.install,
		.doctor,
		.state,
		.scope {
			grid-template-columns: minmax(0, 1fr);
		}

		.facts,
		.bento {
			grid-template-columns: minmax(0, 1fr);
			gap: 1.5rem;
		}

		.outputs {
			grid-template-columns: minmax(0, 1fr);
			gap: 0.3rem;
		}

		.outputs dd:not(:last-child) {
			margin-bottom: 0.9rem;
		}

		.next :global(ul) {
			columns: 1;
		}

		.gallery {
			grid-auto-columns: minmax(82%, 1fr);
		}

		.viewer {
			width: 96vw;
			padding: 0.5rem;
		}
	}
</style>
