<script lang="ts">
	import { ragStore } from '$lib/stores/ragStore.svelte';
	import { Trash2, FileText, CheckSquare, Square, Loader2 } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';

	interface Props {
		onSourceClick?: (sourceId: string) => void;
	}

	let { onSourceClick }: Props = $props();

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString();
	}

	function formatFileSize(bytes?: number): string {
		if (!bytes) return '';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	async function handleDelete(e: Event, sourceId: string) {
		e.stopPropagation();
		if (confirm('Delete this document and all its chunks?')) {
			await ragStore.deleteSource(sourceId);
		}
	}

	function toggleSelection(e: Event, sourceId: string) {
		e.stopPropagation();
		ragStore.toggleSourceSelection(sourceId);
	}
</script>

<div class="flex flex-col gap-1">
	{#if ragStore.isLoading && ragStore.sources.length === 0}
		<div class="flex items-center justify-center py-4 text-sm text-muted-foreground">
			<Loader2 class="mr-2 h-4 w-4 animate-spin" />
			Loading documents...
		</div>
	{:else if ragStore.sources.length === 0}
		<div class="py-4 text-center text-sm text-muted-foreground">
			<FileText class="mx-auto mb-2 h-8 w-8 opacity-50" />
			<p>No documents yet</p>
			<p class="text-xs">Upload files to get started</p>
		</div>
	{:else}
		{#each ragStore.sources as source (source.id)}
			{@const isSelected = ragStore.selectedSourceIds.includes(source.id)}
			<div
				class="group flex w-full items-center gap-2 rounded-md p-2 text-left transition-colors hover:bg-muted"
			>
				<span
					role="button"
					tabindex="0"
					class="flex-shrink-0 cursor-pointer text-muted-foreground hover:text-foreground"
					onclick={(e) => toggleSelection(e, source.id)}
					onkeydown={(e) => e.key === 'Enter' && toggleSelection(e, source.id)}
					title={isSelected ? 'Deselect for queries' : 'Select for queries'}
				>
					{#if isSelected}
						<CheckSquare class="h-4 w-4 text-primary" />
					{:else}
						<Square class="h-4 w-4" />
					{/if}
				</span>

				<FileText class="h-4 w-4 flex-shrink-0 text-muted-foreground" />

				<div class="min-w-0 flex-1">
					<p class="truncate text-sm font-medium">{source.name}</p>
					<p class="text-xs text-muted-foreground">
						{source.chunk_count} chunks
						{#if source.file_size}
							• {formatFileSize(source.file_size)}
						{/if}
						• {formatDate(source.created_at)}
					</p>
				</div>

				<Button
					variant="ghost"
					size="icon"
					class="h-6 w-6 flex-shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
					onclick={(e) => handleDelete(e, source.id)}
					title="Delete document"
				>
					<Trash2 class="h-3.5 w-3.5 text-destructive" />
				</Button>
			</div>
		{/each}
	{/if}
</div>
