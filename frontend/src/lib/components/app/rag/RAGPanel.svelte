<script lang="ts">
	import { ragStore } from '$lib/stores/ragStore.svelte';
	import { Database, Plus, RefreshCw, ChevronDown, ChevronRight } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import RAGSourceList from './RAGSourceList.svelte';
	import RAGUploadDialog from './RAGUploadDialog.svelte';

	let isExpanded = $state(true);
	let uploadDialogOpen = $state(false);

	const sourceCount = $derived(ragStore.sources.length);
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
		<span class="flex-1 text-left">Knowledge Base</span>
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
					onclick={() => ragStore.loadSources()}
					title="Refresh"
				>
					<RefreshCw class="h-3.5 w-3.5" />
				</Button>
			</div>

			<!-- Source list -->
			<div class="max-h-48 overflow-y-auto">
				<RAGSourceList />
			</div>
		</div>
	{/if}
</div>

<RAGUploadDialog bind:open={uploadDialogOpen} onOpenChange={(o) => (uploadDialogOpen = o)} />
