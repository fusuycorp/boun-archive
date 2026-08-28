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

  let filteredDepts = $derived(
    globalFacets.dept_code 
      ? Object.keys(globalFacets.dept_code)
          .sort()
          .filter(d => d.toLowerCase().includes(deptSearch.toLowerCase()))
      : []
  );
</script>

<div class="space-y-6">
  <!-- Term Filter -->
  <div class="space-y-3">
    <div class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center justify-between">
      <span>Academic Term</span>
      <span class="text-[#0080c9] dark:text-sky-400 font-mono">{selectedTerms.length || ''}</span>
    </div>
    <div class="space-y-1 max-h-48 overflow-y-auto pr-1 custom-scrollbar">
      {#if globalFacets.term}
        {#each Object.keys(globalFacets.term).sort().reverse() as term}
          <button 
            onclick={() => onToggleTerm(term)}
            class="w-full flex items-center justify-between p-2 rounded-lg text-xs sm:text-sm transition-all cursor-pointer
            {selectedTerms.includes(term) 
              ? 'bg-[#002d72]/10 text-[#002d72] font-bold dark:bg-sky-500/15 dark:text-sky-300' 
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/40'}"
          >
            <div class="flex items-center space-x-2">
              <div class="w-4 h-4 rounded border flex items-center justify-center transition-colors
                {selectedTerms.includes(term) 
                  ? 'bg-[#002d72] border-[#002d72] dark:bg-sky-500 dark:border-sky-500' 
                  : 'bg-white border-slate-300 dark:bg-slate-800 dark:border-slate-700'}">
                {#if selectedTerms.includes(term)}
                  <Check size={12} class="text-white" />
                {/if}
              </div>
              <span class="truncate">{term}</span>
            </div>
            <span class="text-[10px] opacity-50 font-mono">
               {currentFacets.term?.[term] ?? 0}
            </span>
          </button>
        {/each}
      {/if}
    </div>
  </div>

  <!-- Department Filter -->
  <div class="space-y-3">
    <div class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center justify-between">
      <span>Department</span>
      <span class="text-[#0080c9] dark:text-sky-400 font-mono">{selectedDepts.length || ''}</span>
    </div>
    
    <div class="relative">
      <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" size={12} />
      <input 
        type="text" 
        value={deptSearch}
        oninput={(e) => onDeptSearchChange(e.currentTarget.value)}
        placeholder="Filter departments..."
        class="w-full pl-8 pr-2 py-1.5 bg-slate-50 border border-slate-200/80 rounded-md text-xs outline-none focus:ring-1 focus:ring-[#0080c9] focus:border-[#0080c9] dark:bg-slate-950 dark:border-slate-800 dark:text-slate-200"
      />
    </div>

    <div class="space-y-1 max-h-60 overflow-y-auto pr-1 custom-scrollbar">
      {#each filteredDepts as dept}
        <button 
          onclick={() => onToggleDept(dept)}
          class="w-full flex items-center justify-between p-2 rounded-lg text-xs sm:text-sm transition-all cursor-pointer
          {selectedDepts.includes(dept) 
            ? 'bg-[#002d72]/10 text-[#002d72] font-bold dark:bg-sky-500/15 dark:text-sky-300' 
            : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/40'}"
        >
          <div class="flex items-center space-x-2">
            <div class="w-4 h-4 rounded border flex items-center justify-center transition-colors
              {selectedDepts.includes(dept) 
                ? 'bg-[#002d72] border-[#002d72] dark:bg-sky-500 dark:border-sky-500' 
                : 'bg-white border-slate-300 dark:bg-slate-800 dark:border-slate-700'}">
              {#if selectedDepts.includes(dept)}
                <Check size={12} class="text-white" />
              {/if}
            </div>
            <span class="truncate">{dept}</span>
          </div>
          <span class="text-[10px] opacity-50 font-mono">
            {currentFacets.dept_code?.[dept] ?? 0}
          </span>
        </button>
      {/each}
    </div>
  </div>
</div>
