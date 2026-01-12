/**
 * Authentication types for frontend
 */

export interface User {
    id: string;
    email: string;
    displayName: string | null;
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
