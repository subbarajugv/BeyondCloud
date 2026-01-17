<script lang="ts">
	import { agentStore } from '$lib/stores/agentStore.svelte';
	import { agentApi, type ToolExecuteResult } from '$lib/services/agentApi';
	import { 
		Terminal, FileText, FolderOpen, Search, 
		Check, X, Loader2, AlertTriangle, Shield, ShieldCheck 
	} from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';

	interface Props {
		toolCalls: Array<{
			id?: string;
			type?: string;
			function?: {
				name?: string;
				arguments?: string;
			};
		}>;
		onToolResult?: (results: Array<{ tool_call_id: string; content: string }>) => void;
	}

	let { toolCalls, onToolResult }: Props = $props();

	let processing = $state<Record<string, boolean>>({});
	let results = $state<Record<string, ToolExecuteResult>>({});

	const toolIcons: Record<string, typeof Terminal> = {
		read_file: FileText,
		write_file: FileText,
		list_dir: FolderOpen,
		search_files: Search,
		run_command: Terminal,
	};

	function getToolIcon(name: string) {
		return toolIcons[name] || Terminal;
	}

	function parseArgs(argsString?: string): Record<string, unknown> {
		if (!argsString) return {};
		try {
			return JSON.parse(argsString);
		} catch {
			return { raw: argsString };
		}
	}

	async function executeTool(toolCall: typeof toolCalls[0]) {
		const callId = toolCall.id || `call_${Date.now()}`;
		const toolName = toolCall.function?.name || 'unknown';
		const args = parseArgs(toolCall.function?.arguments);

		processing[callId] = true;

		try {
			// Execute with approval (we're in the approval flow)
			const result = await agentStore.executeTool(toolName, args, true);
			results[callId] = result;

			// If successful, notify parent with result
			if (result.status === 'success' && onToolResult) {
				onToolResult([{
					tool_call_id: callId,
					content: JSON.stringify(result.result)
				}]);
			}
		} catch (e) {
			results[callId] = {
				status: 'error',
				tool_name: toolName,
				args,
				error: (e as Error).message
			};
		} finally {
			processing[callId] = false;
		}
	}

	function rejectTool(toolCall: typeof toolCalls[0]) {
		const callId = toolCall.id || `call_${Date.now()}`;
		results[callId] = {
			status: 'rejected',
			tool_name: toolCall.function?.name || 'unknown',
			args: parseArgs(toolCall.function?.arguments),
			error: 'Rejected by user'
		};

		// Notify parent with rejection
		if (onToolResult) {
			onToolResult([{
				tool_call_id: callId,
				content: 'Tool call rejected by user'
			}]);
		}
	}

	async function approveAll() {
		for (const tool of toolCalls) {
			if (!results[tool.id || '']) {
				await executeTool(tool);
			}
		}
	}
</script>

{#if !agentStore.sandboxActive}
	<div class="my-2 rounded-lg border border-yellow-500/20 bg-yellow-500/10 p-3">
		<div class="flex items-center gap-2 text-yellow-600">
			<AlertTriangle class="h-4 w-4" />
			<span class="text-sm font-medium">Sandbox not configured</span>
		</div>
		<p class="mt-1 text-xs text-muted-foreground">
			Set a sandbox folder in settings to enable tool execution.
		</p>
	</div>
{:else}
	<div class="my-3 space-y-2 rounded-lg border bg-muted/30 p-3">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2 text-sm font-medium">
				<ShieldCheck class="h-4 w-4 text-primary" />
				Agent wants to use {toolCalls.length} tool{toolCalls.length > 1 ? 's' : ''}
			</div>
			{#if toolCalls.length > 1 && Object.keys(results).length < toolCalls.length}
				<Button variant="outline" size="sm" onclick={approveAll}>
					Approve All
				</Button>
			{/if}
		</div>

		{#each toolCalls as tool (tool.id || tool.function?.name)}
			{@const callId = tool.id || `call_${tool.function?.name}`}
			{@const Icon = getToolIcon(tool.function?.name || '')}
			{@const args = parseArgs(tool.function?.arguments)}
			{@const result = results[callId]}
			{@const isProcessing = processing[callId]}

			<div class="rounded-md border bg-card p-2.5">
				<div class="flex items-start gap-2">
					<svelte:component this={Icon} class="mt-0.5 h-4 w-4 flex-shrink-0 text-muted-foreground" />
					
					<div class="min-w-0 flex-1">
						<p class="text-sm font-medium">{tool.function?.name}</p>
						<pre class="mt-1 max-h-24 overflow-auto rounded bg-muted px-2 py-1 text-xs">{JSON.stringify(args, null, 2)}</pre>
					</div>
				</div>

				{#if result}
					<!-- Show result -->
					<div class="mt-2 rounded bg-muted p-2">
						{#if result.status === 'success'}
							<div class="flex items-center gap-1 text-xs text-green-600">
								<Check class="h-3 w-3" />
								<span>Success</span>
							</div>
							<pre class="mt-1 max-h-32 overflow-auto text-xs">{JSON.stringify(result.result, null, 2)}</pre>
						{:else if result.status === 'rejected'}
							<div class="flex items-center gap-1 text-xs text-muted-foreground">
								<X class="h-3 w-3" />
								<span>Rejected</span>
							</div>
						{:else if result.status === 'error'}
							<div class="flex items-center gap-1 text-xs text-destructive">
								<AlertTriangle class="h-3 w-3" />
								<span>{result.error}</span>
							</div>
						{/if}
					</div>
				{:else}
					<!-- Show approval buttons -->
					<div class="mt-2 flex gap-2">
						<Button
							variant="default"
							size="sm"
							class="h-7 flex-1"
							onclick={() => executeTool(tool)}
							disabled={isProcessing}
						>
							{#if isProcessing}
								<Loader2 class="mr-1 h-3 w-3 animate-spin" />
							{:else}
								<Check class="mr-1 h-3 w-3" />
							{/if}
							Approve
						</Button>
						<Button
							variant="outline"
							size="sm"
							class="h-7 flex-1"
							onclick={() => rejectTool(tool)}
							disabled={isProcessing}
						>
							<X class="mr-1 h-3 w-3" />
							Reject
						</Button>
					</div>
				{/if}
			</div>
		{/each}
	</div>
{/if}
