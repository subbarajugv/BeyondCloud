/**
 * Agent API Client - Frontend interface for agentic operations
 */

// Python AI Service base URL
const AGENT_API_BASE = 'http://localhost:8001/api/agent';

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
        const response = await fetch(`${AGENT_API_BASE}/set-sandbox`, {
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
        const response = await fetch(`${AGENT_API_BASE}/set-mode`, {
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
        const response = await fetch(`${AGENT_API_BASE}/status`);
        return handleResponse(response);
    },

    /**
     * Get available tool schemas for LLM
     */
    async getTools(): Promise<{ tools: ToolSchema[] }> {
        const response = await fetch(`${AGENT_API_BASE}/tools`);
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
        const response = await fetch(`${AGENT_API_BASE}/execute`, {
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
        const response = await fetch(`${AGENT_API_BASE}/approve/${callId}`, {
            method: 'POST'
        });
        return handleResponse(response);
    },

    /**
     * Reject a pending tool call
     */
    async rejectCall(callId: string): Promise<{ status: string; tool_name: string; message: string }> {
        const response = await fetch(`${AGENT_API_BASE}/reject/${callId}`, {
            method: 'POST'
        });
        return handleResponse(response);
    },

    /**
     * Get all pending tool calls
     */
    async getPendingCalls(): Promise<{ pending: PendingToolCall[] }> {
        const response = await fetch(`${AGENT_API_BASE}/pending`);
        return handleResponse(response);
    }
};

export default agentApi;
