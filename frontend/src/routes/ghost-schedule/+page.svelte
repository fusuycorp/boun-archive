<script lang="ts">
  import { onMount } from "svelte";
  import { Calendar, Layers, Map, ChevronLeft, ChevronRight, Search, Filter, Check, X } from "lucide-svelte";

  let terms = $state<any[]>([]);
  let globalFacets = $state<any>({});
  let selectedTerm = $state("");
  let selectedDepts = $state<string[]>([]);
  let deptSearch = $state("");
  let isDeptOpen = $state(false);
  let scheduleData = $state<any[]>([]);
  let loading = $state(false);
  let days = ["M", "T", "W", "Th", "F", "St", "Su"];
  let hours = Array.from({ length: 14 }, (_, i) => i + 1);

  // Grouped data for visualization
  let activeDay = $state("M");
  let filteredSchedule = $derived(scheduleData.filter(s => s.day_code === activeDay));

  const filteredDepts = $derived(
    globalFacets.dept_code 
      ? Object.keys(globalFacets.dept_code)
          .sort()
          .filter(d => d.toLowerCase().includes(deptSearch.toLowerCase()))
      : []
  );

  function toggleDept(dept: string) {
    if (selectedDepts.includes(dept)) {
      selectedDepts = selectedDepts.filter(d => d !== dept);
    } else {
      selectedDepts = [...selectedDepts, dept];
    }
    fetchSchedule();
  }

  async function fetchInitialData() {
    try {
      const [termsRes, facetsRes] = await Promise.all([
        fetch("http://localhost:8000/api/v1/terms"),
        fetch("http://localhost:8000/api/v1/facets")
      ]);
      terms = await termsRes.json();
      globalFacets = await facetsRes.json();
      
      if (terms.length > 0) {
        selectedTerm = terms[0].id;
        fetchSchedule();
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function fetchSchedule() {
    if (!selectedTerm) return;
    loading = true;
    try {
      const params = new URLSearchParams();
      selectedDepts.forEach(d => params.append("dept", d));
      
      const res = await fetch(`http://localhost:8000/api/v1/analytics/ghost-schedule/${selectedTerm}?${params.toString()}`);
      scheduleData = await res.json();
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  }

  onMount(fetchInitialData);
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-3xl font-bold text-slate-800 dark:text-slate-100">Ghost Schedule</h2>
    <p class="text-slate-500 mt-2 dark:text-slate-400">Historical campus reconstruction and building utilization.</p>
  </div>

  <!-- Control Bar -->
  <div class="flex flex-wrap items-center gap-4 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm dark:bg-slate-900 dark:border-slate-800">
    <div class="flex flex-col space-y-1">
      <label class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest px-1">Academic Term</label>
      <select 
        bind:value={selectedTerm} 
        onchange={fetchSchedule}
        class="min-w-[200px] p-2 bg-slate-50 border border-slate-100 rounded-xl text-sm font-bold text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500 transition-all dark:bg-slate-950 dark:border-slate-800 dark:text-slate-200"
      >
        {#each terms as term}
          <option value={term.id}>{term.id}</option>
        {/each}
      </select>
    </div>

    <div class="h-10 w-px bg-slate-100 dark:bg-slate-800 mx-2 hidden md:block"></div>

    <div class="flex flex-col space-y-1">
      <label class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest px-1">Active Day</label>
      <div class="flex bg-slate-50 p-1 rounded-xl border border-slate-100 dark:bg-slate-950 dark:border-slate-800">
        {#each days as day}
          <button 
            onclick={() => activeDay = day}
            class="px-5 py-1.5 rounded-lg text-xs font-bold transition-all
            {activeDay === day 
              ? 'bg-indigo-600 text-white shadow-md' 
              : 'text-slate-500 hover:text-slate-600 dark:text-slate-400 dark:hover:text-slate-350'}"
          >
            {day}
          </button>
        {/each}
      </div>
    </div>

    <div class="h-10 w-px bg-slate-100 dark:bg-slate-800 mx-2 hidden md:block"></div>

    <div class="flex flex-col space-y-1 relative">
      <label class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest px-1">Department Filter</label>
      
      <!-- Custom Searchable Multi-select -->
      <div class="relative">
        <button 
          onclick={() => isDeptOpen = !isDeptOpen}
          class="min-w-[200px] flex items-center justify-between p-2 bg-slate-50 border border-slate-100 rounded-xl text-xs font-bold text-slate-700 outline-none hover:border-indigo-300 transition-all dark:bg-slate-950 dark:border-slate-800 dark:text-slate-300 dark:hover:border-slate-700"
        >
          <span class="truncate">
            {selectedDepts.length === 0 ? 'All Departments' : `${selectedDepts.length} Selected`}
          </span>
          <Filter size={14} class="text-slate-400" />
        </button>

        {#if isDeptOpen}
          <div class="absolute top-full left-0 mt-2 w-64 bg-white border border-slate-200 rounded-2xl shadow-xl z-50 overflow-hidden dark:bg-slate-900 dark:border-slate-800">
            <div class="p-3 border-b border-slate-50 bg-slate-50/50 dark:border-slate-850 dark:bg-slate-950/50">
              <div class="relative">
                <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" size={12} />
                <input 
                  type="text" 
                  bind:value={deptSearch}
                  placeholder="Search departments..."
                  class="w-full pl-8 pr-2 py-1.5 bg-white border border-slate-200 rounded-lg text-xs outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-slate-950 dark:border-slate-800 dark:text-white"
                />
              </div>
            </div>
            
            <div class="max-h-60 overflow-y-auto p-2 custom-scrollbar space-y-1">
              {#each filteredDepts as dept}
                <button 
                  onclick={() => toggleDept(dept)}
                  class="w-full flex items-center justify-between p-2 rounded-lg text-xs transition-all
                  {selectedDepts.includes(dept) 
                    ? 'bg-indigo-50 text-indigo-700 font-bold dark:bg-indigo-950/40 dark:text-indigo-400' 
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/40'}"
                >
                  <div class="flex items-center space-x-2">
                    <div class="w-3.5 h-3.5 rounded border flex items-center justify-center
                      {selectedDepts.includes(dept) 
                        ? 'bg-indigo-600 border-indigo-600 dark:bg-indigo-500 dark:border-indigo-500' 
                        : 'bg-white border-slate-300 dark:bg-slate-800 dark:border-slate-700'}">
                      {#if selectedDepts.includes(dept)}
                        <Check size={10} class="text-white" />
                      {/if}
                    </div>
                    <span>{dept}</span>
                  </div>
                </button>
              {/each}
            </div>

            {#if selectedDepts.length > 0}
              <div class="p-2 border-t border-slate-50 bg-slate-50/30 dark:border-slate-800 dark:bg-slate-950/30">
                <button 
                  onclick={() => { selectedDepts = []; isDeptOpen = false; fetchSchedule(); }}
                  class="w-full py-1.5 text-[10px] font-black text-indigo-600 dark:text-indigo-400 uppercase tracking-widest hover:bg-white dark:hover:bg-slate-800 rounded-lg transition-all"
                >
                  Clear Selection
                </button>
              </div>
            {/if}
          </div>
        {/if}
      </div>
    </div>

    <div class="ml-auto hidden lg:flex items-center space-x-6 px-4">
      <div class="flex items-center space-x-2">
        <div class="w-3 h-3 bg-indigo-100 border border-indigo-200 rounded dark:bg-indigo-950/40 dark:border-indigo-900/50"></div>
        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Occupied</span>
      </div>
      <div class="flex items-center space-x-2">
        <div class="w-3 h-3 bg-slate-50 border border-slate-100 rounded dark:bg-slate-900/30 dark:border-slate-800"></div>
        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Available</span>
      </div>
    </div>
  </div>

  {#if loading}
    <div class="flex justify-center py-24">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 dark:border-indigo-500"></div>
    </div>
  {:else}
    <!-- Matrix View -->
    <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden dark:bg-slate-900 dark:border-slate-800">
      <div class="overflow-x-auto">
        <table class="w-full border-collapse">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 dark:bg-slate-950 dark:border-slate-800">
              <th class="p-4 text-left text-xs font-bold text-slate-400 dark:text-slate-500 uppercase border-r border-slate-200 dark:border-slate-800 w-48">Room / Hour</th>
              {#each hours as hour}
                <th class="p-4 text-center text-xs font-bold text-slate-400 dark:text-slate-500 uppercase min-w-[100px]">{hour}</th>
              {/each}
            </tr>
          </thead>
          <tbody>
            <!-- We'll show a subset of rooms for performance/demo -->
            {#each Array.from(new Set(filteredSchedule.map(s => s.room_name))).sort().slice(0, 50) as room}
              <tr class="border-b border-slate-100 hover:bg-slate-50 transition-colors dark:border-slate-800/60 dark:hover:bg-slate-850/30">
                <td class="p-4 text-sm font-bold text-slate-700 dark:text-slate-300 border-r border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/20">{room}</td>
                {#each hours as hour}
                  {@const slot = filteredSchedule.find(s => s.room_name === room && s.slot_hour === hour)}
                  <td class="p-1 text-center h-16">
                    {#if slot}
                      <div class="h-full w-full bg-indigo-100 border border-indigo-200 rounded p-1 flex flex-col justify-center items-center shadow-sm dark:bg-indigo-950/40 dark:border-indigo-900/50">
                        <span class="text-[10px] font-black text-indigo-700 dark:text-indigo-300 leading-tight">{slot.course_code}</span>
                        <span class="text-[8px] text-indigo-500 dark:text-indigo-400 font-bold uppercase">{slot.dept_kisaadi}</span>
                      </div>
                    {:else}
                      <div class="h-full w-full bg-slate-50/30 dark:bg-slate-950/10 rounded border border-transparent"></div>
                    {/if}
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</div>

<style>
  .custom-scrollbar::-webkit-scrollbar {
    width: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: #e2e8f0;
    border-radius: 10px;
  }
  :global(.dark) .custom-scrollbar::-webkit-scrollbar-thumb {
    background: #334155;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: #cbd5e1;
  }
  :global(.dark) .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: #475569;
  }
</style>
