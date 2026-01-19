<script lang="ts">
  import { onMount } from 'svelte';
  import { ragSettingsStore } from '$lib/stores/ragSettingsStore.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import * as Select from '$lib/components/ui/select';
  import { Separator } from '$lib/components/ui/separator';
  import { Save, RotateCcw, Loader2 } from '@lucide/svelte';

  // Local state for form
  let store = ragSettingsStore;
  
  onMount(() => {
    if (!store.initialized) {
      store.loadSettings();
    }
  });

  async function handleSave() {
    const success = await store.saveSettings();
    if (success) {
      console.log('RAG settings saved');
    }
  }

  async function handleReset() {
    if (confirm('Reset all RAG settings to defaults?')) {
      await store.resetToDefaults();
    }
  }

  // Context ordering options
  const orderingOptions = [
    { value: 'score_desc', label: 'Highest Score First' },
    { value: 'score_asc', label: 'Lowest Score First' },
    { value: 'position', label: 'Original Position' },
  ];
</script>

<div class="space-y-6 p-4">
  {#if store.loading}
    <div class="flex items-center justify-center py-8">
      <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
      <span class="ml-2 text-muted-foreground">Loading settings...</span>
    </div>
  {:else}
    <!-- Chunking Settings -->
    <div class="space-y-4">
      <h3 class="text-lg font-semibold">Chunking</h3>
      <div class="grid gap-4 sm:grid-cols-2">
        <div class="space-y-2">
          <Label for="chunk_size">Chunk Size (100 - 2000)</Label>
          <Input
            id="chunk_size"
            type="number"
            min={100}
            max={2000}
            value={store.settings.chunk_size}
            onchange={(e) => store.updateSetting('chunk_size', parseInt(e.currentTarget.value))}
          />
        </div>
        <div class="space-y-2">
          <Label for="chunk_overlap">Chunk Overlap (0 - 500)</Label>
          <Input
            id="chunk_overlap"
            type="number"
            min={0}
            max={500}
            value={store.settings.chunk_overlap}
            onchange={(e) => store.updateSetting('chunk_overlap', parseInt(e.currentTarget.value))}
          />
        </div>
      </div>
      <div class="flex items-center space-x-2">
        <Checkbox
          id="sentence_boundary"
          checked={store.settings.use_sentence_boundary}
          onCheckedChange={(checked) => store.updateSetting('use_sentence_boundary', !!checked)}
        />
        <Label for="sentence_boundary">Split at sentence boundaries</Label>
      </div>
    </div>

    <Separator />

    <!-- Search & Reranking -->
    <div class="space-y-4">
      <h3 class="text-lg font-semibold">Search & Reranking</h3>
      
      <div class="flex items-center space-x-2">
        <Checkbox
          id="hybrid_search"
          checked={store.settings.use_hybrid_search}
          onCheckedChange={(checked) => store.updateSetting('use_hybrid_search', !!checked)}
        />
        <Label for="hybrid_search">Enable Hybrid Search (BM25 + Vector)</Label>
      </div>

      {#if store.settings.use_hybrid_search}
        <div class="space-y-2 pl-6">
          <Label for="bm25_weight">BM25 Weight (0.0 - 1.0)</Label>
          <Input
            id="bm25_weight"
            type="number"
            step={0.1}
            min={0}
            max={1}
            value={store.settings.bm25_weight}
            onchange={(e) => store.updateSetting('bm25_weight', parseFloat(e.currentTarget.value))}
          />
        </div>
      {/if}

      <div class="flex items-center space-x-2">
        <Checkbox
          id="use_reranking"
          checked={store.settings.use_reranking}
          onCheckedChange={(checked) => store.updateSetting('use_reranking', !!checked)}
        />
        <Label for="use_reranking">Enable Cross-Encoder Reranking</Label>
      </div>

      {#if store.settings.use_reranking}
        <div class="grid gap-4 sm:grid-cols-2 pl-6">
          <div class="space-y-2">
            <Label for="rerank_top_k">Top-K Results (1 - 20)</Label>
            <Input
              id="rerank_top_k"
              type="number"
              min={1}
              max={20}
              value={store.settings.rerank_top_k}
              onchange={(e) => store.updateSetting('rerank_top_k', parseInt(e.currentTarget.value))}
            />
          </div>
          <div class="space-y-2">
            <Label for="min_score">Min Relevance Score (0.0 - 1.0)</Label>
            <Input
              id="min_score"
              type="number"
              step={0.1}
              min={0}
              max={1}
              value={store.settings.min_score}
              onchange={(e) => store.updateSetting('min_score', parseFloat(e.currentTarget.value))}
            />
          </div>
        </div>
      {/if}
    </div>

    <Separator />

    <!-- Context Assembly -->
    <div class="space-y-4">
      <h3 class="text-lg font-semibold">Context Assembly</h3>
      <div class="grid gap-4 sm:grid-cols-2">
        <div class="space-y-2">
          <Label for="context_max_tokens">Max Context Tokens (500 - 32000)</Label>
          <Input
            id="context_max_tokens"
            type="number"
            min={500}
            max={32000}
            step={500}
            value={store.settings.context_max_tokens}
            onchange={(e) => store.updateSetting('context_max_tokens', parseInt(e.currentTarget.value))}
          />
        </div>
        <div class="space-y-2">
          <Label for="context_ordering">Context Ordering</Label>
          <Select.Root
            type="single"
            value={{ value: store.settings.context_ordering, label: orderingOptions.find(o => o.value === store.settings.context_ordering)?.label || '' }}
            onValueChange={(v) => v && store.updateSetting('context_ordering', v.value as 'score_desc' | 'score_asc' | 'position')}
          >
            <Select.Trigger id="context_ordering" class="w-full">
              {orderingOptions.find(o => o.value === store.settings.context_ordering)?.label || 'Select...'}
            </Select.Trigger>
            <Select.Content>
              {#each orderingOptions as option}
                <Select.Item value={option.value} label={option.label}>{option.label}</Select.Item>
              {/each}
            </Select.Content>
          </Select.Root>
        </div>
      </div>
    </div>

    <Separator />

    <!-- Grounding Rules -->
    <div class="space-y-4">
      <h3 class="text-lg font-semibold">Grounding & Citations</h3>
      <div class="flex items-center space-x-2">
        <Checkbox
          id="require_citations"
          checked={store.settings.require_citations}
          onCheckedChange={(checked) => store.updateSetting('require_citations', !!checked)}
        />
        <Label for="require_citations">Require citations in responses</Label>
      </div>
      {#if store.settings.require_citations}
        <div class="space-y-2 pl-6">
          <Label for="max_citations">Max Citations (1 - 20)</Label>
          <Input
            id="max_citations"
            type="number"
            min={1}
            max={20}
            value={store.settings.max_citations}
            onchange={(e) => store.updateSetting('max_citations', parseInt(e.currentTarget.value))}
          />
        </div>
      {/if}
    </div>

    <Separator />

    <!-- Actions -->
    <div class="flex items-center justify-end space-x-3 pt-2">
      {#if store.error}
        <span class="text-sm text-destructive">{store.error}</span>
      {/if}
      <Button variant="outline" onclick={handleReset} disabled={store.saving}>
        <RotateCcw class="mr-2 h-4 w-4" />
        Reset Defaults
      </Button>
      <Button onclick={handleSave} disabled={store.saving}>
        {#if store.saving}
          <Loader2 class="mr-2 h-4 w-4 animate-spin" />
          Saving...
        {:else}
          <Save class="mr-2 h-4 w-4" />
          Save Settings
        {/if}
      </Button>
    </div>
  {/if}
</div>
