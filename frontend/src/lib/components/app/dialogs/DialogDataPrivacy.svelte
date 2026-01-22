<script lang="ts">
  import * as Dialog from '$lib/components/ui/dialog';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Separator } from '$lib/components/ui/separator';
  import { Download, Trash2, AlertTriangle, Loader2, CheckCircle, XCircle } from '@lucide/svelte';
  import { getAccessToken } from '$lib/services/api';

  let { open = $bindable(false) } = $props();

  // State
  let deleteConfirmText = $state('');
  let isExporting = $state(false);
  let isDeleting = $state(false);
  let exportSuccess = $state(false);
  let deleteSuccess = $state(false);
  let error = $state<string | null>(null);

  const CONFIRM_TEXT = 'DELETE';
  const API_BASE = 'http://localhost:8001/api';

  let canDelete = $derived(deleteConfirmText === CONFIRM_TEXT);

  function resetState() {
    deleteConfirmText = '';
    isExporting = false;
    isDeleting = false;
    exportSuccess = false;
    deleteSuccess = false;
    error = null;
  }

  async function handleExport() {
    isExporting = true;
    error = null;
    exportSuccess = false;

    try {
      const token = getAccessToken();
      const response = await fetch(`${API_BASE}/admin/my-data/export`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to export data');
      }

      // Download the ZIP file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `beyondcloud_export_${new Date().toISOString().split('T')[0]}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      exportSuccess = true;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Export failed';
    } finally {
      isExporting = false;
    }
  }

  async function handleDelete() {
    if (!canDelete) return;

    isDeleting = true;
    error = null;

    try {
      const token = getAccessToken();
      const response = await fetch(`${API_BASE}/admin/my-data?confirm=true`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to delete data');
      }

      deleteSuccess = true;
      deleteConfirmText = '';
    } catch (e) {
      error = e instanceof Error ? e.message : 'Delete failed';
    } finally {
      isDeleting = false;
    }
  }
</script>

<Dialog.Root bind:open onOpenChange={() => resetState()}>
  <Dialog.Content class="max-w-lg">
    <Dialog.Header>
      <Dialog.Title class="flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        </svg>
        Data & Privacy
      </Dialog.Title>
      <Dialog.Description>
        Manage your personal data. Export everything or delete your data permanently.
      </Dialog.Description>
    </Dialog.Header>

    <div class="space-y-6 py-4">
      <!-- Export Section -->
      <div class="space-y-3">
        <h4 class="font-medium text-sm">Export Your Data</h4>
        <p class="text-sm text-muted-foreground">
          Download a ZIP file containing all your data including documents, collections, 
          usage history, and settings.
        </p>
        <Button 
          variant="outline" 
          onclick={handleExport} 
          disabled={isExporting}
          class="w-full sm:w-auto"
        >
          {#if isExporting}
            <Loader2 class="mr-2 h-4 w-4 animate-spin" />
            Exporting...
          {:else if exportSuccess}
            <CheckCircle class="mr-2 h-4 w-4 text-green-500" />
            Downloaded!
          {:else}
            <Download class="mr-2 h-4 w-4" />
            Export My Data
          {/if}
        </Button>
      </div>

      <Separator />

      <!-- Delete Section -->
      <div class="space-y-4">
        <h4 class="font-medium text-sm text-red-600 dark:text-red-400">Danger Zone</h4>
        
        <!-- Big Warning Box -->
        <div class="rounded-lg border-2 border-red-500/50 bg-red-50 p-4 dark:bg-red-950/30">
          <div class="flex gap-3">
            <AlertTriangle class="h-6 w-6 flex-shrink-0 text-red-600 dark:text-red-400" />
            <div class="space-y-2">
              <p class="font-semibold text-red-800 dark:text-red-200">
                Permanent Data Deletion
              </p>
              <p class="text-sm text-red-700 dark:text-red-300">
                This will <strong>permanently delete</strong> all your data:
              </p>
              <ul class="text-sm text-red-700 dark:text-red-300 list-disc list-inside space-y-1">
                <li>All uploaded documents and their chunks</li>
                <li>All collections you created</li>
                <li>All usage history and analytics</li>
                <li>All support tickets</li>
                <li>All RAG settings and preferences</li>
              </ul>
              <p class="text-sm font-semibold text-red-800 dark:text-red-200 pt-2">
                ⚠️ This action cannot be undone!
              </p>
            </div>
          </div>
        </div>

        {#if deleteSuccess}
          <div class="rounded-lg border border-green-500 bg-green-50 p-4 dark:bg-green-950/30">
            <div class="flex items-center gap-2 text-green-700 dark:text-green-300">
              <CheckCircle class="h-5 w-5" />
              <span class="font-medium">Your data has been deleted successfully.</span>
            </div>
          </div>
        {:else}
          <!-- Confirmation Input -->
          <div class="space-y-2">
            <Label for="delete-confirm" class="text-sm">
              Type <code class="rounded bg-slate-200 px-1.5 py-0.5 font-mono text-red-600 dark:bg-slate-700 dark:text-red-400">DELETE</code> to confirm:
            </Label>
            <Input
              id="delete-confirm"
              bind:value={deleteConfirmText}
              placeholder="Type DELETE to confirm"
              class="font-mono {deleteConfirmText && !canDelete ? 'border-red-500' : ''}"
              autocomplete="off"
            />
            {#if deleteConfirmText && !canDelete}
              <p class="text-xs text-red-500">Please type DELETE exactly (case-sensitive)</p>
            {/if}
          </div>

          <Button 
            variant="destructive" 
            onclick={handleDelete} 
            disabled={!canDelete || isDeleting}
            class="w-full"
          >
            {#if isDeleting}
              <Loader2 class="mr-2 h-4 w-4 animate-spin" />
              Deleting...
            {:else}
              <Trash2 class="mr-2 h-4 w-4" />
              Permanently Delete All My Data
            {/if}
          </Button>
        {/if}

        {#if error}
          <div class="flex items-center gap-2 text-sm text-red-600">
            <XCircle class="h-4 w-4" />
            {error}
          </div>
        {/if}
      </div>
    </div>

    <Dialog.Footer>
      <Button variant="outline" onclick={() => open = false}>
        Close
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
