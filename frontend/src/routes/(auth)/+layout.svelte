<script lang="ts">
    import '../../app.css';
    let { children } = $props();
</script>

<div class="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
    <div class="w-full max-w-md p-8">
        {@render children?.()}
    </div>
</div>
