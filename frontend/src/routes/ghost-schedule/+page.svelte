<script lang="ts">
  import { onMount } from "svelte";
  import { Search, Filter, Check, Download } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import { exportToCSV } from "$lib/utils";

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
  let slotMap = $derived(new Map(filteredSchedule.map(s => [`${s.room_name}|${s.slot_hour}`, s])));
  let uniqueRooms = $derived(Array.from(new Set(filteredSchedule.map(s => s.room_name))).sort());

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
      const [termsRes, facetsRes] = await Promise.allSettled([
        fetch(`${API_BASE}/v1/terms`),
        fetch(`${API_BASE}/v1/facets`)
      ]);
      if (termsRes.status === "fulfilled" && termsRes.value.ok) {
        terms = await termsRes.value.json();
      }
      if (facetsRes.status === "fulfilled" && facetsRes.value.ok) {
        globalFacets = await facetsRes.value.json();
      }
      
      if (terms.length > 0 && !selectedTerm) {
        selectedTerm = terms[0].id;
        fetchSchedule();
      }
    } catch (e) {
      console.error("Failed to load ghost schedule initial data", e);
    }
  }

  async function fetchSchedule() {
    if (!selectedTerm) return;
    loading = true;
    try {
      const params = new URLSearchParams();
      selectedDepts.forEach(d => params.append("dept", d));
      
      const res = await fetch(`${API_BASE}/v1/analytics/ghost-schedule/${selectedTerm}?${params.toString()}`);
      if (res.ok) {
        scheduleData = await res.json();
      }
    } catch (e) {
      console.error("Failed to fetch ghost schedule", e);
    } finally {
      loading = false;
    }
  }

  function handleExport() {
    if (scheduleData.length === 0) return;
    
    const exportData = scheduleData.map(s => ({
      term: selectedTerm,
      day: s.day_code,
      hour: s.slot_hour,
      room: s.room_name,
      course_code: s.course_code,
      department: s.dept_kisaadi
    }));
    
    exportToCSV(exportData, `boun_ghost_schedule_${selectedTerm}_${new Date().toISOString().split('T')[0]}`);
  }

  onMount(fetchInitialData);
</script>

