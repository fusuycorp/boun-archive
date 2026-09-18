<script lang="ts">
  import { onMount } from "svelte";
  import { Search, Filter, Check, Download, Building2, AlertTriangle, MapPin } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import { exportToCSV } from "$lib/utils";
  import { resolveRoomLocation } from "$lib/campus";
  import type { Term, GhostScheduleItem, FacetDistribution } from "$lib/types";

  let terms = $state<Term[]>([]);
  let globalFacets = $state<FacetDistribution>({});
  let selectedTerm = $state("");
  let selectedDepts = $state<string[]>([]);
  let deptSearch = $state("");
  let isDeptOpen = $state(false);
  let selectedCampus = $state("");
  let selectedBuilding = $state("");
  let showOnlyConflicts = $state(false);
  let scheduleData = $state<GhostScheduleItem[]>([]);
  let loading = $state(false);
  let days = ["M", "T", "W", "Th", "F", "St", "Su"];
  let hours = Array.from({ length: 14 }, (_, i) => i + 1);

  // Active Day
  let activeDay = $state("M");
  let filteredSchedule = $derived(scheduleData.filter(s => s.day_code === activeDay));

  // Multi-slot collision mapping: key = "room_name|slot_hour" -> GhostScheduleItem[]
  let slotMap = $derived.by(() => {
    const map = new Map<string, GhostScheduleItem[]>();
    for (const s of filteredSchedule) {
      const key = `${s.room_name}|${s.slot_hour}`;
      const list = map.get(key);
      if (list) {
        list.push(s);
      } else {
        map.set(key, [s]);
      }
    }
    return map;
  });

  // Room to Location (Building & Campus) mapping
  let roomLocationMap = $derived.by(() => {
    const map = new Map<string, { building: string; campus: string }>();
    for (const s of scheduleData) {
      if (!map.has(s.room_name)) {
        const loc = resolveRoomLocation(s.room_name, s.building);
        map.set(s.room_name, {
          building: s.building || loc.building,
          campus: s.campus || loc.campus
        });
      }
    }
    return map;
  });

  // Conflict metrics for the active day
  let conflictEntries = $derived(
    Array.from(slotMap.entries()).filter(([_, slots]) => slots.length > 1)
  );
  let conflictCount = $derived(conflictEntries.length);
  let conflictRoomNames = $derived(new Set(conflictEntries.map(([key]) => key.split("|")[0])));

  // Available unique campuses with room counts
  let availableCampuses = $derived.by(() => {
    const cMap = new Map<string, Set<string>>();
    for (const s of scheduleData) {
      const loc = roomLocationMap.get(s.room_name) || resolveRoomLocation(s.room_name, s.building);
      if (!cMap.has(loc.campus)) cMap.set(loc.campus, new Set());
      cMap.get(loc.campus)!.add(s.room_name);
    }
    return Array.from(cMap.entries())
      .map(([name, set]) => ({ name, count: set.size }))
      .sort((a, b) => a.name.localeCompare(b.name));
  });

  // Available unique buildings (filtered by selectedCampus if active)
  let availableBuildings = $derived.by(() => {
    const bCountMap = new Map<string, Set<string>>();
    for (const s of scheduleData) {
      const loc = roomLocationMap.get(s.room_name) || resolveRoomLocation(s.room_name, s.building);
      if (selectedCampus && loc.campus !== selectedCampus) continue;
      if (!bCountMap.has(loc.building)) bCountMap.set(loc.building, new Set());
      bCountMap.get(loc.building)!.add(s.room_name);
    }
    return Array.from(bCountMap.entries())
      .map(([name, roomSet]) => ({ name, count: roomSet.size }))
      .sort((a, b) => a.name.localeCompare(b.name));
  });

  // Building Groups for rendering in the 2D matrix
  interface BuildingGroup {
    building: string;
    campus: string;
    rooms: string[];
  }
  let buildingGroups = $derived.by(() => {
    const activeRooms = Array.from(new Set(filteredSchedule.map(s => s.room_name)));
    const bMap = new Map<string, { campus: string; rooms: string[] }>();

    for (const room of activeRooms) {
      if (showOnlyConflicts && !conflictRoomNames.has(room)) {
        continue;
      }
      const loc = roomLocationMap.get(room) || resolveRoomLocation(room);
      if (selectedCampus && loc.campus !== selectedCampus) {
        continue;
      }
      if (selectedBuilding && loc.building !== selectedBuilding) {
        continue;
      }
      if (!bMap.has(loc.building)) {
        bMap.set(loc.building, { campus: loc.campus, rooms: [] });
      }
      bMap.get(loc.building)!.rooms.push(room);
    }

    const groups: BuildingGroup[] = [];
    for (const [building, data] of bMap.entries()) {
      data.rooms.sort();
      groups.push({ building, campus: data.campus, rooms: data.rooms });
    }
    groups.sort((a, b) => a.building.localeCompare(b.building));
    return groups;
  });

  let totalVisibleRooms = $derived(buildingGroups.reduce((sum, g) => sum + g.rooms.length, 0));

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
    
    const exportData = scheduleData.map(s => {
      const slots = slotMap.get(`${s.room_name}|${s.slot_hour}`);
      const isConflict = slots && slots.length > 1;
      const loc = roomLocationMap.get(s.room_name) || resolveRoomLocation(s.room_name, s.building);
      return {
        term: selectedTerm,
        campus: loc.campus,
        building: loc.building,
        room: s.room_name,
        day: s.day_code,
        hour: s.slot_hour,
        course_code: s.course_code,
        department: s.dept_kisaadi,
        is_conflict: isConflict ? "YES" : "NO",
        simultaneous_courses: isConflict ? slots.map(c => c.course_code).join("; ") : ""
      };
    });
    
    exportToCSV(exportData, `boun_ghost_schedule_${selectedTerm.replace('/', '-')}_${new Date().toISOString().split('T')[0]}`);
  }

  onMount(fetchInitialData);
