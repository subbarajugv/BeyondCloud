/**
 * Agent API Client - Frontend interface for agentic operations
 * 
 * Supports two modes:
 * - Local: Agent daemon runs on user's machine (localhost:8002)
 * - Remote: Agent runs on backend server (for self-hosted setups)
 */

// Agent modes
export type AgentMode = 'local' | 'remote';

// Base URLs for each mode
const AGENT_API_URLS = {
    local: 'http://localhost:8002/api/agent',   // Local daemon
    remote: 'http://localhost:8001/api/agent',  // Backend server
};

// Current mode - persisted to localStorage
function getStoredMode(): AgentMode {
    if (typeof localStorage === 'undefined') return 'local';
    const stored = localStorage.getItem('agentMode');
    if (stored === 'local' || stored === 'remote') return stored;
    return 'local'; // Default to local for SaaS
}

let currentMode: AgentMode = getStoredMode();

/**
 * Get current agent mode
 */
export function getAgentMode(): AgentMode {
    return currentMode;
}

/**
 * Set agent mode (local or remote)
 */
export function setAgentMode(mode: AgentMode): void {
    currentMode = mode;
    if (typeof localStorage !== 'undefined') {
        localStorage.setItem('agentMode', mode);
    }
}

/**
 * Get the API base URL for current mode
 */
function getAgentApiBase(): string {
    return AGENT_API_URLS[currentMode];
}

/**
 * Check if local daemon is available
 */
export async function checkLocalDaemon(): Promise<boolean> {
    try {
        const response = await fetch('http://localhost:8002/', {
            method: 'GET',
            signal: AbortSignal.timeout(2000)
        });
        return response.ok;
    } catch {
        return false;
    }
}

// Types
export type ApprovalMode = 'require_approval' | 'trust_mode';

export interface AgentStatus {
    sandbox_path: string | null;
    sandbox_active: boolean;
    approval_mode: ApprovalMode;
    pending_approvals: number;
}

export interface PendingToolCall {
    id: string;
    tool_name: string;
    args: Record<string, unknown>;
    safety_level: 'safe' | 'moderate' | 'dangerous';
}

export interface ToolExecuteResult {
    status: 'success' | 'error' | 'pending_approval' | 'rejected';
    tool_name: string;
    args: Record<string, unknown>;
    result?: unknown;
    error?: string;
    call_id?: string;
    safety_level?: string;
    message?: string;
}

export interface ToolSchema {
    type: 'function';
    function: {
        name: string;
        description: string;
        parameters: {
            type: 'object';
            properties: Record<string, { type: string; description: string }>;
            required: string[];
        };
    };
}

async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        const text = await response.text();
        throw new Error(`Agent API Error ${response.status}: ${text}`);
    }
    return response.json() as Promise<T>;
}

/**
 * Agent API endpoints
 */
