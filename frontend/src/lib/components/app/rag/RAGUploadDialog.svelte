<script lang="ts">
	import { ragStore } from '$lib/stores/ragStore.svelte';
	import { authStore } from '$lib/stores/auth.svelte';
	import { Upload, FileText, X, Loader2, Globe, Lock, Folder } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import * as Dialog from '$lib/components/ui/dialog';
	import type { VisibilityType } from '$lib/services/ragApi';
	import { onMount } from 'svelte';

	interface Props {
		open: boolean;
		onOpenChange: (open: boolean) => void;
	}

	let { open, onOpenChange }: Props = $props();

	let mode = $state<'file' | 'text'>('file');
	let textName = $state('');
	let textContent = $state('');
	let selectedFile = $state<File | null>(null);
	let chunkSize = $state(500);
	let chunkOverlap = $state(50);
	let visibility = $state<VisibilityType>('private');
	let isDragging = $state(false);
	let selectedCollectionId = $state<string | null>(null);

	const acceptedTypes = '.txt,.md,.pdf,.docx,.html';
	const isAdmin = $derived(authStore.isAdmin);

	// Load collections when dialog opens
	$effect(() => {
		if (open) {
			ragStore.loadCollections();
			// Default to current collection
			selectedCollectionId = ragStore.currentCollectionId;
		}
	});

	function reset() {
		mode = 'file';
		textName = '';
		textContent = '';
		selectedFile = null;
		isDragging = false;
		visibility = 'private';
		selectedCollectionId = ragStore.currentCollectionId;
	}

	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		isDragging = true;
	}

	function handleDragLeave() {
		isDragging = false;
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		isDragging = false;
		const file = e.dataTransfer?.files[0];
		if (file) {
			selectedFile = file;
		}
	}

	function handleFileSelect(e: Event) {
		const input = e.target as HTMLInputElement;
		if (input.files?.[0]) {
			selectedFile = input.files[0];
		}
	}

	async function handleUpload() {
		let success = false;
		if (mode === 'file' && selectedFile) {
			success = await ragStore.ingestFileToCollection(
				selectedFile, 
				selectedCollectionId,
				chunkSize, 
				chunkOverlap, 
				visibility
			);
		} else if (mode === 'text' && textName && textContent) {
			success = await ragStore.ingestText(textName, textContent, chunkSize, chunkOverlap, visibility);
		}
		if (success) {
			reset();
			onOpenChange(false);
		}
	}

	function handleClose() {
		reset();
		onOpenChange(false);
	}

	const canUpload = $derived(
		mode === 'file' ? !!selectedFile : textName.trim() && textContent.trim()
	);
</script>

