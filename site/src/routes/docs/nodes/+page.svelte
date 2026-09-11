<script>
	import { base } from '$app/paths';
	import Shot from '$lib/Shot.svelte';
</script>

<svelte:head>
	<title>The two nodes. Flow Production Tracking for ComfyUI</title>
	<meta name="description" content="What SG Publish writes to a Version, what SG Load reads back, and what each node reports before a Run." />
</svelte:head>

<h1>The two nodes</h1>
<p class="lede">
	SG Publish records a generation. SG Load reads one back. Nothing here generates, encodes or
	decodes.
</p>

<h2>SG Publish</h2>
<ul>
	<li>Creates a Version linked to a Shot, an Asset, or whatever your site links Versions to.</li>
	<li>Reads project, link, Task and status live from your site.</li>
	<li>Writes nine typed fields: generator, model, prompt, negative prompt, seed, sampler, steps, CFG, lineage.</li>
	<li>Attaches the workflow and a <code>.provenance.json</code> record.</li>
	<li>Uploads review media that plays in a browser.</li>
	<li>Registers the frames or the movie as PublishedFiles when Create Published Files is ticked.</li>
	<li>Writes frames as 8-bit PNG, 16-bit PNG or EXR 32-bit float, picked on the format widget.</li>
</ul>

<Shot
	name="sg-publish-node"
	alt="SG Publish in ComfyUI after a Run, showing the Version it will create and the last one it made"
	caption="Before a Run the panel says what this Run will publish. After a Run it says what the last one did."
/>

<Shot
	name="sg-publish-info"
	alt="The side panel on Info, listing each SG Publish input with its type and description"
	caption="The side panel on Info: each SG Publish input, its type and what it sets."
/>

<h2>SG Load</h2>
<ul>
	<li>Finds a Version by project, link, Task, status and name. <code>pin_version_id</code> takes an id instead.</li>
	<li>Outputs <code>image</code>, <code>video</code>, <code>mask</code>, <code>version_id</code>, <code>code</code>, <code>colour_space</code>.</li>
	<li>Reads 16-bit PNG and EXR at full precision.</li>
	<li>Records the Version it read on anything published downstream.</li>
</ul>

<Shot
	name="sg-load-node"
	alt="SG Load in ComfyUI on an EXR Version, showing the format line, the image and the mask"
	caption="SG Load on an EXR Version: the format line, the provenance it records, the image and the mask."
/>

<Shot
	name="sg-load-info"
	alt="The side panel on Info, listing each SG Load input and output with its type and description"
	caption="The side panel on Info: each SG Load input and output, with its type."
/>

<h2>In the editor</h2>
<ul>
	<li>Settings, then SG: site address, sign-in, project, publish defaults.</li>
	<li>SG Site Setup, in that group: counts the nine provenance fields on the site, creates the missing ones.</li>
	<li>Sync from SG on a node forces a read past the 600 second lookup cache.</li>
	<li>Typing <code>{'{'}</code> in root name or version name offers a Default row that writes the Settings template into the field.</li>
</ul>

<h2>Known limits</h2>
<ul>
	<li>A loader inside a ComfyUI subgraph is replaced there, not promoted to the top level.</li>
	<li>A zip uploaded to a Version is not unpacked. SG Load returns it unchanged.</li>
</ul>

<p>
	The output order is frozen from the first release, like the widget order. See
	<a href="{base}/docs/provenance">the provenance fields</a> for what SG Publish writes.
</p>
