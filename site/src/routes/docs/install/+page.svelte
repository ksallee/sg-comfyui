<script>
	import { base } from '$app/paths';
	import Markdown from '$lib/Markdown.svelte';
	import requirements from '$lib/readme/requirements.md?raw';
	import installCommands from '$lib/readme/install-commands.md?raw';

	const doctor = `ok    Python 3.11.11 at /Users/you/ComfyUI/venv/bin/python.
ok    sg_groundtruth imports here.
ok    requests imports here.
ok    Pillow imports here.
ok    This is the interpreter ComfyUI runs on, /Users/you/ComfyUI/venv/bin/python.`;
</script>

<svelte:head>
	<title>Install. Flow Production Tracking for ComfyUI</title>
	<meta name="description" content="The interpreter to install into, the three install paths, the four local files, and the offline check." />
</svelte:head>

<h1>Install</h1>
<p class="lede">
	Install the requirements into the interpreter ComfyUI itself runs on. Installing into a different
	one leaves the pack loaded, the pickers empty, and no error naming a cause.
</p>

<h2>Requirements</h2>
<Markdown source={requirements} />

<h2>The three paths</h2>
<Markdown source={installCommands} />

<h2>Which interpreter</h2>
<table>
	<thead>
		<tr>
			<th scope="col">install</th>
			<th scope="col">the interpreter</th>
		</tr>
	</thead>
	<tbody>
		<tr><td>source</td><td><code>ComfyUI/venv/bin/python</code></td></tr>
		<tr><td>desktop</td><td>the <code>python</code> inside the app bundle</td></tr>
		<tr><td>studio</td><td>whatever your launch script names</td></tr>
	</tbody>
</table>

<p>Check which one you have:</p>

<pre><code>cd ComfyUI/custom_nodes/sg-comfyui
../../venv/bin/python tools/doctor.py</code></pre>

<pre><code>{doctor}</code></pre>

<ul>
	<li>A <code>fail</code> line names the fix.</li>
	<li><code>--site</code> adds the connection, the provenance fields, the storage roots and the link types.</li>
	<li><code>COMFYUI_PATH</code> tells the doctor where ComfyUI is. It defaults to <code>~/dev/ComfyUI</code>.</li>
	<li>The doctor exits non-zero on anything that would fail a publish. It warns on the rest.</li>
</ul>

<h2>The four local files</h2>
<p>All of them yours, none of them in git.</p>
<table>
	<thead>
		<tr>
			<th scope="col">file</th>
			<th scope="col">what it is</th>
			<th scope="col">written by</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td><code>settings.local.json</code></td>
			<td>site address, script name, application key, publish as</td>
			<td>Settings, then SG</td>
		</tr>
		<tr>
			<td><code>session.local.json</code></td>
			<td>the session token from Log in</td>
			<td>Settings, then SG</td>
		</tr>
		<tr>
			<td><code>profile.local.json</code></td>
			<td>what your site practices, per project</td>
			<td>the inspector, Settings, and you</td>
		</tr>
		<tr>
			<td><code>.env.local</code></td>
			<td>a script key for the command-line tools</td>
			<td>you</td>
		</tr>
	</tbody>
</table>

<p>
	The protected user directory is <code>&lt;ComfyUI user directory&gt;/__sg_comfyui</code>, which is
	<code>ComfyUI/user/__sg_comfyui</code> unless <code>--user-directory</code> or
	<code>--base-directory</code> moved it. It is outside <code>custom_nodes</code>, so an upgrade
	leaves it alone. ComfyUI serves no HTTP route for a <code>__</code> directory.
</p>

<h2>Colour management</h2>
<p>Core ComfyUI has none, and none of this is needed to publish. For a colour-managed pipeline:</p>
<ol>
	<li>Install the ComfyUI-OCIO pack.</li>
	<li>Set <code>OPENCV_IO_ENABLE_OPENEXR=1</code> in the environment that launches ComfyUI.</li>
	<li>Put <code>ffmpeg</code> on the path.</li>
</ol>

<p>Next: <a href="{base}/docs/first-run">First run</a>.</p>
