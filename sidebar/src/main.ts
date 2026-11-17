/**
 * Mounts the SG sidebar in a shadow root, so its styles and ComfyUI's stay apart.
 *
 * `web/sg_sidebar.js` registers the ComfyUI tab and calls `mountSidebar`. The widgets read the
 * site through the relay at `/sg/rest` (`relay.py`), with `RestClient`.
 */
import { mount, unmount } from 'svelte';
import { createSgContext, RestClient, type EntityRef } from 'sg-widgets-core';
import css from './app.css?inline';
import Sidebar from './Sidebar.svelte';
import { splitForShadow } from '$lib/pure/shadow-css';
import type { LoadValues } from '$lib/pure/load-values';
import type { ProvenanceField } from '$lib/pure/detail-rows';

export { DRAG_TYPE } from '$lib/drag';
export { LOAD_NODE, type LoadValues } from '$lib/pure/load-values';
export { startProject } from '$lib/pure/start-project';

export type SidebarOptions = {
	/** The relay's root, `api.apiURL('/sg/rest')`. */
	relayUrl: string;
	/** The site's web address, for links and the status sprite. */
	siteUrl: string;
	project: EntityRef | null;
	/** True when ComfyUI draws its dark palette. */
	dark: boolean;
	onAdd: (values: LoadValues) => void;
	/** The field each provenance concept is recorded in on a project, from `/sg/provenance_fields`. */
	provenanceFields: (projectId: number) => Promise<ProvenanceField[]>;
	/** Called with each project picked, so the next session opens on it. */
	onProjectChange: (project: EntityRef) => void;
};

const { document: documentCss, shadow: shadowCss } = splitForShadow(css);

function styleDocumentOnce() {
	if (!documentCss || document.querySelector('style[data-sg-sidebar]')) return;
	const style = document.createElement('style');
	style.dataset.sgSidebar = '';
	style.textContent = documentCss;
	document.head.append(style);
}

/** Draws the sidebar into `host` and returns the function that removes it. */
export function mountSidebar(host: HTMLElement, options: SidebarOptions): () => void {
	styleDocumentOnce();
	const root = host.shadowRoot ?? host.attachShadow({ mode: 'open' });
	const style = document.createElement('style');
	style.textContent = shadowCss;
	const target = document.createElement('div');
	target.className = options.dark ? 'sg-sidebar dark' : 'sg-sidebar';
	// The popups' layer. It has no height of its own: a popup is positioned by floating-ui.
	const portal = document.createElement('div');
	portal.className = options.dark ? 'dark' : '';
	root.replaceChildren(style, target, portal);

	// The relay adds this ComfyUI's credentials. The token here is a placeholder it ignores.
	const client = new RestClient({ siteUrl: options.relayUrl, token: () => 'relay' });
	const context = createSgContext({ client, siteUrl: options.siteUrl });
	const app = mount(Sidebar, {
		target,
		props: {
			context,
			portal,
			project: options.project,
			onAdd: options.onAdd,
			provenanceFields: options.provenanceFields,
			onProjectChange: options.onProjectChange
		}
	});
	return () => unmount(app);
}
