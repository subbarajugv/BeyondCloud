<script lang="ts">
	import '../../app.css';
	import { page } from '$app/state';
	import { ChatSidebar, DialogConversationTitleUpdate } from '$lib/components/app';
	import {
		activeMessages,
		isLoading,
		setTitleUpdateConfirmationCallback
	} from '$lib/stores/chat.svelte';
	import { authStore } from '$lib/stores/auth.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { serverStore } from '$lib/stores/server.svelte';
	import { config, settingsStore } from '$lib/stores/settings.svelte';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	let { children } = $props();

	// Auth Guard
	onMount(() => {
		if (!authStore.isAuthenticated && !authStore.isLoading) {
			goto('/login');
		}
	});

	$effect(() => {
		if (!authStore.isLoading && !authStore.isAuthenticated) {
			goto('/login');
		}
	});

	let isChatRoute = $derived(page.route.id === '/(app)/chat/[id]');
	let isHomeRoute = $derived(page.route.id === '/(app)');
	let isNewChatMode = $derived(page.url.searchParams.get('new_chat') === 'true');
	let showSidebarByDefault = $derived(activeMessages().length > 0 || isLoading());
	let sidebarOpen = $state(false);
	let innerHeight = $state<number | undefined>();
	let chatSidebar:
		| { activateSearchMode?: () => void; editActiveConversation?: () => void }
		| undefined = $state();

	// Conversation title update dialog state
	let titleUpdateDialogOpen = $state(false);
	let titleUpdateCurrentTitle = $state('');
	let titleUpdateNewTitle = $state('');
	let titleUpdateResolve: ((value: boolean) => void) | null = null;
	let showUserMenu = $state(false);
	let showAnalyticsDialog = $state(false);

	import { DialogUsageAnalytics } from '$lib/components/app';

	// Logout handler
	function handleLogout() {
		authStore.logout();
		goto('/login');
	}

	// Global keyboard shortcuts
	function handleKeydown(event: KeyboardEvent) {
		const isCtrlOrCmd = event.ctrlKey || event.metaKey;

		if (isCtrlOrCmd && event.key === 'k') {
			event.preventDefault();
			if (chatSidebar?.activateSearchMode) {
				chatSidebar.activateSearchMode();
				sidebarOpen = true;
			}
		}

		if (isCtrlOrCmd && event.shiftKey && event.key === 'O') {
			event.preventDefault();
			goto('?new_chat=true#/');
		}

		if (event.shiftKey && isCtrlOrCmd && event.key === 'E') {
			event.preventDefault();

			if (chatSidebar?.editActiveConversation) {
				chatSidebar.editActiveConversation();
			}
		}
	}

	function handleTitleUpdateCancel() {
		titleUpdateDialogOpen = false;
		if (titleUpdateResolve) {
			titleUpdateResolve(false);
			titleUpdateResolve = null;
		}
	}

	function handleTitleUpdateConfirm() {
		titleUpdateDialogOpen = false;
		if (titleUpdateResolve) {
			titleUpdateResolve(true);
			titleUpdateResolve = null;
		}
	}

	$effect(() => {
		if (isHomeRoute && !isNewChatMode) {
			// Auto-collapse sidebar when navigating to home route (but not in new chat mode)
			sidebarOpen = false;
		} else if (isHomeRoute && isNewChatMode) {
			// Keep sidebar open in new chat mode
			sidebarOpen = true;
		} else if (isChatRoute) {
			// On chat routes, show sidebar by default
			sidebarOpen = true;
		} else {
			// Other routes follow default behavior
			sidebarOpen = showSidebarByDefault;
		}
	});

	// Initialize server properties on app load
	$effect(() => {
		serverStore.fetchServerProps();
	});

	// Sync settings when server props are loaded
	$effect(() => {
		const serverProps = serverStore.serverProps;

		if (serverProps?.default_generation_settings?.params) {
			settingsStore.syncWithServerDefaults();
		}
	});

	// Set up title update confirmation callback
	$effect(() => {
		setTitleUpdateConfirmationCallback(async (currentTitle: string, newTitle: string) => {
			return new Promise<boolean>((resolve) => {
				titleUpdateCurrentTitle = currentTitle;
				titleUpdateNewTitle = newTitle;
				titleUpdateResolve = resolve;
				titleUpdateDialogOpen = true;
			});
		});
	});
</script>

<DialogUsageAnalytics bind:open={showAnalyticsDialog} />

<DialogConversationTitleUpdate
	bind:open={titleUpdateDialogOpen}
	currentTitle={titleUpdateCurrentTitle}
	newTitle={titleUpdateNewTitle}
	onConfirm={handleTitleUpdateConfirm}
	onCancel={handleTitleUpdateCancel}
/>

<Sidebar.Provider bind:open={sidebarOpen}>
	<div class="flex h-screen w-full" style:height="{innerHeight}px">
		<Sidebar.Root class="h-full">
			<ChatSidebar bind:this={chatSidebar} />
		</Sidebar.Root>

		<Sidebar.Trigger
			class="transition-left absolute left-0 z-[900] h-8 w-8 duration-200 ease-linear {sidebarOpen
				? 'md:left-[var(--sidebar-width)]'
				: ''}"
			style="translate: 1rem 1rem;"
		/>

		<Sidebar.Inset class="flex flex-1 flex-col overflow-hidden">
			<!-- User Menu - positioned to the left of settings button -->
			<div class="fixed right-16 top-4 z-[51]">
				<button
					onclick={() => showUserMenu = !showUserMenu}
					class="flex items-center gap-2 rounded-lg bg-slate-800/80 px-3 py-2 text-sm text-white shadow-lg backdrop-blur-sm transition-colors hover:bg-slate-700"
				>
					<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
						<circle cx="12" cy="7" r="4"></circle>
					</svg>
					<span class="hidden sm:inline">{authStore.user?.displayName || authStore.user?.email || 'User'}</span>
				</button>

				{#if showUserMenu}
					<div class="absolute right-0 mt-2 w-48 rounded-lg border border-slate-700 bg-slate-800 py-2 shadow-xl">
						<div class="border-b border-slate-700 px-4 py-2">
							<p class="text-sm font-medium text-white">{authStore.user?.displayName || 'User'}</p>
							<p class="text-xs text-slate-400">{authStore.user?.email}</p>
						</div>
						<button
							onclick={() => { showAnalyticsDialog = true; showUserMenu = false; }}
							class="flex w-full items-center gap-2 px-4 py-2 text-sm text-slate-300 transition-colors hover:bg-slate-700"
						>
							<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<path d="M3 3v18h18"></path>
								<path d="M18 17V9"></path>
								<path d="M13 17V5"></path>
								<path d="M8 17v-3"></path>
							</svg>
							Usage Analytics
						</button>
						<button
							onclick={handleLogout}
							class="flex w-full items-center gap-2 px-4 py-2 text-sm text-red-400 transition-colors hover:bg-slate-700"
						>
							<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
								<polyline points="16 17 21 12 16 7"></polyline>
								<line x1="21" y1="12" x2="9" y2="12"></line>
							</svg>
							Sign out
						</button>
					</div>
				{/if}
			</div>

			{@render children?.()}
		</Sidebar.Inset>
	</div>
</Sidebar.Provider>

<svelte:window onkeydown={handleKeydown} bind:innerHeight />
