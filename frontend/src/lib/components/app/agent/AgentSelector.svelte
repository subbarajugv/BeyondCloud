<script lang="ts">
    import { agentStore } from '$lib/stores/agentStore.svelte';
    import { fade } from 'svelte/transition';
    import { MessageSquare, Globe, BarChart, ChevronDown, Plus } from '@lucide/svelte';
    import DialogAgentBuilder from './DialogAgentBuilder.svelte';

    let isOpen = $state(false);
    let builderOpen = $state(false);

    function toggle() {
        isOpen = !isOpen;
    }

    function select(id: string) {
        agentStore.selectAgent(id);
        isOpen = false;
    }

    function openBuilder() {
        builderOpen = true;
        isOpen = false;
    }

    function handleClickOutside(event: MouseEvent) {
        const target = event.target as Element;
        if (isOpen && target && !target.closest('.agent-selector')) {
            isOpen = false;
        }
    }

    const iconMap: Record<string, any> = {
        'message-square': MessageSquare,
        'globe': Globe,
        'bar-chart': BarChart
    };

    function getAgentColorClass(color: string, type: 'bg' | 'text'): string {
        if (color === 'blue') return type === 'bg' ? 'bg-blue-500/20' : 'text-blue-400';
        if (color === 'purple') return type === 'bg' ? 'bg-purple-500/20' : 'text-purple-400';
        if (color === 'orange') return type === 'bg' ? 'bg-orange-500/20' : 'text-orange-400';
        return type === 'bg' ? 'bg-gray-500/20' : 'text-gray-400';
    }
</script>

<svelte:window onclick={handleClickOutside} />

<div class="agent-selector relative z-20">
    <button 
        class="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-white/5 transition-colors border border-transparent hover:border-white/10"
        class:bg-white-5={isOpen}
        onclick={toggle}
    >
        <div class={'w-5 h-5 rounded-md flex items-center justify-center ' + getAgentColorClass(agentStore.activeAgent.color, 'bg') + ' ' + getAgentColorClass(agentStore.activeAgent.color, 'text')}>
            <svelte:component this={iconMap[agentStore.activeAgent.icon] || MessageSquare} size={14} />
        </div>
        <span class="text-sm font-medium text-gray-300">{agentStore.activeAgent.name}</span>
        <ChevronDown size={14} class={'text-gray-500 transition-transform ' + (isOpen ? 'rotate-180' : '')} />
    </button>

    {#if isOpen}
        <div 
            transition:fade={{ duration: 100 }}
            class="absolute top-full left-0 mt-2 w-64 bg-[#1e1e1e] border border-white/10 rounded-xl shadow-2xl overflow-hidden backdrop-blur-xl"
        >
            <div class="px-2 py-2 space-y-0.5">
                {#each agentStore.agentPolicies as agent}
                    <button
                        class={'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors relative group ' + (agentStore.selectedAgentId === agent.id ? 'bg-white/10' : 'hover:bg-white/5')}
                        onclick={() => select(agent.id)}
                    >
                        <div class={'w-8 h-8 rounded-lg flex items-center justify-center transition-colors ' + (agentStore.selectedAgentId === agent.id ? (getAgentColorClass(agent.color, 'bg') + ' ' + getAgentColorClass(agent.color, 'text')) : 'bg-white/5 text-gray-400 group-hover:text-gray-300')}>
                            <svelte:component this={iconMap[agent.icon] || MessageSquare} size={16} />
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="text-sm font-medium text-gray-200">{agent.name}</div>
                            <div class="text-xs text-gray-500 truncate">{agent.description}</div>
                        </div>
                        {#if agentStore.selectedAgentId === agent.id}
                            <div class="absolute right-3 w-1.5 h-1.5 rounded-full bg-blue-500"></div>
                        {/if}
                    </button>
                {/each}
            </div>
            
            <div class="p-2 border-t border-white/5">
                <button 
                    class="w-full h-9 flex items-center justify-center gap-2 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-medium text-gray-300 transition-colors"
                    onclick={openBuilder}
                >
                    <Plus class="h-3.5 w-3.5" />
                    Create New Agent
                </button>
            </div>

            <div class="px-3 py-2 bg-black/20 border-t border-white/5 text-[10px] text-gray-500">
                Agents determine capabilities and execution strategy.
            </div>
        </div>
    {/if}
</div>

<DialogAgentBuilder bind:open={builderOpen} />
