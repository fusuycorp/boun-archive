<script lang="ts">
  import { TrendingUp, LayoutGrid, Award, BookOpen, Calendar, RotateCcw, AlertTriangle } from "lucide-svelte";
  import { invalidateAll } from "$app/navigation";
  import { Chart, registerables } from 'chart.js';
  import { Line } from 'svelte-chartjs';
  import type { PageData } from './$types';

  Chart.register(...registerables);

  let { data }: { data: PageData } = $props();

  let totalCourses = $derived(data.totalCourses);
  let totalDepts = $derived(data.totalDepts);
  let totalTerms = $derived(data.totalTerms);
  let isRetrying = $state(false);

  // Chart & Heatmap State
  let evolutionData = $derived(data.evolutionData);
  let heatmapData = $derived(data.heatmapData ?? []);

  async function handleRetry() {
    isRetrying = true;
    try {
      await invalidateAll();
    } finally {
      isRetrying = false;
    }
  }

  // Chart preparation
  const evolutionChartData = $derived(evolutionData ? {
    labels: evolutionData.years,
    datasets: Object.keys(evolutionData.departments).slice(0, 5).map((dept, i) => {
      const colors = ["#002d72", "#0080c9", "#c5a059", "#005696", "#0284c7"];
      return {
        label: dept,
        data: evolutionData.years.map((y: string) => evolutionData.departments[dept][y] || 0),
        borderColor: colors[i % colors.length],
        backgroundColor: `${colors[i % colors.length]}15`,
        fill: true,
        tension: 0.4
      };
    })
  } : null);

  // Heatmap Helpers
  const days = ["M", "T", "W", "Th", "F", "St", "Su"];
  const hours = Array.from({ length: 14 }, (_, i) => i + 1);

  function getHeatColor(count: number) {
    if (heatmapData.length === 0) return 'transparent';
    const max = Math.max(...heatmapData.map(d => d.count), 1);
    const intensity = count / max;
    return `rgba(0, 128, 201, ${0.06 + intensity * 0.94})`;
  }

  function getSlotCount(day: string, hour: number) {
    const slot = heatmapData.find(d => d.day_code === day && d.slot_hour === hour);
    return slot ? slot.count : 0;
  }

  const hasStatsError = $derived(totalCourses === null && totalDepts === null && totalTerms === null);

  const statsList = $derived([
    { 
      label: "Total Courses", 
      value: totalCourses != null ? totalCourses.toLocaleString() : null, 
      icon: BookOpen, 
      color: "text-[#002d72] bg-[#002d72]/10 dark:text-sky-400 dark:bg-sky-500/10" 
    },
    { 
      label: "Unique Departments", 
      value: totalDepts != null ? totalDepts.toString() : null, 
      icon: Award, 
      color: "text-[#0080c9] bg-[#0080c9]/10 dark:text-sky-300 dark:bg-sky-400/10" 
    },
    { 
      label: "Semesters Logged", 
      value: totalTerms != null ? totalTerms.toString() : null, 
      icon: Calendar, 
      color: "text-[#c5a059] bg-[#c5a059]/15 dark:text-amber-300 dark:bg-amber-400/10" 
    },
    { 
      label: "Historical Range", 
      value: "50+ Years", 
      icon: TrendingUp, 
      color: "text-emerald-600 bg-emerald-50 dark:text-emerald-400 dark:bg-emerald-950/40" 
    }
  ]);
</script>

