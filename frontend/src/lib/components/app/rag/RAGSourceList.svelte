<script lang="ts">
	import { ragStore } from '$lib/stores/ragStore.svelte';
	import { authStore } from '$lib/stores/auth.svelte';
	import { Trash2, FileText, CheckSquare, Square, Loader2, Globe, Lock, Download } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';

	interface Props {
		onSourceClick?: (sourceId: string) => void;
		filter?: 'all' | 'private' | 'shared';
	}

	let { onSourceClick, filter = 'all' }: Props = $props();

	const isAdmin = $derived(authStore.isAdmin);
	
	const filteredSources = $derived(() => {
		if (filter === 'private') return ragStore.privateSources;
		if (filter === 'shared') return ragStore.sharedSources;
		return ragStore.sources;
	});

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

	async function toggleVisibility(e: Event, sourceId: string, currentVisibility: string) {
		e.stopPropagation();
		const newVisibility = currentVisibility === 'private' ? 'shared' : 'private';
		await ragStore.updateVisibility(sourceId, newVisibility);
	}

	function toggleSelection(e: Event, sourceId: string) {
		e.stopPropagation();
		ragStore.toggleSourceSelection(sourceId);
	}

	async function handleDownload(e: Event, sourceId: string) {
		e.stopPropagation();
		await ragStore.downloadSource(sourceId);
	}
</script>

<div class="flex flex-col gap-1">
	{#if ragStore.isLoading && ragStore.sources.length === 0}
		<div class="flex items-center justify-center py-4 text-sm text-muted-foreground">
			<Loader2 class="mr-2 h-4 w-4 animate-spin" />
			Loading documents...
		</div>
	{:else if filteredSources().length === 0}
		<div class="py-4 text-center text-sm text-muted-foreground">
			<FileText class="mx-auto mb-2 h-8 w-8 opacity-50" />
			{#if filter === 'shared'}
				<p>No shared sources</p>
				<p class="text-xs">Admins can make sources shared</p>
			{:else if filter === 'private'}
				<p>No private sources</p>
				<p class="text-xs">Upload files to get started</p>
			{:else}
				<p>No documents yet</p>
				<p class="text-xs">Upload files to get started</p>
			{/if}
		</div>
	{:else}
		{#each filteredSources() as source (source.id)}
			{@const isSelected = ragStore.selectedSourceIds.includes(source.id)}
			{@const isShared = source.visibility === 'shared'}
			{@const canModify = source.is_owner || isAdmin}
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
					<div class="flex items-center gap-1.5">
						<p class="truncate text-sm font-medium">{source.name}</p>
						<!-- Visibility badge -->
						{#if isShared}
							<span class="inline-flex items-center rounded-full bg-blue-100 px-1.5 py-0.5 text-[10px] font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" title="Shared with all users">
								<Globe class="mr-0.5 h-2.5 w-2.5" />
								Shared
							</span>
						{:else if !source.is_owner}
							<!-- Show lock for other users' private sources (shouldn't happen, but just in case) -->
							<span class="inline-flex items-center rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-400" title="Private">
								<Lock class="mr-0.5 h-2.5 w-2.5" />
							</span>
						{/if}
					</div>
					<p class="text-xs text-muted-foreground">
						{source.chunk_count} chunks
						{#if source.file_size}
							• {formatFileSize(source.file_size)}
						{/if}
						• {formatDate(source.created_at)}
					</p>
				</div>

				<!-- Admin visibility toggle -->
				{#if isAdmin && canModify}
					<Button
						variant="ghost"
						size="icon"
						class="h-6 w-6 flex-shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
						onclick={(e) => toggleVisibility(e, source.id, source.visibility)}
						title={isShared ? 'Make private' : 'Make shared'}
					>
						{#if isShared}
							<Lock class="h-3.5 w-3.5 text-muted-foreground" />
						{:else}
							<Globe class="h-3.5 w-3.5 text-muted-foreground" />
						{/if}
					</Button>
				{/if}

				<!-- Download button (if file stored) -->
				{#if (source as any).has_file}
					<Button
						variant="ghost"
						size="icon"
						class="h-6 w-6 flex-shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
						onclick={(e) => handleDownload(e, source.id)}
						title="Download original file"
					>
						<Download class="h-3.5 w-3.5 text-muted-foreground" />
					</Button>
				{/if}

				<!-- Delete button (only for owners or admins) -->
				{#if canModify}
					<Button
						variant="ghost"
						size="icon"
						class="h-6 w-6 flex-shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
						onclick={(e) => handleDelete(e, source.id)}
						title="Delete document"
					>
						<Trash2 class="h-3.5 w-3.5 text-destructive" />
					</Button>
				{/if}
			</div>
		{/each}
	{/if}
</div>

