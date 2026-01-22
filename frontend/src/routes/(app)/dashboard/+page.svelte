<script lang="ts">
  import { goto } from '$app/navigation';
  import { authStore } from '$lib/stores/auth.svelte';
  import UsageAnalytics from '$lib/components/app/UsageAnalytics.svelte';
  
  // Dashboard tabs
  let activeTab = $state<'overview' | 'admin' | 'user'>('overview');
  
  // Check if user is admin (rudimentary check - backend should verify)
  let isAdmin = $derived(authStore.user?.email?.includes('admin') || false);
</script>

<div class="dashboard-container">
  <header class="dashboard-header">
    <h1>📊 Dashboard</h1>
    <nav class="dashboard-tabs">
      <button 
        class="tab" 
        class:active={activeTab === 'overview'}
        onclick={() => activeTab = 'overview'}
      >
        Overview
      </button>
      <button 
        class="tab"
        class:active={activeTab === 'user'}
        onclick={() => activeTab = 'user'}
      >
        My Dashboard
      </button>
      {#if isAdmin}
        <button 
          class="tab"
          class:active={activeTab === 'admin'}
          onclick={() => activeTab = 'admin'}
        >
          Admin
        </button>
      {/if}
    </nav>
    <button class="back-btn" onclick={() => goto('/')}>
      ← Back to Chat
    </button>
  </header>

  <main class="dashboard-content">
    {#if activeTab === 'overview'}
      <UsageAnalytics />
    {:else if activeTab === 'user'}
      <div class="user-dashboard">
        <h2>🙋 My Dashboard</h2>
        
        <div class="section">
          <h3>📁 My Collections</h3>
          <p class="placeholder">View and manage your RAG collections here.</p>
          <button class="btn-primary" onclick={() => goto('/')}>Go to Chat to manage</button>
        </div>
        
        <div class="section">
          <h3>🤖 My Agents</h3>
          <p class="placeholder">Your configured agent settings and history.</p>
        </div>
        
        <div class="section">
          <h3>🎫 Support Tickets</h3>
          <div class="ticket-form">
            <input type="text" placeholder="Subject" class="input" />
            <textarea placeholder="Describe your issue..." class="textarea"></textarea>
            <button class="btn-primary">Submit Ticket</button>
          </div>
        </div>
      </div>
    {:else if activeTab === 'admin'}
      <div class="admin-dashboard">
        <h2>🛡️ Admin Dashboard</h2>
        
        <div class="admin-grid">
          <div class="admin-card">
            <h3>👥 Users</h3>
            <div class="stat-big">--</div>
            <p>Total registered users</p>
            <button class="btn-secondary">Manage Users</button>
          </div>
          
          <div class="admin-card">
            <h3>📚 Documents</h3>
            <div class="stat-big">--</div>
            <p>Total RAG sources</p>
          </div>
          
          <div class="admin-card">
            <h3>⚠️ Guardrail Violations</h3>
            <div class="stat-big">0</div>
            <p>Last 7 days</p>
          </div>
          
          <div class="admin-card">
            <h3>🎫 Open Tickets</h3>
            <div class="stat-big">0</div>
            <p>Pending support requests</p>
          </div>
        </div>

        <div class="section">
          <h3>🔐 User Management</h3>
          <table class="admin-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Role</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td colspan="4" class="placeholder-row">Loading users...</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    {/if}
  </main>
</div>

<style>
  .dashboard-container {
    min-height: 100vh;
    background: var(--bg-primary, #f8fafc);
  }

  .dashboard-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 2rem;
    background: white;
    border-bottom: 1px solid var(--border, #e2e8f0);
    flex-wrap: wrap;
    gap: 1rem;
    padding-right: 12rem; /* Make space for fixed user menu */
  }

  .dashboard-header h1 {
    margin: 0;
    font-size: 1.5rem;
    color: var(--text-primary, #1e293b);
  }

  .dashboard-tabs {
    display: flex;
    gap: 0.5rem;
  }

  .tab {
    padding: 0.5rem 1rem;
    border: none;
    background: transparent;
    border-radius: 8px;
    cursor: pointer;
    color: var(--text-secondary, #64748b);
    font-weight: 500;
    transition: all 0.2s;
  }

  .tab:hover {
    background: var(--bg-secondary, #f1f5f9);
  }

  .tab.active {
    background: var(--primary, #3b82f6);
    color: white;
  }

  .back-btn {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border, #e2e8f0);
    background: white;
    border-radius: 8px;
    cursor: pointer;
    color: var(--text-secondary, #64748b);
    transition: all 0.2s;
  }

  .back-btn:hover {
    background: var(--bg-secondary, #f1f5f9);
  }

  .dashboard-content {
    padding: 2rem;
    max-width: 1400px;
    margin: 0 auto;
  }

  .user-dashboard, .admin-dashboard {
    padding: 1rem;
  }

  .user-dashboard h2, .admin-dashboard h2 {
    margin: 0 0 1.5rem;
    color: var(--text-primary, #1e293b);
  }

  .section {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }

  .section h3 {
    margin: 0 0 1rem;
    color: var(--text-primary, #1e293b);
  }

  .placeholder {
    color: var(--text-secondary, #64748b);
    margin-bottom: 1rem;
  }

  .admin-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .admin-card {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    text-align: center;
  }

  .admin-card h3 {
    margin: 0 0 0.5rem;
    font-size: 0.875rem;
    color: var(--text-secondary, #64748b);
  }

  .stat-big {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--primary, #3b82f6);
    margin: 0.5rem 0;
  }

  .admin-card p {
    margin: 0;
    font-size: 0.75rem;
    color: var(--text-secondary, #64748b);
  }

  .admin-table {
    width: 100%;
    border-collapse: collapse;
  }

  .admin-table th, .admin-table td {
    padding: 0.75rem 1rem;
    text-align: left;
    border-bottom: 1px solid var(--border, #e2e8f0);
  }

  .admin-table th {
    font-weight: 600;
    color: var(--text-secondary, #64748b);
    font-size: 0.875rem;
  }

  .placeholder-row {
    color: var(--text-secondary, #64748b);
    text-align: center;
  }

  .btn-primary {
    padding: 0.5rem 1rem;
    background: var(--primary, #3b82f6);
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 500;
    transition: background 0.2s;
  }

  .btn-primary:hover {
    background: var(--primary-dark, #2563eb);
  }

  .btn-secondary {
    padding: 0.5rem 1rem;
    background: var(--bg-secondary, #f1f5f9);
    color: var(--text-primary, #1e293b);
    border: 1px solid var(--border, #e2e8f0);
    border-radius: 8px;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.2s;
    margin-top: 1rem;
  }

  .btn-secondary:hover {
    background: var(--bg-tertiary, #e2e8f0);
  }

  .ticket-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    max-width: 500px;
  }

  .input, .textarea {
    padding: 0.75rem;
    border: 1px solid var(--border, #e2e8f0);
    border-radius: 8px;
    font-size: 1rem;
    transition: border-color 0.2s;
  }

  .input:focus, .textarea:focus {
    outline: none;
    border-color: var(--primary, #3b82f6);
  }

  .textarea {
    min-height: 100px;
    resize: vertical;
  }
</style>
