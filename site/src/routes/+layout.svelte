<script>
	import '../app.css';
	import Footer from '$lib/Footer.svelte';
	import Nav from '$lib/Nav.svelte';

	let { children } = $props();
</script>

<a class="skip" href="#main">Skip to content</a>
<Nav />
<main id="main">
	{@render children()}
</main>
<Footer />

<style>
	.skip {
		position: absolute;
		left: -9999px;
		top: 0;
		z-index: 40;
		background: var(--ink);
		color: var(--paper);
		padding: 0.6rem 1rem;
		border-radius: 0 0 var(--r) 0;
		text-decoration: none;
	}

	.skip:focus {
		left: 0;
	}
</style>