</script>

<div class="space-y-4 sm:space-y-6">
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
    <div>
      <h1 class="font-serif text-2xl sm:text-3xl font-bold text-[#002d72] dark:text-slate-50 tracking-tight">Ghost Schedule</h1>
      <p class="font-sans text-xs sm:text-sm text-[#525f7f] mt-1 dark:text-slate-400">Historical campus classroom occupancy, room collisions, and building timetable utilization matrix.</p>
    </div>

    <button 
        onclick={handleExport}
        disabled={scheduleData.length === 0}
        class="flex items-center justify-center space-x-2 bg-white border border-[#e5e0d8] text-[#161e2e] px-4 py-2 rounded-lg text-xs font-semibold hover:bg-[#f3efe6] transition-colors shadow-2xs dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700 disabled:opacity-40 cursor-pointer w-full sm:w-auto"
    >
      <Download size={13} />
      <span>Export Schedule CSV</span>
    </button>
  </div>

  <!-- Control Bar -->
  <div class="flex flex-col gap-3 sm:gap-4 bg-white p-3 sm:p-4 rounded-xl border border-[#e5e0d8] shadow-2xs dark:bg-[#121827] dark:border-[#1e293b]">
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 flex-wrap">
      <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 flex-wrap">
        <!-- Term Selector -->
        <div class="flex flex-col space-y-1">
          <label for="ghost-term-select" class="font-mono text-[9px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider px-1">Academic Term</label>
          <select 
            id="ghost-term-select"
            bind:value={selectedTerm} 
            onchange={fetchSchedule}
            class="w-full sm:min-w-[150px] p-2 bg-[#faf8f5] border border-[#e5e0d8] rounded-lg text-xs sm:text-sm font-semibold text-[#161e2e] outline-none focus:ring-1 focus:ring-[#002d72] transition-colors dark:bg-[#0a0e1a] dark:border-[#1e293b] dark:text-slate-200 cursor-pointer font-mono"
          >
            {#each terms as term}
              <option value={term.id}>{term.id}</option>
            {/each}
          </select>
        </div>

        <!-- Campus Selector -->
        <div class="flex flex-col space-y-1">
          <label for="ghost-campus-select" class="font-mono text-[9px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider px-1">Campus</label>
          <select 
            id="ghost-campus-select"
            bind:value={selectedCampus} 
            onchange={() => selectedBuilding = ""}
            class="w-full sm:min-w-[150px] p-2 bg-[#faf8f5] border border-[#e5e0d8] rounded-lg text-xs sm:text-sm font-semibold text-[#161e2e] outline-none focus:ring-1 focus:ring-[#002d72] transition-colors dark:bg-[#0a0e1a] dark:border-[#1e293b] dark:text-slate-200 cursor-pointer font-mono"
          >
            <option value="">All Campuses ({availableCampuses.reduce((acc, c) => acc + c.count, 0)})</option>
            {#each availableCampuses as c}
              <option value={c.name}>{c.name} Kampüs ({c.count})</option>
            {/each}
          </select>
        </div>

        <!-- Building Selector -->
        <div class="flex flex-col space-y-1">
          <label for="ghost-building-select" class="font-mono text-[9px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider px-1">Building</label>
          <select 
            id="ghost-building-select"
            bind:value={selectedBuilding} 
            class="w-full sm:min-w-[170px] p-2 bg-[#faf8f5] border border-[#e5e0d8] rounded-lg text-xs sm:text-sm font-semibold text-[#161e2e] outline-none focus:ring-1 focus:ring-[#002d72] transition-colors dark:bg-[#0a0e1a] dark:border-[#1e293b] dark:text-slate-200 cursor-pointer font-mono"
          >
            <option value="">All Buildings ({availableBuildings.reduce((acc, b) => acc + b.count, 0)})</option>
            {#each availableBuildings as b}
              <option value={b.name}>{b.name} ({b.count} {b.count === 1 ? 'room' : 'rooms'})</option>
            {/each}
          </select>
        </div>

        <!-- Department Multi-select -->
        <div class="flex flex-col space-y-1 relative">
          <span class="font-mono text-[9px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider px-1">Department</span>
          <div class="relative">
            <button 
              onclick={() => isDeptOpen = !isDeptOpen}
              class="w-full sm:min-w-[150px] flex items-center justify-between p-2 bg-[#faf8f5] border border-[#e5e0d8] rounded-lg text-xs font-semibold text-[#161e2e] outline-none hover:border-[#c5a059] transition-colors dark:bg-[#0a0e1a] dark:border-[#1e293b] dark:text-slate-200 cursor-pointer font-mono"
            >
              <span class="truncate">
                {selectedDepts.length === 0 ? 'All Departments' : `${selectedDepts.length} Selected`}
              </span>
              <Filter size={12} class="text-[#525f7f] ml-2 shrink-0" />
            </button>

            {#if isDeptOpen}
              <div class="absolute top-full left-0 mt-2 w-72 max-w-[90vw] bg-white border border-[#e5e0d8] rounded-xl shadow-xl z-50 overflow-hidden dark:bg-[#121827] dark:border-[#1e293b]">
                <div class="p-2.5 border-b border-[#e5e0d8] bg-[#f3efe6]/60 dark:border-[#1e293b] dark:bg-[#0a0e1a]">
                  <div class="relative">
                    <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#525f7f]" size={12} />
                    <input 
                      type="text" 
                      bind:value={deptSearch}
                      placeholder="Search departments..."
                      class="w-full pl-8 pr-2 py-1.5 bg-[#faf8f5] border border-[#e5e0d8] rounded-md text-xs outline-none focus:ring-1 focus:ring-[#002d72] dark:bg-[#0a0e1a] dark:border-[#1e293b] dark:text-white"
                    />
                  </div>
                </div>
                
                <div class="max-h-60 overflow-y-auto p-2 custom-scrollbar space-y-1">
                  {#each filteredDepts as dept}
                    <button 
                      onclick={() => toggleDept(dept)}
                      class="w-full flex items-center justify-between p-1.5 rounded-md text-xs transition-colors cursor-pointer
                      {selectedDepts.includes(dept) 
                        ? 'bg-[#002d72]/10 text-[#002d72] font-semibold dark:bg-[#8cc8ea]/15 dark:text-[#8cc8ea]' 
                        : 'text-[#161e2e] dark:text-slate-300 hover:bg-[#f3efe6] dark:hover:bg-slate-800/60'}"
                    >
                      <div class="flex items-center space-x-2">
                        <div class="w-3.5 h-3.5 rounded border flex items-center justify-center
                          {selectedDepts.includes(dept) 
                            ? 'bg-[#002d72] border-[#002d72] dark:bg-[#8cc8ea] dark:border-[#8cc8ea]' 
                            : 'bg-white border-[#e5e0d8] dark:bg-[#0a0e1a] dark:border-slate-700'}">
                          {#if selectedDepts.includes(dept)}
                            <Check size={10} class="text-white dark:text-[#0a0e1a] stroke-[3]" />
                          {/if}
                        </div>
                        <span class="font-mono">{dept}</span>
                      </div>
                    </button>
                  {/each}
                </div>

                {#if selectedDepts.length > 0}
                  <div class="p-2 border-t border-[#e5e0d8] bg-[#f3efe6]/40 dark:border-[#1e293b] dark:bg-[#0a0e1a]">
                    <button 
                      onclick={() => { selectedDepts = []; isDeptOpen = false; fetchSchedule(); }}
                      class="w-full py-1.5 font-mono text-[10px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider hover:bg-[#e5e0d8] dark:hover:bg-slate-800 rounded transition-colors cursor-pointer"
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

      <!-- Conflict Toggle & Indicator -->
      <div class="flex items-center space-x-3 self-end md:self-auto">
        {#if conflictCount > 0}
          <button
            onclick={() => showOnlyConflicts = !showOnlyConflicts}
            class="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold font-mono transition-colors cursor-pointer border
              {showOnlyConflicts 
                ? 'bg-amber-600 text-white border-amber-700 shadow-xs dark:bg-amber-600 dark:border-amber-500' 
                : 'bg-amber-50 border-amber-300 text-amber-900 hover:bg-amber-100 dark:bg-amber-950/40 dark:border-amber-800 dark:text-amber-300 dark:hover:bg-amber-900/60'}"
            title="Filter matrix to classrooms with double-booking conflicts"
          >
            <AlertTriangle size={13} class={showOnlyConflicts ? 'text-white' : 'text-amber-600 dark:text-amber-400'} />
            <span>{conflictCount} Conflict{conflictCount > 1 ? 's' : ''}</span>
            {#if showOnlyConflicts}
              <span class="text-[9px] bg-amber-800 text-white px-1 py-0.5 rounded font-bold uppercase">Active</span>
            {/if}
          </button>
        {:else if !loading && scheduleData.length > 0}
          <div class="flex items-center space-x-1 text-emerald-700 dark:text-emerald-400 font-mono text-[11px] font-medium px-2 py-1 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-md">
            <Check size={12} class="stroke-[2.5]" />
            <span>0 Conflicts</span>
          </div>
        {/if}
      </div>
    </div>

    <!-- Day Navigation & Legend Bar -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-[#e5e0d8] dark:border-[#1e293b]">
      <div class="flex flex-col space-y-1">
        <span class="font-mono text-[9px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider px-1">Active Day</span>
        <div class="flex bg-[#e5e0d8] p-1 rounded-lg border border-[#e5e0d8] dark:bg-[#0a0e1a] dark:border-[#1e293b] overflow-x-auto no-scrollbar font-mono">
          {#each days as day}
            <button 
              onclick={() => activeDay = day}
              class="px-3 sm:px-3.5 py-1 rounded text-xs font-semibold transition-colors shrink-0 cursor-pointer
              {activeDay === day 
                ? 'bg-[#002d72] text-white dark:bg-[#8cc8ea] dark:text-[#0a0e1a] shadow-2xs font-bold' 
                : 'text-[#525f7f] hover:text-[#002d72] dark:text-slate-400 dark:hover:text-slate-200'}"
            >
              {day}
            </button>
          {/each}
        </div>
      </div>

      <div class="flex items-center space-x-4 font-mono text-[10px] flex-wrap gap-y-1">
        <div class="flex items-center space-x-1.5">
          <div class="w-2.5 h-2.5 bg-[#002d72]/15 border border-[#002d72]/30 rounded dark:bg-[#8cc8ea]/20 dark:border-[#8cc8ea]/40"></div>
          <span class="text-[#525f7f] dark:text-slate-400 uppercase tracking-wider">Occupied</span>
        </div>
        <div class="flex items-center space-x-1.5">
          <div class="w-2.5 h-2.5 bg-amber-500/20 border border-amber-500/60 rounded dark:bg-amber-950/50 dark:border-amber-500"></div>
          <span class="text-amber-800 dark:text-amber-300 font-bold uppercase tracking-wider">Conflict (Double Booked)</span>
        </div>
        <div class="flex items-center space-x-1.5">
          <div class="w-2.5 h-2.5 bg-[#faf8f5] border border-[#e5e0d8] rounded dark:bg-[#0a0e1a] dark:border-[#1e293b]"></div>
          <span class="text-[#525f7f] dark:text-slate-400 uppercase tracking-wider">Available</span>
        </div>
      </div>
    </div>
  </div>

  {#if loading}
    <div class="flex justify-center py-20">
      <div class="animate-spin rounded-full h-8 w-8 border-3 border-[#e5e0d8] border-t-[#002d72] dark:border-slate-800 dark:border-t-[#8cc8ea]"></div>
    </div>
  {:else if totalVisibleRooms === 0}
    <div class="bg-white rounded-xl border border-[#e5e0d8] p-12 text-center shadow-2xs dark:bg-[#121827] dark:border-[#1e293b]">
      <AlertTriangle size={32} class="mx-auto text-[#c5a059] mb-3 opacity-80" />
      <h3 class="font-serif text-lg font-bold text-[#002d72] dark:text-slate-200">No Classrooms Match Filters</h3>
      <p class="font-sans text-xs text-[#525f7f] dark:text-slate-400 mt-1 max-w-md mx-auto">
        {#if showOnlyConflicts}
          No double-booking conflicts were detected on <strong>{activeDay}</strong> for {selectedCampus ? `${selectedCampus} Kampüs` : 'selected filters'}.
        {:else}
          No occupied rooms found for the selected term, campus, building, and department filters.
        {/if}
      </p>
      {#if showOnlyConflicts || selectedCampus || selectedBuilding || selectedDepts.length > 0}
        <button
          onclick={() => { showOnlyConflicts = false; selectedCampus = ""; selectedBuilding = ""; selectedDepts = []; fetchSchedule(); }}
          class="mt-4 px-4 py-2 bg-[#002d72] text-white rounded-lg text-xs font-semibold hover:bg-[#002d72]/90 transition-colors cursor-pointer font-mono"
        >
          Reset Filters
        </button>
      {/if}
    </div>
  {:else}
    <!-- Matrix View with Sticky Room Header, Campus & Building Grouping -->
    <div class="bg-white rounded-xl border border-[#e5e0d8] shadow-2xs overflow-hidden dark:bg-[#121827] dark:border-[#1e293b]">
      <div class="overflow-x-auto custom-scrollbar">
        <table class="w-full border-collapse min-w-[950px]">
          <thead>
            <tr class="bg-[#f3efe6]/90 border-b border-[#e5e0d8] dark:bg-[#0a0e1a] dark:border-[#1e293b] sticky top-0 z-20">
              <th class="p-3 text-left font-mono text-[11px] font-bold text-[#525f7f] dark:text-slate-400 uppercase border-r border-[#e5e0d8] dark:border-[#1e293b] w-40 sm:w-48 sticky left-0 z-30 bg-[#f3efe6] dark:bg-[#0a0e1a] shadow-2xs">Room / Hour</th>
              {#each hours as hour}
                <th class="p-3 text-center font-mono text-[11px] font-bold text-[#525f7f] dark:text-slate-400 uppercase min-w-[75px] sm:min-w-[95px]">{hour}</th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#each buildingGroups as group}
              <!-- Building & Campus Group Header Row -->
              <tr class="bg-[#ede8dc]/85 border-y border-[#dfd9cc] dark:bg-[#0d1322] dark:border-[#1e293b]/80">
                <td colspan={15} class="py-2 px-3 sticky left-0 z-15 bg-[#ede8dc] dark:bg-[#0d1322]">
                  <div class="flex items-center space-x-2 flex-wrap gap-y-1">
                    <Building2 size={13} class="text-[#002d72] dark:text-[#8cc8ea] shrink-0" />
                    <span class="font-mono text-xs font-bold text-[#002d72] dark:text-[#8cc8ea] uppercase tracking-wide">{group.building}</span>
                    <span class="font-mono text-[9px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider
                      {group.campus === 'Güney' ? 'bg-emerald-100 text-emerald-900 border border-emerald-300 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800' :
                       group.campus === 'Kuzey' ? 'bg-blue-100 text-blue-900 border border-blue-300 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800' :
                       group.campus === 'Hisar' ? 'bg-purple-100 text-purple-900 border border-purple-300 dark:bg-purple-950/60 dark:text-purple-300 dark:border-purple-800' :
                       'bg-slate-100 text-slate-800 border border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700'}">
                      {group.campus} Kampüs
                    </span>
                    <span class="font-mono text-[10px] text-[#525f7f] dark:text-slate-400 font-semibold">({group.rooms.length} {group.rooms.length === 1 ? 'room' : 'rooms'})</span>
                  </div>
                </td>
              </tr>

              <!-- Room Rows within this Building -->
              {#each group.rooms as room}
                <tr class="border-b border-[#e5e0d8] hover:bg-[#f3efe6]/40 transition-colors dark:border-[#1e293b] dark:hover:bg-slate-800/40">
                  <td class="p-3 text-xs font-mono font-bold text-[#161e2e] dark:text-slate-200 border-r border-[#e5e0d8] dark:border-[#1e293b] bg-[#f3efe6]/80 dark:bg-[#0a0e1a] sticky left-0 z-10 truncate max-w-[140px] sm:max-w-none shadow-2xs">
                    <div class="flex flex-col">
                      <span class="truncate">{room}</span>
                      <span class="text-[9px] font-normal text-[#525f7f] dark:text-slate-400 truncate">{group.building}</span>
                    </div>
                  </td>
                  {#each hours as hour}
                    {@const slots = slotMap.get(`${room}|${hour}`)}
                    <td class="p-1 text-center h-14 sm:h-16">
                      {#if !slots || slots.length === 0}
                        <div class="h-full w-full bg-[#faf8f5]/40 dark:bg-[#0a0e1a]/40 rounded-lg border border-transparent"></div>
                      {:else if slots.length === 1}
                        <div class="h-full w-full bg-[#002d72]/10 border border-[#002d72]/20 rounded-lg p-1 flex flex-col justify-center items-center shadow-2xs dark:bg-[#8cc8ea]/15 dark:border-[#8cc8ea]/30">
                          <span class="font-mono text-[9px] sm:text-[10px] font-bold text-[#002d72] dark:text-[#8cc8ea] leading-tight truncate max-w-[80px]">{slots[0].course_code}</span>
                          <span class="font-mono text-[7px] sm:text-[8px] text-[#0080c9] dark:text-slate-300 uppercase font-semibold">{slots[0].dept_kisaadi}</span>
                        </div>
                      {:else}
                        <!-- Multi-Course Collision / Double Booking -->
                        <div 
                          class="h-full w-full bg-amber-500/15 border border-amber-500/70 rounded-lg p-1 flex flex-col justify-between items-center shadow-2xs dark:bg-amber-950/50 dark:border-amber-500/70 relative overflow-hidden"
                          title="Conflict: {slots.map(s => `${s.course_code} (${s.dept_kisaadi})`).join(' vs ')}"
                        >
                          <div class="flex items-center space-x-0.5 text-[7px] font-bold text-amber-700 dark:text-amber-300 uppercase leading-none mb-0.5">
                            <AlertTriangle size={8} class="text-amber-600 dark:text-amber-400 shrink-0" />
                            <span>Conflict ({slots.length})</span>
                          </div>
                          <div class="w-full flex flex-col items-center gap-0.5 overflow-hidden">
                            {#each slots as slot}
                              <div class="font-mono text-[8px] sm:text-[9px] font-bold text-amber-950 dark:text-amber-100 truncate max-w-[85px] leading-tight">
                                {slot.course_code} <span class="text-[7px] font-normal text-amber-800 dark:text-amber-300">({slot.dept_kisaadi})</span>
                              </div>
                            {/each}
                          </div>
                        </div>
                      {/if}
                    </td>
                  {/each}
                </tr>
              {/each}
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</div>
