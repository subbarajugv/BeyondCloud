/**
 * RAG Settings Store - Manages user's RAG pipeline configuration
 * 
 * Uses Svelte 5 runes for reactive state.
 */

import {
    type RAGSettings,
    DEFAULT_RAG_SETTINGS,
    getRAGSettings,
    updateRAGSettings as apiUpdateSettings,
    resetRAGSettings as apiResetSettings
} from '$lib/services/ragSettingsApi';

class RAGSettingsStore {
    settings = $state<RAGSettings>({ ...DEFAULT_RAG_SETTINGS });
    loading = $state(false);
    saving = $state(false);
    error = $state<string | null>(null);
    initialized = $state(false);

    /**
     * Load settings from backend
     */
    async loadSettings(): Promise<void> {
        if (this.loading) return;

        this.loading = true;
        this.error = null;

        try {
            const data = await getRAGSettings();
            this.settings = data;
            this.initialized = true;
        } catch (e) {
            this.error = 'Failed to load RAG settings';
            console.error('RAG Settings load error:', e);
        } finally {
            this.loading = false;
        }
    }

    /**
     * Save current settings to backend
     */
    async saveSettings(): Promise<boolean> {
        if (this.saving) return false;

        this.saving = true;
        this.error = null;

        try {
            const updated = await apiUpdateSettings(this.settings);
            this.settings = updated;
            return true;
        } catch (e) {
            this.error = 'Failed to save RAG settings';
            console.error('RAG Settings save error:', e);
            return false;
        } finally {
            this.saving = false;
        }
    }

    /**
     * Update a single setting locally (call saveSettings to persist)
     */
    updateSetting<K extends keyof RAGSettings>(key: K, value: RAGSettings[K]): void {
        this.settings = { ...this.settings, [key]: value };
    }

    /**
     * Update multiple settings at once
     */
    updateMultiple(updates: Partial<RAGSettings>): void {
        this.settings = { ...this.settings, ...updates };
    }

    /**
     * Reset to default settings
     */
    async resetToDefaults(): Promise<boolean> {
        this.saving = true;
        this.error = null;

        try {
            const defaults = await apiResetSettings();
            this.settings = defaults;
            return true;
        } catch (e) {
            this.error = 'Failed to reset settings';
            console.error('RAG Settings reset error:', e);
            return false;
        } finally {
            this.saving = false;
        }
    }
}

// Export singleton instance
export const ragSettingsStore = new RAGSettingsStore();