export const agentApi = {
    /**
     * Set the sandbox directory for agent operations
     */
    async setSandbox(path: string): Promise<{ success: boolean; sandbox_path: string; message: string }> {
        const response = await fetch(`${getAgentApiBase()}/set-sandbox`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path })
        });
        return handleResponse(response);
    },

    /**
     * Set the approval mode
     */
    async setMode(mode: ApprovalMode): Promise<{ success: boolean; mode: string; message: string }> {
        const response = await fetch(`${getAgentApiBase()}/set-mode`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode })
        });
        return handleResponse(response);
    },

    /**
     * Get current agent status
     */
    async getStatus(): Promise<AgentStatus> {
        const response = await fetch(`${getAgentApiBase()}/status`);
        return handleResponse(response);
    },

    /**
     * Get available tool schemas for LLM
     */
    async getTools(): Promise<{ tools: ToolSchema[] }> {
        const response = await fetch(`${getAgentApiBase()}/tools`);
        return handleResponse(response);
    },

    /**
     * Execute a tool (may require approval)
     */
    async executeTool(
        toolName: string,
        args: Record<string, unknown>,
        approved: boolean = false
    ): Promise<ToolExecuteResult> {
        const response = await fetch(`${getAgentApiBase()}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tool_name: toolName,
                args,
                approved
            })
        });
        return handleResponse(response);
    },

    /**
     * Approve a pending tool call
     */
    async approveCall(callId: string): Promise<ToolExecuteResult> {
        const response = await fetch(`${getAgentApiBase()}/approve/${callId}`, {
            method: 'POST'
        });
        return handleResponse(response);
    },

    /**
     * Reject a pending tool call
     */
    async rejectCall(callId: string): Promise<{ status: string; tool_name: string; message: string }> {
        const response = await fetch(`${getAgentApiBase()}/reject/${callId}`, {
            method: 'POST'
        });
        return handleResponse(response);
    },

    /**
     * Get all pending tool calls
     */
    async getPendingCalls(): Promise<{ pending: PendingToolCall[] }> {
        const response = await fetch(`${getAgentApiBase()}/pending`);
        return handleResponse(response);
    },

    // ========== MCP Server Management ==========

    /**
     * List all configured MCP servers (remote mode only)
     */
    async listMCPServers(): Promise<MCPServer[]> {
        const response = await fetch(`http://localhost:8000/api/mcp/servers`);
        return handleResponse(response);
    },

    /**
     * Add a new MCP server
     */
    async addMCPServer(config: MCPServerConfig): Promise<{ id: string; name: string; is_active: boolean }> {
        const response = await fetch(`http://localhost:8000/api/mcp/servers`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        return handleResponse(response);
    },

    /**
     * Remove an MCP server
     */
    async removeMCPServer(serverId: string): Promise<{ message: string }> {
        const response = await fetch(`http://localhost:8000/api/mcp/servers/${serverId}`, {
            method: 'DELETE'
        });
        return handleResponse(response);
    },

    /**
     * Get tools from MCP servers
     */
    async getMCPTools(): Promise<{ tools: MCPTool[]; count: number }> {
        const response = await fetch(`http://localhost:8000/api/mcp/tools/openai-format`);
        return handleResponse(response);
    },

    /**
     * Execute a tool - routes to MCP if tool name starts with "mcp_"
     */
    async executeToolWithRouting(
        toolName: string,
        args: Record<string, unknown>,
        approved: boolean = false
    ): Promise<ToolExecuteResult> {
        // Route MCP tools to MCP service
        if (toolName.startsWith('mcp_')) {
            return this.executeMCPTool(toolName, args);
        }
        // Otherwise use regular agent execution
        return this.executeTool(toolName, args, approved);
    },

    /**
     * Execute an MCP tool
     */
    async executeMCPTool(
        toolName: string,
        args: Record<string, unknown>
    ): Promise<ToolExecuteResult> {
        // Parse MCP tool name: mcp_{server_id}_{tool_name}
        const parts = toolName.substring(4).split('_');
        if (parts.length < 2) {
            return { status: 'error', tool_name: toolName, args, error: 'Invalid MCP tool name' };
        }
        const serverId = parts[0];
        const actualToolName = parts.slice(1).join('_');

        const response = await fetch(`http://localhost:8000/api/mcp/tools/call`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                server_id: serverId,
                tool_name: actualToolName,
                args
            })
        });

        const result = await handleResponse<{ status: string; tool_name: string; result?: unknown; error?: string }>(response);
        return {
            status: result.status as 'success' | 'error',
            tool_name: toolName,
            args,
            result: result.result,
            error: result.error
        };
    }
};

// MCP Types
export interface MCPServer {
    id: string;
    name: string;
    transport: 'stdio' | 'http';
    command?: string;
    args: string[];
    url?: string;
    is_active: boolean;
}

export interface MCPServerConfig {
    name: string;
    transport: 'stdio' | 'http';
    command?: string;
    args?: string[];
    url?: string;
    env?: Record<string, string>;
}

export interface MCPTool {
    type: 'function';
    function: {
        name: string;
        description: string;
        parameters: Record<string, unknown>;
    };
}

export default agentApi;

