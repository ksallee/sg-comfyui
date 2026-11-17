<script lang="ts" module>
	import type { Snippet } from 'svelte';
	import { CHIP_CROSS, type ChipSize } from '$lib/components/leaf-classes.js';

	export type FilterEditorSize = 'sm' | 'md' | 'lg';

	/** The control ladder of `docs/design-rules.md`, which a condition's own controls stand on. */
	const BOX: Record<FilterEditorSize, string> = { sm: 'h-7', md: 'h-8', lg: 'h-9' };
	const ROW: Record<FilterEditorSize, string> = { sm: 'min-h-7', md: 'min-h-8', lg: 'min-h-9' };
	/** Every control in a row stands on the row's own step, so one row has one height. */
	const INNER: Record<FilterEditorSize, FilterEditorSize> = { sm: 'sm', md: 'md', lg: 'lg' };
	/** A cross sits one step under the row's own control on the chip ladder. */
	const CROSS: Record<FilterEditorSize, ChipSize> = { sm: 'xs', md: 'xs', lg: 'sm' };
	const TOGGLE: Record<FilterEditorSize, 'sm' | 'default' | 'lg'> = { sm: 'sm', md: 'default', lg: 'lg' };
	/** The select trigger has two steps of its own; the third is its default step lifted to `h-9`. */
	const SELECT: Record<FilterEditorSize, { size: 'sm' | 'default'; class?: string }> = {
		sm: { size: 'sm' },
		md: { size: 'default' },
		lg: { size: 'default', class: 'data-[size=default]:h-9' }
	};
	import type {
		ConditionValue,
		EntityRef,
		FieldSchema,
		FilterCondition,
		FilterGroup,
		FilterNode,
		NodePath,
		Operator,
		Scalar
	} from 'sg-widgets-core';

	/** What the field slot is given. Its job is to call `onSelect` with a dotted path. */
	export interface FieldChooserArgs {
		entityType: string;
		/** The path the row holds now, empty on a new row. */
		path: string;
		hidePaths: string[];
		/** Only fields the API can filter on. Always true here. */
		filterableOnly: true;
		disabled: boolean;
		onSelect: (path: string) => void;
	}

	/** What a value slot is given. Its job is to call `onChange` with the value the operator expects. */
	export interface ValueEditorArgs {
		field: FieldSchema | null;
		dataType: string;
		operator: Operator;
		value: ConditionValue;
		/** The arity the operator's wire shape asks for. */
		arity: 'none' | 'one' | 'many' | 'two' | 'relative';
		disabled: boolean;
		onChange: (value: ConditionValue) => void;
	}

	/** The six types NumberEditor parses. `footage` is numeric to the API and reads as a plain number. */
	const NUMERIC_EDITORS = ['number', 'float', 'percent', 'duration', 'timecode', 'currency'] as const;
	type NumericEditor = (typeof NUMERIC_EDITORS)[number];

	function numericType(dataType: string): NumericEditor {
		return (NUMERIC_EDITORS as readonly string[]).includes(dataType) ? (dataType as NumericEditor) : 'number';
	}

	function textValue(value: Scalar | undefined): string | null {
		if (value === null || value === undefined) return null;
		return typeof value === 'object' ? null : String(value);
	}

	function numberValue(value: Scalar | undefined): number | string | null {
		if (value === null || value === undefined || value === '') return null;
		return typeof value === 'number' || typeof value === 'string' ? value : null;
	}

	function codes(value: ConditionValue): string[] {
		if (!Array.isArray(value)) return [];
		return (value as Scalar[]).filter((v): v is string => typeof v === 'string');
	}

	/** `is` takes one entity hash and `in` a list of them; a list under `is` is a 400 (field_types/entity). */
	function entityRefs(value: ConditionValue): EntityRef[] {
		if (Array.isArray(value)) return value.filter((v) => v !== null && typeof v === 'object') as EntityRef[];
		return value !== null && typeof value === 'object' ? [value as EntityRef] : [];
	}

	function entityRef(value: ConditionValue): EntityRef | null {
		return value !== null && typeof value === 'object' && !Array.isArray(value) ? (value as EntityRef) : null;
	}

	/** Every dotted path the tree holds. A flat name needs no resolution. */
	function dottedPaths(node: FilterNode, out: string[] = []): string[] {
		if (node.kind === 'condition') {
			if (node.path.includes('.')) out.push(node.path);
			return out;
		}
		for (const child of node.conditions) dottedPaths(child, out);
		return out;
	}
