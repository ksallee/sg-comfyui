<script>
	import Head from '$lib/Head.svelte';
	import { base } from '$app/paths';
	import { repo } from '$lib/site.js';
</script>

<svelte:head>
	<Head title="For an agent. SG ComfyUI" description="The entry point for an agent: the offline check, which install this is, which document answers which question, and the four procedures." />
</svelte:head>

<h1>For an agent</h1>
<p class="lede">
	This pack is two ComfyUI nodes. SG Publish sends a generation to Flow Production Tracking as a
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

<h2>Which install this is</h2>
<table>
	<thead>
		<tr>
			<th scope="col">file</th>
			<th scope="col">the Registry pack</th>
			<th scope="col">the repo checkout</th>
		</tr>
	</thead>
	<tbody>
		<tr><td><code>__init__.py</code>, <code>src/</code>, <code>web/</code>, <code>example_workflows/</code></td><td>yes</td><td>yes</td></tr>
		<tr><td><code>README.md</code>, <code>INSTALL.md</code>, <code>DESIGN.md</code>, <code>CLAUDE.md</code>, <code>AGENTS.md</code></td><td>yes</td><td>yes</td></tr>
		<tr><td><code>.claude/commands/</code>, <code>tools/doctor.py</code></td><td>yes</td><td>yes</td></tr>
		<tr><td><code>tests/</code>, the rest of <code>tools/</code>, <code>site/</code>, <code>RELEASE.md</code></td><td>no</td><td>yes</td></tr>
	</tbody>
</table>
<p>
	Manager updates the pack. <code>git pull</code> updates the checkout. Changing the code needs the
	checkout.
</p>

<h2>Documents</h2>
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

<h2>Procedures</h2>
<p>
	<code>.claude/commands/</code> has four procedures. They are plain markdown with no Claude Code in
	them. Follow the file whether or not your harness has slash commands.
</p>
<table>
	<thead>
		<tr><th scope="col">file</th><th scope="col">does</th><th scope="col">also needs</th></tr>
	</thead>
	<tbody>
		<tr><td><code>setup.md</code></td><td>a first run, from the connection to the example workflow</td><td>nothing</td></tr>
		<tr><td><code>inspect-site.md</code></td><td>measure one project and write <code>profile.local.json</code></td><td>the <code>sg-groundtruth</code> checkout</td></tr>
		<tr><td><code>track-workflow.md</code></td><td>put the nodes into a graph the operator already uses</td><td>nothing</td></tr>
		<tr><td><code>task.md</code></td><td>do a job against the API, grounded in the corpus</td><td>the <code>sg-groundtruth</code> checkout</td></tr>
	</tbody>
</table>

<p>
	<a href="{base}/docs/profile">The profile</a> says where to clone <code>sg-groundtruth</code>.
</p>

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

<h2>Positional order</h2>
<ul>
	<li><code>widgets_values</code> is positional. Append a widget, never insert or remove one. The order is declared once, in <code>widgets.py</code>.</li>
	<li>Outputs are positional. The order in <code>RETURN_NAMES</code> is frozen from the first release. Append only.</li>
</ul>

<p><a href={repo} rel="external">The source is on GitHub.</a></p>
