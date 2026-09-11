<script>
	import { base } from '$app/paths';
	import Markdown from '$lib/Markdown.svelte';
	import Shot from '$lib/Shot.svelte';
	import firstRun from '$lib/readme/first-run.md?raw';
</script>

<svelte:head>
	<title>First run. Flow Production Tracking for ComfyUI</title>
	<meta name="description" content="Eight steps from the Settings dialog to a published Version, and what a farm does instead of step three." />
</svelte:head>

<h1>First run</h1>

<Markdown source={firstRun} />

<p>
	A farm enters a Script name and Application key under Script Authentication instead of step 3. An
	agent follows the same steps with <code>/setup</code>.
</p>
<p>
	Restart ComfyUI to install or upgrade the pack. A profile edit is read on a browser refresh.
</p>

<Shot
	name="example-workflow"
	alt="The 00_example template open in ComfyUI after a Run"
	caption="Step 6 opens this graph. SG Publish creates the Version, SG Load reads it back."
/>

<h2>Signing in</h2>
<p>Both paths are under Settings, then SG.</p>
<h3>A person, at a workstation</h3>
<p>
	Press Log in under Log In As Yourself. Approve the request in the browser tab. The nodes publish as
	you.
</p>
<h3>A script, on a farm or a machine nobody signs in on</h3>
<p>
	Make the script under Admin, then Scripts, in Flow Production Tracking. Enter its Script name and
	Application key under Script Authentication. The script needs read on Projects, Versions, Tasks and
	every entity type you link Versions to, plus create on Version and upload of media.
</p>
<p>Press Test either way. It reports who the nodes publish as.</p>

<h2>After the first Run</h2>
<p>
	Without a measured profile the pickers run on the site's own defaults, which suit a Shot-linked
	show. <code>/inspect-site</code> measures one project and writes
	<a href="{base}/docs/profile"><code>profile.local.json</code></a>.
</p>
<p>
	An empty root name or version name shows the Settings template greyed inside it.
	<code>/track-workflow</code> adds the nodes to a graph you already use.
</p>