</script>

<script lang="ts">
	import PlusIcon from '@lucide/svelte/icons/plus';
	import XIcon from '@lucide/svelte/icons/x';
	import type { HTMLAttributes } from 'svelte/elements';
	import type { SgContext, TimeUnit } from 'sg-widgets-core';
	import {
		appendAt,
		applyPreset,
		fieldOperators,
		condition as makeCondition,
		conditionArity,
		conditionList,
		defaultCondition,
		emptyFilter,
		group as makeGroup,
		NOTHING_CHOSEN_LABEL,
		operatorMenu,
		presetById,
		presetIdOf,
		relativeWindow,
		removeAt,
		replaceAt,
		timeUnitField,
		valueEditorFor,
		withAddedListValue,
		withListValue,
		withoutListValue,
		withRelativeWindow
	} from 'sg-widgets-core';
	import { Button } from '$lib/components/ui/button/index.js';
	import { CONTROL_BUTTON } from '$lib/components/control-classes.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import * as ToggleGroup from '$lib/components/ui/toggle-group/index.js';
	import { cn, type WithElementRef } from '$lib/utils.js';
	import { entityFields } from '$lib/components/entity-fields.svelte.js';
	import CheckboxEditor from '$lib/components/checkbox-editor.svelte';
	import StateLine from '$lib/components/state-line.svelte';
	import ColorEditor from '$lib/components/color-editor.svelte';
	import DateEditor from '$lib/components/date-editor.svelte';
	import DateTimeEditor from '$lib/components/date-time-editor.svelte';
	import EntityMultiPicker from '$lib/components/entity-multi-picker.svelte';
	import EntityPicker from '$lib/components/entity-picker.svelte';
	import FieldPicker from '$lib/components/field-picker.svelte';
	import { REMOVE_CONTROL } from '$lib/components/leaf-classes.js';
	import ListMultiPicker from '$lib/components/list-multi-picker.svelte';
	import ListPicker from '$lib/components/list-picker.svelte';
	import NumberEditor from '$lib/components/number-editor.svelte';
	import StatusMultiPicker from '$lib/components/status-multi-picker.svelte';
	import StatusPicker from '$lib/components/status-picker.svelte';
	import TextEditor from '$lib/components/text-editor.svelte';
	import UrlEditor from '$lib/components/url-editor.svelte';

	type Props = WithElementRef<HTMLAttributes<HTMLDivElement>, HTMLDivElement> & {
		/** Type the root of every field path is read on. */
		entityType: string;
		/** The widget context. Every read goes through it, so widgets on a page share one cache. */
		context: SgContext;
		value: FilterGroup;
		/** Paths to keep out of the field list, each hiding itself and everything under it. */
		hidePaths?: string[];
		/** Scopes the status pickers to the codes one project allows. */
		projectId?: number;
		/** Shown when a group holds no condition. */
		emptyLabel?: string;
		size?: FilterEditorSize;
		disabled?: boolean;
		onValueChange?: (value: FilterGroup) => void;
		fieldChooser?: Snippet<[FieldChooserArgs]>;
		valueEditor?: Snippet<[ValueEditorArgs]>;
		entityEditor?: Snippet<[ValueEditorArgs]>;
		class?: string;
	};

	let {
		entityType,
		context,
		value = $bindable(emptyFilter()),
		hidePaths = [],
		projectId,
		emptyLabel = NOTHING_CHOSEN_LABEL,
		size = 'md',
		disabled = false,
		onValueChange,
		fieldChooser,
		valueEditor,
		entityEditor,
		class: className,
		ref = $bindable(null),
		...rest
	}: Props = $props();

	const schemaFields = entityFields(
		() => context,
		() => entityType
	);
	const fields = $derived(schemaFields.current);

	/**
	 * The leaf schema of every dotted path the tree holds, added once and kept.
	 * `resolving` is a plain map, so filling the cache never re-triggers the walk.
	 */
	let leaves = $state<Record<string, FieldSchema | null>>({});
	const resolving = new Map<string, Promise<FieldSchema | null>>();

	function leafKey(path: string): string {
		return `${entityType}|${path}`;
	}

	function resolveLeaf(path: string): Promise<FieldSchema | null> {
		const key = leafKey(path);
		let job = resolving.get(key);
		if (!job) {
			job = context.schema.resolvePath(entityType, path).then(
				(segments) => segments[segments.length - 1]?.field ?? null,
				// A path the schema no longer holds still has to be editable, so the row keeps it.
				() => null
			);
			resolving.set(key, job);
			void job.then((leaf) => {
				leaves = { ...leaves, [key]: leaf };
			});
		}
		return job;
	}

	$effect(() => {
		for (const path of dottedPaths(value)) void resolveLeaf(path);
	});

	/** The leaf field of a path. A flat name is a field of the root type. */
	function fieldOf(path: string): FieldSchema | null {
		if (!path) return null;
		if (!path.includes('.')) return fields[path] ?? null;
		return leaves[leafKey(path)] ?? null;
	}

	function dataTypeOf(path: string): string {
		return fieldOf(path)?.dataType ?? '';
	}

	/** The operators the site answers on a path, which may be fewer than its data type takes. */
	function operatorsOf(path: string): readonly Operator[] {
		return fieldOperators(fieldOf(path) ?? { dataType: dataTypeOf(path) });
	}

	/** True while a dotted path is still being walked; its leaf decides the whole row. */
	function unresolved(path: string): boolean {
		return path.includes('.') && !(leafKey(path) in leaves);
	}

	function commit(next: FilterGroup): void {
		value = next;
		onValueChange?.(next);
	}

	function edit(path: NodePath, node: FilterCondition | FilterGroup): void {
		commit(replaceAt(value, path, node));
	}

	async function pickField(path: NodePath, current: FilterCondition, chosen: string): Promise<void> {
		const before = dataTypeOf(current.path);
		const leaf = chosen.includes('.') ? await resolveLeaf(chosen) : fieldOf(chosen);
		const after = leaf?.dataType ?? '';
		// The operator vocabulary is per data type, so moving to another type resets the row.
		edit(
			path,
			before === after && current.path
				? { ...current, path: chosen }
				: defaultCondition(chosen, after, fieldOperators(leaf ?? { dataType: after }))
		);
	}

	function pickPreset(path: NodePath, current: FilterCondition, id: string): void {
		const dataType = dataTypeOf(current.path);
		const preset = presetById(dataType, id, operatorsOf(current.path));
		if (preset) edit(path, applyPreset(current, preset, dataType));
	}
