<!--
	One Version: its picture, its name, the fields a reviewer looks at first, its provenance, and
	its lineage: the Versions it was generated from, and theirs. A Version in the lineage opens on
	click.
-->
<script lang="ts">
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Plus from '@lucide/svelte/icons/plus';
	import {
		cellValue,
		type EntityRow,
		type FieldSchema,
		type SgContext,
		type StatusRecord
	} from 'sg-widgets-core';
	import FieldValue from '$lib/components/field-value.svelte';
	import Thumbnail from '$lib/components/thumbnail.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import {
		conceptField,
		detailRows,
		lineageField,
		provenanceRows,
		STANDARD_FIELDS,
		type DetailRow,
		type ProvenanceField
	} from '$lib/pure/detail-rows';
	import { readLineage, type LineageNode } from '$lib/lineage';
	import { lineageInfo } from '$lib/pure/lineage-info';
	import StatusGlyph from '$lib/components/status-glyph.svelte';
	import { loadValues, VERSION_FIELDS, type LoadValues } from '$lib/pure/load-values';

	type Props = {
		context: SgContext;
		version: EntityRow;
		provenance: Promise<ProvenanceField[]>;
		/** What the back button says: where it goes. */
		backLabel: string;
		onBack: () => void;
		/** Opens another Version's detail, from the lineage. */
		onOpen: (row: EntityRow) => void;
		onAdd: (values: LoadValues) => void;
	};

	let { context, version, provenance, backLabel, onBack, onOpen, onAdd }: Props = $props();

	type Detail = {
		row: EntityRow;
		schema: Record<string, FieldSchema>;
		statuses: Record<string, StatusRecord>;
		standard: DetailRow[];
		recorded: DetailRow[];
		/** The field the lineage is read from, or null when the project records none. */
		lineage: string | null;
		/** The field the model is recorded in, or null. */
		model: string | null;
	};

	async function load(id: number): Promise<Detail> {
		const [schema, mapped, byCode] = await Promise.all([
			context.schema.fields('Version'),
			provenance,
			context.statuses.byCode()
		]);
		const standard = detailRows(STANDARD_FIELDS, schema);
		const recorded = provenanceRows(mapped, schema);
		const lineage = lineageField(mapped, schema);
		const model = conceptField(mapped, schema, 'model');
		const fields = [
			...new Set([
				...VERSION_FIELDS,
				...standard.map((r) => r.field),
				...recorded.map((r) => r.field),
				...(lineage ? [lineage] : [])
			])
		];
		const row = await context.client.read('Version', id, { fields });
		return { row, schema, statuses: Object.fromEntries(byCode), standard, recorded, lineage, model };
	}

	/** Versions by id, with what a lineage row draws and what opening one needs. */
	function reader(fields: string[]) {
		return async (ids: number[]) =>
			(
				await context.client.search('Version', {
					filters: { logical_operator: 'and', conditions: [['id', 'in', ids]] },
					fields: [...VERSION_FIELDS, ...fields],
					page: { size: ids.length }
				})
			).data;
	}

	function linkOf(row: EntityRow) {
		const data = row.relationships.entity?.data;
		return data && !Array.isArray(data) ? data : null;
	}

	/** The tooltip of a lineage row: the name, who made it and when. */
	function tooltip(row: EntityRow, name: string): string {
		const artist = (row.relationships.user?.data as { name?: string } | null)?.name;
		const created = row.attributes.created_at;
		const date = typeof created === 'string' ? new Date(created).toLocaleDateString() : '';
		return [name, artist, date].filter(Boolean).join(' · ');
	}

	type Lineage = {
		root: LineageNode | null;
		statuses: Record<string, StatusRecord>;
		model: string | null;
		link: ReturnType<typeof linkOf>;
	};

	const detail = $derived(load(version.id));
	// Read after the detail, so the fields show while the tree is read.
	const tree = $derived(
		detail.then(async (d) => ({
			root: d.lineage
				? await readLineage(d.row, d.lineage, reader([d.lineage, ...(d.model ? [d.model] : [])]))
				: null,
			statuses: d.statuses,
			model: d.model,
			link: linkOf(d.row)
		}))
	);
	const name = $derived(String(version.attributes.code ?? version.id));
</script>

