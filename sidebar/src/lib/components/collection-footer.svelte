<script lang="ts">
	import type { EntitySource, PageRange } from 'sg-widgets-core';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import * as Select from '$lib/components/ui/select/index.js';

	type Props = {
		/** The source the controls drive. */
		source: EntitySource;
		/** The numbers to draw, from core's `describePaging`. */
		pager: PageRange;
		/** The page sizes offered in `pages` mode. */
		pageSizes: number[];
		/** True while the set is being read: the arrows wait for it. */
		loading: boolean;
		/** The widget's own name, which prefixes every `data-slot` here. */
		slotName: string;
	};

	let { source, pager, pageSizes, loading, slotName }: Props = $props();

	/** What the reader has typed, until Enter or a blur takes it. */
	let pageDraft = $state('');

	function goToPage(value: string): void {
		const wanted = Number(value);
		pageDraft = '';
		if (!Number.isFinite(wanted) || wanted < 1) return;
		void source.setPage(pager.pageCount === null ? wanted : Math.min(wanted, pager.pageCount));
	}
</script>

<!--
	The footer of every collection that pages: the page size, the range and the
	arrows in `pages`, the loaded count in `more` and `scroll`. The numbers are
	core's `describePaging`, so the three collections cannot report the set
	differently.
-->
<div
	data-slot="{slotName}-footer"
	class="text-muted-foreground flex w-full min-w-0 flex-wrap items-center justify-between gap-2 text-xs"
>
	{#if pager.mode === 'pages'}
		<div data-slot="{slotName}-page-size" class="flex items-center gap-2">
			<span>Rows per page</span>
			<Select.Root
				type="single"
				value={String(pager.pageSize)}
				onValueChange={(value) => void source.setPageSize(Number(value))}
			>
				<Select.Trigger aria-label="Rows per page" class="w-auto min-w-16">
					<span data-slot="select-value" class="tabular-nums">{pager.pageSize}</span>
				</Select.Trigger>
				<Select.Content>
					{#each pageSizes as option (option)}
						<Select.Item value={String(option)} label={String(option)} />
					{/each}
				</Select.Content>
			</Select.Root>
		</div>
		<div data-slot="{slotName}-pager" class="flex items-center gap-2">
			<span data-slot="{slotName}-range" class="tabular-nums">{pager.rangeLabel}</span>
			<Button
				variant="outline"
				size="icon"
				aria-label="Previous page"
				disabled={!pager.hasPrevious || loading}
				onclick={() => void source.setPage(pager.page - 1)}
			>
				<ChevronLeft aria-hidden="true" />
			</Button>
			<Input
				type="number"
				min="1"
				inputmode="numeric"
				aria-label="Page number"
				class="w-14 text-center tabular-nums"
				value={pageDraft === '' ? String(pager.page) : pageDraft}
				oninput={(event) => (pageDraft = event.currentTarget.value)}
				onkeydown={(event) => {
					if (event.key !== 'Enter') return;
					event.preventDefault();
					goToPage(event.currentTarget.value);
				}}
				onblur={(event) => goToPage(event.currentTarget.value)}
			/>
			{#if pager.pageCount !== null}
				<span class="tabular-nums">of {pager.pageCount}</span>
			{/if}
			<Button
				variant="outline"
				size="icon"
				aria-label="Next page"
				disabled={!pager.hasNext || loading}
				onclick={() => void source.setPage(pager.page + 1)}
			>
				<ChevronRight aria-hidden="true" />
			</Button>
		</div>
	{:else}
		<span data-slot="{slotName}-loaded" class="tabular-nums">{pager.loadedLabel}</span>
	{/if}
</div>
