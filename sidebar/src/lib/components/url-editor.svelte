<script lang="ts" module>
	import type { ControlSize } from '$lib/components/control-classes.js';

	export type UrlEditorSize = ControlSize;

	/** The two halves of a web link, as the control holds them. */
	interface LinkDraft {
		url: string;
		name: string;
	}
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import type { FieldSchema, UrlValue, UrlWriteValue } from 'sg-widgets-core';
	import { parseUrlInput } from 'sg-widgets-core';
	import { Input } from '$lib/components/ui/input/index.js';
	import type { WithElementRef } from '$lib/utils.js';
	import { CONTROL_BOX } from '$lib/components/control-classes.js';
	import ValueEditor from '$lib/components/value-editor.svelte';
	import { createValueSession } from '$lib/components/value-editor.svelte.js';

	type Props = WithElementRef<HTMLAttributes<HTMLDivElement>, HTMLDivElement> & {
		/** The stored object. Only the web-link shape is edited here (field_types/url). */
		value?: UrlValue | null;
		onValueChange?: (value: UrlWriteValue | null) => void;
		field?: Pick<FieldSchema, 'displayName' | 'mandatory'> | null;
		size?: UrlEditorSize;
		disabled?: boolean;
		readonly?: boolean;
		invalid?: boolean;
		error?: string | null;
		onErrorChange?: (error: string | null) => void;
		placeholder?: string;
		/** The placeholder of the second input. */
		namePlaceholder?: string;
		errorMessage?: Snippet<[string]>;
	};

	let {
		value = $bindable(null),
		onValueChange,
		field = null,
		size = 'md',
		disabled = false,
		readonly = false,
		invalid = false,
		error = null,
		onErrorChange,
		placeholder = 'https://example.com/plate.mov',
		namePlaceholder = 'Name',
		errorMessage,
		class: className,
		ref = $bindable(null),
		...rest
	}: Props = $props();

	const session = createValueSession<UrlWriteValue | null, LinkDraft>({
		// The stored object carries more than a link; the two edited halves are all this reads.
		value: () => value as UrlWriteValue | null,
		format: (stored) => ({ url: stored?.url ?? '', name: stored?.name ?? '' }),
		parse: (draft) => parseUrlInput(draft.url, draft.name),
		onValueChange: (next) => {
			value = next;
			onValueChange?.(next);
		},
		onErrorChange: (next) => onErrorChange?.(next),
		error: () => error,
		invalid: () => invalid,
		// A committed link is a fresh object, so every commit is a write.
		same: () => false
	});

	// A local value carries paths and no url at all; uploads and local paths are not
	// edited here, so the control says so rather than showing an empty box
	// (field_types/url).
	const localOnly = $derived(value?.link_type === 'local');
</script>

<!--
	A `url` field, as a web link.

	The only accepted write is an object holding `url`: a bare string is a 400, the url
	itself is validated, and a raw space is the one character measured to fail. With no
	name the field reads back the whole url as its name. Uploads mint an Attachment
	through a separate flow and are out of scope here (field_types/url).
-->
<ValueEditor
	bind:ref
	slotName="url-editor"
	{size}
	message={session.message}
	{errorMessage}
	class={className}
	{...rest}
>
	<div class="flex w-full min-w-0 flex-col gap-2">
		<Input
			bind:value={session.draft.url}
			type="text"
			data-slot="url-editor-url"
			disabled={disabled || localOnly}
			{readonly}
			{placeholder}
			class={CONTROL_BOX[size]}
			aria-invalid={session.invalid}
			aria-label={field?.displayName}
			aria-required={field?.mandatory}
			onfocus={session.onfocus}
			onblur={session.onblur}
			onkeydown={session.onkeydown}
		/>
		<Input
			bind:value={session.draft.name}
			type="text"
			data-slot="url-editor-name"
			disabled={disabled || localOnly}
			{readonly}
			placeholder={namePlaceholder}
			class={CONTROL_BOX[size]}
			aria-invalid={session.invalid}
			aria-label="Link name"
			onfocus={session.onfocus}
			onblur={session.onblur}
			onkeydown={session.onkeydown}
		/>
	</div>
	{#if localOnly}
		<p data-slot="url-editor-note" class="text-muted-foreground text-xs">
			This value is a local path. Only web links are edited here.
		</p>
	{/if}
</ValueEditor>