<!-- The right padding and the stable gutter keep the status icons clear of the scrollbar. -->
<div class="flex h-full min-h-0 flex-col gap-3 overflow-y-auto pr-2 [scrollbar-gutter:stable]">
	<div class="flex items-center justify-between gap-2">
		<Button variant="ghost" size="sm" onclick={onBack}>
			<ArrowLeft />
			{backLabel}
		</Button>
		<Button size="sm" onclick={() => onAdd(loadValues(version))}>
			<Plus />
			Add to graph
		</Button>
	</div>

	<!-- Full width: the height follows the 16:9 aspect. -->
	<Thumbnail
		src={cellValue(version, 'image') as string | null}
		alt=""
		size="lg"
		entityType="Version"
		class="h-auto w-full"
	/>
	<h3 class="truncate text-sm font-medium" title={name}>{name}</h3>

	{#await detail}
		<p class="text-muted-foreground text-xs">Reading the Version…</p>
	{:then { row, schema, statuses, standard, recorded }}
		{#snippet rows(list: DetailRow[])}
			<dl class="grid grid-cols-[max-content_minmax(0,1fr)] items-baseline gap-x-3 gap-y-2 text-xs">
				{#each list as r (r.field)}
					<dt class="text-muted-foreground">{r.label}</dt>
					<dd class="min-w-0 break-words">
						<FieldValue
							value={cellValue(row, r.field)}
							dataType={r.dataType}
							field={schema[r.field]}
							{statuses}
							{context}
							density="compact"
						/>
					</dd>
				{/each}
			</dl>
		{/snippet}

		{@render rows(standard)}

		<section class="flex flex-col gap-2">
			<h4 class="text-muted-foreground text-xs font-medium tracking-wide uppercase">Provenance</h4>
			{#if recorded.length}
				{@render rows(recorded)}
			{:else}
				<p class="text-muted-foreground text-xs">
					This project records provenance in the description, or has no provenance fields.
				</p>
			{/if}
		</section>
	{:catch error}
		<p class="text-destructive text-xs">{error instanceof Error ? error.message : String(error)}</p>
	{/await}

	{#snippet branch(nodes: LineageNode[], nested: boolean, info: Lineage)}
		<ul class={['flex flex-col gap-0.5', nested && 'border-border ml-3 border-l pl-2']}>
			{#each nodes as n (n.row.id)}
				{@const name = String(n.row.attributes.code ?? n.row.id)}
				{@const line = lineageInfo(n.row, info.model, info.link)}
				{@const status = info.statuses[String(n.row.attributes.sg_status_list ?? '')] ?? null}
				<li class="flex flex-col gap-0.5">
					<button
						type="button"
						class="hover:bg-accent focus-visible:ring-ring flex w-full min-w-0 items-center gap-2 rounded-md p-1 text-left outline-none focus-visible:ring-2 disabled:pointer-events-none"
						disabled={n.stub}
						title={tooltip(n.row, name)}
						onclick={() => onOpen(n.row)}
					>
						<Thumbnail
							src={cellValue(n.row, 'image') as string | null}
							alt=""
							size="sm"
							entityType="Version"
						/>
						<span class="flex min-w-0 flex-1 flex-col">
							<span class="truncate text-xs">{name}</span>
							{#if n.repeat}
								<span class="text-muted-foreground text-[11px]">Listed elsewhere in the tree.</span>
							{:else if n.stub}
								<span class="text-muted-foreground text-[11px]">Cannot be read.</span>
							{:else if line.model || line.elsewhere}
								<span class="text-muted-foreground truncate text-[11px]">
									{[line.model, line.elsewhere && `from ${line.elsewhere}`].filter(Boolean).join(' · ')}
								</span>
							{/if}
							{#if n.more}
								<span class="text-muted-foreground text-[11px]">Open it to see its sources.</span>
							{/if}
						</span>
						{#if status && !n.repeat}
							<span class="shrink-0" title={status.name}>
								<StatusGlyph {status} siteUrl={context.siteUrl} fallback class="size-3.5" />
							</span>
						{/if}
					</button>
					{#if n.parents.length}
						{@render branch(n.parents, true, info)}
					{/if}
				</li>
			{/each}
		</ul>
	{/snippet}

	{#await tree then info}
		{#if info.root}
			<section class="flex flex-col gap-2 pb-2">
				<h4 class="text-muted-foreground text-xs font-medium tracking-wide uppercase">Lineage</h4>
				{#if info.root.parents.length}
					{@render branch(info.root.parents, false, info)}
				{:else}
					<p class="text-muted-foreground text-xs">Not generated from another Version.</p>
				{/if}
			</section>
		{/if}
	{:catch error}
		<p class="text-destructive text-xs">{error instanceof Error ? error.message : String(error)}</p>
	{/await}
</div>
