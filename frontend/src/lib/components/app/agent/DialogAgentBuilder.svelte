<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog';
    import AgentBuilder from './AgentBuilder.svelte';

    /** Props */
    interface Props {
        open?: boolean;
        onOpenChange?: (open: boolean) => void;
    }
    let { open = false, onOpenChange }: Props = $props();

    function handleClose() {
        onOpenChange?.(false);
    }

    function handleSave() {
        onOpenChange?.(false);
    }
</script>

<Dialog.Root {open} onOpenChange={onOpenChange}>
    <Dialog.Content 
        class="max-w-3xl h-[90vh] md:h-auto overflow-y-auto bg-[#1a1a1a] border-white/10"
        hideCloseButton={true}
    >
        <AgentBuilder onSave={handleSave} onCancel={handleClose} />
    </Dialog.Content>
</Dialog.Root>
