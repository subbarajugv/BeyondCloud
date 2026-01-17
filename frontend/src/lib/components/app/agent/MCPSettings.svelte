<script lang="ts">
    import { agentApi, type MCPServer, type MCPServerConfig } from '$lib/services/agentApi';
    
    // State
    let servers: MCPServer[] = $state([]);
    let loading = $state(false);
    let error = $state<string | null>(null);
    
    // New server form
    let showAddForm = $state(false);
    let newServer = $state<MCPServerConfig>({
        name: '',
        transport: 'stdio',
        command: 'npx',
        args: [],
    });
    let argsInput = $state('');
    
    // Load servers on mount
    $effect(() => {
        loadServers();
    });
    
    async function loadServers() {
        loading = true;
        error = null;
        try {
            servers = await agentApi.listMCPServers();
        } catch (e) {
            error = e instanceof Error ? e.message : 'Failed to load servers';
            servers = [];
        } finally {
            loading = false;
        }
    }
    
    async function addServer() {
        if (!newServer.name) {
            error = 'Server name is required';
            return;
        }
        
        loading = true;
        error = null;
        try {
            // Parse args from comma-separated string
            const config: MCPServerConfig = {
                ...newServer,
                args: argsInput.split(',').map(s => s.trim()).filter(Boolean)
            };
            
            await agentApi.addMCPServer(config);
            await loadServers();
            
            // Reset form
            showAddForm = false;
            newServer = { name: '', transport: 'stdio', command: 'npx', args: [] };
            argsInput = '';
        } catch (e) {
            error = e instanceof Error ? e.message : 'Failed to add server';
        } finally {
            loading = false;
        }
    }
    
    async function removeServer(serverId: string) {
        loading = true;
        error = null;
        try {
            await agentApi.removeMCPServer(serverId);
            await loadServers();
        } catch (e) {
            error = e instanceof Error ? e.message : 'Failed to remove server';
        } finally {
            loading = false;
        }
    }
</script>

<div class="mcp-settings">
    <div class="header">
        <h3>🔌 MCP Servers</h3>
        <button class="add-btn" onclick={() => showAddForm = !showAddForm}>
            {showAddForm ? 'Cancel' : '+ Add Server'}
        </button>
    </div>
    
    {#if error}
        <div class="error">{error}</div>
    {/if}
    
    {#if showAddForm}
        <div class="add-form">
            <div class="form-group">
                <label>Name</label>
                <input type="text" bind:value={newServer.name} placeholder="e.g., filesystem" />
            </div>
            
            <div class="form-group">
                <label>Transport</label>
                <select bind:value={newServer.transport}>
                    <option value="stdio">stdio (local process)</option>
                    <option value="http">http (remote server)</option>
                </select>
            </div>
            
            {#if newServer.transport === 'stdio'}
                <div class="form-group">
                    <label>Command</label>
                    <input type="text" bind:value={newServer.command} placeholder="npx" />
                </div>
                <div class="form-group">
                    <label>Arguments (comma-separated)</label>
                    <input type="text" bind:value={argsInput} 
                           placeholder="@modelcontextprotocol/server-filesystem, /tmp" />
                </div>
            {:else}
                <div class="form-group">
                    <label>URL</label>
                    <input type="text" bind:value={newServer.url} placeholder="http://localhost:3001" />
                </div>
            {/if}
            
            <button class="submit-btn" onclick={addServer} disabled={loading}>
                {loading ? 'Adding...' : 'Add Server'}
            </button>
        </div>
    {/if}
    
    <div class="server-list">
        {#if loading && servers.length === 0}
            <div class="loading">Loading...</div>
        {:else if servers.length === 0}
            <div class="empty">No MCP servers configured. Add one to extend agent capabilities.</div>
        {:else}
            {#each servers as server}
                <div class="server-item" class:inactive={!server.is_active}>
                    <div class="server-info">
                        <span class="status" class:active={server.is_active}>●</span>
                        <span class="name">{server.name}</span>
                        <span class="transport">{server.transport}</span>
                    </div>
                    <div class="server-details">
                        {#if server.command}
                            <code>{server.command} {server.args.join(' ')}</code>
                        {:else if server.url}
                            <code>{server.url}</code>
                        {/if}
                    </div>
                    <button class="remove-btn" onclick={() => removeServer(server.id)}>✕</button>
                </div>
            {/each}
        {/if}
    </div>
</div>

<style>
    .mcp-settings {
        padding: 1rem;
        background: var(--bg-secondary, #1e1e1e);
        border-radius: 8px;
    }
    
    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    
    .header h3 {
        margin: 0;
        font-size: 1rem;
    }
    
    .add-btn {
        padding: 0.5rem 1rem;
        background: var(--primary, #4a9eff);
        border: none;
        border-radius: 4px;
        color: white;
        cursor: pointer;
    }
    
    .add-form {
        padding: 1rem;
        background: var(--bg-primary, #121212);
        border-radius: 6px;
        margin-bottom: 1rem;
    }
    
    .form-group {
        margin-bottom: 0.75rem;
    }
    
    .form-group label {
        display: block;
        font-size: 0.85rem;
        margin-bottom: 0.25rem;
        opacity: 0.8;
    }
    
    .form-group input,
    .form-group select {
        width: 100%;
        padding: 0.5rem;
        background: var(--bg-secondary, #1e1e1e);
        border: 1px solid var(--border, #333);
        border-radius: 4px;
        color: inherit;
    }
    
    .submit-btn {
        width: 100%;
        padding: 0.75rem;
        background: var(--primary, #4a9eff);
        border: none;
        border-radius: 4px;
        color: white;
        cursor: pointer;
        margin-top: 0.5rem;
    }
    
    .submit-btn:disabled {
        opacity: 0.5;
    }
    
    .error {
        padding: 0.75rem;
        background: rgba(255, 0, 0, 0.1);
        border: 1px solid rgba(255, 0, 0, 0.3);
        border-radius: 4px;
        color: #ff6b6b;
        margin-bottom: 1rem;
    }
    
    .server-list {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    
    .server-item {
        display: flex;
        align-items: center;
        padding: 0.75rem;
        background: var(--bg-primary, #121212);
        border-radius: 6px;
        position: relative;
    }
    
    .server-item.inactive {
        opacity: 0.5;
    }
    
    .server-info {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex: 1;
    }
    
    .status {
        color: #ff6b6b;
    }
    
    .status.active {
        color: #4caf50;
    }
    
    .name {
        font-weight: 500;
    }
    
    .transport {
        font-size: 0.75rem;
        padding: 0.2rem 0.5rem;
        background: var(--bg-secondary, #1e1e1e);
        border-radius: 4px;
        opacity: 0.7;
    }
    
    .server-details {
        flex: 2;
        margin: 0 1rem;
    }
    
    .server-details code {
        font-size: 0.8rem;
        opacity: 0.7;
    }
    
    .remove-btn {
        padding: 0.25rem 0.5rem;
        background: transparent;
        border: 1px solid rgba(255, 0, 0, 0.3);
        border-radius: 4px;
        color: #ff6b6b;
        cursor: pointer;
    }
    
    .empty, .loading {
        text-align: center;
        padding: 2rem;
        opacity: 0.6;
    }
</style>
