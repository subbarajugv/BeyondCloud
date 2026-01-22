<script lang="ts">
    import { agentStore } from '$lib/stores/agentStore.svelte';
    import { Button } from '$lib/components/ui/button';
    import { Input } from '$lib/components/ui/input';
    import { Textarea } from '$lib/components/ui/textarea';
    import { Label } from '$lib/components/ui/label';
    import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '$lib/components/ui/card';
    import * as Select from '$lib/components/ui/select';
    import { toast } from 'svelte-sonner';
    import { X, Plus, Info, Check, ShieldCheck } from '@lucide/svelte';

    /** Props */
    interface Props {
        onSave?: () => void;
        onCancel?: () => void;
    }
    let { onSave, onCancel }: Props = $props();

    /** Form State */
    let name = $state('');
    let description = $state('');
    let objective = $state('');
    let executionMode = $state('planner');
    let maxSteps = $state(5);
    let allowedTools = $state<string[]>(['rag']);
    let icon = $state('user');
    let color = $state('blue');

    const availableTools = [
        { id: 'rag', name: 'Knowledge (RAG)', description: 'Access internal documents' },
        { id: 'web_search', name: 'Web Search', description: 'Search the live web' },
        { id: 'run_python', name: 'Code Sandbox', description: 'Execute Python code' },
        { id: 'screenshot', name: 'Browser', description: 'Take screenshots of URLs' },
        { id: 'database_query', name: 'SQL Database', description: 'Query approved databases' }
    ];

    const colors = ['blue', 'purple', 'orange', 'green', 'rose', 'indigo'];

    function toggleTool(toolId: string) {
        if (allowedTools.includes(toolId)) {
            allowedTools = allowedTools.filter(t => t !== toolId);
        } else {
            allowedTools = [...allowedTools, toolId];
        }
    }

    async function handleSave() {
        if (!name.trim()) {
            toast.error('Agent name is required');
            return;
        }

        const success = await agentStore.saveCustomAgent({
            name,
            description,
            spec: {
                objective,
                execution_mode: executionMode,
                max_steps: maxSteps,
                allowed_tools: allowedTools,
                allowed_models: ['gemini-1.5-pro', 'gpt-4o'], // Default for now
                icon,
                color
            }
        });

        if (success) {
            toast.success('Custom agent created successfully');
            onSave?.();
        } else {
            toast.error('Failed to save agent: ' + agentStore.error);
        }
    }
</script>

