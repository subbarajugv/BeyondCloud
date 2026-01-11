import { providersStore } from '$lib/stores/providers.svelte';
import type { ModelsResponse } from '$lib/types/providers';

export interface ApiModelListItem {
	id: string;
	object: string;
	created?: number;
	owned_by?: string;
	meta?: any;
}

export interface ApiModelListResponse {
	data: ApiModelListItem[];
	models?: any[];
}

export class ModelsService {
	static async list(): Promise<ApiModelListResponse> {
		const activeProviderId = providersStore.activeProviderId;
		console.log('[DEBUG] ModelsService.list - Active Provider:', activeProviderId);

		const response = await fetch(`/api/models?provider=${encodeURIComponent(activeProviderId)}`);

		if (!response.ok) {
			throw new Error(`Failed to fetch model list (status ${response.status})`);
		}

		const data = (await response.json()) as ModelsResponse;
		console.log('[DEBUG] ModelsService.list - Response:', data);

		// Map backend flat string array to the format expected by the frontend store
		return {
			data: data.models.map(modelId => ({
				id: modelId,
				object: 'model'
			}))
		};
	}
}
