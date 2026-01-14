/**
 * Settings API Client
 * Syncs user settings with the backend API when authenticated
 */

import { getAccessToken } from '$lib/services/api';

const API_BASE = '/api';

function getAuthHeaders(): HeadersInit {
    const token = getAccessToken();
    return {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
}

async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error?.message || `HTTP ${response.status}`);
    }
    return response.json();
}

export interface SettingsData {
    [key: string]: string | number | boolean;
}

export const settingsApi = {
    /**
     * Get user settings from the backend
     */
    async getSettings(): Promise<SettingsData> {
        const response = await fetch(`${API_BASE}/settings`, {
            method: 'GET',
            headers: getAuthHeaders()
        });
        const data = await handleResponse<{ settings: SettingsData }>(response);
        return data.settings;
    },

    /**
     * Save user settings to the backend (merges with existing)
     */
    async saveSettings(settings: SettingsData): Promise<SettingsData> {
        const response = await fetch(`${API_BASE}/settings`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ settings })
        });
        const data = await handleResponse<{ settings: SettingsData }>(response);
        return data.settings;
    }
};

export default settingsApi;
