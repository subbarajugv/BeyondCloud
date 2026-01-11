<script lang="ts">
	import { ChevronDown, Loader2 } from '@lucide/svelte';
	import { cn } from '$lib/components/ui/utils';
	import { portalToBody } from '$lib/utils/portal-to-body';
	import {
		providers,
		activeProviderId,
		activeProvider,
		providersLoading,
		fetchProviders,
		selectProvider
	} from '$lib/stores/providers.svelte';
	import { fetchModels } from '$lib/stores/models.svelte';
	import type { Provider } from '$lib/types/providers';
	import { onMount, tick } from 'svelte';

	interface Props {
		class?: string;
	}

	let { class: className = '' }: Props = $props();

	let providerList = $derived(providers());
	let currentProviderId = $derived(activeProviderId());
	let currentProvider = $derived(activeProvider());
	let loading = $derived(providersLoading());

	let isOpen = $state(false);
	let triggerButton = $state<HTMLButtonElement | null>(null);
	let menuRef = $state<HTMLDivElement | null>(null);
	let menuPosition = $state<{ top: number; left: number } | null>(null);

	onMount(async () => {
		if (providerList.length === 0) {
			await fetchProviders();
		}
	});

	function toggleDropdown() {
		if (loading) return;
		if (isOpen) {
			isOpen = false;
			menuPosition = null;
		} else {
			isOpen = true;
			tick().then(updateMenuPosition);
		}
	}

	function updateMenuPosition() {
		if (!triggerButton || !menuRef) return;
		
		const rect = triggerButton.getBoundingClientRect();
		const menuHeight = menuRef.offsetHeight;
		
		menuPosition = {
			top: rect.top - menuHeight - 4,
			left: rect.left
		};
	}

	async function handleSelectProvider(provider: Provider) {
		selectProvider(provider.id);
		isOpen = false;
		menuPosition = null;

		// Re-fetch models for the new provider
		try {
			await fetchModels(true);
		} catch (error) {
			console.error('Failed to fetch models for new provider:', error);
		}
	}

	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (triggerButton && triggerButton.contains(target)) return;
		if (menuRef && menuRef.contains(target)) return;
		isOpen = false;
		menuPosition = null;
	}

	function getProviderIcon(providerId: string): string {
		const icons: Record<string, string> = {
			'llama.cpp': '🦙',
			ollama: '🦙',
			openai: '🤖',
			gemini: '✨',
			groq: '⚡'
		};
		return icons[providerId] || '🔌';
	}
</script>

<svelte:document onpointerdown={handleClickOutside} />

<div class={cn('inline-provider-selector relative', className)}>
	<button
		type="button"
		bind:this={triggerButton}
		class={cn(
			'flex items-center gap-1.5 rounded-md px-2 py-1 text-sm text-muted-foreground transition',
			'hover:bg-accent hover:text-accent-foreground',
			'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
			loading && 'cursor-not-allowed opacity-60',
			isOpen && 'bg-accent text-accent-foreground'
		)}
		onclick={toggleDropdown}
		disabled={loading}
	>
		{#if loading && providerList.length === 0}
			<Loader2 class="h-3.5 w-3.5 animate-spin" />
		{:else if currentProvider}
			<span class="text-sm">{getProviderIcon(currentProvider.id)}</span>
			<span class="max-w-[80px] truncate text-xs font-medium">{currentProvider.name.split(' ')[0]}</span>
		{:else}
			<span class="text-xs">Provider</span>
		{/if}
		<ChevronDown class={cn('h-3.5 w-3.5 transition-transform', isOpen && 'rotate-180')} />
	</button>

	{#if isOpen}
		<div
			bind:this={menuRef}
			use:portalToBody
			class={cn(
				'fixed z-[1000] min-w-[180px] overflow-hidden rounded-md border border-border bg-popover shadow-lg',
				menuPosition ? 'opacity-100' : 'pointer-events-none opacity-0'
			)}
			style:top={menuPosition ? `${menuPosition.top}px` : undefined}
			style:left={menuPosition ? `${menuPosition.left}px` : undefined}
		>
			{#each providerList as provider (provider.id)}
				<button
					type="button"
					class={cn(
						'flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition',
						'hover:bg-accent hover:text-accent-foreground',
						provider.id === currentProviderId && 'bg-accent/50 font-medium'
					)}
					onclick={() => handleSelectProvider(provider)}
				>
					<span>{getProviderIcon(provider.id)}</span>
					<span class="flex-1">{provider.name}</span>
				</button>
			{/each}
		</div>
	{/if}
</div>
