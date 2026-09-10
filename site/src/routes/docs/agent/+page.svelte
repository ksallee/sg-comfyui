<script>
	import { repo } from '$lib/site.js';
</script>

<svelte:head>
	<title>For an agent. Flow Production Tracking for ComfyUI</title>
	<meta name="description" content="The entry point for an agent: the offline check, which document answers which question, and the three procedures." />
</svelte:head>

<h1>For an agent</h1>
<p class="lede">
	This repo is two ComfyUI nodes. SG Publish sends a generation to Flow Production Tracking as a
	Version with the model, prompt, seed, sampler and workflow that produced it. SG Load reads a
	Version's media back into a graph. Nothing here makes images.
</p>

<h2>Run this first</h2>
<pre><code>&lt;comfy-python&gt; tools/doctor.py            # the interpreter, the paths, the profile
&lt;comfy-python&gt; tools/doctor.py --site     # also the connection, the fields, the storage, the links</code></pre>
<p>
	It prints one line per thing a publish needs, with the fix appended where it fails. It exits
	non-zero on anything that would stop a publish.
</p>

<h2>Which document</h2>
<table>
	<thead>
		<tr><th scope="col">job</th><th scope="col">read</th></tr>
	</thead>
	<tbody>
		<tr><td>What the nodes do, and a first run</td><td><code>README.md</code></td></tr>
		<tr><td>A local file, an interpreter, a command, a profile key, a fix</td><td><code>INSTALL.md</code></td></tr>
		<tr><td>Changing this code</td><td><code>CLAUDE.md</code>, then <code>DESIGN.md</code></td></tr>
	</tbody>
</table>

<h2>The procedures</h2>
<p>
	<code>.claude/commands/</code> has three procedures. They are plain markdown with no Claude Code in
	them. Follow the file whether or not your harness has slash commands.
</p>
<table>
	<thead>
		<tr><th scope="col">file</th><th scope="col">does</th></tr>
	</thead>
	<tbody>
		<tr><td><code>setup.md</code></td><td>a first run, from the connection to the example workflow</td></tr>
		<tr><td><code>inspect-site.md</code></td><td>measure one project and write <code>profile.local.json</code></td></tr>
		<tr><td><code>track-workflow.md</code></td><td>put the nodes into a graph the operator already uses</td></tr>
	</tbody>
</table>

<h2>Command lines</h2>
<table>
	<thead>
		<tr><th scope="col">command</th><th scope="col">needs</th></tr>
	</thead>
	<tbody>
		<tr><td><code>&lt;comfy-python&gt; tools/doctor.py [--site]</code></td><td>nothing without <code>--site</code></td></tr>
		<tr><td><code>&lt;comfy-python&gt; src/comfyui_sg/instrument.py &lt;wf.json&gt;</code></td><td>no site, no profile, no torch</td></tr>
		<tr><td><code>PYTHONPATH=src &lt;comfy-python&gt; -m comfyui_sg.fields</code></td><td><code>.env.local</code></td></tr>
		<tr><td><code>PYTHONPATH=src &lt;comfy-python&gt; -m comfyui_sg.seed &lt;file&gt; ...</code></td><td><code>.env.local</code>, <code>profile.local.json</code></td></tr>
	</tbody>
</table>
<ul>
	<li><code>PYTHONPATH=src</code> is required for every <code>-m comfyui_sg.*</code>. The package is under <code>src/</code> and nothing installs it.</li>
	<li><code>instrument.py</code> and <code>doctor.py</code> are run as files. <code>-m</code> would import the package <code>__init__</code> and therefore torch.</li>
	<li>None of these reads Settings. They read <code>.env.local</code> in the pack directory, or the same three keys in the environment.</li>
</ul>

<h2>Two rules that break saved graphs</h2>
<ul>
	<li><code>widgets_values</code> is positional. Append a widget, never insert or remove one. The order is declared once, in <code>widgets.py</code>.</li>
	<li>Outputs are positional. The order in <code>RETURN_NAMES</code> is frozen from the first release. Append only.</li>
</ul>

<p><a href={repo} rel="external">The source is on GitHub.</a></p>
