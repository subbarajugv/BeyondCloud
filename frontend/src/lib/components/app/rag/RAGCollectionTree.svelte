<script lang="ts">
	import { ragStore } from '$lib/stores/ragStore.svelte';
	import { authStore } from '$lib/stores/auth.svelte';
	import type { RAGCollection } from '$lib/services/ragApi';
	import { 
		ChevronRight, 
		ChevronDown, 
		Folder, 
		FolderOpen, 
		Plus, 
		Trash2, 
		Edit2,
		Globe,
		Lock,
		Users
	} from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import { onMount } from 'svelte';

	interface Props {
		onSelect?: (collectionId: string | null) => void;
	}

	let { onSelect }: Props = $props();

	let expandedIds = $state<Set<string>>(new Set());
	let isCreating = $state(false);
	let newFolderName = $state('');
	let editingId = $state<string | null>(null);
	let editingName = $state('');

	const isAdmin = $derived(authStore.isAdmin);

	onMount(() => {
		ragStore.loadCollectionTree();
		ragStore.loadCollections();
	});

	function toggleExpand(id: string) {
		const newSet = new Set(expandedIds);
		if (newSet.has(id)) {
			newSet.delete(id);
		} else {
			newSet.add(id);
		}
		expandedIds = newSet;
	}

	function selectCollection(id: string | null) {
		ragStore.setCurrentCollection(id);
		onSelect?.(id);
	}

	async function createFolder() {
		if (!newFolderName.trim()) return;
		const success = await ragStore.createCollection(
			newFolderName.trim(),
			ragStore.currentCollectionId
		);
		if (success) {
			newFolderName = '';
			isCreating = false;
		}
	}

	async function deleteFolder(e: Event, id: string) {
		e.stopPropagation();
		if (confirm('Delete this folder and all its contents?')) {
			await ragStore.deleteCollection(id);
		}
	}

	function startEditing(e: Event, collection: RAGCollection) {
		e.stopPropagation();
		editingId = collection.id;
		editingName = collection.name;
	}

	async function saveEdit(e: Event) {
		e.stopPropagation();
		if (editingId && editingName.trim()) {
			await ragStore.updateCollection(editingId, editingName.trim());
		}
		editingId = null;
		editingName = '';
	}

	function getVisibilityIcon(visibility: string) {
		switch (visibility) {
			case 'public': return Globe;
			case 'role': return Users;
			case 'team': return Users;
			case 'private': return Lock;
			default: return Lock;
		}
	}

	function getVisibilityColor(visibility: string) {
		switch (visibility) {
			case 'public': return 'text-green-500';
			case 'role': return 'text-blue-500';
			case 'team': return 'text-purple-500';
			case 'private': return 'text-orange-500';
			default: return 'text-gray-500';
		}
	}
</script>

<div class="flex flex-col gap-1">
	<!-- All Sources option -->
	<button
		type="button"
		class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-muted {ragStore.currentCollectionId === null ? 'bg-primary/10 text-primary font-medium' : ''}"
		onclick={() => selectCollection(null)}
	>
		<Folder class="h-4 w-4" />
		<span>All Documents</span>
		<span class="ml-auto text-xs text-muted-foreground">{ragStore.sources.length}</span>
	</button>

	<!-- Collection tree -->
	{#each ragStore.collectionTree as collection (collection.id)}
		{@render collectionNode(collection, 0)}
	{/each}

	<!-- New folder input -->
	{#if isCreating}
		<div class="flex items-center gap-1 px-2 py-1">
			<input
				type="text"
				bind:value={newFolderName}
				placeholder="Folder name"
				class="flex-1 rounded border bg-background px-2 py-1 text-sm"
				onkeydown={(e) => e.key === 'Enter' && createFolder()}
			/>
			<Button size="sm" variant="ghost" onclick={createFolder}>
				<Plus class="h-4 w-4" />
			</Button>
		</div>
	{/if}

	<!-- Add folder button -->
	<button
		type="button"
		class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
		onclick={() => (isCreating = !isCreating)}
	>
		<Plus class="h-4 w-4" />
		<span>New Folder</span>
	</button>
</div>

{#snippet collectionNode(collection: RAGCollection, depth: number)}
	{@const isExpanded = expandedIds.has(collection.id)}
	{@const isSelected = ragStore.currentCollectionId === collection.id}
	{@const hasChildren = collection.children && collection.children.length > 0}
	{@const canModify = collection.is_owner || isAdmin}
	{@const VisibilityIcon = getVisibilityIcon(collection.visibility)}

	<div class="relative" style="padding-left: {depth * 12}px">
		<div
			class="group flex w-full items-center gap-1 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-muted {isSelected ? 'bg-primary/10 text-primary font-medium' : ''}"
		>
			<!-- Expand toggle -->
			{#if hasChildren}
				<button
					type="button"
					class="flex-shrink-0 text-muted-foreground hover:text-foreground"
					onclick={() => toggleExpand(collection.id)}
				>
					{#if isExpanded}
						<ChevronDown class="h-4 w-4" />
					{:else}
						<ChevronRight class="h-4 w-4" />
					{/if}
				</button>
			{:else}
				<span class="w-4"></span>
			{/if}

			<!-- Folder icon -->
			<button
				type="button"
				class="flex flex-1 items-center gap-2 text-left"
				onclick={() => selectCollection(collection.id)}
			>
				{#if isExpanded}
					<FolderOpen class="h-4 w-4 text-amber-500" />
				{:else}
					<Folder class="h-4 w-4 text-amber-500" />
				{/if}

				<!-- Name or edit input -->
				{#if editingId === collection.id}
					<input
						type="text"
						bind:value={editingName}
						class="flex-1 rounded border bg-background px-1 text-sm"
						onclick={(e) => e.stopPropagation()}
						onkeydown={(e) => e.key === 'Enter' && saveEdit(e)}
						onblur={saveEdit}
					/>
				{:else}
					<span class="truncate">{collection.name}</span>
				{/if}

				<!-- Visibility badge -->
				{#if collection.visibility !== 'personal'}
					<VisibilityIcon class="h-3 w-3 {getVisibilityColor(collection.visibility)}" />
				{/if}
			</button>

			<!-- Source count -->
			{#if collection.source_count}
				<span class="text-xs text-muted-foreground">{collection.source_count}</span>
			{/if}

			<!-- Actions -->
			{#if canModify}
				<div class="flex gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
					<button
						type="button"
						class="rounded p-1 text-muted-foreground hover:bg-muted-foreground/10 hover:text-foreground"
						onclick={(e) => startEditing(e, collection)}
						title="Rename"
					>
						<Edit2 class="h-3 w-3" />
					</button>
					<button
						type="button"
						class="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
						onclick={(e) => deleteFolder(e, collection.id)}
						title="Delete"
					>
						<Trash2 class="h-3 w-3" />
					</button>
				</div>
			{/if}
		</div>

		<!-- Children -->
		{#if isExpanded && hasChildren}
			{#each collection.children ?? [] as child (child.id)}
				{@render collectionNode(child, depth + 1)}
			{/each}
		{/if}

	</div>
{/snippet}
