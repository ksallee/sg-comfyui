<script>
	import Shot from '$lib/Shot.svelte';
	import { provenance } from '$lib/site.js';
</script>

<svelte:head>
	<title>Provenance fields. SG ComfyUI</title>
	<meta name="description" content="The nine typed fields on Version, where each value comes from, and what a site without them records instead." />
</svelte:head>

<h1>Provenance fields</h1>
<p class="lede">
	Nine typed fields on Version, created under Settings, then SG, SG Site Setup. A publish does not
	need them.
</p>

<table>
	<thead>
		<tr>
			<th scope="col">field</th>
			<th scope="col">programmatic name</th>
			<th scope="col">from</th>
		</tr>
	</thead>
	<tbody>
		{#each provenance as [label, name, from] (name)}
			<tr>
				<td>{label}</td>
				<td><code>{name}</code></td>
				<td>{from}</td>
			</tr>
		{/each}
	</tbody>
</table>

<p>
	<code>sg_ai_seed</code> is text, not a number: seeds reach 2**64-1, which no numeric field on the
	site has (probe 019).
</p>

<h2>Without the fields</h2>
<ul>
	<li>The facts go in the Version's description: the note, a blank line, then one line per fact, lineage included.</li>
	<li>Where some of the nine exist, those take their values. The description records the rest.</li>
	<li>The nodes say nothing about creating fields.</li>
</ul>

<Shot
	name="05_publish_provenance_into_description"
	alt="A Version's description holding the provenance facts, one per line, on a site with none of the nine fields"
	caption="The note, a blank line, then one line per fact."
/>

<h2>Attachments</h2>
<ul>
	<li>The record is attached as <code>.provenance.json</code>.</li>
	<li>The workflow is attached when the submitting client sent one.</li>
	<li>Provenance is scoped per branch. The node walks back through its own inputs.</li>
</ul>

<h2>Creating the fields from the command line</h2>
<pre><code>PYTHONPATH=src &lt;comfy-python&gt; -m comfyui_sg.fields</code></pre>
<ul>
	<li>It reads the schema first and creates only what is missing. Pressing twice is safe.</li>
	<li>It imports no torch.</li>
	<li>It reads a script key from <code>.env.local</code>, never from Settings.</li>
	<li>That key needs permission to create fields on Version. Most artist accounts do not have it.</li>
	<li>Field names are permanent. Deleting a field frees the field, never its name. Trashed fields cannot be listed, so a name spent here is spent site-wide forever (probe 019).</li>
</ul>

<h2>Mapping to existing fields</h2>
<p>
	Point the profile's <code>provenance.map</code> at them. Mapping onto a studio's own fields works
	and is not a release feature.
</p>

<h2>The submitting client</h2>
<p>
	A Version that reads <code>ComfyUI (unknown client)</code> means the client that POSTed
	<code>/prompt</code> did not name itself. The name is the client's own claim, in
	<code>extra_data.comfy_usage_source</code>. Set it in your own submitter:
</p>
<pre><code>POST /prompt  &#123;"prompt": &#123;...&#125;, "extra_data": &#123;"comfy_usage_source": "my-farm-submitter"&#125;&#125;</code></pre>
<p>
	A <code>Comfy-Usage-Source</code> header works too. The server copies it into
	<code>extra_data</code> only when the body left the key out.
</p>
