<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import UsageAnalytics from '../UsageAnalytics.svelte';

	interface Props {
		onOpenChange?: (open: boolean) => void;
		open?: boolean;
	}

	let { onOpenChange, open = false }: Props = $props();

	function handleClose() {
		onOpenChange?.(false);
	}
</script>

<Dialog.Root {open} onOpenChange={handleClose}>
	<Dialog.Content
		class="z-999999 flex h-[100dvh] max-h-[100dvh] min-h-[100dvh] flex-col gap-0 rounded-none p-0
			md:h-[80vh] md:max-h-[80vh] md:min-h-0 md:rounded-lg overflow-auto"
		style="max-width: 48rem;"
	>
		<Dialog.Header class="px-6 pt-6 pb-0">
			<Dialog.Title>Usage Analytics</Dialog.Title>
			<Dialog.Description>View your usage statistics and activity trends.</Dialog.Description>
		</Dialog.Header>
		<div class="flex-1 overflow-auto">
			<UsageAnalytics />
		</div>
	</Dialog.Content>
</Dialog.Root>
