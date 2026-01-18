/**
 * Auth Store - Manages authentication state
 */
import { authApi, setAccessToken, signalAuthReady } from '$lib/services/api';
import type { LoginCredentials, RegisterCredentials, User, UserRole } from '$lib/types/auth';
import { browser } from '$app/environment';
import { syncFromApi, setAuthenticated } from '$lib/stores/settings.svelte';

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

// Role hierarchy for permission checks
const ROLE_HIERARCHY: UserRole[] = ['user', 'rag_user', 'agent_user', 'admin', 'owner'];

function getRoleLevel(role: UserRole): number {
    const level = ROLE_HIERARCHY.indexOf(role);
    return level >= 0 ? level : 0;
}

class AuthStore {
    user = $state<User | null>(null);
    token = $state<string | null>(null);
    isAuthenticated = $derived(!!this.token);
    isLoading = $state(true);
    error = $state<string | null>(null);

    // Role-based computed properties
    get userRole(): UserRole {
        return this.user?.role ?? 'user';
    }

    get isAdmin(): boolean {
        return getRoleLevel(this.userRole) >= getRoleLevel('admin');
    }

    get isOwner(): boolean {
        return this.userRole === 'owner';
    }

    get canManageSharedRAG(): boolean {
        return this.isAdmin;
    }

    /**
     * Check if user has at least the specified role level
     */
    hasMinRole(minRole: UserRole): boolean {
        return getRoleLevel(this.userRole) >= getRoleLevel(minRole);
    }

    /**
     * Promise that resolves when auth state is fully restored from localStorage.
     * External modules should await this before making authenticated API calls.
     * This fixes race conditions where modules try to fetch data before auth token is set.
     */
    ready: Promise<void>;
    private resolveReady!: () => void;

    constructor() {
        this.ready = new Promise((resolve) => {
            this.resolveReady = resolve;
        });

        if (browser) {
            this.init();
        } else {
            // Resolve immediately in SSR context
            this.resolveReady();
            signalAuthReady();
        }
    }

    private init() {
        const storedToken = localStorage.getItem(TOKEN_KEY);
        const storedUser = localStorage.getItem(USER_KEY);

        if (storedToken) {
            this.token = storedToken;
            setAccessToken(storedToken);
            setAuthenticated(true);

            if (storedUser) {
                try {
                    this.user = JSON.parse(storedUser);
                } catch {
                    this.user = null;
                }
            }

            // Verify token validity and sync settings
            this.fetchProfile()
                .then(() => syncFromApi())
                .catch(() => {
                    this.logout();
                });
        }

        this.isLoading = false;
        // Signal that auth state is fully restored
        this.resolveReady();
        signalAuthReady();  // Also signal via api.ts for modules that can't import authStore
    }

    async register(credentials: RegisterCredentials) {
        this.isLoading = true;
        this.error = null;
        try {
            const { user, token } = await authApi.register(credentials);
            this.setSession(user, token);
            return user;
        } catch (e: unknown) {
            const error = e as Error;
            this.error = error.message || 'Registration failed';
            throw e;
        } finally {
            this.isLoading = false;
        }
    }

    async login(credentials: LoginCredentials) {
        this.isLoading = true;
        this.error = null;
        try {
            const { user, token } = await authApi.login(credentials);
            this.setSession(user, token);
            // Sync settings from API after login (Phase 3)
            setAuthenticated(true);
            await syncFromApi();
            return user;
        } catch (e: unknown) {
            const error = e as Error;
            this.error = error.message || 'Login failed';
            throw e;
        } finally {
            this.isLoading = false;
        }
    }

    logout() {
        this.user = null;
        this.token = null;
        this.error = null;
        setAuthenticated(false);

        if (browser) {
            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(USER_KEY);
        }
        setAccessToken(null);
    }

    async fetchProfile() {
        try {
            const { user } = await authApi.getProfile();
            this.user = user;
            if (browser) {
                localStorage.setItem(USER_KEY, JSON.stringify(user));
            }
            return user;
        } catch (e) {
            this.logout();
            throw e;
        }
    }

    private setSession(user: User, token: string) {
        this.user = user;
        this.token = token;
        setAccessToken(token);

        if (browser) {
            localStorage.setItem(TOKEN_KEY, token);
            localStorage.setItem(USER_KEY, JSON.stringify(user));
        }
    }
}

export const authStore = new AuthStore();
