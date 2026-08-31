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
      <h1 class="font-serif text-2xl sm:text-3xl font-bold text-[#002d72] dark:text-slate-50 tracking-tight">University Overview</h1>
      <p class="font-sans text-xs sm:text-sm text-[#525f7f] mt-1 sm:mt-1.5 dark:text-slate-400">Historical offerings, faculty distribution, and scheduling patterns across 50 years.</p>
    </div>
    {#if hasStatsError || data.hasError}
      <button 
        onclick={handleRetry}
        disabled={isRetrying}
        class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-[#002d72] bg-[#002d72]/10 hover:bg-[#002d72]/20 dark:text-[#8cc8ea] dark:bg-[#8cc8ea]/10 dark:hover:bg-[#8cc8ea]/20 rounded-lg transition-colors cursor-pointer disabled:opacity-50 w-fit"
      >
        <RotateCcw size={13} class={isRetrying ? "animate-spin" : ""} />
        <span>{isRetrying ? "Retrying..." : "Retry Overview"}</span>
      </button>
    {/if}
  </div>

  <!-- Stats Grid -->
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
    {#each statsList as stat}
      <div class="bg-white p-4 sm:p-5 rounded-xl border border-[#e5e0d8] shadow-2xs transition-all duration-200 dark:bg-[#121827] dark:border-[#1e293b] hover:border-[#c5a059]/60 dark:hover:border-[#8cc8ea]/40 flex items-center justify-between">
        <div class="space-y-1 sm:space-y-1.5">
          <p class="font-sans text-[10px] sm:text-[11px] text-[#525f7f] font-semibold uppercase tracking-wider dark:text-slate-400">{stat.label}</p>
          {#if isRetrying}
            <div class="h-7 sm:h-8 w-20 sm:w-24 bg-[#f3efe6] animate-pulse rounded dark:bg-slate-800"></div>
          {:else if stat.value !== null}
            <h3 class="font-serif text-2xl sm:text-3xl font-bold text-[#161e2e] dark:text-slate-100 leading-none">{stat.value}</h3>
          {:else}
            <span class="font-mono text-base font-semibold text-[#8a94a6] dark:text-slate-500">—</span>
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
    <div class="lg:col-span-2 bg-white p-4 sm:p-6 rounded-xl border border-[#e5e0d8] shadow-2xs flex flex-col dark:bg-[#121827] dark:border-[#1e293b]">
      <div class="mb-4 sm:mb-6">
        <h3 class="font-serif text-base sm:text-lg font-bold text-[#002d72] dark:text-slate-100 flex items-center gap-2">
          <TrendingUp size={18} class="text-[#0080c9] dark:text-[#8cc8ea] shrink-0" />
          <span>Department Evolution (1970 – Present)</span>
        </h3>
        <p class="font-sans text-xs text-[#525f7f] dark:text-slate-400 mt-1">Course offering volume for major departments over 5 decades.</p>
      </div>
      
      <div class="flex-1 min-h-[260px] sm:min-h-[300px] flex items-center justify-center">
        {#if isRetrying}
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-[#002d72] dark:border-[#8cc8ea]"></div>
        {:else if evolutionChartData}
          <div class="w-full h-full min-h-[260px] sm:min-h-[300px]">
            <Line 
              data={evolutionChartData} 
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10, family: 'Inter' } } }
                },
                scales: {
                  y: { grid: { color: 'rgba(140,160,180,0.12)' } },
                  x: { grid: { display: false } }
                }
              }} 
            />
          </div>
        {:else}
          <div class="flex flex-col items-center justify-center text-center p-6 space-y-2 text-[#525f7f] dark:text-slate-400">
            <AlertTriangle size={24} class="opacity-40" />
            <p class="text-xs">Department evolution data unavailable.</p>
            <button 
              onclick={handleRetry}
              class="text-xs font-semibold text-[#0080c9] dark:text-[#8cc8ea] hover:underline cursor-pointer"
            >
              Retry
            </button>
          </div>
        {/if}
      </div>
    </div>
    
    <!-- Scheduling Heatmap -->
    <div class="bg-white p-4 sm:p-6 rounded-xl border border-[#e5e0d8] shadow-2xs flex flex-col dark:bg-[#121827] dark:border-[#1e293b]">
      <div class="mb-4 sm:mb-6">
        <h3 class="font-serif text-base sm:text-lg font-bold text-[#002d72] dark:text-slate-100 flex items-center gap-2">
          <LayoutGrid size={18} class="text-[#0080c9] dark:text-[#8cc8ea] shrink-0" />
          <span>Campus Scheduling Matrix</span>
        </h3>
        <p class="font-sans text-xs text-[#525f7f] dark:text-slate-400 mt-1">Peak lecture hours across all historical records.</p>
      </div>
      
      <div class="flex-1 flex flex-col justify-center">
        {#if isRetrying}
          <div class="flex items-center justify-center h-48">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-[#002d72] dark:border-[#8cc8ea]"></div>
          </div>
        {:else if heatmapData.length === 0}
          <div class="flex flex-col items-center justify-center h-48 text-center p-6 space-y-2 text-[#525f7f] dark:text-slate-400">
            <AlertTriangle size={24} class="opacity-40" />
            <p class="text-xs">Scheduling heatmap data unavailable.</p>
            <button 
              onclick={handleRetry}
              class="text-xs font-semibold text-[#0080c9] dark:text-[#8cc8ea] hover:underline cursor-pointer"
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
                    <th class="p-0.5 sm:p-1 font-mono text-[9px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider">{day}</th>
                  {/each}
                </tr>
              </thead>
              <tbody>
                {#each hours as hour}
                  <tr>
                    <td class="text-right pr-1 sm:pr-2 font-mono text-[9px] font-bold text-[#8a94a6] dark:text-slate-500 uppercase leading-none">{hour}</td>
                    {#each days as day}
                      {@const count = getSlotCount(day, hour)}
                      <td 
                        class="h-4 sm:h-5 rounded-md border border-[#e5e0d8] dark:border-[#1e293b] transition-all hover:ring-1 hover:ring-[#c5a059] group relative cursor-help"
                        style="background-color: {getHeatColor(count)}"
                      >
                         {#if count > 0}
                           <div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-10">
                              <span class="font-mono text-[9px] font-bold text-white bg-slate-950/95 px-1.5 py-0.5 rounded shadow-lg whitespace-nowrap border border-slate-800">
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
          <div class="flex items-center justify-center space-x-3 pt-4 border-t border-[#e5e0d8] dark:border-[#1e293b] mt-4 font-mono text-[10px]">
            <div class="flex items-center space-x-1">
               <div class="w-2.5 h-2.5 rounded bg-[#f3efe6] dark:bg-slate-800"></div>
               <span class="text-[#525f7f] dark:text-slate-400 uppercase tracking-wider">Low</span>
            </div>
            <div class="flex items-center space-x-1">
               <div class="w-2.5 h-2.5 rounded bg-[#0080c9] dark:bg-[#38bdf8]"></div>
               <span class="text-[#525f7f] dark:text-slate-400 uppercase tracking-wider">High</span>
            </div>
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>