</script>

{#snippet fieldSlot(path: NodePath, node: FilterCondition)}
	<!--
		The field is the row's widest cell: it takes 14rem, truncates, and gives the rest back.
		It is one line tall whatever the value beside it grows to.
	-->
	<div data-slot="filter-field" class={cn('flex min-w-24 max-w-56 grow basis-24 items-center', ROW[size])}>
		{#if fieldChooser}
			{@render fieldChooser({
				entityType,
				path: node.path,
				hidePaths,
				filterableOnly: true,
				disabled,
				onSelect: (next: string) => void pickField(path, node, next)
			})}
		{:else}
			<FieldPicker
				{context}
				{entityType}
				{hidePaths}
				{disabled}
				value={node.path}
				deepLinks
				filterableOnly
				clearable={false}
				size={INNER[size]}
				placeholder="Select a field"
				onValueChange={(next) => void pickField(path, node, next)}
			/>
		{/if}
	</div>
{/snippet}

{#snippet operatorSlot(path: NodePath, node: FilterCondition)}
	{@const dataType = dataTypeOf(node.path)}
	{@const operators = operatorsOf(node.path)}
	{@const menu = operatorMenu(dataType, operators)}
	{@const current = presetIdOf(node, dataType)}
	<!-- The menu stands on the row's first line, beside the field, not in the middle of a grown value. -->
	<div class={cn('flex shrink-0 items-center', ROW[size])}>
		<Select.Root
			type="single"
			value={current}
			disabled={disabled || menu.length === 0}
			onValueChange={(id) => pickPreset(path, node, id)}
		>
			<Select.Trigger size={SELECT[size].size} class={cn(SELECT[size].class, 'w-40 shrink-0')} data-slot="filter-operator">
				{presetById(dataType, current, operators)?.label ?? current}
			</Select.Trigger>
			<Select.Content>
				{#each menu as run (run.label)}
					<Select.Group>
						<Select.GroupHeading>{run.label}</Select.GroupHeading>
						{#each run.presets as preset (preset.id)}
							<Select.Item value={preset.id} label={preset.label} data-preset={preset.id} />
						{/each}
					</Select.Group>
				{/each}
			</Select.Content>
		</Select.Root>
	</div>
{/snippet}

<!--
	A value editor sized for a row. The typed types take the width their content needs and
	the free width goes to the ones that hold a name: a date, a time and a number never
	push the row onto a second line.
-->
{#snippet scalarEditor(kind: string, dataType: string, label: string, current: Scalar, set: (v: Scalar) => void)}
	{#if kind === 'number'}
		<NumberEditor
			class="shrink-0"
			size={INNER[size]}
			inline
			{disabled}
			dataType={numericType(dataType)}
			field={{ displayName: label, mandatory: false }}
			value={numberValue(current)}
			onValueChange={(next) => set(next ?? '')}
		/>
	{:else if kind === 'date'}
		<DateEditor
			class="shrink-0"
			size={INNER[size]}
			inline
			{disabled}
			field={{ displayName: label, mandatory: false }}
			value={textValue(current)}
			onValueChange={(next) => set(next ?? '')}
		/>
	{:else if kind === 'date_time'}
		<DateTimeEditor
			class="shrink-0"
			size={INNER[size]}
			inline
			hint={false}
			{disabled}
			field={{ displayName: label, mandatory: false }}
			value={textValue(current)}
			onValueChange={(next) => set(next ?? '')}
		/>
	{:else if kind === 'color'}
		<ColorEditor
			class="w-44 shrink-0"
			size={INNER[size]}
			hint={false}
			{disabled}
			field={{ displayName: label, mandatory: false }}
			value={textValue(current)}
			onValueChange={(next) => set(next ?? '')}
		/>
	{:else if kind === 'url'}
		<!-- The row compares the link itself, so the editor's name half is left out of the value. -->
		<UrlEditor
			class="min-w-0 flex-1"
			size={INNER[size]}
			{disabled}
			field={{ displayName: label, mandatory: false }}
			value={textValue(current) ? { url: String(textValue(current)) } : null}
			onValueChange={(next) => set(next?.url ?? '')}
		/>
	{:else}
		<TextEditor
			class="min-w-0 flex-1"
			size={INNER[size]}
			{disabled}
			field={{ displayName: label, mandatory: false }}
			value={textValue(current)}
			onValueChange={(next) => set(next ?? '')}
		/>
	{/if}
{/snippet}

<!--
	A list of values, one to a line, each edited by its own data type's control and each
	with the control that drops it. The arity is the operator's: `in` and `not_in` take a
	JSON array, and a blank value is dropped on serialisation rather than sent.
-->
{#snippet listEditor(kind: string, dataType: string, label: string, current: ConditionValue, set: (v: ConditionValue) => void)}
	{@const items = conditionList(current)}
	<div class="flex min-w-0 flex-1 flex-col items-start gap-2" data-slot="filter-list">
		{#each items as item, i (i)}
			<div class="flex min-w-0 items-center gap-1.5" data-slot="filter-list-value" data-index={i}>
				{@render scalarEditor(kind, dataType, label, item, (v) =>
					set(withListValue(current, i, v) as ConditionValue)
				)}
				<button
					type="button"
					class={cn(REMOVE_CONTROL, 'disabled:pointer-events-none disabled:opacity-50')}
					{disabled}
					aria-label="Remove value"
					data-slot="filter-list-remove"
					onclick={() => set(withoutListValue(current, i) as ConditionValue)}
				>
					<XIcon aria-hidden="true" class={CHIP_CROSS[CROSS[size]]} />
				</button>
			</div>
		{/each}
		<Button
			variant="ghost"
			size={CONTROL_BUTTON[size]}
			class="text-muted-foreground shrink-0"
			{disabled}
			data-slot="filter-list-add"
			onclick={() => set(withAddedListValue(current) as ConditionValue)}
		>
			<PlusIcon />
			Value
		</Button>
	</div>
{/snippet}

{#snippet entityValue(field: FieldSchema | null, arity: string, current: ConditionValue, set: (v: ConditionValue) => void)}
	{@const types = field?.validTypes?.length ? field.validTypes : [entityType]}
	{#if arity === 'many'}
		<EntityMultiPicker
			class="min-w-0 flex-1"
			size={INNER[size]}
			{context}
			{disabled}
			{projectId}
			entityTypes={types}
			placeholder="Search entities"
			value={entityRefs(current)}
			onValueChange={(next) => set([...next])}
		/>
	{:else}
		<EntityPicker
			class="min-w-0 flex-1"
			size={INNER[size]}
			{context}
			{disabled}
			{projectId}
			entityTypes={types}
			placeholder="Search entities"
			value={entityRef(current)}
			onValueChange={(next) => set(next ?? '')}
		/>
	{/if}
{/snippet}

{#snippet valueSlot(path: NodePath, node: FilterCondition)}
	{@const field = fieldOf(node.path)}
	{@const dataType = field?.dataType ?? ''}
	{@const kind = valueEditorFor(dataType, node.operator)}
	{@const arity = conditionArity(node, dataType)}
	{@const set = (v: ConditionValue) => edit(path, { ...node, value: v })}
	<div class={cn('flex min-w-40 flex-1 flex-wrap items-start gap-2', ROW[size])} data-slot="filter-value">
		{#if unresolved(node.path)}
			<Skeleton class={cn(BOX[size], 'min-w-0 flex-1')} />
		{:else if valueEditor}
			<!-- Integration point: a caller's own editors replace every one below. -->
			{@render valueEditor({
				field,
				dataType,
				operator: node.operator,
				value: node.value,
				arity,
				disabled,
				onChange: set
			})}
		{:else if arity === 'none'}
			<!-- `is empty` and the calendar presets pin their value; there is nothing to edit. -->
		{:else if arity === 'relative'}
			{@const window_ = relativeWindow(node.value)}
			<!-- A window is a count and a unit: the number editor and the list a `list` field uses. -->
			<div class="flex min-w-0 shrink-0 items-center gap-2" data-slot="filter-window">
				<NumberEditor
					class="w-16 shrink-0"
					size={INNER[size]}
					inline
					{disabled}
					dataType="number"
					min={1}
					field={{ displayName: 'Count', mandatory: true }}
					value={window_.count}
					onValueChange={(next) =>
						set(withRelativeWindow(node.value, { count: next === null ? null : Number(next) }) as ConditionValue)}
				/>
				<ListPicker
					class="w-24 shrink-0"
					size={INNER[size]}
					{disabled}
					field={timeUnitField()}
					value={window_.unit}
					onValueChange={(next) =>
						set(withRelativeWindow(node.value, { unit: (next ?? 'DAY') as TimeUnit }) as ConditionValue)}
				/>
			</div>
		{:else if kind === 'entity'}
			{#if entityEditor}
				<!-- Integration point: EntityMultiPicker plugs in here. -->
				{@render entityEditor({
					field,
					dataType,
					operator: node.operator,
					value: node.value,
					arity,
					disabled,
					onChange: set
				})}
			{:else}
				{@render entityValue(field, arity, node.value, set)}
			{/if}
		{:else if kind === 'checkbox'}
			<CheckboxEditor
				class="min-w-0 flex-1"
				size={INNER[size]}
				{disabled}
				field={{ displayName: field?.displayName ?? 'Value', mandatory: false }}
				value={node.value === true}
				onValueChange={(next) => set(next)}
			/>
		{:else if kind === 'options' && dataType === 'status_list' && arity === 'many'}
			<StatusMultiPicker
				class="min-w-0 flex-1"
				size={INNER[size]}
				{context}
				{disabled}
				{projectId}
				entityType={field?.entityType ?? entityType}
				field={field?.name}
				value={codes(node.value)}
				onValueChange={(next) => set([...next])}
			/>
		{:else if kind === 'options' && dataType === 'status_list'}
			<StatusPicker
				class="min-w-0 flex-1"
				size={INNER[size]}
				{context}
				{disabled}
				{projectId}
				entityType={field?.entityType ?? entityType}
				field={field?.name}
				value={typeof node.value === 'string' && node.value !== '' ? node.value : null}
				onValueChange={(next) => set(next ?? '')}
			/>
		{:else if kind === 'options' && arity === 'many'}
			<ListMultiPicker
				class="min-w-0 flex-1"
				size={INNER[size]}
				{disabled}
				{field}
				placeholder="Select values…"
				value={codes(node.value)}
				onValueChange={(next) => set([...next])}
			/>
		{:else if kind === 'options'}
			<ListPicker
				class="min-w-0 flex-1"
				size={INNER[size]}
				{disabled}
				{field}
				placeholder="Select a value…"
				value={typeof node.value === 'string' && node.value !== '' ? node.value : null}
				onValueChange={(next) => set(next ?? '')}
			/>
		{:else if arity === 'two'}
			{@const pair = (Array.isArray(node.value) ? node.value : [null, null]) as [Scalar, Scalar]}
			<!-- Both ends on one line, joined by the word that reads the range. -->
			<div class="flex min-w-0 flex-1 flex-wrap items-center gap-2" data-slot="filter-range">
				{@render scalarEditor(kind, dataType, 'From', pair[0], (v) => set([v, pair[1]] as ConditionValue))}
				<span class="text-muted-foreground shrink-0 text-sm">and</span>
				{@render scalarEditor(kind, dataType, 'To', pair[1], (v) => set([pair[0], v] as ConditionValue))}
			</div>
		{:else if arity === 'many'}
			{@render listEditor(kind, dataType, field?.displayName ?? 'Value', node.value, set)}
		{:else}
			{@render scalarEditor(kind, dataType, field?.displayName ?? 'Value', node.value as Scalar, (v) => set(v))}
		{/if}
	</div>
{/snippet}

<!--
	A row is two bands: the field, the operator and the value on one line of the row's own height, and
	the remove button on its own. The remove sits outside the wrapping band, so it
	holds the same vertical axis at every depth and never costs the row a line.

	Both bands hang off the row's first line. A multi-value operator grows the value into one line
	per value and an add row, and the controls beside it belong to the row rather than to the list:
	top-aligned, each on the axis of the first value line, so a list that grows pushes only the rows
	under it. Each control cell stands the row's own control height, which is that axis.
-->
{#snippet conditionRow(path: NodePath, node: FilterCondition)}
	<div class={cn('flex min-w-0 items-start gap-2', ROW[size])} data-slot="filter-row" data-path={path.join('.')}>
		<div class="flex min-w-0 flex-1 flex-wrap items-start gap-2" data-slot="filter-row-content">
			{@render fieldSlot(path, node)}
			{@render operatorSlot(path, node)}
			{@render valueSlot(path, node)}
		</div>
		<div class={cn('flex shrink-0 items-center self-start', BOX[size])}>
			<button
				type="button"
				class={cn(REMOVE_CONTROL, 'disabled:pointer-events-none disabled:opacity-50')}
				{disabled}
				aria-label="Remove condition"
				data-slot="filter-remove"
				onclick={() => commit(removeAt(value, path))}
			>
				<XIcon aria-hidden="true" class={CHIP_CROSS[CROSS[size]]} />
			</button>
		</div>
	</div>
{/snippet}

<!--
	A group is a header, its rows and a foot. The header says how the rows join and
	removes the group; the rows hang off one rail, so a level of nesting is one
	indent; the foot is where rows and groups are added.
-->
{#snippet groupNode(path: NodePath, node: FilterGroup)}
	{@const depth = path.length}
	<div
		class={cn('flex min-w-0 flex-col gap-2', depth > 0 && 'bg-muted/40 rounded-lg p-2')}
		data-slot="filter-group"
		data-path={path.join('.')}
		data-depth={depth}
		data-logical-operator={node.logicalOperator}
	>
		<div class={cn('flex min-w-0 items-center gap-2', ROW[size])} data-slot="filter-group-header">
			<ToggleGroup.Root
				type="single"
				size={TOGGLE[size]}
				variant="outline"
				{disabled}
				value={node.logicalOperator}
				data-slot="filter-logic"
				onValueChange={(next) =>
					next && edit(path, { ...node, logicalOperator: next as FilterGroup['logicalOperator'] })}
			>
				<ToggleGroup.Item value="and" aria-label="Match all">All</ToggleGroup.Item>
				<ToggleGroup.Item value="or" aria-label="Match any">Any</ToggleGroup.Item>
			</ToggleGroup.Root>
			<span class="text-muted-foreground min-w-0 flex-1 truncate text-xs">of these match</span>
			{#if depth > 0}
				<div class={cn('flex shrink-0 items-center self-start', BOX[size])}>
					<button
						type="button"
						class={cn(REMOVE_CONTROL, 'disabled:pointer-events-none disabled:opacity-50')}
						{disabled}
						aria-label="Remove group"
						data-slot="filter-remove"
						onclick={() => commit(removeAt(value, path))}
					>
						<XIcon aria-hidden="true" class={CHIP_CROSS[CROSS[size]]} />
					</button>
				</div>
			{/if}
		</div>
		<div
			class="border-border flex min-w-0 flex-col gap-2 border-l pl-3"
			data-slot="filter-group-body"
		>
			{#each node.conditions as child, i (i)}
				{#if child.kind === 'group'}
					{@render groupNode([...path, i], child)}
				{:else}
					{@render conditionRow([...path, i], child)}
				{/if}
			{/each}
			{#if node.conditions.length === 0}
				<StateLine state="empty" slotName="filter-group-empty" label={emptyLabel} />
			{/if}
		</div>
		<div class="flex min-w-0 flex-wrap items-center gap-1 pl-3" data-slot="filter-foot">
			<Button
				variant="ghost"
				size={CONTROL_BUTTON[size]}
				class="text-muted-foreground"
				{disabled}
				data-slot="filter-add-condition"
				data-path={path.join('.')}
				onclick={() => commit(appendAt(value, path, makeCondition('', 'is', '')))}
			>
				<PlusIcon />
				Condition
			</Button>
			<Button
				variant="ghost"
				size={CONTROL_BUTTON[size]}
				class="text-muted-foreground"
				{disabled}
				data-slot="filter-add-group"
				data-path={path.join('.')}
				onclick={() => commit(appendAt(value, path, makeGroup('or')))}
			>
				<PlusIcon />
				Group
			</Button>
		</div>
	</div>
{/snippet}

<!--
	A filter tree, edited.

	A row is a field, an operator and a value; a group nests rows under `All` or
	`Any`. The operator menu and the value editor both come from the field's
	`data_type` through core, so a row can only build a filter the API accepts
	(017_filter_operators). A row with no field, or one whose operator still has no
	value, is dropped on serialisation rather than sent.

	The field is chosen with FieldPicker, which descends through links, so a row may
	filter on a dotted path; the leaf of that path is resolved through the schema
	service and is what picks the operator menu and the value editor. An operator that
	pins its value draws no editor at all.
-->
<div
	bind:this={ref}
	data-slot="filter-editor"
	data-entity-type={entityType}
	aria-disabled={disabled ? 'true' : undefined}
	class={cn('flex w-full min-w-0 flex-col gap-3', disabled && 'opacity-50', className)}
	{...rest}
>
	{@render groupNode([], value)}
</div>
