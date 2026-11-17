<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = {
		/** The message, or null when there is nothing to say. */
		message?: string | null;
		/** Renders the message. Default is a small destructive line under the control. */
		errorMessage?: Snippet<[string]>;
	};

	let { message = null, errorMessage }: Props = $props();
</script>

<!--
	The line a field editor shows under its control when a parse fails or the caller
	names an error. Every editor in this registry draws this one.
-->
{#if message}
	{#if errorMessage}
		{@render errorMessage(message)}
	{:else}
		<p data-slot="field-editor-error" class="text-destructive text-xs">{message}</p>
	{/if}
{/if}
