<script lang="ts">
    import { authStore } from '$lib/stores/auth.svelte';
    import { goto } from '$app/navigation';

    let email = $state('');
    let password = $state('');
    let isSubmitting = $state(false);
    let errorMessage = $state('');

    async function handleSubmit(e: Event) {
        e.preventDefault();
        isSubmitting = true;
        errorMessage = '';

        try {
            await authStore.login({ email, password });
            goto('/');
        } catch (err: unknown) {
            const error = err as Error;
            errorMessage = error.message || 'Login failed';
        } finally {
            isSubmitting = false;
        }
    }
</script>

<svelte:head>
    <title>Login - BeyondCloud</title>
</svelte:head>

<div class="rounded-2xl border border-slate-700/50 bg-slate-800/50 p-8 shadow-2xl backdrop-blur-sm">
    <div class="mb-8 text-center">
        <h1 class="mb-2 text-3xl font-bold text-white">Welcome Back</h1>
        <p class="text-slate-400">Sign in to your BeyondCloud account</p>
    </div>

    <form onsubmit={handleSubmit} class="space-y-6">
        {#if errorMessage}
            <div class="rounded-lg border border-red-500/50 bg-red-500/10 p-4 text-sm text-red-400">
                {errorMessage}
            </div>
        {/if}

        <div>
            <label for="email" class="mb-2 block text-sm font-medium text-slate-300">
                Email
            </label>
            <input
                id="email"
                type="email"
                bind:value={email}
                required
                disabled={isSubmitting}
                class="w-full rounded-lg border border-slate-600 bg-slate-700/50 px-4 py-3 text-white placeholder-slate-400 transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50"
                placeholder="you@example.com"
            />
        </div>

        <div>
            <label for="password" class="mb-2 block text-sm font-medium text-slate-300">
                Password
            </label>
            <input
                id="password"
                type="password"
                bind:value={password}
                required
                disabled={isSubmitting}
                class="w-full rounded-lg border border-slate-600 bg-slate-700/50 px-4 py-3 text-white placeholder-slate-400 transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50"
                placeholder="••••••••"
            />
        </div>

        <button
            type="submit"
            disabled={isSubmitting}
            class="w-full rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 px-4 py-3 font-semibold text-white shadow-lg transition-all hover:from-blue-500 hover:to-blue-400 hover:shadow-blue-500/25 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
            {#if isSubmitting}
                <span class="flex items-center justify-center gap-2">
                    <svg class="h-5 w-5 animate-spin" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Signing in...
                </span>
            {:else}
                Sign In
            {/if}
        </button>
    </form>

    <div class="mt-6 text-center">
        <p class="text-slate-400">
            Don't have an account?
            <a href="/register" class="font-medium text-blue-400 transition-colors hover:text-blue-300">
                Create one
            </a>
        </p>
    </div>
</div>
