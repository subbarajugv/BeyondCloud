/**
 * Conversations API Client
 * Handles all conversation and message operations with the backend
 */

import { getAccessToken } from './api';

const API_BASE = '/api';

interface ApiError {
    code: string;
    message: string;
}

interface ApiErrorResponse {
    error: ApiError;
}

class ApiClientError extends Error {
    code: string;

    constructor(error: ApiError) {
        super(error.message);
        this.code = error.code;
        this.name = 'ApiClientError';
    }
}

function getAuthHeaders(): HeadersInit {
    const token = getAccessToken();
    const headers: HeadersInit = {
        'Content-Type': 'application/json'
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        try {
            const errorData = (await response.json()) as ApiErrorResponse;
            throw new ApiClientError(errorData.error);
        } catch (e) {
            if (e instanceof ApiClientError) throw e;
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
    }
    return response.json() as Promise<T>;
}

// Backend conversation type
export interface ApiConversation {
    id: string;
    name: string | null;
    current_node: string | null;
    created_at: string;
    updated_at: string;
    message_count?: number;
    last_message?: string;
}

// Backend message type
export interface ApiMessage {
    id: string;
    parent_id: string | null;
    role: string;
    content: string;
    model: string | null;
    provider: string | null;
    reasoning_content: string | null;
    created_at: string;
}

interface ListConversationsResponse {
    conversations: ApiConversation[];
}

interface CreateConversationResponse {
    conversation: ApiConversation;
}

interface GetConversationResponse {
    conversation: ApiConversation;
    messages: ApiMessage[];
}

interface UpdateConversationResponse {
    conversation: ApiConversation;
}

interface AddMessageResponse {
    message: ApiMessage;
}

/**
 * Conversations API endpoints
 */
export const conversationsApi = {
    /**
     * GET /api/conversations - List all conversations for the authenticated user
     */
    async list(): Promise<ApiConversation[]> {
        const response = await fetch(`${API_BASE}/conversations`, {
            headers: getAuthHeaders()
        });
        const data = await handleResponse<ListConversationsResponse>(response);
        return data.conversations;
    },

    /**
     * POST /api/conversations - Create a new conversation
     */
    async create(name?: string): Promise<ApiConversation> {
        const response = await fetch(`${API_BASE}/conversations`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ name })
        });
        const data = await handleResponse<CreateConversationResponse>(response);
        return data.conversation;
    },

    /**
     * GET /api/conversations/:id - Get a conversation with its messages
     */
    async get(id: string): Promise<{ conversation: ApiConversation; messages: ApiMessage[] }> {
        const response = await fetch(`${API_BASE}/conversations/${id}`, {
            headers: getAuthHeaders()
        });
        return handleResponse<GetConversationResponse>(response);
    },

    /**
     * PUT /api/conversations/:id - Update a conversation
     */
    async update(id: string, data: { name?: string; current_node?: string }): Promise<ApiConversation> {
        const response = await fetch(`${API_BASE}/conversations/${id}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(data)
        });
        const result = await handleResponse<UpdateConversationResponse>(response);
        return result.conversation;
    },

    /**
     * DELETE /api/conversations/:id - Delete a conversation
     */
    async delete(id: string): Promise<void> {
        const response = await fetch(`${API_BASE}/conversations/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            const errorData = (await response.json()) as ApiErrorResponse;
            throw new ApiClientError(errorData.error);
        }
    },

    /**
     * POST /api/conversations/:id/messages - Add a message to a conversation
     */
    async addMessage(
        conversationId: string,
        message: {
            role: string;
            content: string;
            parent_id?: string | null;
            model?: string;
            provider?: string;
            reasoning_content?: string;
        }
    ): Promise<ApiMessage> {
        const response = await fetch(`${API_BASE}/conversations/${conversationId}/messages`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(message)
        });
        const data = await handleResponse<AddMessageResponse>(response);
        return data.message;
    }
};
