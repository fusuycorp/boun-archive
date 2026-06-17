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
      const [searchRes, termsRes, deptsRes] = await Promise.all([
        fetch(`${API_BASE}/v1/search?limit=0`),
        fetch(`${API_BASE}/v1/terms`),
        fetch(`${API_BASE}/v1/departments`)
      ]);
      
      const searchData = await searchRes.json();
      const termsData = await termsRes.json();
      const deptsData = await deptsRes.json();
      
      totalCourses = searchData.totalHits ?? searchData.estimatedTotalHits ?? 136939;
      totalTerms = termsData.length || 50;
      totalDepts = deptsData.length || 72;
    } catch (e) {
      console.error("Failed to fetch dashboard stats", e);
    } finally {
      loadingStats = false;
    }
  }

  async function fetchChartData() {
    loadingChart = true;
    try {
      const res = await fetch(`${API_BASE}/v1/analytics/macro/departments-evolution`);
      evolutionData = await res.json();
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
      heatmapData = await res.json();
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
      const colors = ["#6366f1", "#10b981", "#3b82f6", "#f59e0b", "#ec4899"];
      return {
        label: dept,
        data: evolutionData.years.map((y: string) => evolutionData.departments[dept][y] || 0),
        borderColor: colors[i % colors.length],
        backgroundColor: `${colors[i % colors.length]}10`,
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
    return `rgba(99, 102, 241, ${0.05 + intensity * 0.95})`;
  }

  function getSlotCount(day: string, hour: number) {
    const slot = heatmapData.find(d => d.day_code === day && d.slot_hour === hour);
    return slot ? slot.count : 0;
  }

  const statsList = $derived([
    { label: "Total Courses", value: totalCourses.toLocaleString(), icon: BookOpen, color: "text-indigo-500 bg-indigo-50 dark:bg-indigo-950/40" },
    { label: "Unique Departments", value: totalDepts.toString(), icon: Award, color: "text-emerald-500 bg-emerald-50 dark:bg-emerald-950/40" },
    { label: "Semesters Logged", value: totalTerms.toString(), icon: Calendar, color: "text-blue-500 bg-blue-50 dark:bg-blue-950/40" },
    { label: "Historical Range", value: "50+ Years", icon: TrendingUp, color: "text-amber-500 bg-amber-50 dark:bg-amber-950/40" }
  ]);
</script>

<div class="space-y-8">
  <div class="flex items-end justify-between">
    <div>
      <h2 class="text-3xl font-bold text-slate-800 dark:text-slate-100">University Overview</h2>
      <p class="text-slate-500 mt-2 dark:text-slate-400">Historical trends and global university metrics.</p>
    </div>
  </div>

  <!-- Stats Grid -->
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
    {#each statsList as stat}
      <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm transition-all duration-200 dark:bg-slate-900 dark:border-slate-800 hover:shadow-md flex items-center justify-between">
        <div class="space-y-2">
          <p class="text-xs text-slate-400 font-bold uppercase tracking-wider dark:text-slate-500">{stat.label}</p>
          {#if loadingStats}
            <div class="h-8 w-24 bg-slate-100 animate-pulse rounded dark:bg-slate-800"></div>
          {:else}
            <h3 class="text-2xl font-black text-slate-900 dark:text-white leading-none">{stat.value}</h3>
          {/if}
        </div>
        <div class="p-4 rounded-xl {stat.color}">
          <stat.icon size={24} />
        </div>
      </div>
    {/each}
  </div>

  <!-- Charts Grid -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- Department Evolution Line Chart -->
    <div class="lg:col-span-2 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col dark:bg-slate-900 dark:border-slate-800 animate-fade-in">
      <div class="mb-6">
        <h3 class="text-lg font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
          <TrendingUp size={20} class="text-indigo-500" />
          <span>Department Growth (1970 - 2024)</span>
        </h3>
        <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Course offering frequencies for top departments over 50 years.</p>
      </div>
      
      <div class="flex-1 min-h-[300px] flex items-center justify-center">
        {#if loadingChart}
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 dark:border-indigo-500"></div>
        {:else}
          <div class="w-full h-full min-h-[300px]">
            {#if evolutionChartData}
              <Line 
                data={evolutionChartData} 
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 9 } } }
                  },
                  scales: {
                    y: { grid: { color: 'rgba(0,0,0,0.02)' } },
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
    <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col dark:bg-slate-900 dark:border-slate-800">
      <div class="mb-6">
        <h3 class="text-lg font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
          <LayoutGrid size={20} class="text-indigo-500" />
          <span>Global Campus Activity</span>
        </h3>
        <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Heatmap of peak scheduling hours across all time.</p>
      </div>
      
      <div class="flex-1 flex flex-col justify-center">
        {#if loadingHeatmap}
          <div class="flex items-center justify-center h-48">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 dark:border-indigo-500"></div>
          </div>
        {:else}
          <div class="overflow-x-auto no-scrollbar">
            <table class="w-full border-separate border-spacing-[3px]">
              <thead>
                <tr>
                  <th class="w-8"></th>
                  {#each days as day}
                    <th class="p-1 text-[8px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">{day}</th>
                  {/each}
                </tr>
              </thead>
              <tbody>
                {#each hours as hour}
                  <tr>
                    <td class="text-right pr-2 text-[8px] font-black text-slate-300 dark:text-slate-650 uppercase tracking-widest leading-none">{hour}</td>
                    {#each days as day}
                      {@const count = getSlotCount(day, hour)}
                      <td 
                        class="h-5 rounded-md border border-slate-100/50 dark:border-slate-800/50 transition-all hover:ring-2 hover:ring-indigo-500 group relative cursor-help"
                        style="background-color: {getHeatColor(count)}"
                      >
                         {#if count > 0}
                           <div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-10">
                              <span class="text-[9px] font-black text-white bg-slate-900/90 px-1.5 py-0.5 rounded shadow-lg whitespace-nowrap">
                                {count.toLocaleString()} Classes
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
          <div class="flex items-center justify-center space-x-3 pt-4 border-t border-slate-50 dark:border-slate-800/60 mt-4 font-mono">
            <div class="flex items-center space-x-1">
               <div class="w-2.5 h-2.5 rounded bg-indigo-50 dark:bg-indigo-950/40"></div>
               <span class="text-[8px] font-bold text-slate-400 uppercase tracking-wider">Low</span>
            </div>
            <div class="flex items-center space-x-1">
               <div class="w-2.5 h-2.5 rounded bg-indigo-600 dark:bg-indigo-500"></div>
               <span class="text-[8px] font-bold text-slate-400 uppercase tracking-wider">High</span>
            </div>
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>
