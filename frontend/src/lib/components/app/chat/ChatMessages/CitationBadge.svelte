<script lang="ts">
  import * as Tooltip from '$lib/components/ui/tooltip';
  import { FileText } from '@lucide/svelte';
  import type { Citation } from '$lib/services/ragApi';

  interface Props {
    citation: Citation;
  }

  let { citation }: Props = $props();
  
  const scorePercent = $derived(Math.round(citation.score * 100));
  
  const scoreColorClass = $derived(
    scorePercent >= 80 
      ? 'bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/30' 
      : scorePercent >= 60 
        ? 'bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 border-yellow-500/30'
        : 'bg-slate-500/20 text-slate-600 dark:text-slate-400 border-slate-500/30'
  );
</script>

<Tooltip.Root>
  <Tooltip.Trigger asChild>
    <button 
      class="inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-medium transition-colors hover:opacity-80 {scoreColorClass}"
      type="button"
    >
      <FileText class="h-3 w-3 flex-shrink-0" />
      <span class="max-w-[120px] truncate">{citation.source_name}</span>
      <span class="rounded bg-black/10 px-1 py-0.5 text-[10px] dark:bg-white/10">
        {scorePercent}%
      </span>
    </button>
  </Tooltip.Trigger>
  <Tooltip.Content class="max-w-sm p-0" side="top">
    <div class="space-y-2 p-3">
      <div class="flex items-center justify-between gap-4">
        <span class="font-medium text-sm">{citation.source_name}</span>
        <span class="text-xs {scoreColorClass} rounded px-1.5 py-0.5">
          {scorePercent}% match
        </span>
      </div>
      
      {#if citation.content_preview}
        <div class="rounded-md bg-muted/50 p-2">
          <p class="text-xs text-muted-foreground italic leading-relaxed line-clamp-4">
            "{citation.content_preview}"
          </p>
        </div>
      {/if}
      
      <p class="text-[10px] text-muted-foreground">
        Click to view full source
      </p>
    </div>
  </Tooltip.Content>
</Tooltip.Root>
