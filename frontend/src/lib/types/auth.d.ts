/**
 * Authentication types for frontend
 */

export type UserRole = 'user' | 'rag_user' | 'agent_user' | 'admin' | 'owner';

export interface User {
    id: string;
    email: string;
    displayName: string | null;
    role?: UserRole;  // RBAC role - may not be present for legacy tokens
}

export interface LoginCredentials {
    email: string;
    password: string;
}

export interface RegisterCredentials {
    email: string;
    password: string;
    displayName?: string;
}

export interface AuthResponse {
    user: User;
    token: string;
}

export interface ProfileResponse {
    user: User;
}
