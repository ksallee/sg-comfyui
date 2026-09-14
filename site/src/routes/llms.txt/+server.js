import { text } from '@sveltejs/kit';
import { llmsTxt } from '$lib/seo.js';

export const prerender = true;
export const trailingSlash = 'never';

export const GET = () => text(llmsTxt());
