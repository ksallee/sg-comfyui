<svelte:head>
	<title>Troubleshooting. Flow Production Tracking for ComfyUI</title>
	<meta name="description" content="The symptom, then the fix: a 404 Settings dialog, empty pickers, a stale lookup, a refused storage, an unnamed client." />
</svelte:head>

<h1>Troubleshooting</h1>
<p class="lede">
	Run <code>tools/doctor.py</code> first, with the interpreter ComfyUI runs on. It names both when
	they differ.
</p>

<h2>The Settings dialog says 404</h2>
<p>
	The running ComfyUI started before the pack was installed, so it registered no routes. Restart
	ComfyUI and reload the page. If it still says 404, read the startup log for the pack: a pack whose
	import failed registers nothing.
</p>

<h2>The pickers are empty</h2>
<p>
	Open Settings, then SG, and press Test. An empty project list with a passing Test means the account
	can see no project. A passing Test and an empty link list means this project has no entity of that
	type yet.
</p>

<h2>A new Shot, Task or Version does not show up</h2>
<p>The editor's lookups are cached for 600 seconds. Press Sync from SG on the node to force a read.</p>

<h2>Nothing works and the pack looks installed</h2>
<p>
	Run <code>tools/doctor.py</code> with the interpreter ComfyUI runs on. Installing the requirements
	into a different interpreter leaves the pack loaded, the pickers empty, and no error naming a
	cause.
</p>

<h2>Create Published Files refuses, and the site has no storage</h2>
<p>
	Add a Local File Storage under Site Preferences, then File Management, in Flow Production Tracking.
	Name it under Settings, then SG, Storage. Until then, untick Create Published Files and publish
	review media.
</p>

<h2>The storage root is not mounted</h2>
<p>
	The publish stops before the Version exists and names the root. Mount it, or name a storage this
	machine can see.
</p>

<h2>Versions read <code>ComfyUI (unknown client)</code></h2>
<p>
	The client that POSTed <code>/prompt</code> did not name itself. The standard frontend sends
	<code>comfyui-frontend</code>. Set it in your own submitter:
</p>
<pre><code>POST /prompt  &#123;"prompt": &#123;...&#125;, "extra_data": &#123;"comfy_usage_source": "my-farm-submitter"&#125;&#125;</code></pre>

<h2>A publish failed after the frames were copied</h2>
<p>
	The copies stay where they are and the error names their paths. Nothing is deleted, so a second
	attempt costs a copy rather than a re-render.
</p>

<h2>The session has expired</h2>
<p>
	The node keeps the link it had and says to sign in again. Press Log in under Settings, then SG, and
	run again.
</p>
