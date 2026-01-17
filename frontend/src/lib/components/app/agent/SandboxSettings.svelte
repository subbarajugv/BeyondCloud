<script lang="ts">
	import { 
		agentApi, 
		type ApprovalMode, 
		type AgentStatus, 
		type AgentMode,
		getAgentMode,
		setAgentMode,
		checkLocalDaemon
	} from '$lib/services/agentApi';
	import { agentStore } from '$lib/stores/agentStore.svelte';
	import { Folder, Shield, ShieldCheck, RefreshCw, Loader2, Info, Cloud, Monitor, AlertCircle, CheckCircle2 } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import { toast } from 'svelte-sonner';
	import { onMount } from 'svelte';

	let sandboxPath = $state('');
	let status = $state<AgentStatus | null>(null);
	let isLoading = $state(false);
	let isSaving = $state(false);
	let agentMode = $state<AgentMode>(getAgentMode());
	let daemonAvailable = $state<boolean | null>(null);

	// Common example paths
	const examplePaths = [
		{ label: 'Home', path: '~' },
		{ label: 'Documents', path: '~/Documents' },
		{ label: 'Projects', path: '~/projects' },
		{ label: 'Downloads', path: '~/Downloads' }
	];

	onMount(async () => {
		agentMode = getAgentMode();
		await checkDaemonAndLoadStatus();
	});

	async function checkDaemonAndLoadStatus() {
		if (agentMode === 'local') {
			daemonAvailable = await checkLocalDaemon();
		} else {
			daemonAvailable = true; // Remote mode always "available"
		}
		
		if (daemonAvailable) {
			await loadStatus();
		}
	}

	async function loadStatus() {
		isLoading = true;
		try {
			status = await agentApi.getStatus();
			if (status.sandbox_path) {
				sandboxPath = status.sandbox_path;
			}
			// Sync with agentStore so tool schemas are loaded
			if (status.sandbox_active) {
				await agentStore.initialize();
			}
		} catch (e) {
			console.error('Failed to load agent status:', e);
			status = null;
		} finally {
			isLoading = false;
		}
	}

	async function setSandbox() {
		if (!sandboxPath.trim()) {
			toast.error('Please enter a folder path');
			return;
		}
		isSaving = true;
		try {
			// Use agentStore.setSandbox to ensure tool schemas are loaded
			const success = await agentStore.setSandbox(sandboxPath.trim());
			if (success) {
				toast.success(`Working directory set to: ${agentStore.sandboxPath}`);
				// Reload local status
				status = await agentApi.getStatus();
			} else {
				toast.error(`Failed: ${agentStore.error || 'Unknown error'}`);
			}
		} catch (e) {
			const error = e as Error;
			toast.error(`Failed: ${error.message}`);
		} finally {
			isSaving = false;
		}
	}

	async function toggleMode() {
		if (!status) return;
		const newMode: ApprovalMode = 
			status.approval_mode === 'require_approval' ? 'trust_mode' : 'require_approval';
		
		try {
			await agentApi.setMode(newMode);
			toast.success(`Mode changed to: ${newMode.replace('_', ' ')}`);
			await loadStatus();
		} catch (e) {
			const error = e as Error;
			toast.error(`Failed: ${error.message}`);
		}
	}

	function setQuickPath(path: string) {
		sandboxPath = path;
	}

	async function handleModeChange(mode: AgentMode) {
		agentMode = mode;
		setAgentMode(mode);
		status = null;
		await checkDaemonAndLoadStatus();
	}

	// Tools enabled toggle
	let toolsEnabledLocal = $state(agentStore.toolsEnabled);

	function toggleToolsEnabled() {
		toolsEnabledLocal = !toolsEnabledLocal;
		agentStore.setToolsEnabled(toolsEnabledLocal);
		if (toolsEnabledLocal) {
			toast.success('Agent tools enabled');
		} else {
			toast.info('Agent tools disabled - chat will work without function calling');
		}
	}
</script>

