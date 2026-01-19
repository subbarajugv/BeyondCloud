<script lang="ts">
	import { ragStore } from '$lib/stores/ragStore.svelte';
	import { Database, Plus, RefreshCw, ChevronDown, ChevronRight, FolderPlus } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import RAGSourceList from './RAGSourceList.svelte';
	import RAGUploadDialog from './RAGUploadDialog.svelte';
	import RAGCollectionTree from './RAGCollectionTree.svelte';

	let isExpanded = $state(true);
	let uploadDialogOpen = $state(false);
	let showTree = $state(true);

	const sourceCount = $derived(ragStore.sources.length);
	const collectionCount = $derived(ragStore.collections.length);
	const currentCollection = $derived(
		ragStore.currentCollectionId 
			? ragStore.getCollection(ragStore.currentCollectionId)
			: null
	);

	function handleRefresh() {
		ragStore.loadSources();
		ragStore.loadCollectionTree();
		ragStore.loadCollections();
	}
</script>

<div class="border-t border-border">
	<!-- Header -->
	<button
		type="button"
		class="flex w-full items-center gap-2 px-3 py-2 text-sm font-medium transition-colors hover:bg-muted"
		onclick={() => (isExpanded = !isExpanded)}
	>
		{#if isExpanded}
			<ChevronDown class="h-4 w-4" />
		{:else}
			<ChevronRight class="h-4 w-4" />
		{/if}
		<Database class="h-4 w-4" />
		<span class="flex-1 text-left">Knowledge Library</span>
		{#if sourceCount > 0}
			<span class="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
				{sourceCount}
			</span>
		{/if}
	</button>

	<!-- Content -->
	{#if isExpanded}
		<div class="px-2 pb-2">
			<!-- Actions -->
			<div class="mb-2 flex gap-1">
				<Button
					variant="outline"
					size="sm"
					class="flex-1"
					onclick={() => (uploadDialogOpen = true)}
				>
					<Plus class="mr-1 h-3.5 w-3.5" />
					Upload
				</Button>
				<Button
					variant="ghost"
					size="icon"
					class="h-8 w-8"
					onclick={handleRefresh}
					title="Refresh"
				>
					<RefreshCw class="h-3.5 w-3.5" />
				</Button>
			</div>

			<!-- Current folder breadcrumb -->
			{#if currentCollection}
				<div class="mb-2 flex items-center gap-1 rounded bg-muted/50 px-2 py-1 text-xs">
					<span class="text-muted-foreground">Folder:</span>
					<span class="font-medium">{currentCollection.name}</span>
					<button
						type="button"
						class="ml-auto text-muted-foreground hover:text-foreground"
						onclick={() => ragStore.setCurrentCollection(null)}
					>
						×
					</button>
				</div>
			{/if}

			<!-- Tab toggle between tree and list -->
			<div class="mb-2 flex gap-1 border-b border-border">
				<button
					type="button"
					class="flex-1 border-b-2 px-2 py-1 text-xs transition-colors {showTree ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}"
					onclick={() => (showTree = true)}
				>
					Folders
				</button>
				<button
					type="button"
					class="flex-1 border-b-2 px-2 py-1 text-xs transition-colors {!showTree ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}"
					onclick={() => (showTree = false)}
				>
					Documents
				</button>
			</div>

			<!-- Content area -->
			<div class="max-h-64 overflow-y-auto">
				{#if showTree}
					<RAGCollectionTree onSelect={() => (showTree = false)} />
				{:else}
					<RAGSourceList />
				{/if}
			</div>
		</div>
	{/if}
</div>

<RAGUploadDialog bind:open={uploadDialogOpen} onOpenChange={(o) => (uploadDialogOpen = o)} />

