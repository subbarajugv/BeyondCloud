/**
 * Auth Store - Manages authentication state
 */
import { authApi, setAccessToken } from '$lib/services/api';
import type { LoginCredentials, RegisterCredentials, User } from '$lib/types/auth';
import { browser } from '$app/environment';

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

class AuthStore {
    user = $state<User | null>(null);
    token = $state<string | null>(null);
    isAuthenticated = $derived(!!this.token);
    isLoading = $state(true);
    error = $state<string | null>(null);

    constructor() {
        if (browser) {
            this.init();
        }
    }

    private init() {
        const storedToken = localStorage.getItem(TOKEN_KEY);
        const storedUser = localStorage.getItem(USER_KEY);

        if (storedToken) {
            this.token = storedToken;
            setAccessToken(storedToken);

            if (storedUser) {
                try {
                    this.user = JSON.parse(storedUser);
                } catch {
                    this.user = null;
                }
            }

            // Verify token validity
            this.fetchProfile().catch(() => {
                this.logout();
            });
        }

        this.isLoading = false;
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
