<script lang="ts">
  import { Search, Check } from "lucide-svelte";

  interface Props {
    globalFacets: any;
    currentFacets: any;
    selectedTerms: string[];
    selectedDepts: string[];
    deptSearch: string;
    onToggleTerm: (term: string) => void;
    onToggleDept: (dept: string) => void;
    onDeptSearchChange: (val: string) => void;
  }

  let {
    globalFacets,
    currentFacets,
    selectedTerms,
    selectedDepts,
    deptSearch,
    onToggleTerm,
    onToggleDept,
    onDeptSearchChange
  }: Props = $props();

  let availableTerms = $derived(
    globalFacets?.term && Object.keys(globalFacets.term).length > 0
      ? Object.keys(globalFacets.term).sort().reverse()
      : (currentFacets?.term ? Object.keys(currentFacets.term).sort().reverse() : [])
  );

  let availableDeptsMap = $derived(
    (globalFacets?.dept_code && Object.keys(globalFacets.dept_code).length > 0)
      ? globalFacets.dept_code
      : (currentFacets?.dept_code || {})
  );

  let filteredDepts = $derived(
    Object.keys(availableDeptsMap)
      .sort()
      .filter(d => d.toLowerCase().includes(deptSearch.toLowerCase()))
  );
</script>

<div class="space-y-6">
  <!-- Term Filter -->
  <div class="space-y-2.5">
    <div class="font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider flex items-center justify-between">
      <span>Academic Term</span>
      <span class="text-[#0080c9] dark:text-amber-400">{selectedTerms.length || ''}</span>
    </div>
    <div class="space-y-1 max-h-48 overflow-y-auto pr-1 custom-scrollbar">
      {#if availableTerms.length > 0}
        {#each availableTerms as term}
          <button 
            onclick={() => onToggleTerm(term)}
            class="w-full flex items-center justify-between p-2 rounded-lg text-xs transition-colors cursor-pointer
            {selectedTerms.includes(term) 
              ? 'bg-[#002d72]/10 text-[#002d72] font-semibold dark:bg-amber-400/10 dark:text-amber-300' 
              : 'text-[#45423b] dark:text-neutral-400 hover:bg-[#edeae0] dark:hover:bg-[#232328]'}"
          >
            <div class="flex items-center space-x-2">
              <div class="w-3.5 h-3.5 rounded border flex items-center justify-center transition-colors
                {selectedTerms.includes(term) 
                  ? 'bg-[#002d72] border-[#002d72] dark:bg-amber-400 dark:border-amber-400' 
                  : 'bg-[#eeece2] border-[#c8c3b5] dark:bg-[#18181b] dark:border-[#3f3f46]'}">
                {#if selectedTerms.includes(term)}
                  <Check size={10} class="text-white dark:text-neutral-950 stroke-[3]" />
                {/if}
              </div>
              <span class="truncate font-mono">{term}</span>
            </div>
            <span class="text-[10px] opacity-60 font-mono text-[#746f65] dark:text-neutral-500">
               {currentFacets?.term?.[term] ?? globalFacets?.term?.[term] ?? 0}
            </span>
          </button>
        {/each}
      {/if}
    </div>
  </div>

  <!-- Department Filter -->
  <div class="space-y-2.5">
    <div class="font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider flex items-center justify-between">
      <span>Department</span>
      <span class="text-[#0080c9] dark:text-amber-400">{selectedDepts.length || ''}</span>
    </div>
    
    <div class="relative">
      <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#746f65]" size={12} />
      <input 
        type="text" 
        value={deptSearch}
        oninput={(e) => onDeptSearchChange(e.currentTarget.value)}
        placeholder="Filter departments..."
        class="w-full pl-8 pr-2 py-1.5 bg-[#eeece2] border border-[#dbd7cc] rounded-md text-xs outline-none focus:ring-1 focus:ring-[#c5a059] focus:border-[#c5a059] dark:bg-[#121214] dark:border-[#27272a] dark:text-neutral-200"
      />
    </div>

    <div class="space-y-1 max-h-60 overflow-y-auto pr-1 custom-scrollbar">
      {#each filteredDepts as dept}
        <button 
          onclick={() => onToggleDept(dept)}
          class="w-full flex items-center justify-between p-2 rounded-lg text-xs transition-colors cursor-pointer
          {selectedDepts.includes(dept) 
            ? 'bg-[#002d72]/10 text-[#002d72] font-semibold dark:bg-amber-400/10 dark:text-amber-300' 
            : 'text-[#45423b] dark:text-neutral-400 hover:bg-[#edeae0] dark:hover:bg-[#232328]'}"
        >
          <div class="flex items-center space-x-2">
            <div class="w-3.5 h-3.5 rounded border flex items-center justify-center transition-colors
              {selectedDepts.includes(dept) 
                ? 'bg-[#002d72] border-[#002d72] dark:bg-amber-400 dark:border-amber-400' 
                : 'bg-[#eeece2] border-[#c8c3b5] dark:bg-[#18181b] dark:border-[#3f3f46]'}">
              {#if selectedDepts.includes(dept)}
                <Check size={10} class="text-white dark:text-neutral-950 stroke-[3]" />
              {/if}
            </div>
            <span class="truncate font-mono">{dept}</span>
          </div>
          <span class="text-[10px] opacity-60 font-mono text-[#746f65] dark:text-neutral-500">
            {currentFacets?.dept_code?.[dept] ?? globalFacets?.dept_code?.[dept] ?? 0}
          </span>
        </button>
      {/each}
    </div>
  </div>
</div>
