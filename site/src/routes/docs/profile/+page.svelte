<script>
	const sample = `{
  "default_project": 1180,
  "projects": {
    "1180": {
      "link_type": "Shot",
      "link_field": "entity",
      "root_name": "{entity}_{sg_task.Task.step.Step.short_name}",
      "code_template": "{root_name}_v{version:03d}",
      "status": "rev",
      "published_files": {
        "storage": "primary",
        "path_template": "{entity}/{root_name}/{version_name}/{version_name}.%04d{ext}",
        "still_path_template": "{entity}/{root_name}/{version_name}{ext}",
        "movie_path_template": "{entity}/{root_name}/{version_name}{ext}",
        "register_movie": false,
        "colour_space": "sRGB"
      }
    }
  }
}`;
</script>

<svelte:head>
	<title>The profile. SG ComfyUI</title>
	<meta name="description" content="profile.local.json sets what a Version links to, what it is called, and where each provenance fact is written." />
</svelte:head>

<h1>The profile</h1>
<p class="lede">
	<code>profile.local.json</code> sets what a Version links to, what it is called, and which field
	each provenance fact is written to. It is plain JSON and hand-editing it is expected.
</p>

<p>
	Top-level keys are the site default. A <code>projects</code> block overrides them per show, so two
	graphs in one ComfyUI can publish into two projects that name Versions differently.
</p>

<pre><code>{sample}</code></pre>

<h2>Site-wide keys</h2>
<table>
	<thead>
		<tr><th scope="col">key</th><th scope="col">default</th><th scope="col">written by</th></tr>
	</thead>
	<tbody>
		<tr>
			<td><code>default_project</code></td>
			<td>none, and both nodes then ask</td>
			<td>Settings, SG Defaults</td>
		</tr>
		<tr>
			<td><code>show_all_projects</code></td>
			<td><code>false</code>, so template, demo and archived shows stay out of the picker</td>
			<td>you</td>
		</tr>
	</tbody>
</table>

<h2>Per project</h2>
<p>Each of these is valid at the top level as a site default.</p>
<table>
	<thead>
		<tr><th scope="col">key</th><th scope="col">default</th><th scope="col">written by</th></tr>
	</thead>
	<tbody>
		<tr><td><code>link_type</code></td><td><code>Shot</code>, the type a bare link name means</td><td>the inspector</td></tr>
		<tr><td><code>link_field</code></td><td><code>entity</code>, the Version field the link is written to</td><td>the inspector</td></tr>
		<tr><td><code>link_types</code></td><td>the types this show's Versions already use, most used first</td><td>you</td></tr>
		<tr><td><code>root_name</code></td><td><code>{'{entity}_{sg_task.Task.step.Step.short_name}'}</code></td><td>Settings, SG Publish Defaults</td></tr>
		<tr><td><code>code_template</code></td><td><code>{'{root_name}_v{version:03d}'}</code></td><td>Settings, SG Publish Defaults</td></tr>
		<tr><td><code>code_regex</code></td><td>derived from the version name template</td><td>the inspector</td></tr>
		<tr><td><code>status</code></td><td>none, so the site sets its own</td><td>Settings, SG Publish Defaults</td></tr>
		<tr><td><code>version_number_field</code></td><td>none, so the version number is inside the name</td><td>you</td></tr>
		<tr><td><code>widgets</code></td><td>what <code>src/comfyui_sg/widgets.py</code> declares</td><td>you</td></tr>
		<tr><td><code>provenance</code></td><td><code>{'{"mode": "fields"}'}</code>, the nine fields by their own names</td><td>you</td></tr>
	</tbody>
</table>

<h2>Inside <code>published_files</code></h2>
<table>
	<thead>
		<tr><th scope="col">key</th><th scope="col">default</th><th scope="col">written by</th></tr>
	</thead>
	<tbody>
		<tr><td><code>default</code></td><td><code>false</code>, so Create Published Files starts unticked</td><td>Settings, SG Publish Defaults</td></tr>
		<tr><td><code>storage</code></td><td>none, and the only Local File Storage when the site has exactly one</td><td>Settings, Storage</td></tr>
		<tr><td><code>path_platform</code></td><td>this machine's</td><td>Settings, Operating system</td></tr>
		<tr><td><code>path_template</code></td><td><code>{'{entity}/{root_name}/{version_name}/{version_name}.%04d{ext}'}</code></td><td>Settings, Sequence path, or sequence path on the node</td></tr>
		<tr><td><code>still_path_template</code></td><td><code>{'{entity}/{root_name}/{version_name}{ext}'}</code></td><td>Settings, Still path, or still path on the node</td></tr>
		<tr><td><code>movie_path_template</code></td><td><code>{'{entity}/{root_name}/{version_name}{ext}'}</code></td><td>Settings, Movie path, or movie path on the node</td></tr>
		<tr><td><code>register_movie</code></td><td><code>false</code>, so a clip beside frames is review only</td><td>Settings, Review movie</td></tr>
		<tr><td><code>path_to_frames</code></td><td><code>true</code></td><td>Settings, Path to Frames</td></tr>
		<tr><td><code>path_to_movie</code></td><td><code>true</code></td><td>Settings, Path to Movie</td></tr>
		<tr><td><code>colour_space</code></td><td>none, so a publish declares nothing</td><td>Settings, Colour space</td></tr>
	</tbody>
</table>

<h2>Measuring a site</h2>
<p>
	<code>/inspect-site</code> is a procedure an agent follows. The inspector under it is a script in
	the <code>sg-groundtruth</code> checkout, and you can run it yourself. Clone that checkout anywhere
	except <code>custom_nodes</code>, where ComfyUI would load it as a node pack.
</p>
<pre><code>&lt;comfy-python&gt; ~/dev/sg-groundtruth/inspect_site.py                                # list the projects
&lt;comfy-python&gt; ~/dev/sg-groundtruth/inspect_site.py --project 1180 --out &lt;profile&gt; # measure one</code></pre>
<ul>
	<li>Pass <code>--out</code>. Its default is <code>./profile.local.json</code> relative to the working directory, and the file has to be written to the path <code>tools/doctor.py</code> reports.</li>
	<li>Read the report before accepting it, starting with the link field.</li>
	<li>The code convention comes with a coverage number saying how much of the show agrees with it.</li>
	<li>Re-running keeps your edits and prints <code>(yours, kept)</code> beside each value it would have changed. <code>--overwrite</code> discards them.</li>
</ul>