<Dialog.Root {open} onOpenChange={(o) => (o ? onOpenChange(o) : handleClose())}>
	<Dialog.Content class="max-w-lg">
		<Dialog.Header>
			<Dialog.Title>Upload Document</Dialog.Title>
			<Dialog.Description>
				Add documents to your knowledge base for RAG queries.
			</Dialog.Description>
		</Dialog.Header>

		<div class="space-y-4">
			<!-- Mode toggle -->
			<div class="flex gap-2">
				<Button
					variant={mode === 'file' ? 'default' : 'outline'}
					size="sm"
					onclick={() => (mode = 'file')}
				>
					<Upload class="mr-1 h-4 w-4" />
					Upload File
				</Button>
				<Button
					variant={mode === 'text' ? 'default' : 'outline'}
					size="sm"
					onclick={() => (mode = 'text')}
				>
					<FileText class="mr-1 h-4 w-4" />
					Paste Text
				</Button>
			</div>

			{#if mode === 'file'}
				<!-- File upload area -->
				<div
					class="relative rounded-lg border-2 border-dashed p-6 text-center transition-colors {isDragging
						? 'border-primary bg-primary/5'
						: 'border-muted-foreground/25 hover:border-primary/50'}"
					ondragover={handleDragOver}
					ondragleave={handleDragLeave}
					ondrop={handleDrop}
				>
					{#if selectedFile}
						<div class="flex items-center justify-center gap-2">
							<FileText class="h-5 w-5 text-primary" />
							<span class="font-medium">{selectedFile.name}</span>
							<button
								type="button"
								class="ml-2 text-muted-foreground hover:text-foreground"
								onclick={() => (selectedFile = null)}
							>
								<X class="h-4 w-4" />
							</button>
						</div>
					{:else}
						<Upload class="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
						<p class="text-sm">Drag & drop or click to browse</p>
						<p class="text-xs text-muted-foreground">Supports: .txt, .md, .pdf, .docx, .html</p>
					{/if}
					<input
						type="file"
						accept={acceptedTypes}
						class="absolute inset-0 cursor-pointer opacity-0"
						onchange={handleFileSelect}
					/>
				</div>
			{:else}
				<!-- Text input -->
				<div class="space-y-3">
					<input
						type="text"
						placeholder="Document name"
						bind:value={textName}
						class="w-full rounded-md border bg-background px-3 py-2 text-sm"
					/>
					<textarea
						placeholder="Paste your text content here..."
						bind:value={textContent}
						rows={8}
						class="w-full resize-none rounded-md border bg-background px-3 py-2 text-sm"
					></textarea>
				</div>
			{/if}

			<!-- Folder picker -->
			{#if ragStore.collections.length > 0}
				<div class="rounded-md border bg-muted/30 p-3">
					<label class="mb-2 block text-sm font-medium">
						<Folder class="mr-1.5 inline-block h-4 w-4" />
						Save to folder
					</label>
					<select
						bind:value={selectedCollectionId}
						class="w-full rounded-md border bg-background px-3 py-2 text-sm"
					>
						<option value={null}>No folder (root)</option>
						{#each ragStore.collections as collection}
							<option value={collection.id}>{collection.name}</option>
						{/each}
					</select>
				</div>
			{/if}

			<!-- Visibility selector (admin only) -->
			{#if isAdmin}
				<div class="rounded-md border bg-muted/30 p-3">
					<label class="mb-2 block text-sm font-medium">Visibility</label>
					<div class="flex gap-2">
						<Button
							variant={visibility === 'private' ? 'default' : 'outline'}
							size="sm"
							onclick={() => (visibility = 'private')}
						>
							<Lock class="mr-1.5 h-3.5 w-3.5" />
							Private
						</Button>
						<Button
							variant={visibility === 'shared' ? 'default' : 'outline'}
							size="sm"
							onclick={() => (visibility = 'shared')}
						>
							<Globe class="mr-1.5 h-3.5 w-3.5" />
							Shared
						</Button>
					</div>
					{#if visibility === 'shared'}
						<p class="mt-2 text-xs text-amber-600 dark:text-amber-400">
							⚠️ Shared sources are visible to all users
						</p>
					{/if}
				</div>
			{/if}

			<!-- Chunking settings -->
			<details class="text-sm">
				<summary class="cursor-pointer text-muted-foreground hover:text-foreground">
					Advanced settings
				</summary>
				<div class="mt-2 grid grid-cols-2 gap-3">
					<div>
						<label class="mb-1 block text-xs text-muted-foreground">Chunk size</label>
						<input
							type="number"
							bind:value={chunkSize}
							min="100"
							max="2000"
							class="w-full rounded-md border bg-background px-2 py-1 text-sm"
						/>
					</div>
					<div>
						<label class="mb-1 block text-xs text-muted-foreground">Chunk overlap</label>
						<input
							type="number"
							bind:value={chunkOverlap}
							min="0"
							max="500"
							class="w-full rounded-md border bg-background px-2 py-1 text-sm"
						/>
					</div>
				</div>
			</details>
		</div>

		<Dialog.Footer>
			<Button variant="outline" onclick={handleClose}>Cancel</Button>
			<Button onclick={handleUpload} disabled={!canUpload || ragStore.isUploading}>
				{#if ragStore.isUploading}
					<Loader2 class="mr-2 h-4 w-4 animate-spin" />
					Uploading...
				{:else}
					<Upload class="mr-2 h-4 w-4" />
					Upload
				{/if}
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

