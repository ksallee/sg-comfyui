<!--
	The SG sidebar tab: one project's Versions, searched by name and narrowed by the filter bar.

	A tile is dragged onto the canvas, or added with its button, as an SG Load node pinned to that
	Version. A click opens the Version's detail.
-->
<script lang="ts">
	import { untrack } from 'svelte';
	import { BitsConfig } from 'bits-ui';
	import Plus from '@lucide/svelte/icons/plus';
	import {
		createEntitySource,
		emptyFilter,
		toApi3Hash,
		type EntityRef,
		type EntityRow,
		type FilterGroup,
		type SgContext,
		type WireGroup
	} from 'sg-widgets-core';
	import EntityCard from '$lib/components/entity-card.svelte';
	import EntityGrid from '$lib/components/entity-grid.svelte';
	import FilterBar from '$lib/components/filter-bar.svelte';
	import ProjectPicker from '$lib/components/project-picker.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { DRAG_TYPE } from '$lib/drag';
	import { loadValues, VERSION_FIELDS, type LoadValues } from '$lib/pure/load-values';
	import { versionFilter } from '$lib/pure/version-filter';
	import type { ProvenanceField } from '$lib/pure/detail-rows';
	import VersionDetail from './VersionDetail.svelte';

	type Props = {
		context: SgContext;
		/** Where the widgets' popups are drawn: inside the shadow root, so they are styled. */
		portal: HTMLElement;
		project: EntityRef | null;
		onAdd: (values: LoadValues) => void;
		/** The field each provenance concept is recorded in on a project. */
		provenanceFields: (projectId: number) => Promise<ProvenanceField[]>;
		/** Called with each project picked. */
		onProjectChange: (project: EntityRef) => void;
	};

	let { context, portal, project: initial, onAdd, provenanceFields, onProjectChange }: Props =
		$props();

	// The project the tab opens on, and the client. Both are read once, at mount.
	const start = untrack(() => initial);
	const client = untrack(() => context.client);

	const FACETS = ['sg_status_list', 'user', 'entity', 'sg_task'];
	// The search is typed, so the read waits for a pause.
	const DEBOUNCE_MS = 250;

	let project = $state<EntityRef | null>(start);
	let text = $state('');
	let bar = $state<FilterGroup>(emptyFilter());
	/** The Versions opened, the last one shown. The grid stays mounted under them, so its scroll is kept. */
	let opened = $state<EntityRow[]>([]);
	const shown = $derived(opened.at(-1) ?? null);

	const wire = (p: EntityRef): WireGroup => toApi3Hash(versionFilter(p, bar, text)) as WireGroup;

	const source = createEntitySource({
		client,
		entityType: 'Version',
		fields: VERSION_FIELDS,
		filters: start ? wire(start) : null,
		sort: [{ path: 'created_at', descending: true }],
		pageSize: 24
	});

	const next = $derived(project ? JSON.stringify(wire(project)) : null);

	$effect(() => {
		const filters = next;
		const timer = setTimeout(() => {
			if (filters && JSON.stringify(source.filters) !== filters) {
				void source.setFilters(JSON.parse(filters) as WireGroup);
			}
		}, DEBOUNCE_MS);
		return () => clearTimeout(timer);
	});

	$effect(() => {
		if (project && project.id !== start?.id) onProjectChange(project);
	});

	const provenance = $derived(project ? provenanceFields(project.id) : Promise.resolve([]));

	const scope = $derived(project ? versionFilter(project, emptyFilter(), '') : null);

	function drag(event: DragEvent, row: EntityRow) {
		if (!event.dataTransfer) return;
		event.dataTransfer.setData(DRAG_TYPE, JSON.stringify(loadValues(row)));
		event.dataTransfer.setData('text/plain', String(row.attributes.code ?? row.id));
		event.dataTransfer.effectAllowed = 'copy';
	}
</script>

<BitsConfig defaultPortalTo={portal}>
	<div class="bg-background text-foreground flex h-full min-h-0 flex-col gap-2 p-2">
		{#if shown}
			{#key shown.id}
				<VersionDetail
					{context}
					version={shown}
					{provenance}
					backLabel={opened.length > 1 ? 'Back' : 'Versions'}
					onBack={() => (opened = opened.slice(0, -1))}
					onOpen={(row) => (opened = [...opened, row])}
					{onAdd}
				/>
			{/key}
		{/if}
		<div class={['flex min-h-0 flex-1 flex-col gap-2', shown && 'hidden']}>
		<ProjectPicker {context} bind:value={project} placeholder="Pick a project" />
		{#if project}
			<Input type="search" placeholder="Search Versions by name" bind:value={text} />
			{#key project.id}
				<FilterBar
					entityType="Version"
					{context}
					facets={FACETS}
					value={bar}
					baseFilter={scope}
					size="sm"
					onValueChange={(value) => (bar = value)}
				/>
			{/key}
			<div class="min-h-0 flex-1">
				<!-- The grid takes the panel's height and its scroll box the space under the header. -->
				<EntityGrid
					{source}
					{context}
					class="h-full min-h-0 [&_[data-slot=entity-grid-scroll]]:min-h-0 [&_[data-slot=entity-grid-scroll]]:flex-1"
					size="sm"
					density="compact"
					maxHeight="100%"
					emptyLabel="No Version matches. Change the search or the filters."
					onSelect={(row) => (opened = [row])}
				>
					{#snippet card({ row })}
						<!-- The tile drags from anywhere. The name shows a pointer: a click opens the detail. -->
						<div
							class="group relative h-full cursor-grab active:cursor-grabbing [&_[data-slot=entity-card-name]]:cursor-pointer [&_[data-slot=entity-card-name]:hover]:underline"
							draggable="true"
							ondragstart={(event) => drag(event, row)}
							role="listitem"
						>
							<EntityCard {row} {context} variant="tile" size="sm" />
							<!-- The grid ignores a click inside this slot. -->
							<div data-slot="entity-card-actions" class="absolute top-1.5 right-1.5">
								<Button
									size="icon-sm"
									variant="secondary"
									class="cursor-pointer opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
									aria-label="Add to the graph"
									title="Add to the graph"
									onclick={() => onAdd(loadValues(row))}
								>
									<Plus />
								</Button>
							</div>
						</div>
					{/snippet}
				</EntityGrid>
			</div>
		{:else}
			<p class="text-muted-foreground text-sm">Pick a project to list its Versions.</p>
		{/if}
		</div>
	</div>
</BitsConfig>
