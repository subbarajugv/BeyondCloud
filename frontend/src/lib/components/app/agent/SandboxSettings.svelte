<script lang="ts">
	import { agentApi, type ApprovalMode, type AgentStatus } from '$lib/services/agentApi';
	import { Folder, Shield, ShieldCheck, RefreshCw, Loader2 } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import { toast } from 'svelte-sonner';
	import { onMount } from 'svelte';

	let sandboxPath = $state('');
	let status = $state<AgentStatus | null>(null);
	let isLoading = $state(false);
	let isSaving = $state(false);

	onMount(async () => {
		await loadStatus();
	});

	async function loadStatus() {
		isLoading = true;
		try {
			status = await agentApi.getStatus();
			if (status.sandbox_path) {
				sandboxPath = status.sandbox_path;
			}
		} catch (e) {
			console.error('Failed to load agent status:', e);
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
			const result = await agentApi.setSandbox(sandboxPath);
			toast.success(result.message);
			await loadStatus();
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
</script>

<div class="space-y-4 rounded-lg border bg-card p-4">
	<div class="flex items-center gap-2">
		<Folder class="h-5 w-5" />
		<h3 class="font-semibold">Agent Sandbox</h3>
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

	<p class="text-sm text-muted-foreground">
		Set a folder where the AI agent can read/write files and run commands.
	</p>

	<div class="flex gap-2">
		<input
			type="text"
			placeholder="/path/to/project"
			bind:value={sandboxPath}
			class="flex-1 rounded-md border bg-background px-3 py-2 text-sm"
		/>
		<Button onclick={setSandbox} disabled={isSaving}>
			{#if isSaving}
				<Loader2 class="mr-2 h-4 w-4 animate-spin" />
			{/if}
			Set
		</Button>
	</div>

	{#if status?.sandbox_active}
		<div class="flex items-center gap-2 rounded-md bg-green-500/10 p-2 text-sm text-green-600">
			<ShieldCheck class="h-4 w-4" />
			<span>Sandbox active: {status.sandbox_path}</span>
		</div>

		<!-- Trust Mode Toggle -->
		<div class="flex items-center justify-between rounded-md border p-3">
			<div>
				<p class="text-sm font-medium">Approval Mode</p>
				<p class="text-xs text-muted-foreground">
					{#if status.approval_mode === 'trust_mode'}
						Auto-execute safe tools (commands still need approval)
					{:else}
						All tool calls require your approval
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
				{status.pending_approvals} pending tool call(s) awaiting approval
			</div>
		{/if}
	{/if}
</div>
