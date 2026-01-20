/**
 * Agent API Client - Frontend interface for agentic operations
 * 
 * Supports two modes:
 * - Local: Agent daemon runs on user's machine (localhost:8002)
 * - Remote: Agent runs on backend server (localhost:8001)
 * 
 * All tool calls are routed through MCP protocol for consistency.
 */

// Agent modes
export type AgentMode = 'local' | 'remote';

// Base URLs for each mode
const API_URLS = {
    local: {
        agent: 'http://localhost:8002/api/agent',
        mcp: 'http://localhost:8002/api/mcp',
    },
    remote: {
        agent: 'http://localhost:8001/api/agent',
        mcp: 'http://localhost:8001/api/mcp',
    },
};

// Current mode - persisted to localStorage
function getStoredMode(): AgentMode {
    if (typeof localStorage === 'undefined') return 'local';
    const stored = localStorage.getItem('agentMode');
    if (stored === 'local' || stored === 'remote') return stored;
    return 'local';
}

let currentMode: AgentMode = getStoredMode();

/** Get current agent mode */
export function getAgentMode(): AgentMode {
    return currentMode;
}

/** Set agent mode (local or remote) */
export function setAgentMode(mode: AgentMode): void {
    currentMode = mode;
    if (typeof localStorage !== 'undefined') {
        localStorage.setItem('agentMode', mode);
    }
}

/** Get the Agent API base URL for current mode */
function getAgentApiBase(): string {
    return API_URLS[currentMode].agent;
}

/** Get the MCP API base URL for current mode */
function getMCPApiBase(): string {
    return API_URLS[currentMode].mcp;
}

/** Check if local daemon is available */
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
    pending_approvals?: number;
    pending_count?: number;
}

export interface PendingToolCall {
    id: string;
    name: string;
    arguments: Record<string, unknown>;
    safety_level: 'safe' | 'moderate' | 'dangerous';
}

export interface ToolExecuteResult {
    status: 'success' | 'error' | 'pending_approval' | 'rejected';
    tool_name?: string;
    content?: Array<{ type: string; text?: string; data?: string; mimeType?: string }>;
    call_id?: string;
    safety_level?: string;
    error?: string;
}

export interface MCPTool {
    name: string;
    description: string;
    inputSchema: Record<string, unknown>;
}

async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        const text = await response.text();
        throw new Error(`API Error ${response.status}: ${text}`);
    }
    return response.json() as Promise<T>;
}

/**
 * Agent API endpoints
 */
export const agentApi = {
    // ========== Agent Configuration ==========

    /** Set the sandbox directory for agent operations */
    async setSandbox(path: string): Promise<{ success: boolean; path: string }> {
        const response = await fetch(`${getAgentApiBase()}/set-sandbox`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path })
        });
        return handleResponse(response);
    },

    /** Set the approval mode */
    async setMode(mode: ApprovalMode): Promise<{ success: boolean; mode: string }> {
        const response = await fetch(`${getAgentApiBase()}/set-mode`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode })
        });
        return handleResponse(response);
    },

    /** Get current agent status */
    async getStatus(): Promise<AgentStatus> {
        const response = await fetch(`${getAgentApiBase()}/status`);
        return handleResponse(response);
    },

    // ========== MCP Tools ==========

    /** Get available MCP tools */
    async getTools(): Promise<{ tools: MCPTool[] }> {
        const response = await fetch(`${getMCPApiBase()}/tools`);
        return handleResponse(response);
    },

    /** Execute a tool via MCP protocol */
    async executeTool(
        name: string,
        args: Record<string, unknown>,
        approved: boolean = false
    ): Promise<ToolExecuteResult> {
        const response = await fetch(`${getMCPApiBase()}/tools/call`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, arguments: args, approved })
        });
        return handleResponse(response);
    },

    // ========== Approval Flow ==========

    /** Approve a pending tool call */
    async approveCall(callId: string): Promise<ToolExecuteResult> {
        const response = await fetch(`${getAgentApiBase()}/approve/${callId}`, {
            method: 'POST'
        });
        return handleResponse(response);
    },

    /** Reject a pending tool call */
    async rejectCall(callId: string): Promise<{ status: string }> {
        const response = await fetch(`${getAgentApiBase()}/reject/${callId}`, {
            method: 'POST'
        });
        return handleResponse(response);
    },

    /** Get all pending tool calls */
    async getPendingCalls(): Promise<{ pending: PendingToolCall[] }> {
        const response = await fetch(`${getAgentApiBase()}/pending`);
        return handleResponse(response);
    },

    // ========== MCP Server Management (Remote Only) ==========

    /** List all configured MCP servers */
    async listMCPServers(): Promise<MCPServer[]> {
        const response = await fetch(`${API_URLS.remote.mcp}/servers`);
        return handleResponse(response);
    },

    /** Add a new MCP server */
    async addMCPServer(config: MCPServerConfig): Promise<{ id: string; name: string; is_active: boolean }> {
        const response = await fetch(`${API_URLS.remote.mcp}/servers`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        return handleResponse(response);
    },

    /** Remove an MCP server */
    async removeMCPServer(serverId: string): Promise<{ message: string }> {
        const response = await fetch(`${API_URLS.remote.mcp}/servers/${serverId}`, {
            method: 'DELETE'
        });
        return handleResponse(response);
    },

    /** Get tools in OpenAI format (for LLM) */
    async getToolsOpenAIFormat(): Promise<{ tools: unknown[]; count: number }> {
        const response = await fetch(`${API_URLS.remote.mcp}/tools/openai-format`);
        return handleResponse(response);
    }
};

// MCP Types
export interface MCPServer {
    id: string;
    name: string;
    transport: 'stdio' | 'http' | 'builtin';
    command?: string;
    args?: string[];
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

export default agentApi;