<div class="space-y-4 sm:space-y-6">
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
    <div>
      <h2 class="text-2xl sm:text-3xl font-black text-slate-800 dark:text-slate-100 tracking-tight">Ghost Schedule</h2>
      <p class="text-xs sm:text-sm text-slate-500 mt-1 dark:text-slate-400">Historical campus reconstruction and classroom utilization matrix.</p>
    </div>

    <button 
        onclick={handleExport}
        disabled={scheduleData.length === 0}
        class="flex items-center justify-center space-x-2 bg-white border border-slate-200 text-slate-600 px-4 py-2 rounded-xl text-xs font-bold hover:bg-slate-50 transition-colors shadow-xs dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700 disabled:opacity-50 cursor-pointer w-full sm:w-auto"
    >
      <Download size={14} />
      <span>Export Schedule CSV</span>
    </button>
  </div>

  <!-- Control Bar -->
  <div class="flex flex-col md:flex-row md:items-center gap-3 sm:gap-4 bg-white p-3 sm:p-4 rounded-2xl border border-slate-200/80 shadow-2xs dark:bg-[#0f172a] dark:border-slate-800/80">
    <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
      <div class="flex flex-col space-y-1">
        <label for="ghost-term-select" class="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest px-1">Academic Term</label>
        <select 
          id="ghost-term-select"
          bind:value={selectedTerm} 
          onchange={fetchSchedule}
          class="w-full sm:min-w-[180px] p-2 bg-slate-50 border border-slate-200/80 rounded-xl text-xs sm:text-sm font-bold text-slate-700 outline-none focus:ring-2 focus:ring-[#0080c9] transition-all dark:bg-slate-950 dark:border-slate-800 dark:text-slate-200 cursor-pointer"
        >
          {#each terms as term}
            <option value={term.id}>{term.id}</option>
          {/each}
        </select>
      </div>

      <div class="flex flex-col space-y-1 relative">
        <span class="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest px-1">Department</span>
        
        <!-- Custom Searchable Multi-select -->
        <div class="relative">
          <button 
            onclick={() => isDeptOpen = !isDeptOpen}
            class="w-full sm:min-w-[180px] flex items-center justify-between p-2 bg-slate-50 border border-slate-200/80 rounded-xl text-xs font-bold text-slate-700 outline-none hover:border-[#0080c9] transition-all dark:bg-slate-950 dark:border-slate-800 dark:text-slate-300 cursor-pointer"
          >
            <span class="truncate">
              {selectedDepts.length === 0 ? 'All Departments' : `${selectedDepts.length} Selected`}
            </span>
            <Filter size={13} class="text-slate-400 ml-2 shrink-0" />
          </button>

          {#if isDeptOpen}
            <div class="absolute top-full left-0 mt-2 w-72 max-w-[90vw] bg-white border border-slate-200/80 rounded-2xl shadow-xl z-50 overflow-hidden dark:bg-[#0f172a] dark:border-slate-800/80">
              <div class="p-3 border-b border-slate-100 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-950/50">
                <div class="relative">
                  <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" size={12} />
                  <input 
                    type="text" 
                    bind:value={deptSearch}
                    placeholder="Search departments..."
                    class="w-full pl-8 pr-2 py-1.5 bg-white border border-slate-200/80 rounded-lg text-xs outline-none focus:ring-2 focus:ring-[#0080c9] dark:bg-slate-950 dark:border-slate-800 dark:text-white"
                  />
                </div>
              </div>
              
              <div class="max-h-60 overflow-y-auto p-2 custom-scrollbar space-y-1">
                {#each filteredDepts as dept}
                  <button 
                    onclick={() => toggleDept(dept)}
                    class="w-full flex items-center justify-between p-2 rounded-lg text-xs transition-all cursor-pointer
                    {selectedDepts.includes(dept) 
                      ? 'bg-[#002d72]/10 text-[#002d72] font-bold dark:bg-sky-500/15 dark:text-sky-300' 
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/40'}"
                  >
                    <div class="flex items-center space-x-2">
                      <div class="w-3.5 h-3.5 rounded border flex items-center justify-center
                        {selectedDepts.includes(dept) 
                          ? 'bg-[#002d72] border-[#002d72] dark:bg-sky-500 dark:border-sky-500' 
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
                <div class="p-2 border-t border-slate-100 bg-slate-50/30 dark:border-slate-800 dark:bg-slate-950/30">
                  <button 
                    onclick={() => { selectedDepts = []; isDeptOpen = false; fetchSchedule(); }}
                    class="w-full py-1.5 text-[10px] font-black text-[#002d72] dark:text-sky-400 uppercase tracking-widest hover:bg-slate-50 dark:hover:bg-slate-800 rounded-lg transition-all cursor-pointer"
                  >
                    Clear Selection
                  </button>
                </div>
              {/if}
            </div>
          {/if}
        </div>
      </div>
    </div>

    <div class="flex flex-col space-y-1">
      <span class="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest px-1">Active Day</span>
      <div class="flex bg-slate-50 p-1 rounded-xl border border-slate-100 dark:bg-slate-950 dark:border-slate-800 overflow-x-auto no-scrollbar">
        {#each days as day}
          <button 
            onclick={() => activeDay = day}
            class="px-3.5 sm:px-4 py-1.5 rounded-lg text-xs font-bold transition-all shrink-0 cursor-pointer
            {activeDay === day 
              ? 'bg-[#002d72] text-white shadow-2xs' 
              : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300'}"
          >
            {day}
          </button>
        {/each}
      </div>
    </div>

    <div class="md:ml-auto flex items-center space-x-4 pt-1 md:pt-0">
      <div class="flex items-center space-x-1.5">
        <div class="w-2.5 h-2.5 bg-[#002d72]/15 border border-[#002d72]/30 rounded dark:bg-sky-500/20 dark:border-sky-500/40"></div>
        <span class="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Occupied</span>
      </div>
      <div class="flex items-center space-x-1.5">
        <div class="w-2.5 h-2.5 bg-slate-50 border border-slate-200 rounded dark:bg-slate-900/30 dark:border-slate-800"></div>
        <span class="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Available</span>
      </div>
    </div>
  </div>

  {#if loading}
    <div class="flex justify-center py-20">
      <div class="animate-spin rounded-full h-10 w-10 border-4 border-slate-100 border-t-[#002d72] dark:border-slate-800 dark:border-t-sky-400"></div>
    </div>
  {:else}
    <!-- Matrix View with Sticky Room Header -->
    <div class="bg-white rounded-2xl border border-slate-200/80 shadow-2xs overflow-hidden dark:bg-[#0f172a] dark:border-slate-800/80">
      <div class="overflow-x-auto custom-scrollbar">
        <table class="w-full border-collapse min-w-[900px]">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 dark:bg-slate-950 dark:border-slate-800 sticky top-0 z-20">
              <th class="p-3 sm:p-4 text-left text-xs font-bold text-slate-400 dark:text-slate-500 uppercase border-r border-slate-200 dark:border-slate-800 w-36 sm:w-48 sticky left-0 z-30 bg-slate-50 dark:bg-slate-950 shadow-2xs">Room / Hour</th>
              {#each hours as hour}
                <th class="p-3 text-center text-xs font-bold text-slate-400 dark:text-slate-500 uppercase min-w-[70px] sm:min-w-[90px]">{hour}</th>
              {/each}
            </tr>
          </thead>
          <tbody>
            <!-- Show all rooms in the matrix -->
            {#each uniqueRooms as room}
              <tr class="border-b border-slate-100 hover:bg-slate-50/80 transition-colors dark:border-slate-800/60 dark:hover:bg-slate-850/30">
                <td class="p-3 sm:p-4 text-xs sm:text-sm font-bold text-slate-700 dark:text-slate-300 border-r border-slate-200 dark:border-slate-800 bg-slate-50/95 dark:bg-slate-950/95 sticky left-0 z-10 truncate max-w-[140px] sm:max-w-none shadow-2xs">{room}</td>
                {#each hours as hour}
                  {@const slot = slotMap.get(`${room}|${hour}`)}
                  <td class="p-1 text-center h-14 sm:h-16">
                    {#if slot}
                      <div class="h-full w-full bg-[#002d72]/10 border border-[#002d72]/20 rounded-lg p-1 flex flex-col justify-center items-center shadow-2xs dark:bg-sky-500/15 dark:border-sky-500/30">
                        <span class="text-[9px] sm:text-[10px] font-black text-[#002d72] dark:text-sky-300 leading-tight truncate max-w-[75px]">{slot.course_code}</span>
                        <span class="text-[7px] sm:text-[8px] text-[#0080c9] dark:text-sky-400 font-bold uppercase">{slot.dept_kisaadi}</span>
                      </div>
                    {:else}
                      <div class="h-full w-full bg-slate-50/30 dark:bg-slate-950/10 rounded-lg border border-transparent"></div>
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
