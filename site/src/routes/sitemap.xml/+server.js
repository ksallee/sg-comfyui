import { sitemap } from '$lib/seo.js';

export const prerender = true;
export const trailingSlash = 'never';

export const GET = () =>
	new Response(sitemap(), { headers: { 'content-type': 'application/xml; charset=utf-8' } });
