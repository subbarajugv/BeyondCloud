/**
 * Agent Store - State management for sandbox and tool execution
 */
import { agentApi, type AgentStatus, type ApprovalMode, type PendingToolCall, type ToolExecuteResult } from '$lib/services/agentApi';

// Reactive state
let sandboxPath = $state<string | null>(null);
let sandboxActive = $state(false);
let approvalMode = $state<ApprovalMode>('require_approval');
let pendingCalls = $state<PendingToolCall[]>([]);
let isLoading = $state(false);
let error = $state<string | null>(null);

// Tool schemas for LLM
let toolSchemas = $state<unknown[]>([]);

// Toggle for enabling/disabling tools (for models that don't support function calling)
// Default to DISABLED since most models don't support function calling
let toolsEnabled = $state<boolean>(
    typeof localStorage !== 'undefined'
        ? localStorage.getItem('agentToolsEnabled') === 'true'
        : false
);

/**
 * Agent Store - Manages sandbox configuration and tool execution state
 */
class AgentStore {
    // Getters
    get sandboxPath() { return sandboxPath; }
    get sandboxActive() { return sandboxActive; }
    get approvalMode() { return approvalMode; }
    get pendingCalls() { return pendingCalls; }
    get isLoading() { return isLoading; }
    get error() { return error; }
    get toolSchemas() { return toolSchemas; }
    get toolsEnabled() { return toolsEnabled; }

    /**
     * Enable or disable tools being sent to LLM
     */
    setToolsEnabled(enabled: boolean): void {
        toolsEnabled = enabled;
        if (typeof localStorage !== 'undefined') {
            localStorage.setItem('agentToolsEnabled', enabled ? 'true' : 'false');
        }
    }

    /**
     * Initialize agent store - load status from backend
     */
    async initialize(): Promise<void> {
        try {
            isLoading = true;
            const status = await agentApi.getStatus();
            sandboxPath = status.sandbox_path;
            sandboxActive = status.sandbox_active;
            approvalMode = status.approval_mode;

            // Load tool schemas if sandbox is active
            if (sandboxActive) {
                const result = await agentApi.getTools();
                toolSchemas = result.tools;
            }

            // Load pending calls
            const pending = await agentApi.getPendingCalls();
            pendingCalls = pending.pending;
        } catch (e) {
            error = (e as Error).message;
        } finally {
            isLoading = false;
        }
    }

    /**
     * Set the sandbox folder path
     */
    async setSandbox(path: string): Promise<boolean> {
        try {
            isLoading = true;
            error = null;
            const result = await agentApi.setSandbox(path);
            sandboxPath = result.path;
            sandboxActive = true;

            // Load tool schemas
            const tools = await agentApi.getTools();
            toolSchemas = tools.tools;

            return true;
        } catch (e) {
            error = (e as Error).message;
            return false;
        } finally {
            isLoading = false;
        }
    }

    /**
     * Set approval mode
     */
    async setMode(mode: ApprovalMode): Promise<void> {
        try {
            await agentApi.setMode(mode);
            approvalMode = mode;
        } catch (e) {
            error = (e as Error).message;
        }
    }

    /**
     * Toggle between approval and trust mode
     */
    async toggleMode(): Promise<void> {
        const newMode = approvalMode === 'require_approval' ? 'trust_mode' : 'require_approval';
        await this.setMode(newMode);
    }

    /**
     * Execute a tool (called when LLM requests a tool)
     */
    async executeTool(
        toolName: string,
        args: Record<string, unknown>,
        approved: boolean = false
    ): Promise<ToolExecuteResult> {
        try {
            const result = await agentApi.executeTool(toolName, args, approved);

            // If pending, add to pending calls
            if (result.status === 'pending_approval' && result.call_id) {
                const pending: PendingToolCall = {
                    id: result.call_id,
                    name: toolName,
                    arguments: args,
                    safety_level: (result.safety_level as 'safe' | 'moderate' | 'dangerous') || 'moderate'
                };
                pendingCalls = [...pendingCalls, pending];
            }

            return result;
        } catch (e) {
            throw e;
        }
    }

    /**
     * Approve a pending tool call
     */
    async approveCall(callId: string): Promise<ToolExecuteResult> {
        try {
            const result = await agentApi.approveCall(callId);
            // Remove from pending
            pendingCalls = pendingCalls.filter(c => c.id !== callId);
            return result;
        } catch (e) {
            throw e;
        }
    }

    /**
     * Reject a pending tool call
     */
    async rejectCall(callId: string): Promise<void> {
        try {
            await agentApi.rejectCall(callId);
            pendingCalls = pendingCalls.filter(c => c.id !== callId);
        } catch (e) {
            throw e;
        }
    }

    /**
     * Clear sandbox
     */
    clearSandbox(): void {
        sandboxPath = null;
        sandboxActive = false;
        toolSchemas = [];
        pendingCalls = [];
    }

    /**
     * Get tools for LLM request (only if sandbox is active AND tools are enabled)
     */
    getToolsForLLM(): unknown[] | undefined {
        if (!toolsEnabled || !sandboxActive || toolSchemas.length === 0) {
            return undefined;
        }
        return toolSchemas;
    }
}

// Singleton export
export const agentStore = new AgentStore();
