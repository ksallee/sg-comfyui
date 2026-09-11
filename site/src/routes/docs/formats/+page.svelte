<script>
	import { base } from '$app/paths';
	import Shot from '$lib/Shot.svelte';
</script>

<svelte:head>
	<title>Formats and colour space. SG ComfyUI</title>
	<meta name="description" content="The three frame formats, what writes them, what review media is, and how a declared colour space is recorded." />
</svelte:head>

<h1>Formats and colour space</h1>
<p class="lede">
	This pack records. It does not make media. Frames are written by ComfyUI's image encoder in the
	format the operator picked, clips by <code>VideoInput.save_to()</code>, and both are read back by
	ComfyUI's decoder.
</p>

<h2>Frame formats</h2>
<table>
	<thead>
		<tr><th scope="col">format</th><th scope="col">what it is for</th></tr>
	</thead>
	<tbody>
		<tr><td>8-bit PNG</td><td>The plain case. Review media is 8-bit whatever the frames are.</td></tr>
		<tr><td>16-bit PNG</td><td>SG Load reads it back at full precision.</td></tr>
		<tr><td>EXR 32-bit float</td><td>Pixels are written unchanged.</td></tr>
	</tbody>
</table>
<p>The format widget on SG Publish picks one. The extension follows the files, not the path template.</p>

<Shot
	name="01_publish_before_run_exr"
	alt="SG Publish before a Run with the format widget set to EXR 32-bit float"
	caption="The panel says what this Run will publish, and in what format, before the Run."
/>

<h2>Video</h2>
<ul>
	<li>A VIDEO read from a file is uploaded as that file, byte for byte.</li>
	<li>Anything else is written by ComfyUI's <code>VideoInput.save_to()</code>, with its colour space, bit depth and audio.</li>
	<li>ComfyUI's IMAGE is a float32 tensor with no file behind it, so a still is encoded before upload.</li>
</ul>

<h2>Review media</h2>
<p>
	Review media is 8-bit and is derived, so it may be transcoded. A deliverable file is never
	transformed. Pillow writes the 8-bit review still and nothing else.
</p>
<p>
	A Version has one uploaded media file (probe 022). <code>sg_path_to_frames</code> and
	<code>sg_path_to_movie</code> are path references, and RV reads them to switch between the
	transcode and the source.
</p>

<h2>Colour space</h2>
<ul>
	<li>Colour space is recorded, never applied.</li>
	<li>The declared value goes in the PublishedFile's description.</li>
	<li>SG Load returns it as the <code>colour_space</code> output.</li>
	<li>Core ComfyUI has no colour management. <a href="{base}/docs/install">Install</a> says what to add for a colour-managed pipeline.</li>
</ul>

<Shot
	name="07_load_exr"
	alt="SG Load on an EXR Version in ComfyUI, showing the format line and the colour space output"
	caption="SG Load reports the format before a run and returns the colour space it was told."
/>