<div class="space-y-4">
	<!-- Enable Tools Toggle -->
	<div class="rounded-lg border bg-card p-4">
		<div class="flex items-center justify-between">
			<div>
				<h3 class="font-semibold">Enable Agent Tools</h3>
				<p class="text-xs text-muted-foreground">
					Requires a model that supports function calling (Llama 3.1+, Qwen 2.5, etc.)
				</p>
			</div>
			<button
				class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors {toolsEnabledLocal ? 'bg-primary' : 'bg-muted'}"
				onclick={toggleToolsEnabled}
			>
				<span
					class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {toolsEnabledLocal ? 'translate-x-6' : 'translate-x-1'}"
				></span>
			</button>
		</div>
		{#if !toolsEnabledLocal}
			<p class="mt-2 text-xs text-yellow-600">
				⚠️ Tools disabled - the AI won't be able to read/write files or run commands
			</p>
		{/if}
	</div>

	<!-- Agent Mode Selector -->
	<div class="rounded-lg border bg-card p-4">
		<div class="flex items-center gap-2 mb-3">
			<h3 class="font-semibold">Agent Mode</h3>
		</div>
		
		<div class="grid grid-cols-2 gap-2">
			<button
				class="flex items-center gap-2 p-3 rounded-lg border-2 transition-all {agentMode === 'local' 
					? 'border-primary bg-primary/10' 
					: 'border-border hover:border-primary/50'}"
				onclick={() => handleModeChange('local')}
			>
				<Monitor class="h-5 w-5 {agentMode === 'local' ? 'text-primary' : ''}" />
				<div class="text-left">
					<div class="font-medium text-sm">Local Agent</div>
					<div class="text-xs text-muted-foreground">Works on your machine</div>
				</div>
			</button>
			
			<button
				class="flex items-center gap-2 p-3 rounded-lg border-2 transition-all {agentMode === 'remote' 
					? 'border-primary bg-primary/10' 
					: 'border-border hover:border-primary/50'}"
				onclick={() => handleModeChange('remote')}
			>
				<Cloud class="h-5 w-5 {agentMode === 'remote' ? 'text-primary' : ''}" />
				<div class="text-left">
					<div class="font-medium text-sm">Remote Agent</div>
					<div class="text-xs text-muted-foreground">Backend server files</div>
				</div>
			</button>
		</div>

		<!-- Local daemon status -->
		{#if agentMode === 'local'}
			<div class="mt-3 flex items-center gap-2 text-sm {daemonAvailable ? 'text-green-600' : 'text-yellow-600'}">
				{#if daemonAvailable === null}
					<Loader2 class="h-4 w-4 animate-spin" />
					<span>Checking daemon...</span>
				{:else if daemonAvailable}
					<CheckCircle2 class="h-4 w-4" />
					<span>Local agent daemon connected</span>
				{:else}
					<AlertCircle class="h-4 w-4" />
					<span>Daemon not running</span>
					<Button variant="link" size="sm" class="h-auto p-0 text-yellow-600" onclick={() => checkDaemonAndLoadStatus()}>
						Retry
					</Button>
				{/if}
			</div>
			
			{#if daemonAvailable === false}
				<div class="mt-2 p-2 rounded bg-muted text-xs font-mono">
					python agent_daemon.py
				</div>
			{/if}
		{/if}
	</div>

	<!-- Working Directory (only show if daemon available or remote mode) -->
	{#if daemonAvailable || agentMode === 'remote'}
		<div class="rounded-lg border bg-card p-4">
			<div class="flex items-center gap-2">
				<Folder class="h-5 w-5 text-primary" />
				<h3 class="font-semibold">Working Directory</h3>
				<Button
					variant="ghost"
					size="icon"
					class="ml-auto h-7 w-7"
					onclick={loadStatus}
					disabled={isLoading}
				>
					<RefreshCw class="h-4 w-4 {isLoading ? 'animate-spin' : ''}" />
				</Button>
			</div>

			<p class="mt-2 text-sm text-muted-foreground">
				Set the folder where the AI can work. Files outside this folder are not accessible.
			</p>

			<div class="mt-3 flex gap-2">
				<input
					type="text"
					placeholder="Enter folder path, e.g. ~/projects/myapp"
					bind:value={sandboxPath}
					class="flex-1 rounded-md border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
				/>
				<Button onclick={setSandbox} disabled={isSaving}>
					{#if isSaving}
						<Loader2 class="mr-2 h-4 w-4 animate-spin" />
					{/if}
					Set
				</Button>
			</div>

			<!-- Quick access paths -->
			<div class="mt-3 flex flex-wrap gap-2">
				<span class="text-xs text-muted-foreground self-center">Quick:</span>
				{#each examplePaths as example}
					<Button 
						variant="outline" 
						size="sm" 
						class="h-6 text-xs"
						onclick={() => setQuickPath(example.path)}
					>
						{example.label}
					</Button>
				{/each}
			</div>
		</div>

		{#if status?.sandbox_active}
			<div class="rounded-lg border bg-card p-4 space-y-3">
				<div class="flex items-center gap-2 rounded-md bg-green-500/10 p-2 text-sm text-green-600">
					<ShieldCheck class="h-4 w-4" />
					<span class="truncate"><strong>Active:</strong> {status.sandbox_path}</span>
				</div>

				<!-- Trust Mode Toggle -->
				<div class="flex items-center justify-between rounded-md border p-3">
					<div>
						<p class="text-sm font-medium">Approval Mode</p>
						<p class="text-xs text-muted-foreground">
							{#if status.approval_mode === 'trust_mode'}
								Auto-execute safe tools
							{:else}
								All tools require approval
							{/if}
						</p>
					</div>
					<Button
						variant={status.approval_mode === 'trust_mode' ? 'default' : 'outline'}
						size="sm"
						onclick={toggleMode}
					>
						{#if status.approval_mode === 'trust_mode'}
							<ShieldCheck class="mr-1 h-4 w-4" />
							Trust Mode
						{:else}
							<Shield class="mr-1 h-4 w-4" />
							Approval Required
						{/if}
					</Button>
				</div>

				{#if status.pending_approvals > 0}
					<div class="rounded-md bg-yellow-500/10 p-2 text-sm text-yellow-600">
						{status.pending_approvals} pending tool call(s)
					</div>
				{/if}
			</div>
		{/if}
	{/if}
</div>

