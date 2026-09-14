<script>
	import { page } from '$app/state';
	import { localBase, origin, shareImage, siteName } from '$lib/seo.js';

	/** The title, the description, the canonical URL and the share card of one page. */
	let { title, description } = $props();

	// The canonical is where the page is served, whatever base a local build uses.
	const url = $derived(
		origin + (page.url.pathname.startsWith(localBase + '/') ? page.url.pathname.slice(localBase.length) : page.url.pathname)
	);
</script>

<svelte:head>
	<title>{title}</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={url} />
	<meta property="og:type" content="website" />
	<meta property="og:site_name" content={siteName} />
	<meta property="og:title" content={title} />
	<meta property="og:description" content={description} />
	<meta property="og:url" content={url} />
	<meta property="og:image" content={shareImage} />
	<meta property="og:image:width" content="1200" />
	<meta property="og:image:height" content="630" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content={title} />
	<meta name="twitter:description" content={description} />
	<meta name="twitter:image" content={shareImage} />
</svelte:head>
