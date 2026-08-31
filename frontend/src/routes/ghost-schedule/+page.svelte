<script lang="ts">
  import { onMount } from "svelte";
  import { Search, Filter, Check, Download } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import { exportToCSV } from "$lib/utils";
  import type { Term, GhostScheduleItem, FacetDistribution } from "$lib/types";

  let terms = $state<Term[]>([]);
  let globalFacets = $state<FacetDistribution>({});
  let selectedTerm = $state("");
  let selectedDepts = $state<string[]>([]);
  let deptSearch = $state("");
  let isDeptOpen = $state(false);
  let scheduleData = $state<GhostScheduleItem[]>([]);
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
      <h1 class="font-serif text-2xl sm:text-3xl font-bold text-[#1c1b18] dark:text-neutral-50 tracking-tight">Ghost Schedule</h1>
      <p class="font-sans text-xs sm:text-sm text-[#746f65] mt-1 dark:text-neutral-400">Historical campus classroom occupancy and timetable utilization matrix.</p>
    </div>

    <button 
        onclick={handleExport}
        disabled={scheduleData.length === 0}
        class="flex items-center justify-center space-x-2 bg-[#f7f5ee] border border-[#dbd7cc] text-[#45423b] px-4 py-2 rounded-lg text-xs font-semibold hover:bg-[#dedacb] transition-colors shadow-2xs dark:bg-[#18181b] dark:border-[#27272a] dark:text-neutral-300 dark:hover:bg-[#232328] disabled:opacity-40 cursor-pointer w-full sm:w-auto"
    >
      <Download size={13} />
      <span>Export Schedule CSV</span>
    </button>
  </div>

  <!-- Control Bar -->
  <div class="flex flex-col md:flex-row md:items-center gap-3 sm:gap-4 bg-[#f7f5ee] p-3 sm:p-4 rounded-xl border border-[#dbd7cc] shadow-2xs dark:bg-[#18181b] dark:border-[#27272a]">
    <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
      <div class="flex flex-col space-y-1">
        <label for="ghost-term-select" class="font-mono text-[9px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider px-1">Academic Term</label>
        <select 
          id="ghost-term-select"
          bind:value={selectedTerm} 
          onchange={fetchSchedule}
          class="w-full sm:min-w-[180px] p-2 bg-[#eeece2] border border-[#dbd7cc] rounded-lg text-xs sm:text-sm font-semibold text-[#1c1b18] outline-none focus:ring-1 focus:ring-[#c5a059] transition-colors dark:bg-[#121214] dark:border-[#27272a] dark:text-neutral-200 cursor-pointer font-mono"
        >
          {#each terms as term}
            <option value={term.id}>{term.id}</option>
          {/each}
        </select>
      </div>

      <div class="flex flex-col space-y-1 relative">
        <span class="font-mono text-[9px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider px-1">Department</span>
        
        <!-- Custom Searchable Multi-select -->
        <div class="relative">
          <button 
            onclick={() => isDeptOpen = !isDeptOpen}
            class="w-full sm:min-w-[180px] flex items-center justify-between p-2 bg-[#eeece2] border border-[#dbd7cc] rounded-lg text-xs font-semibold text-[#1c1b18] outline-none hover:border-[#c8c3b5] transition-colors dark:bg-[#121214] dark:border-[#27272a] dark:text-neutral-300 cursor-pointer font-mono"
          >
            <span class="truncate">
              {selectedDepts.length === 0 ? 'All Departments' : `${selectedDepts.length} Selected`}
            </span>
            <Filter size={12} class="text-[#746f65] ml-2 shrink-0" />
          </button>

          {#if isDeptOpen}
            <div class="absolute top-full left-0 mt-2 w-72 max-w-[90vw] bg-[#f7f5ee] border border-[#dbd7cc] rounded-xl shadow-xl z-50 overflow-hidden dark:bg-[#18181b] dark:border-[#27272a]">
              <div class="p-2.5 border-b border-[#dbd7cc] bg-[#e7e4d9]/50 dark:border-[#27272a] dark:bg-[#121214]">
                <div class="relative">
                  <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#746f65]" size={12} />
                  <input 
                    type="text" 
                    bind:value={deptSearch}
                    placeholder="Search departments..."
                    class="w-full pl-8 pr-2 py-1.5 bg-[#f7f5ee] border border-[#dbd7cc] rounded-md text-xs outline-none focus:ring-1 focus:ring-[#c5a059] dark:bg-[#121214] dark:border-[#27272a] dark:text-white"
                  />
                </div>
              </div>
              
              <div class="max-h-60 overflow-y-auto p-2 custom-scrollbar space-y-1">
                {#each filteredDepts as dept}
                  <button 
                    onclick={() => toggleDept(dept)}
                    class="w-full flex items-center justify-between p-1.5 rounded-md text-xs transition-colors cursor-pointer
                    {selectedDepts.includes(dept) 
                      ? 'bg-[#002d72]/10 text-[#002d72] font-semibold dark:bg-amber-400/10 dark:text-amber-300' 
                      : 'text-[#45423b] dark:text-neutral-400 hover:bg-[#edeae0] dark:hover:bg-[#232328]'}"
                  >
                    <div class="flex items-center space-x-2">
                      <div class="w-3.5 h-3.5 rounded border flex items-center justify-center
                        {selectedDepts.includes(dept) 
                          ? 'bg-[#002d72] border-[#002d72] dark:bg-amber-400 dark:border-amber-400' 
                          : 'bg-[#eeece2] border-[#c8c3b5] dark:bg-[#18181b] dark:border-[#3f3f46]'}">
                        {#if selectedDepts.includes(dept)}
                          <Check size={10} class="text-white dark:text-neutral-950 stroke-[3]" />
                        {/if}
                      </div>
                      <span class="font-mono">{dept}</span>
                    </div>
                  </button>
                {/each}
              </div>

              {#if selectedDepts.length > 0}
                <div class="p-2 border-t border-[#dbd7cc] bg-[#e7e4d9]/40 dark:border-[#27272a] dark:bg-[#121214]">
                  <button 
                    onclick={() => { selectedDepts = []; isDeptOpen = false; fetchSchedule(); }}
                    class="w-full py-1.5 font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-400 uppercase tracking-wider hover:bg-[#dedacb] dark:hover:bg-[#232328] rounded transition-colors cursor-pointer"
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
      <span class="font-mono text-[9px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider px-1">Active Day</span>
      <div class="flex bg-[#dedacb] p-1 rounded-lg border border-[#c8c3b5]/60 dark:bg-[#121214] dark:border-[#27272a] overflow-x-auto no-scrollbar font-mono">
        {#each days as day}
          <button 
            onclick={() => activeDay = day}
            class="px-3 sm:px-3.5 py-1 rounded text-xs font-semibold transition-colors shrink-0 cursor-pointer
            {activeDay === day 
              ? 'bg-[#f7f5ee] text-[#1c1b18] dark:bg-[#27272a] dark:text-neutral-100 shadow-2xs font-bold' 
              : 'text-[#5c5850] hover:text-[#1c1b18] dark:text-neutral-400 dark:hover:text-neutral-200'}"
          >
            {day}
          </button>
        {/each}
      </div>
    </div>

    <div class="md:ml-auto flex items-center space-x-4 pt-1 md:pt-0 font-mono text-[10px]">
      <div class="flex items-center space-x-1.5">
        <div class="w-2.5 h-2.5 bg-[#002d72]/15 border border-[#002d72]/30 rounded dark:bg-amber-400/20 dark:border-amber-400/40"></div>
        <span class="text-[#746f65] dark:text-neutral-400 uppercase tracking-wider">Occupied</span>
      </div>
      <div class="flex items-center space-x-1.5">
        <div class="w-2.5 h-2.5 bg-[#eeece2] border border-[#dbd7cc] rounded dark:bg-[#121214] dark:border-[#27272a]"></div>
        <span class="text-[#746f65] dark:text-neutral-400 uppercase tracking-wider">Available</span>
      </div>
    </div>
  </div>

  {#if loading}
    <div class="flex justify-center py-20">
      <div class="animate-spin rounded-full h-8 w-8 border-3 border-[#dbd7cc] border-t-[#002d72] dark:border-neutral-800 dark:border-t-amber-400"></div>
    </div>
  {:else}
    <!-- Matrix View with Sticky Room Header -->
    <div class="bg-[#f7f5ee] rounded-xl border border-[#dbd7cc] shadow-2xs overflow-hidden dark:bg-[#18181b] dark:border-[#27272a]">
      <div class="overflow-x-auto custom-scrollbar">
        <table class="w-full border-collapse min-w-[900px]">
          <thead>
            <tr class="bg-[#e7e4d9]/90 border-b border-[#dbd7cc] dark:bg-[#121214] dark:border-[#27272a] sticky top-0 z-20">
              <th class="p-3 text-left font-mono text-[11px] font-bold text-[#746f65] dark:text-neutral-500 uppercase border-r border-[#dbd7cc] dark:border-[#27272a] w-36 sm:w-48 sticky left-0 z-30 bg-[#e7e4d9] dark:bg-[#121214] shadow-2xs">Room / Hour</th>
              {#each hours as hour}
                <th class="p-3 text-center font-mono text-[11px] font-bold text-[#746f65] dark:text-neutral-500 uppercase min-w-[70px] sm:min-w-[90px]">{hour}</th>
              {/each}
            </tr>
          </thead>
          <tbody>
            <!-- Show all rooms in the matrix -->
            {#each uniqueRooms as room}
              <tr class="border-b border-[#dbd7cc]/70 hover:bg-[#edeae0] transition-colors dark:border-[#27272a] dark:hover:bg-[#232328]">
                <td class="p-3 text-xs font-mono font-bold text-[#1c1b18] dark:text-neutral-300 border-r border-[#dbd7cc] dark:border-[#27272a] bg-[#e7e4d9]/80 dark:bg-[#121214] sticky left-0 z-10 truncate max-w-[140px] sm:max-w-none shadow-2xs">{room}</td>
                {#each hours as hour}
                  {@const slot = slotMap.get(`${room}|${hour}`)}
                  <td class="p-1 text-center h-14 sm:h-16">
                    {#if slot}
                      <div class="h-full w-full bg-[#002d72]/10 border border-[#002d72]/20 rounded-lg p-1 flex flex-col justify-center items-center shadow-2xs dark:bg-amber-400/10 dark:border-amber-400/20">
                        <span class="font-mono text-[9px] sm:text-[10px] font-bold text-[#002d72] dark:text-amber-300 leading-tight truncate max-w-[75px]">{slot.course_code}</span>
                        <span class="font-mono text-[7px] sm:text-[8px] text-[#0080c9] dark:text-neutral-400 uppercase font-semibold">{slot.dept_kisaadi}</span>
                      </div>
                    {:else}
                      <div class="h-full w-full bg-[#eeece2]/40 dark:bg-[#121214]/40 rounded-lg border border-transparent"></div>
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
