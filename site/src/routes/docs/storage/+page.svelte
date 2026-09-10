<script>
	import { base } from '$app/paths';
	import Shot from '$lib/Shot.svelte';
</script>

<svelte:head>
	<title>Storage and paths. Flow Production Tracking for ComfyUI</title>
	<meta name="description" content="Local File Storage roots, the two path templates, the tokens they take, and what a failed publish leaves behind." />
</svelte:head>

<h1>Storage and paths</h1>
<p class="lede">
	A PublishedFile's path is under one of your site's Local File Storage roots. The server refuses any
	other path.
</p>

<h2>Copying</h2>
<ul>
	<li>ComfyUI writes the frames to its own output directory. The node copies them under the root.</li>
	<li>Originals are never moved.</li>
	<li>A publish that fails after the copy names the copies it left. Nothing is deleted, so a second attempt costs a copy rather than a re-render.</li>
	<li>A re-run overwrites the same paths.</li>
</ul>

<Shot
	name="04_publish_storage_alert"
	alt="SG Publish refusing before a Run because the site has no Local File Storage"
	caption="A missing, read-only or unmounted root refuses before the Run and names the root."
/>

<h2>Path templates</h2>
<p>Sequence path and Movie path, under Settings, then SG, SG Publish Defaults.</p>
<pre><code>{'{entity}/{root_name}/{version_name}/{version_name}.%04d{ext}'}
{'{entity}/{root_name}/{version_name}{ext}'}</code></pre>

<h2>Tokens</h2>
<table>
	<thead>
		<tr><th scope="col">token</th><th scope="col">what it is</th></tr>
	</thead>
	<tbody>
		<tr><td><code>{'{version}'}</code></td><td>the publish revision</td></tr>
		<tr><td><code>%04d</code> <code>####</code> <code>@@@@</code></td><td>the frame number</td></tr>
		<tr><td><code>{'{entity.Shot.code}'}</code></td><td>a dotted field path, to any depth</td></tr>
		<tr><td><code>{'{version:03d}'}</code></td><td>Python's format spec</td></tr>
		<tr><td><code>[optional blocks]</code></td><td>dropped when the fields inside are empty</td></tr>
		<tr><td><code>v%04d</code></td><td>printf padding, a synonym for a version spec</td></tr>
	</tbody>
</table>
<p>
	A token with no value drops out with its separator. The extension follows the files, not the
	template. <code>tools/doctor.py</code> renders every template in the profile against a sample
	publish and names any token that comes back with nothing.
</p>

<h2>Windows notation</h2>
<p>
	Settings, then SG, Operating system sets the notation the path is written in, so a mac publish can
	write a Windows path. The profile key is <code>path_platform</code>.
</p>

<h2>Sequences</h2>
<p>
	The only out-of-the-box way to register an image sequence is a PublishedFile linked to the Version.
	Tick Create Published Files. A clip beside frames stays review only until
	<code>register_movie</code> is <code>true</code>.
</p>

<p>The keys are on <a href="{base}/docs/profile">the profile page</a>.</p>
