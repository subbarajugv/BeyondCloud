<script lang="ts">
	import { agentApi, type PendingToolCall, type ToolExecuteResult } from '$lib/services/agentApi';
	import { Terminal, FileText, FolderOpen, Search, Check, X, Shield, AlertTriangle, AlertOctagon } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import { toast } from 'svelte-sonner';

	interface Props {
		call: PendingToolCall;
		onResolved?: (result: ToolExecuteResult | null) => void;
	}

	let { call, onResolved }: Props = $props();

	let isProcessing = $state(false);

	const toolIcons: Record<string, typeof Terminal> = {
		read_file: FileText,
		write_file: FileText,
		list_dir: FolderOpen,
		search_files: Search,
		run_command: Terminal,
	};

	const safetyColors: Record<string, string> = {
		safe: 'text-green-600 bg-green-500/10',
		moderate: 'text-yellow-600 bg-yellow-500/10',
		dangerous: 'text-red-600 bg-red-500/10',
	};

	const safetyIcons: Record<string, typeof Shield> = {
		safe: Shield,
		moderate: AlertTriangle,
		dangerous: AlertOctagon,
	};

	async function approve() {
		isProcessing = true;
		try {
			const result = await agentApi.approveCall(call.id);
			toast.success(`Executed: ${call.tool_name}`);
			onResolved?.(result);
		} catch (e) {
			const error = e as Error;
			toast.error(`Failed: ${error.message}`);
			onResolved?.(null);
		} finally {
			isProcessing = false;
		}
	}

	async function reject() {
		isProcessing = true;
		try {
			await agentApi.rejectCall(call.id);
			toast.info(`Rejected: ${call.tool_name}`);
			onResolved?.(null);
		} catch (e) {
			const error = e as Error;
			toast.error(`Failed: ${error.message}`);
		} finally {
			isProcessing = false;
		}
	}

	const Icon = $derived(toolIcons[call.tool_name] || Terminal);
	const SafetyIcon = $derived(safetyIcons[call.safety_level] || Shield);
</script>

<div class="rounded-lg border bg-card p-3">
	<div class="mb-2 flex items-center gap-2">
		<svelte:component this={Icon} class="h-4 w-4" />
		<span class="font-medium">{call.tool_name}</span>
		<span class="ml-auto flex items-center gap-1 rounded px-2 py-0.5 text-xs {safetyColors[call.safety_level]}">
			<svelte:component this={SafetyIcon} class="h-3 w-3" />
			{call.safety_level}
		</span>
	</div>

	<pre class="mb-3 max-h-32 overflow-auto rounded bg-muted p-2 text-xs">{JSON.stringify(call.args, null, 2)}</pre>

	<div class="flex gap-2">
		<Button
			variant="default"
			size="sm"
			class="flex-1"
			onclick={approve}
			disabled={isProcessing}
		>
			<Check class="mr-1 h-4 w-4" />
			Approve
		</Button>
		<Button
			variant="outline"
			size="sm"
			class="flex-1"
			onclick={reject}
			disabled={isProcessing}
		>
			<X class="mr-1 h-4 w-4" />
			Reject
		</Button>
	</div>
</div>
