<script lang="ts">
  import { onMount } from "svelte";
  import { TrendingUp, LayoutGrid, Award, BookOpen, Calendar } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import { Chart, registerables } from 'chart.js';
  import { Line } from 'svelte-chartjs';

  Chart.register(...registerables);

  let totalCourses = $state(0);
  let totalDepts = $state(0);
  let totalTerms = $state(0);
  let loadingStats = $state(true);

  // Chart & Heatmap State
  let evolutionData = $state<any>(null);
  let heatmapData = $state<any[]>([]);
  let loadingChart = $state(true);
  let loadingHeatmap = $state(true);

  async function fetchStats() {
    loadingStats = true;
    try {
      const [searchRes, termsRes, deptsRes] = await Promise.allSettled([
        fetch(`${API_BASE}/v1/search?limit=0`),
        fetch(`${API_BASE}/v1/terms`),
        fetch(`${API_BASE}/v1/departments`)
      ]);
      
      let searchData: any = null;
      let termsData: any[] = [];
      let deptsData: any[] = [];

      if (searchRes.status === "fulfilled" && searchRes.value.ok) {
        searchData = await searchRes.value.json();
      }
      if (termsRes.status === "fulfilled" && termsRes.value.ok) {
        termsData = await termsRes.value.json();
      }
      if (deptsRes.status === "fulfilled" && deptsRes.value.ok) {
        deptsData = await deptsRes.value.json();
      }

      totalCourses = searchData?.totalHits ?? searchData?.estimatedTotalHits ?? (totalCourses || 136939);
      totalTerms = Array.isArray(termsData) && termsData.length > 0 ? termsData.length : (totalTerms || 50);
      totalDepts = Array.isArray(deptsData) && deptsData.length > 0 ? deptsData.length : (totalDepts || 72);
    } catch (e) {
      console.error("Failed to fetch dashboard stats", e);
      totalCourses = totalCourses || 136939;
      totalTerms = totalTerms || 50;
      totalDepts = totalDepts || 72;
    } finally {
      loadingStats = false;
    }
  }

  async function fetchChartData() {
    loadingChart = true;
    try {
      const res = await fetch(`${API_BASE}/v1/analytics/macro/departments-evolution`);
      if (res.ok) {
        evolutionData = await res.json();
      }
    } catch (e) {
      console.error("Failed to fetch evolution data", e);
    } finally {
      loadingChart = false;
    }
  }

  async function fetchHeatmapData() {
    loadingHeatmap = true;
    try {
      const res = await fetch(`${API_BASE}/v1/analytics/macro/scheduling-heatmap`);
      if (res.ok) {
        heatmapData = await res.json();
      }
    } catch (e) {
      console.error("Failed to fetch heatmap data", e);
    } finally {
      loadingHeatmap = false;
    }
  }

  onMount(() => {
    fetchStats();
    fetchChartData();
    fetchHeatmapData();
  });

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

  const statsList = $derived([
    { label: "Total Courses", value: totalCourses.toLocaleString(), icon: BookOpen, color: "text-[#002d72] bg-[#002d72]/10 dark:text-sky-400 dark:bg-sky-500/10" },
    { label: "Unique Departments", value: totalDepts.toString(), icon: Award, color: "text-[#0080c9] bg-[#0080c9]/10 dark:text-sky-300 dark:bg-sky-400/10" },
    { label: "Semesters Logged", value: totalTerms.toString(), icon: Calendar, color: "text-[#c5a059] bg-[#c5a059]/15 dark:text-amber-300 dark:bg-amber-400/10" },
    { label: "Historical Range", value: "50+ Years", icon: TrendingUp, color: "text-emerald-600 bg-emerald-50 dark:text-emerald-400 dark:bg-emerald-950/40" }
  ]);
</script>

<div class="space-y-6 sm:space-y-8">
  <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
    <div>
      <h1 class="font-serif text-2xl sm:text-3xl font-bold text-[#1c1b18] dark:text-neutral-50 tracking-tight">University Overview</h1>
      <p class="font-sans text-xs sm:text-sm text-[#746f65] mt-1 sm:mt-1.5 dark:text-neutral-400">Historical offerings, faculty distribution, and scheduling patterns across 50 years.</p>
    </div>
  </div>

  <!-- Stats Grid -->
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
    {#each statsList as stat}
      <div class="bg-[#f7f5ee] p-4 sm:p-5 rounded-xl border border-[#dbd7cc] shadow-2xs transition-all duration-200 dark:bg-[#18181b] dark:border-[#27272a] hover:border-[#c8c3b5] dark:hover:border-neutral-700 flex items-center justify-between">
        <div class="space-y-1 sm:space-y-1.5">
          <p class="font-sans text-[10px] sm:text-[11px] text-[#746f65] font-semibold uppercase tracking-wider dark:text-neutral-500">{stat.label}</p>
          {#if loadingStats}
            <div class="h-7 sm:h-8 w-20 sm:w-24 bg-[#e7e4d9] animate-pulse rounded dark:bg-[#27272a]"></div>
          {:else}
            <h3 class="font-serif text-2xl sm:text-3xl font-bold text-[#1c1b18] dark:text-neutral-100 leading-none">{stat.value}</h3>
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
        {#if loadingChart}
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-[#002d72] dark:border-amber-400"></div>
        {:else}
          <div class="w-full h-full min-h-[260px] sm:min-h-[300px]">
            {#if evolutionChartData}
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
            {/if}
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
        {#if loadingHeatmap}
          <div class="flex items-center justify-center h-48">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-[#002d72] dark:border-amber-400"></div>
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
