<script lang="ts">
  import { onMount } from 'svelte';
  import { ragSettingsStore } from '$lib/stores/ragSettingsStore.svelte';
  import { ragStore } from '$lib/stores/ragStore.svelte';
  import { getEmbeddingModels, type EmbeddingProvider } from '$lib/services/ragSettingsApi';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import * as Select from '$lib/components/ui/select';
  import { Separator } from '$lib/components/ui/separator';
  import { Save, RotateCcw, Loader2, AlertTriangle } from '@lucide/svelte';

  // Local state for form
  let store = ragSettingsStore;
  
  // Embedding models state
  let embeddingProviders = $state<EmbeddingProvider[]>([]);
  let embeddingModelsLoading = $state(false);
  
  // Computed: models for current provider
  let availableModels = $derived(
    embeddingProviders.find(p => p.name === store.settings.embedding_provider)?.models || []
  );
  
  onMount(async () => {
    if (!store.initialized) {
      store.loadSettings();
    }
    
    // Load embedding models
    embeddingModelsLoading = true;
    try {
      const response = await getEmbeddingModels();
      embeddingProviders = response.providers;
    } catch (e) {
      console.error('Failed to load embedding models:', e);
    } finally {
      embeddingModelsLoading = false;
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
  
  function handleProviderChange(providerName: string) {
    store.updateSetting('embedding_provider', providerName as 'sentence_transformers' | 'openai' | 'ollama');
    // Reset model to first available for new provider
    const provider = embeddingProviders.find(p => p.name === providerName);
    if (provider && provider.models.length > 0) {
      store.updateSetting('embedding_model', provider.models[0].name);
    }
  }

  // Context ordering options
  const orderingOptions = [
    { value: 'score_desc', label: 'Highest Score First' },
    { value: 'score_asc', label: 'Lowest Score First' },
    { value: 'position', label: 'Original Position' },
  ];
  
  // Provider display names
  const providerLabels: Record<string, string> = {
    'sentence_transformers': 'SentenceTransformers (Local)',
    'openai': 'OpenAI',
    'ollama': 'Ollama (Local)',
  };
</script>

<div class="space-y-6 p-4">
  {#if store.loading}
    <div class="flex items-center justify-center py-8">
      <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
      <span class="ml-2 text-muted-foreground">Loading settings...</span>
    </div>
  {:else}
    <!-- Embedding Model Configuration -->
    <div class="space-y-4">
      <h3 class="text-lg font-semibold">Embedding Model</h3>
      <p class="text-sm text-muted-foreground">
        Choose the embedding provider and model for document vectorization.
      </p>
      
      {#if embeddingModelsLoading}
        <div class="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 class="h-4 w-4 animate-spin" />
          Loading models...
        </div>
      {:else}
        <div class="grid gap-4 sm:grid-cols-2">
          <!-- Provider Selector -->
          <div class="space-y-2">
            <Label for="embedding_provider">Provider</Label>
            <Select.Root
              type="single"
              value={{ value: store.settings.embedding_provider, label: providerLabels[store.settings.embedding_provider] || store.settings.embedding_provider }}
              onValueChange={(v) => v && handleProviderChange(v.value)}
            >
              <Select.Trigger id="embedding_provider" class="w-full">
                {providerLabels[store.settings.embedding_provider] || store.settings.embedding_provider}
              </Select.Trigger>
              <Select.Content>
                {#each embeddingProviders as provider}
                  <Select.Item value={provider.name} label={providerLabels[provider.name] || provider.name}>
                    {providerLabels[provider.name] || provider.name}
                  </Select.Item>
                {/each}
              </Select.Content>
            </Select.Root>
          </div>
          
          <!-- Model Selector -->
          <div class="space-y-2">
            <Label for="embedding_model">Model</Label>
            <Select.Root
              type="single"
              value={{ value: store.settings.embedding_model, label: store.settings.embedding_model }}
              onValueChange={(v) => v && store.updateSetting('embedding_model', v.value)}
            >
              <Select.Trigger id="embedding_model" class="w-full">
                {store.settings.embedding_model}
              </Select.Trigger>
              <Select.Content>
                {#each availableModels as model}
                  <Select.Item value={model.name} label={model.name}>
                    {model.name} <span class="text-muted-foreground">({model.dimensions}d)</span>
                  </Select.Item>
                {/each}
              </Select.Content>
            </Select.Root>
          </div>
        </div>
        
        <!-- Warning about changing embeddings -->
        <div class="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
          <AlertTriangle class="h-4 w-4 mt-0.5 flex-shrink-0" />
          <span>Changing embedding model requires re-ingesting existing documents for compatibility.</span>
        </div>
      {/if}
    </div>

    <Separator />

    <!-- Advanced RAG Pipeline -->
    <div class="space-y-4">
      <h3 class="text-lg font-semibold text-primary">Advanced RAG Pipeline</h3>
      
      <div class="flex items-center space-x-2">
        <Checkbox
          id="advanced_mode"
          checked={ragStore.advancedMode}
          onCheckedChange={(checked) => ragStore.advancedMode = !!checked}
        />
        <Label for="advanced_mode" class="font-medium">Enable Advanced Pipeline</Label>
      </div>
      
      {#if ragStore.advancedMode}
        <div class="grid gap-4 sm:grid-cols-2 pl-6 pt-2">
           <div class="space-y-2">
            <Label for="context_budget">Token Budget</Label>
            <Input
              id="context_budget"
              type="number"
              min={1000}
              max={32000}
              value={ragStore.contextBudget}
              onchange={(e) => ragStore.contextBudget = parseInt(e.currentTarget.value)}
            />
            <p class="text-xs text-muted-foreground">Tokens reserved for context window</p>
          </div>
          
           <div class="space-y-2">
            <Label for="hybrid_ratio">Hybrid Ratio (Verbatim)</Label>
            <div class="flex items-center gap-2">
                <Input
                  id="hybrid_ratio"
                  type="number"
                  min={0.1}
                  max={1.0}
                  step={0.1}
                  value={ragStore.hybridRatio}
                  onchange={(e) => ragStore.hybridRatio = parseFloat(e.currentTarget.value)}
                />
                <span class="text-sm font-medium">{(ragStore.hybridRatio * 100).toFixed(0)}%</span>
            </div>
            <p class="text-xs text-muted-foreground">Ratio of budget for verbatim text vs summaries</p>
          </div>
        </div>
        
        <div class="rounded-md bg-muted p-3 text-sm text-muted-foreground ml-6">
            Pipeline: <strong>Retrieval (50)</strong> → <strong>Rerank (Cross-Encoder)</strong> → <strong>Budgeting</strong> → <strong>Summarization (LLM)</strong> → <strong>Lost-in-Middle Assembly</strong>
        </div>
      {/if}
    </div>

    <Separator />

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
