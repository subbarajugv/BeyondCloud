<script lang="ts">
	import { Square, ArrowUp, Database } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import {
		ChatFormActionFileAttachments,
		ChatFormActionRecord,
		ChatFormModelSelector,
		ChatFormProviderSelector
	} from '$lib/components/app';
	import { config } from '$lib/stores/settings.svelte';
	import { ragStore } from '$lib/stores/ragStore.svelte';
	import type { FileTypeCategory } from '$lib/enums/files';

	interface Props {
		canSend?: boolean;
		class?: string;
		disabled?: boolean;
		isLoading?: boolean;
		isRecording?: boolean;
		onFileUpload?: (fileType?: FileTypeCategory) => void;
		onMicClick?: () => void;
		onStop?: () => void;
	}

	let {
		canSend = false,
		class: className = '',
		disabled = false,
		isLoading = false,
		isRecording = false,
		onFileUpload,
		onMicClick,
		onStop
	}: Props = $props();

	let currentConfig = $derived(config());
	const hasSelectedSources = $derived(ragStore.selectedSourceIds.length > 0);
	const isRagActive = $derived(ragStore.isRagActive);
</script>

<div class="flex w-full items-center gap-2 {className}">
	<ChatFormActionFileAttachments class="mr-auto" {disabled} {onFileUpload} />

	<!-- RAG Toggle -->
	{#if hasSelectedSources}
		<Button
			type="button"
			variant={isRagActive ? "default" : "ghost"}
			size="sm"
			class="h-8 gap-1.5 px-2 {isRagActive ? 'bg-primary/90' : ''}"
			onclick={() => ragStore.toggleRag()}
			title={isRagActive ? 'RAG enabled - click to disable' : 'RAG disabled - click to enable'}
		>
			<Database class="h-4 w-4" />
			<span class="text-xs">{ragStore.selectedSourceIds.length}</span>
		</Button>
	{/if}

	{#if currentConfig.modelSelectorEnabled}
		<ChatFormProviderSelector class="shrink-0" />
		<ChatFormModelSelector class="shrink-0" />
	{/if}

	{#if isLoading}
		<Button
			type="button"
			onclick={onStop}
			class="h-8 w-8 bg-transparent p-0 hover:bg-destructive/20"
		>
			<span class="sr-only">Stop</span>
			<Square class="h-8 w-8 fill-destructive stroke-destructive" />
		</Button>
	{:else}
		<ChatFormActionRecord {disabled} {isLoading} {isRecording} {onMicClick} />

		<Button
			type="submit"
			disabled={!canSend || disabled || isLoading}
			class="h-8 w-8 rounded-full p-0"
		>
			<span class="sr-only">Send</span>
			<ArrowUp class="h-12 w-12" />
		</Button>
	{/if}
</div>
