<script lang="ts">
  import CitationBadge from './CitationBadge.svelte';
  import { BookOpen, ChevronDown, ChevronUp } from '@lucide/svelte';
  import type { Citation } from '$lib/services/ragApi';

  interface Props {
    citations: Citation[];
    maxVisible?: number;
  }

  let { citations, maxVisible = 5 }: Props = $props();
  
  let expanded = $state(false);
  
  const visibleCitations = $derived(
    expanded ? citations : citations.slice(0, maxVisible)
  );
  
  const hasMore = $derived(citations.length > maxVisible);
  const hiddenCount = $derived(citations.length - maxVisible);
</script>

{#if citations && citations.length > 0}
  <div class="mt-4 rounded-lg border border-muted-foreground/20 bg-muted/30 p-3">
    <div class="mb-2 flex items-center justify-between">
      <div class="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <BookOpen class="h-3.5 w-3.5" />
        <span>Sources Used ({citations.length})</span>
      </div>
      
      {#if hasMore}
        <button
          type="button"
          class="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          onclick={() => expanded = !expanded}
        >
          {#if expanded}
            <ChevronUp class="h-3 w-3" />
            Show less
          {:else}
            <ChevronDown class="h-3 w-3" />
            +{hiddenCount} more
          {/if}
        </button>
      {/if}
    </div>
    
    <div class="flex flex-wrap gap-2">
      {#each visibleCitations as citation (citation.source_id)}
        <CitationBadge {citation} />
      {/each}
    </div>
  </div>
{/if}