<div class="space-y-6 sm:space-y-8">
  <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
    <div>
      <h1 class="font-serif text-2xl sm:text-3xl font-bold text-[#1c1b18] dark:text-neutral-50 tracking-tight">University Overview</h1>
      <p class="font-sans text-xs sm:text-sm text-[#746f65] mt-1 sm:mt-1.5 dark:text-neutral-400">Historical offerings, faculty distribution, and scheduling patterns across 50 years.</p>
    </div>
    {#if hasStatsError || data.hasError}
      <button 
        onclick={handleRetry}
        disabled={isRetrying}
        class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-[#002d72] bg-[#002d72]/10 hover:bg-[#002d72]/20 dark:text-sky-400 dark:bg-sky-500/10 dark:hover:bg-sky-500/20 rounded-lg transition-colors cursor-pointer disabled:opacity-50 w-fit"
      >
        <RotateCcw size={13} class={isRetrying ? "animate-spin" : ""} />
        <span>{isRetrying ? "Retrying..." : "Retry Overview"}</span>
      </button>
    {/if}
  </div>

  <!-- Stats Grid -->
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
    {#each statsList as stat}
      <div class="bg-[#f7f5ee] p-4 sm:p-5 rounded-xl border border-[#dbd7cc] shadow-2xs transition-all duration-200 dark:bg-[#18181b] dark:border-[#27272a] hover:border-[#c8c3b5] dark:hover:border-neutral-700 flex items-center justify-between">
        <div class="space-y-1 sm:space-y-1.5">
          <p class="font-sans text-[10px] sm:text-[11px] text-[#746f65] font-semibold uppercase tracking-wider dark:text-neutral-500">{stat.label}</p>
          {#if isRetrying}
            <div class="h-7 sm:h-8 w-20 sm:w-24 bg-[#e7e4d9] animate-pulse rounded dark:bg-[#27272a]"></div>
          {:else if stat.value !== null}
            <h3 class="font-serif text-2xl sm:text-3xl font-bold text-[#1c1b18] dark:text-neutral-100 leading-none">{stat.value}</h3>
          {:else}
            <span class="font-mono text-base font-semibold text-[#8a857a] dark:text-neutral-500">—</span>
          {/if}
        </div>
        <div class="p-3 rounded-lg {stat.color} shrink-0">
          <stat.icon size={20} />
        </div>
      </div>
    {/each}
  </div>

  <!-- Charts Grid -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- Department Evolution Line Chart -->
    <div class="lg:col-span-2 bg-[#f7f5ee] p-4 sm:p-6 rounded-xl border border-[#dbd7cc] shadow-2xs flex flex-col dark:bg-[#18181b] dark:border-[#27272a]">
      <div class="mb-4 sm:mb-6">
        <h3 class="font-serif text-base sm:text-lg font-bold text-[#1c1b18] dark:text-neutral-100 flex items-center gap-2">
          <TrendingUp size={18} class="text-[#0080c9] dark:text-amber-400 shrink-0" />
          <span>Department Evolution (1970 – 2024)</span>
        </h3>
        <p class="font-sans text-xs text-[#746f65] dark:text-neutral-400 mt-1">Course offering volume for major departments over 5 decades.</p>
      </div>
      
      <div class="flex-1 min-h-[260px] sm:min-h-[300px] flex items-center justify-center">
        {#if isRetrying}
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-[#002d72] dark:border-amber-400"></div>
        {:else if evolutionChartData}
          <div class="w-full h-full min-h-[260px] sm:min-h-[300px]">
            <Line 
              data={evolutionChartData} 
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10, family: 'Plus Jakarta Sans' } } }
                },
                scales: {
                  y: { grid: { color: 'rgba(120,110,95,0.1)' } },
                  x: { grid: { display: false } }
                }
              }} 
            />
          </div>
        {:else}
          <div class="flex flex-col items-center justify-center text-center p-6 space-y-2 text-[#746f65] dark:text-neutral-400">
            <AlertTriangle size={24} class="opacity-40" />
            <p class="text-xs">Department evolution data unavailable.</p>
            <button 
              onclick={handleRetry}
              class="text-xs font-semibold text-[#0080c9] dark:text-sky-400 hover:underline cursor-pointer"
            >
              Retry
            </button>
          </div>
        {/if}
      </div>
    </div>
    
    <!-- Scheduling Heatmap -->
    <div class="bg-[#f7f5ee] p-4 sm:p-6 rounded-xl border border-[#dbd7cc] shadow-2xs flex flex-col dark:bg-[#18181b] dark:border-[#27272a]">
      <div class="mb-4 sm:mb-6">
        <h3 class="font-serif text-base sm:text-lg font-bold text-[#1c1b18] dark:text-neutral-100 flex items-center gap-2">
          <LayoutGrid size={18} class="text-[#0080c9] dark:text-amber-400 shrink-0" />
          <span>Campus Scheduling Matrix</span>
        </h3>
        <p class="font-sans text-xs text-[#746f65] dark:text-neutral-400 mt-1">Peak lecture hours across all historical records.</p>
      </div>
      
      <div class="flex-1 flex flex-col justify-center">
        {#if isRetrying}
          <div class="flex items-center justify-center h-48">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-[#002d72] dark:border-amber-400"></div>
          </div>
        {:else if heatmapData.length === 0}
          <div class="flex flex-col items-center justify-center h-48 text-center p-6 space-y-2 text-[#746f65] dark:text-neutral-400">
            <AlertTriangle size={24} class="opacity-40" />
            <p class="text-xs">Scheduling heatmap data unavailable.</p>
            <button 
              onclick={handleRetry}
              class="text-xs font-semibold text-[#0080c9] dark:text-sky-400 hover:underline cursor-pointer"
            >
              Retry
            </button>
          </div>
        {:else}
          <div class="overflow-x-auto no-scrollbar">
            <table class="w-full border-separate border-spacing-[2px] sm:border-spacing-[3px] min-w-[240px]">
              <thead>
                <tr>
                  <th class="w-6 sm:w-8"></th>
                  {#each days as day}
                    <th class="p-0.5 sm:p-1 font-mono text-[9px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider">{day}</th>
                  {/each}
                </tr>
              </thead>
              <tbody>
                {#each hours as hour}
                  <tr>
                    <td class="text-right pr-1 sm:pr-2 font-mono text-[9px] font-bold text-[#8a857a] dark:text-neutral-600 uppercase leading-none">{hour}</td>
                    {#each days as day}
                      {@const count = getSlotCount(day, hour)}
                      <td 
                        class="h-4 sm:h-5 rounded-md border border-[#dbd7cc]/70 dark:border-[#27272a] transition-all hover:ring-1 hover:ring-[#c5a059] group relative cursor-help"
                        style="background-color: {getHeatColor(count)}"
                      >
                         {#if count > 0}
                           <div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-10">
                              <span class="font-mono text-[9px] font-bold text-white bg-neutral-950/95 px-1.5 py-0.5 rounded shadow-lg whitespace-nowrap border border-neutral-800">
                                {count.toLocaleString()}
                              </span>
                           </div>
                         {/if}
                      </td>
                    {/each}
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
          <div class="flex items-center justify-center space-x-3 pt-4 border-t border-[#dbd7cc]/70 dark:border-[#27272a] mt-4 font-mono text-[10px]">
            <div class="flex items-center space-x-1">
               <div class="w-2.5 h-2.5 rounded bg-[#e7e4d9] dark:bg-[#27272a]"></div>
               <span class="text-[#746f65] dark:text-neutral-400 uppercase tracking-wider">Low</span>
            </div>
            <div class="flex items-center space-x-1">
               <div class="w-2.5 h-2.5 rounded bg-[#0080c9] dark:bg-sky-500"></div>
               <span class="text-[#746f65] dark:text-neutral-400 uppercase tracking-wider">High</span>
            </div>
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>
