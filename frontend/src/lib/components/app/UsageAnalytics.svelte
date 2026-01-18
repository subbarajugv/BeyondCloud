<script lang="ts">
  import { onMount } from 'svelte';
  import { authStore } from '$lib/stores/auth';
  
  interface UsageStats {
    rag_queries: number;
    rag_ingestions: number;
    rag_chunks_retrieved: number;
    agent_tool_calls: number;
    agent_approvals: number;
    agent_rejections: number;
    llm_requests: number;
    llm_tokens_input: number;
    llm_tokens_output: number;
    mcp_tool_calls: number;
  }
  
  interface DailyData {
    date: string;
    rag_queries: number;
    agent_tool_calls: number;
    llm_requests: number;
  }
  
  let stats: UsageStats | null = null;
  let dailyData: DailyData[] = [];
  let loading = true;
  let error = '';
  let periodDays = 30;
  
  async function fetchStats() {
    loading = true;
    error = '';
    
    try {
      const token = $authStore.token;
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
      
      // Fetch aggregated stats
      const statsRes = await fetch(`http://localhost:8001/api/usage/stats?days=${periodDays}`, { headers });
      if (statsRes.ok) {
        const data = await statsRes.json();
        stats = data.stats;
      }
      
      // Fetch daily breakdown
      const dailyRes = await fetch(`http://localhost:8001/api/usage/daily?days=7`, { headers });
      if (dailyRes.ok) {
        const data = await dailyRes.json();
        dailyData = data.daily || [];
      }
    } catch (e) {
      error = 'Failed to load usage data';
      console.error(e);
    } finally {
      loading = false;
    }
  }
  
  onMount(fetchStats);
  
  function formatNumber(n: number): string {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toString();
  }
  
  $: maxValue = Math.max(...dailyData.map(d => d.rag_queries + d.agent_tool_calls + d.llm_requests), 1);
</script>

<div class="usage-analytics">
  <h2>📊 Usage Analytics</h2>
  
  <div class="period-selector">
    <button class:active={periodDays === 7} on:click={() => { periodDays = 7; fetchStats(); }}>7 Days</button>
    <button class:active={periodDays === 30} on:click={() => { periodDays = 30; fetchStats(); }}>30 Days</button>
    <button class:active={periodDays === 90} on:click={() => { periodDays = 90; fetchStats(); }}>90 Days</button>
  </div>
  
  {#if loading}
    <div class="loading">Loading...</div>
  {:else if error}
    <div class="error">{error}</div>
  {:else if stats}
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{formatNumber(stats.rag_queries)}</div>
        <div class="stat-label">RAG Queries</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{formatNumber(stats.agent_tool_calls)}</div>
        <div class="stat-label">Agent Tools</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{formatNumber(stats.llm_requests)}</div>
        <div class="stat-label">LLM Requests</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{formatNumber(stats.llm_tokens_input + stats.llm_tokens_output)}</div>
        <div class="stat-label">Total Tokens</div>
      </div>
    </div>
    
    {#if dailyData.length > 0}
      <h3>📈 Daily Activity (Last 7 Days)</h3>
      <div class="chart">
        {#each dailyData as day}
          <div class="bar-group">
            <div class="bar-container">
              <div 
                class="bar rag" 
                style="height: {(day.rag_queries / maxValue) * 100}%"
                title="RAG: {day.rag_queries}"
              ></div>
              <div 
                class="bar agent" 
                style="height: {(day.agent_tool_calls / maxValue) * 100}%"
                title="Agent: {day.agent_tool_calls}"
              ></div>
              <div 
                class="bar llm" 
                style="height: {(day.llm_requests / maxValue) * 100}%"
                title="LLM: {day.llm_requests}"
              ></div>
            </div>
            <div class="bar-label">{new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' })}</div>
          </div>
        {/each}
      </div>
      <div class="legend">
        <span class="legend-item"><span class="dot rag"></span> RAG</span>
        <span class="legend-item"><span class="dot agent"></span> Agent</span>
        <span class="legend-item"><span class="dot llm"></span> LLM</span>
      </div>
    {/if}
  {/if}
</div>

<style>
  .usage-analytics {
    padding: 1.5rem;
    max-width: 800px;
    margin: 0 auto;
  }
  
  h2 {
    margin: 0 0 1rem;
    color: var(--text-primary, #1a1a1a);
  }
  
  h3 {
    margin: 1.5rem 0 1rem;
    color: var(--text-secondary, #666);
  }
  
  .period-selector {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
  }
  
  .period-selector button {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border, #ddd);
    background: var(--bg-secondary, #f5f5f5);
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .period-selector button:hover {
    background: var(--bg-tertiary, #eee);
  }
  
  .period-selector button.active {
    background: var(--primary, #3b82f6);
    color: white;
    border-color: var(--primary, #3b82f6);
  }
  
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
  }
  
  .stat-card {
    background: var(--bg-secondary, #f8f9fa);
    padding: 1.25rem;
    border-radius: 12px;
    text-align: center;
    border: 1px solid var(--border, #e5e7eb);
  }
  
  .stat-value {
    font-size: 2rem;
    font-weight: 700;
    color: var(--primary, #3b82f6);
  }
  
  .stat-label {
    font-size: 0.875rem;
    color: var(--text-secondary, #666);
    margin-top: 0.25rem;
  }
  
  .chart {
    display: flex;
    justify-content: space-around;
    align-items: flex-end;
    height: 200px;
    padding: 1rem;
    background: var(--bg-secondary, #f8f9fa);
    border-radius: 12px;
    gap: 0.5rem;
  }
  
  .bar-group {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
  }
  
  .bar-container {
    display: flex;
    gap: 4px;
    align-items: flex-end;
    height: 160px;
  }
  
  .bar {
    width: 16px;
    min-height: 4px;
    border-radius: 4px 4px 0 0;
    transition: height 0.3s ease;
  }
  
  .bar.rag { background: #3b82f6; }
  .bar.agent { background: #10b981; }
  .bar.llm { background: #f59e0b; }
  
  .bar-label {
    font-size: 0.75rem;
    color: var(--text-secondary, #666);
    margin-top: 0.5rem;
  }
  
  .legend {
    display: flex;
    justify-content: center;
    gap: 1.5rem;
    margin-top: 1rem;
  }
  
  .legend-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: var(--text-secondary, #666);
  }
  
  .dot {
    width: 12px;
    height: 12px;
    border-radius: 3px;
  }
  
  .dot.rag { background: #3b82f6; }
  .dot.agent { background: #10b981; }
  .dot.llm { background: #f59e0b; }
  
  .loading, .error {
    text-align: center;
    padding: 2rem;
    color: var(--text-secondary, #666);
  }
  
  .error {
    color: #ef4444;
  }
</style>
