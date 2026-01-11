<script lang="ts">
	import { onMount } from 'svelte';
	import { ChevronDown, Loader2, Check, X, Server, Key, RefreshCw } from '@lucide/svelte';
	import { cn } from '$lib/components/ui/utils';
	import {
		providers,
		activeProviderId,
		activeProvider,
		providersLoading,
		providersTesting,
		fetchProviders,
		selectProvider,
		setProviderApiKey,
		testProvider,
		hasProviderApiKey,
		getProviderApiKeyMasked,
		lastTestResult
	} from '$lib/stores/providers.svelte';
	import { fetchModels } from '$lib/stores/models.svelte';
	import type { Provider } from '$lib/types/providers';

	interface Props {
		class?: string;
		showApiKeyInput?: boolean;
	}

	let { class: className = '', showApiKeyInput = true }: Props = $props();

	let providerList = $derived(providers());
	let currentProviderId = $derived(activeProviderId());
	let currentProvider = $derived(activeProvider());
	let loading = $derived(providersLoading());
	let testing = $derived(providersTesting());
	let testResult = $derived(lastTestResult());

	let isOpen = $state(false);
	let apiKeyInput = $state('');
	let showApiKeyField = $state(false);

	onMount(async () => {
		try {
			await fetchProviders();
			// Also fetch models for the initial provider
			await fetchModels();
		} catch (error) {
			console.error('Failed to fetch providers:', error);
		}
	});

	function toggleDropdown() {
		if (loading) return;
		isOpen = !isOpen;
	}

	async function handleSelectProvider(provider: Provider) {
		selectProvider(provider.id);
		isOpen = false;
		apiKeyInput = '';
		showApiKeyField = provider.hasApiKey && !hasProviderApiKey(provider.id);
		
		// Re-fetch models for the new provider
		try {
			await fetchModels(true);
		} catch (error) {
			console.error('Failed to fetch models for new provider:', error);
		}
	}

	function handleSaveApiKey() {
		if (apiKeyInput.trim()) {
			setProviderApiKey(currentProviderId, apiKeyInput.trim());
			apiKeyInput = '';
			showApiKeyField = false;
		}
	}

	async function handleTestConnection() {
		await testProvider();
	}

	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.provider-selector')) {
			isOpen = false;
		}
	}

	function getProviderIcon(provider: Provider): string {
		const icons: Record<string, string> = {
			'llama.cpp': '🦙',
			ollama: '🦙',
			openai: '🤖',
			gemini: '✨',
			groq: '⚡'
		};
		return icons[provider.id] || '🔌';
	}
</script>

<svelte:document onclick={handleClickOutside} />

<div class={cn('provider-selector relative', className)}>
	<!-- Provider Dropdown Button -->
	<button
		type="button"
		class={cn(
			'flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm transition',
			'hover:bg-accent hover:text-accent-foreground',
			'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
			loading && 'cursor-not-allowed opacity-60'
		)}
		onclick={toggleDropdown}
		disabled={loading}
	>
		{#if loading && providerList.length === 0}
			<Loader2 class="h-4 w-4 animate-spin" />
			<span>Loading...</span>
		{:else if currentProvider}
			<span class="text-base">{getProviderIcon(currentProvider)}</span>
			<span class="font-medium">{currentProvider.name}</span>
			{#if currentProvider.hasApiKey}
				{#if hasProviderApiKey(currentProvider.id)}
					<Key class="h-3 w-3 text-green-500" />
				{:else}
					<Key class="h-3 w-3 text-yellow-500" />
				{/if}
			{/if}
			<ChevronDown class={cn('h-4 w-4 transition-transform', isOpen && 'rotate-180')} />
		{:else}
			<Server class="h-4 w-4" />
			<span>Select Provider</span>
			<ChevronDown class="h-4 w-4" />
		{/if}
	</button>

	<!-- Dropdown Menu -->
	{#if isOpen}
		<div
			class="absolute left-0 top-full z-50 mt-1 min-w-[200px] overflow-hidden rounded-lg border border-border bg-popover shadow-lg"
		>
			{#each providerList as provider (provider.id)}
				<button
					type="button"
					class={cn(
						'flex w-full items-center gap-3 px-3 py-2 text-left text-sm transition',
						'hover:bg-accent hover:text-accent-foreground',
						provider.id === currentProviderId && 'bg-accent/50'
					)}
					onclick={() => handleSelectProvider(provider)}
				>
					<span class="text-base">{getProviderIcon(provider)}</span>
					<div class="flex-1">
						<div class="font-medium">{provider.name}</div>
						<div class="text-xs text-muted-foreground">
							{provider.hasApiKey ? 'Requires API key' : 'Local'}
						</div>
					</div>
					{#if provider.id === currentProviderId}
						<Check class="h-4 w-4 text-primary" />
					{/if}
				</button>
			{/each}
		</div>
	{/if}

	<!-- API Key Input (for cloud providers) -->
	{#if showApiKeyInput && currentProvider?.hasApiKey}
		<div class="mt-2 space-y-2">
			{#if hasProviderApiKey(currentProviderId)}
				<div class="flex items-center gap-2 text-xs text-muted-foreground">
					<Key class="h-3 w-3 text-green-500" />
					<span>API Key: {getProviderApiKeyMasked(currentProviderId)}</span>
					<button
						type="button"
						class="text-xs text-primary hover:underline"
						onclick={() => (showApiKeyField = true)}
					>
						Change
					</button>
				</div>
			{:else}
				<div class="flex items-center gap-2 text-xs text-yellow-600 dark:text-yellow-400">
					<Key class="h-3 w-3" />
					<span>API key required for {currentProvider.name}</span>
				</div>
			{/if}

			{#if showApiKeyField || !hasProviderApiKey(currentProviderId)}
				<div class="flex gap-2">
					<input
						type="password"
						placeholder="Enter API key..."
						class="flex-1 rounded-md border border-input bg-background px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
						bind:value={apiKeyInput}
						onkeydown={(e) => e.key === 'Enter' && handleSaveApiKey()}
					/>
					<button
						type="button"
						class="rounded-md bg-primary px-3 py-1 text-sm text-primary-foreground hover:bg-primary/90"
						onclick={handleSaveApiKey}
						disabled={!apiKeyInput.trim()}
					>
						Save
					</button>
				</div>
			{/if}
		</div>
	{/if}

	<!-- Test Connection Button -->
	<div class="mt-2 flex items-center gap-2">
		<button
			type="button"
			class={cn(
				'flex items-center gap-1.5 rounded-md border border-border px-2 py-1 text-xs transition',
				'hover:bg-accent hover:text-accent-foreground',
				testing && 'cursor-not-allowed opacity-60'
			)}
			onclick={handleTestConnection}
			disabled={testing}
		>
			{#if testing}
				<Loader2 class="h-3 w-3 animate-spin" />
				<span>Testing...</span>
			{:else}
				<RefreshCw class="h-3 w-3" />
				<span>Test Connection</span>
			{/if}
		</button>

		{#if testResult}
			{#if testResult.success}
				<span class="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
					<Check class="h-3 w-3" />
					Connected ({testResult.models?.length || 0} models)
				</span>
			{:else}
				<span class="flex items-center gap-1 text-xs text-red-600 dark:text-red-400">
					<X class="h-3 w-3" />
					{testResult.error || 'Failed'}
				</span>
			{/if}
		{/if}
	</div>
</div>