<div class="agent-builder space-y-6 max-w-2xl mx-auto p-4 md:p-0">
    <div class="flex items-center justify-between">
        <div>
            <h2 class="text-2xl font-bold text-white mb-1">Build Custom Agent</h2>
            <p class="text-gray-400 text-sm">Define an execution policy to compile into an autonomous agent.</p>
        </div>
        <Button variant="ghost" size="icon" onclick={onCancel}>
            <X class="h-5 w-5" />
        </Button>
    </div>

    <div class="space-y-4">
        <!-- Basic Info -->
        <Card class="bg-white/5 border-white/10">
            <CardHeader>
                <CardTitle class="text-lg">Identity</CardTitle>
                <CardDescription>How this agent appears in the product.</CardDescription>
            </CardHeader>
            <CardContent class="space-y-4">
                <div class="grid grid-cols-2 gap-4">
                    <div class="space-y-2">
                        <Label for="name">Agent Name</Label>
                        <Input id="name" placeholder="e.g. Research Analyst" bind:value={name} class="bg-black/20" />
                    </div>
                    <div class="space-y-2">
                        <Label>Accent Color</Label>
                        <div class="flex items-center gap-2 h-10 px-1">
                            {#each colors as c}
                                <button 
                                    class="w-6 h-6 rounded-full border-2 transition-transform hover:scale-110"
                                    class:border-white={color === c}
                                    class:border-transparent={color !== c}
                                    style="background-color: {c}"
                                    onclick={() => color = c}
                                ></button>
                            {/each}
                        </div>
                    </div>
                </div>
                <div class="space-y-2">
                    <Label for="desc">Short Description</Label>
                    <Input id="desc" placeholder="Briefly what it does" bind:value={description} class="bg-black/20" />
                </div>
            </CardContent>
        </Card>

        <!-- The Spec -->
        <Card class="bg-white/5 border-white/10">
            <CardHeader>
                <CardTitle class="text-lg">The Objective</CardTitle>
                <CardDescription>The core system prompt and reasoning goal.</CardDescription>
            </CardHeader>
            <CardContent class="space-y-4">
                <div class="space-y-2">
                    <Label for="objective">System Instructions</Label>
                    <Textarea 
                        id="objective" 
                        placeholder="Define the role and constraints..." 
                        bind:value={objective} 
                        rows={4}
                        class="bg-black/20 resize-none font-mono text-sm"
                    />
                    <p class="text-[10px] text-gray-500 flex items-center gap-1">
                        <Info class="h-3 w-3" />
                        This objective is compiled into the system prompt for the inference engine.
                    </p>
                </div>
            </CardContent>
        </Card>

        <!-- Tools & Guardrails -->
        <Card class="bg-white/5 border-white/10">
            <CardHeader>
                <CardTitle class="text-lg">Capabilities & Safety</CardTitle>
                <CardDescription>Allowed tools and execution constraints.</CardDescription>
            </CardHeader>
            <CardContent class="space-y-4">
                <div class="grid grid-cols-2 gap-4">
                    <div class="space-y-2">
                        <Label>Execution Mode</Label>
                        <select 
                            bind:value={executionMode}
                            class="w-full h-10 px-3 bg-black/20 border border-white/10 rounded-md text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                            <option value="single">Single Response</option>
                            <option value="multi-step">Multi-Step ReAct</option>
                            <option value="planner" selected>Autonomous Planner</option>
                        </select>
                    </div>
                    <div class="space-y-2">
                        <Label>Max Steps ({maxSteps})</Label>
                        <input type="range" min="1" max="10" step="1" bind:value={maxSteps} class="w-full h-10" />
                    </div>
                </div>

                <div class="space-y-3 pt-2">
                    <Label class="flex items-center gap-2">
                        <ShieldCheck class="h-4 w-4 text-green-400" />
                        Tool Firewall (Allowed Tools)
                    </Label>
                    <div class="grid grid-cols-2 gap-2">
                        {#each availableTools as tool}
                            <button 
                                class="flex flex-col items-start p-3 rounded-xl border transition-all text-left group
                                {allowedTools.includes(tool.id) ? 'bg-blue-500/10 border-blue-500/50 shadow-[0_0_15px_-5px_rgba(59,130,246,0.5)]' : 'bg-black/20 border-white/10 hover:border-white/20'}"
                                onclick={() => toggleTool(tool.id)}
                            >
                                <div class="flex items-center gap-2 mb-1">
                                    <div class="w-2 h-2 rounded-full {allowedTools.includes(tool.id) ? 'bg-blue-400' : 'bg-gray-600'}"></div>
                                    <span class="text-sm font-medium {allowedTools.includes(tool.id) ? 'text-white' : 'text-gray-400'}">{tool.name}</span>
                                </div>
                                <span class="text-[10px] text-gray-500 leading-tight">{tool.description}</span>
                            </button>
                        {/each}
                    </div>
                </div>
            </CardContent>
            <CardFooter class="bg-black/10 border-t border-white/5 py-3 flex items-center gap-2 text-[10px] text-gray-500">
                <ShieldCheck class="h-3 w-3" />
                Requests triggering disallowed tools will be denied by the engine.
            </CardFooter>
        </Card>
    </div>

    <div class="flex items-center justify-end gap-3 pt-2 pb-8">
        <Button variant="ghost" onclick={onCancel}>Cancel</Button>
        <Button 
            class="bg-blue-600 hover:bg-blue-500 text-white min-w-32 shadow-lg shadow-blue-900/20"
            onclick={handleSave}
            disabled={agentStore.isLoading}
        >
            {agentStore.isLoading ? 'Saving...' : 'Save Agent'}
        </Button>
    </div>
</div>

<style>
    @reference "tailwindcss";

    /* Styling input range for a more premium feel */
    input[type='range'] {
        @apply bg-transparent appearance-none cursor-pointer;
    }
    input[type='range']::-webkit-slider-runnable-track {
        @apply bg-white/10 h-1.5 rounded-lg;
    }
    input[type='range']::-webkit-slider-thumb {
        @apply appearance-none bg-blue-500 w-4 h-4 rounded-full -mt-1.25 border-2 border-white shadow-lg shadow-blue-500/50;
    }
</style>
