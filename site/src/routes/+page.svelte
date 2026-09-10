<script>
	import { base } from '$app/paths';
	import Clip from '$lib/Clip.svelte';
	import Markdown from '$lib/Markdown.svelte';
	import ProvenancePin from '$lib/ProvenancePin.svelte';
	import Shot from '$lib/Shot.svelte';
	import { issues, repo } from '$lib/site.js';
	import { reveal } from '$lib/reveal.js';

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
	<div class="page split reverse">
		<div class="split-media">
			<Clip
				name="06_load_image_mask"
				caption="An RGBA Version read back. Alpha becomes the mask output, on ComfyUI's convention."
			/>
		</div>
		<div class="split-copy">
			<h2>SG Load reads the media back into the graph.</h2>
			<p>
				Find a Version by project, link, Task, status and name. <code>pin_version_id</code> takes an
				id instead.
			</p>
			<p>
				16-bit PNG and EXR are read at full precision. The Version it read is recorded on anything
				published downstream.
			</p>
			<dl class="outputs">
				<dt>Outputs</dt>
				<dd>
					<code>image</code> <code>video</code> <code>mask</code> <code>version_id</code>
					<code>code</code> <code>colour_space</code>
				</dd>
			</dl>
		</div>
	</div>
</section>

<!-- 5. Provenance, the one pinned section -->
<ProvenancePin />

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
				<h2>Three worked graphs ship with the pack.</h2>
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
					<Shot name={template.name} alt={template.alt} />
					<figcaption><code>{template.title}</code></figcaption>
				</figure>
			{/each}
		</div>
	</div>
</section>

<!-- 8. Storage and paths -->
<section class="band" id="storage" use:reveal>
	<div class="page storage">
		<div class="storage-copy">
			<h2>Files are copied under a storage root, never moved.</h2>
			<p>
				A PublishedFile's path is under one of your site's Local File Storage roots. The server
				refuses any other path. ComfyUI writes the frames to its own output directory and the node
				copies them under the root.
			</p>
			<p>
				A publish that fails after the copy names the copies it left. A re-run overwrites the same
				paths.
			</p>
			<figure class="path">
				<figcaption class="mono-label">Sequence path, and what one publish rendered it to</figcaption>
				<pre><code>{'{entity}/{root_name}/{version_name}/{version_name}.%04d{ext}'}

/Volumes/FPT/sh010/verify_pub_rows/verify_pub_rows_v003/verify_pub_rows_v003.%04d.exr</code></pre>
			</figure>
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
			<p>
				Settings, then SG, Operating system sets the notation the path is written in, so a mac
				publish can write a Windows path.
			</p>
		</div>
		<div class="storage-shot">
			<Shot
				name="04_publish_storage_alert"
				alt="SG Publish refusing before a Run because the site has no Local File Storage"
				caption="A missing or unmounted root refuses before the Run, and names the root."
			/>
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
			<Clip
				name="05_expired_login"
				caption="An expired session keeps the link the node had, and says to sign in again."
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
		</div>
		<div class="install-run">
			<h3 class="run-title">First run</h3>
			<Markdown source={firstRun} />
			<p class="note">
				Restart ComfyUI to install or upgrade the pack. A profile edit is read on a browser refresh.
			</p>
			<Shot
				name="example-workflow"
				alt="The 00_example template open in ComfyUI after a Run"
				caption="Step 6 opens this graph."
			/>
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

<!-- 12. Not in scope -->
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

<!-- 13. What is next -->
<section class="band" id="next" use:reveal>
	<div class="page next">
		<div>
			<h2>What's next</h2>
			<Markdown source={whatsNext} />
		</div>
		<div class="next-cta">
			<p>Open an issue for the one you need, or for one that is not on the list.</p>
			<a class="button" href={issues} rel="external">Open an issue</a>
			<a class="button quiet" href={repo} rel="external">Read the source</a>
		</div>
	</div>
</section>

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

	/* 4. SG Load, 7. Templates */
	.split {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: clamp(2rem, 5vw, 4rem);
		align-items: center;
	}

	.split.reverse .split-media {
		order: -1;
	}

	.split-copy h2 {
		margin-bottom: 1.1rem;
	}

	.outputs {
		margin: 1.75rem 0 0;
		padding-top: 1.25rem;
		border-top: 1px solid var(--line);
	}

	.outputs dt {
		color: var(--muted);
		font-size: 0.8125rem;
		margin-bottom: 0.6rem;
	}

	.outputs dd {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
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

	.gallery figcaption {
		margin-top: 0.7rem;
		color: var(--muted);
		font-size: 0.875rem;
	}

	/* 8. Storage */
	.storage {
		display: grid;
		grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
		gap: clamp(2rem, 5vw, 4rem);
		align-items: start;
	}

	.storage h2 {
		margin-bottom: 1.1rem;
	}

	.path {
		margin: 2rem 0 1.75rem;
	}

	.path figcaption {
		margin-bottom: 0.6rem;
	}

	.path pre {
		margin: 0;
		font-size: 0.75rem;
		white-space: pre;
	}

	.storage-shot {
		position: sticky;
		top: 96px;
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
		margin-top: 2.25rem;
		padding-top: 2rem;
		border-top: 1px solid var(--line);
	}

	.scope p {
		margin: 0;
		color: var(--muted);
		max-width: 44ch;
	}

	/* 13. What is next */
	.next {
		display: grid;
		grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
		gap: clamp(2rem, 5vw, 4rem);
		align-items: start;
	}

	.next h2 {
		margin-bottom: 1.25rem;
	}

	.next-cta {
		border: 1px solid var(--line);
		border-radius: var(--r);
		background: var(--sunk);
		padding: clamp(1.25rem, 2.4vw, 1.9rem);
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 0.75rem;
	}

	.next-cta p {
		margin: 0 0 0.5rem;
	}

	@media (max-width: 900px) {
		.hero-grid,
		.contrast,
		.split,
		.storage,
		.paths,
		.install,
		.doctor,
		.next,
		.scope {
			grid-template-columns: minmax(0, 1fr);
		}

		.facts,
		.bento {
			grid-template-columns: minmax(0, 1fr);
			gap: 1.5rem;
		}

		.split.reverse .split-media {
			order: 0;
		}

		.storage-shot {
			position: static;
		}

		.gallery {
			grid-auto-columns: minmax(82%, 1fr);
		}
	}
</style>
