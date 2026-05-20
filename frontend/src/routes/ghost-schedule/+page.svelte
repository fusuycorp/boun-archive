<script lang="ts">
  import { onMount } from "svelte";
  import { Calendar, Layers, Map, ChevronLeft, ChevronRight } from "lucide-svelte";

  let terms = $state<any[]>([]);
  let selectedTerm = $state("");
  let scheduleData = $state<any[]>([]);
  let loading = $state(false);
  let days = ["M", "T", "W", "Th", "F", "St", "Su"];
  let hours = Array.from({ length: 14 }, (_, i) => i + 1);

  // Grouped data for visualization
  let activeDay = $state("M");
  let filteredSchedule = $derived(scheduleData.filter(s => s.day_code === activeDay));

  async function fetchTerms() {
    const res = await fetch("http://localhost:8000/api/v1/terms");
    terms = await res.json();
    if (terms.length > 0) {
      selectedTerm = terms[0].id;
      fetchSchedule();
    }
  }

  async function fetchSchedule() {
    if (!selectedTerm) return;
    loading = true;
    try {
      const res = await fetch(`http://localhost:8000/api/v1/analytics/ghost-schedule/${selectedTerm}`);
      scheduleData = await res.json();
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  }

  onMount(fetchTerms);
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <h2 class="text-3xl font-bold text-slate-800">Ghost Schedule</h2>
      <p class="text-slate-500">Historical campus reconstruction</p>
    </div>
    <div class="flex items-center space-x-4">
      <select 
        bind:value={selectedTerm} 
        onchange={fetchSchedule}
        class="p-2 bg-white border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500"
      >
        {#each terms as term}
          <option value={term.id}>{term.id}</option>
        {/each}
      </select>
    </div>
  </div>

  <!-- Day Selector -->
  <div class="flex bg-white p-1 rounded-xl border border-slate-200 shadow-sm w-fit">
    {#each days as day}
      <button 
        onclick={() => activeDay = day}
        class="px-6 py-2 rounded-lg text-sm font-bold transition-all
        {activeDay === day ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-500 hover:bg-slate-50'}"
      >
        {day}
      </button>
    {/each}
  </div>

  {#if loading}
    <div class="flex justify-center py-24">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
    </div>
  {:else}
    <!-- Matrix View -->
    <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full border-collapse">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200">
              <th class="p-4 text-left text-xs font-bold text-slate-400 uppercase border-r border-slate-200 w-48">Room / Hour</th>
              {#each hours as hour}
                <th class="p-4 text-center text-xs font-bold text-slate-400 uppercase min-w-[100px]">{hour}</th>
              {/each}
            </tr>
          </thead>
          <tbody>
            <!-- We'll show a subset of rooms for performance/demo -->
            {#each Array.from(new Set(filteredSchedule.map(s => s.room_name))).sort().slice(0, 50) as room}
              <tr class="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                <td class="p-4 text-sm font-bold text-slate-700 border-r border-slate-200 bg-slate-50/50">{room}</td>
                {#each hours as hour}
                  {@const slot = filteredSchedule.find(s => s.room_name === room && s.slot_hour === hour)}
                  <td class="p-1 text-center h-16">
                    {#if slot}
                      <div class="h-full w-full bg-indigo-100 border border-indigo-200 rounded p-1 flex flex-col justify-center items-center shadow-sm">
                        <span class="text-[10px] font-black text-indigo-700 leading-tight">{slot.course_code}</span>
                        <span class="text-[8px] text-indigo-500 font-bold uppercase">{slot.dept_kisaadi}</span>
                      </div>
                    {:else}
                      <div class="h-full w-full bg-slate-50/30 rounded border border-transparent"></div>
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
