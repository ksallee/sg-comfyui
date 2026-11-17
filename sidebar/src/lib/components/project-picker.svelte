<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import type { EntityRef, PickerRow, ProjectPickerOptions } from 'sg-widgets-core';
	import { PROJECT_PICKER_FIELDS, projectPickerFilters } from 'sg-widgets-core';
	import { type WithElementRef } from '$lib/utils.js';
	import EntityPicker, { type EntityPickerBaseProps } from './entity-picker.svelte';

	type Props = WithElementRef<HTMLAttributes<HTMLDivElement>, HTMLDivElement> &
		Omit<EntityPickerBaseProps, 'entityTypes'> &
		ProjectPickerOptions & {
			value?: EntityRef | null;
			onValueChange?: (value: EntityRef | null, row: PickerRow | null) => void;
		};

	let {
		value = $bindable(null),
		includeArchived = false,
		filters = null,
		fields = [],
		placeholder = 'Search for a project',
		open = $bindable(false),
		ref = $bindable(null),
		...rest
	}: Props = $props();
</script>

<!--
	One project, chosen by server-side search.

	The generic entity picker configured for Project: the project thumbnail, the
	status under the name so an active project can be told from a bidding one, and
	archived projects left out unless asked for.
-->
<EntityPicker
	bind:value
	bind:open
	bind:ref
	entityTypes={['Project']}
	fields={[...PROJECT_PICKER_FIELDS, ...fields]}
	filters={projectPickerFilters(includeArchived, filters)}
	subLabelField="sg_status"
	{placeholder}
	{...rest}
/>
