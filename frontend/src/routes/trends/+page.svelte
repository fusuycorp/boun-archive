<script lang="ts">
  import { onMount } from "svelte";
  import { 
    TrendingUp, 
    Calendar, 
    Clock, 
    AlertCircle, 
    Database, 
    Activity, 
    Map as MapIcon, 
    Search,
    History,
    Zap,
    Skull,
    Sparkles,
    Filter
  } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import { Chart, registerables } from 'chart.js';
  import { Line, Bar, Pie, Scatter } from 'svelte-chartjs';

  Chart.register(...registerables);

  // Tabs
  let activeTab = $state("evolution"); // "evolution", "discovery", "timespace", "forecast"

  // Forecast State
  let forecastQuery = $state("");
  let forecastData = $state<any>(null);
  let forecastLoading = $state(false);
  let forecastError = $state("");

  // Macro State
  let evolutionData = $state<any>(null);
  let deliveryData = $state<any>(null);
  let heatmapData = $state<any[]>([]);
  let lifecycleData = $state<any>(null);
  let macroLoading = $state(true);
  let selectedDecade = $state<number | null>(null);

  const decades = [2020, 2010, 2000, 1990, 1980, 1970];

  async function fetchMacroData() {
    macroLoading = true;
    try {
      const [evo, deliv, life] = await Promise.all([
        fetch(`${API_BASE}/api/v1/analytics/macro/departments-evolution`).then(r => r.json()),
        fetch(`${API_BASE}/api/v1/analytics/macro/delivery-evolution`).then(r => r.json()),
        fetch(`${API_BASE}/api/v1/analytics/macro/course-lifecycles`).then(r => r.json())
      ]);
      evolutionData = evo;
      deliveryData = deliv;
      lifecycleData = life;
    } catch (e) {
      console.error("Failed to fetch macro data", e);
    } finally {
      macroLoading = false;
    }
  }

  async function fetchHeatmap() {
    const url = new URL(`${API_BASE}/api/v1/analytics/macro/scheduling-heatmap`);
    if (selectedDecade) url.searchParams.set("decade", selectedDecade.toString());
    const res = await fetch(url);
    heatmapData = await res.json();
  }

  async function getForecast() {
    if (!forecastQuery) return;
    forecastLoading = true;
    forecastError = "";
    forecastData = null;
    try {
      const res = await fetch(`${API_BASE}/api/v1/predict/course/${forecastQuery.toUpperCase()}`);
      if (!res.ok) throw new Error("Course not found in historical records");
      forecastData = await res.json();
    } catch (e: any) {
      forecastError = e.message;
    } finally {
      forecastLoading = false;
    }
  }

  $effect(() => {
    if (activeTab === 'timespace') {
      fetchHeatmap();
    }
  });

  onMount(fetchMacroData);

  // Chart Data Preparation
  const evolutionChartData = $derived(evolutionData ? {
    labels: evolutionData.years,
    datasets: Object.keys(evolutionData.departments).slice(0, 10).map((dept, i) => ({
      label: dept,
      data: evolutionData.years.map((y: string) => evolutionData.departments[dept][y] || 0),
      borderColor: `hsl(${i * 40}, 70%, 50%)`,
      backgroundColor: `hsla(${i * 40}, 70%, 50%, 0.1)`,
      fill: true,
      tension: 0.4
    }))
  } : null);

  const deliveryChartData = $derived(deliveryData ? {
    labels: deliveryData.years,
    datasets: Object.keys(deliveryData.methods).map((method, i) => ({
      label: method,
      data: deliveryData.years.map((y: string) => deliveryData.methods[method][y] || 0),
      backgroundColor: method === "Online" ? "#6366f1" : method === "Hybrid" ? "#f59e0b" : "#94a3b8",
      borderRadius: 4
    }))
  } : null);

  // Heatmap Helpers
  const days = ["M", "T", "W", "Th", "F", "St", "Su"];
  const hours = Array.from({ length: 14 }, (_, i) => i + 1);
  
  function getHeatColor(count: number) {
    if (heatmapData.length === 0) return 'transparent';
    const max = Math.max(...heatmapData.map(d => d.count));
    const intensity = count / max;
    return `rgba(99, 102, 241, ${0.1 + intensity * 0.9})`;
  }

  function getSlotCount(day: string, hour: number) {
    const slot = heatmapData.find(d => d.day_code === day && d.slot_hour === hour);
    return slot ? slot.count : 0;
  }
</script>

<div class="space-y-8">
  <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
    <div>
      <h2 class="text-3xl font-bold text-slate-800 dark:text-slate-100 flex items-center space-x-3">
        <div class="p-2 bg-indigo-600 rounded-xl text-white">
          <TrendingUp size={24} />
        </div>
        <span>Trend Engine <span class="text-indigo-600 dark:text-indigo-400">Pro</span></span>
      </h2>
      <p class="text-slate-500 mt-2 dark:text-slate-400 font-medium">Deep historical intelligence across 50 years of academic evolution.</p>
    </div>

    <!-- Tab Navigation -->
    <div class="flex bg-slate-100 p-1.5 rounded-2xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800 overflow-x-auto no-scrollbar">
      <button 
        onclick={() => activeTab = "evolution"}
        class="flex items-center space-x-2 px-4 py-2 rounded-xl text-sm font-bold whitespace-nowrap transition-all {activeTab === 'evolution' ? 'bg-white text-indigo-600 shadow-sm dark:bg-slate-800 dark:text-white' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400'}"
      >
        <Activity size={16} />
        <span>Evolution</span>
      </button>
      <button 
        onclick={() => activeTab = "timespace"}
        class="flex items-center space-x-2 px-4 py-2 rounded-xl text-sm font-bold whitespace-nowrap transition-all {activeTab === 'timespace' ? 'bg-white text-indigo-600 shadow-sm dark:bg-slate-800 dark:text-white' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400'}"
      >
        <MapIcon size={16} />
        <span>Time & Space</span>
      </button>
      <button 
        onclick={() => activeTab = "discovery"}
        class="flex items-center space-x-2 px-4 py-2 rounded-xl text-sm font-bold whitespace-nowrap transition-all {activeTab === 'discovery' ? 'bg-white text-indigo-600 shadow-sm dark:bg-slate-800 dark:text-white' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400'}"
      >
        <Database size={16} />
        <span>Discovery</span>
      </button>
      <button 
        onclick={() => activeTab = "forecast"}
        class="flex items-center space-x-2 px-4 py-2 rounded-xl text-sm font-bold whitespace-nowrap transition-all {activeTab === 'forecast' ? 'bg-white text-indigo-600 shadow-sm dark:bg-slate-800 dark:text-white' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400'}"
      >
        <Zap size={16} />
        <span>Forecast</span>
      </button>
    </div>
  </div>

  {#if macroLoading && activeTab !== "forecast" && activeTab !== "timespace"}
    <div class="py-24 flex flex-col items-center justify-center space-y-4">
      <div class="animate-spin rounded-full h-12 w-12 border-4 border-slate-100 border-t-indigo-600 dark:border-slate-800 dark:border-t-indigo-500"></div>
      <p class="text-slate-500 dark:text-slate-400 font-medium">Compiling 50 years of data...</p>
    </div>
  {:else}
    <div class="transition-all duration-300">
      
      <!-- Evolution Tab -->
      {#if activeTab === "evolution"}
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <!-- Department Growth -->
          <div class="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm space-y-6 dark:bg-slate-900 dark:border-slate-800">
            <div class="flex items-center justify-between">
              <h3 class="text-xl font-bold text-slate-800 dark:text-slate-100">Departmental Expansion</h3>
              <div class="px-3 py-1 bg-emerald-50 text-emerald-600 text-[10px] font-black rounded-lg uppercase tracking-widest dark:bg-emerald-950/20">Top 10 High-Volume</div>
            </div>
            <div class="h-[300px]">
              {#if evolutionChartData}
                <Line 
                  data={evolutionChartData} 
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } }, x: { grid: { display: false } } }
                  }} 
                />
              {/if}
            </div>
          </div>

          <!-- Delivery Methods -->
          <div class="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm space-y-6 dark:bg-slate-900 dark:border-slate-800">
            <h3 class="text-xl font-bold text-slate-800 dark:text-slate-100">The Online Shift</h3>
            <div class="h-[300px]">
              {#if deliveryChartData}
                <Bar 
                  data={deliveryChartData} 
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { stacked: true, grid: { color: 'rgba(0,0,0,0.05)' } }, x: { stacked: true, grid: { display: false } } }
                  }} 
                />
              {/if}
            </div>
          </div>

          <!-- Stats Summary -->
          <div class="lg:col-span-2 grid grid-cols-1 md:grid-cols-4 gap-6">
             <div class="p-6 bg-indigo-600 rounded-3xl text-white shadow-xl shadow-indigo-200 dark:shadow-none">
                <div class="text-3xl font-black">{lifecycleData?.total_new || 0}</div>
                <div class="text-xs font-bold text-indigo-100 uppercase tracking-widest mt-1">New Courses (2yr)</div>
             </div>
             <div class="p-6 bg-slate-800 rounded-3xl text-white shadow-xl shadow-slate-200 dark:shadow-none dark:bg-slate-950">
                <div class="text-3xl font-black">{lifecycleData?.total_extinct || 0}</div>
                <div class="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">Extinct Courses</div>
             </div>
             <div class="p-6 bg-white rounded-3xl border border-slate-200 dark:bg-slate-900 dark:border-slate-800">
                <div class="text-3xl font-black text-slate-800 dark:text-slate-100">142k</div>
                <div class="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">Data Points</div>
             </div>
             <div class="p-6 bg-white rounded-3xl border border-slate-200 dark:bg-slate-900 dark:border-slate-800">
                <div class="text-3xl font-black text-slate-800 dark:text-slate-100">~120</div>
                <div class="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">Departments</div>
             </div>
          </div>
        </div>
      {/if}

      <!-- Time & Space Tab -->
      {#if activeTab === "timespace"}
        <div class="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm space-y-8 dark:bg-slate-900 dark:border-slate-800">
           <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div>
                <h3 class="text-xl font-bold text-slate-800 dark:text-slate-100">Scheduling Density Heatmap</h3>
                <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Visualizing peak scheduling hours across the entire university.</p>
              </div>
              <div class="flex items-center space-x-2">
                 <Filter size={16} class="text-slate-400" />
                 <select 
                    bind:value={selectedDecade}
                    onchange={fetchHeatmap}
                    class="p-2 bg-slate-50 border border-slate-200 rounded-xl text-sm font-bold dark:bg-slate-950 dark:border-slate-800"
                 >
                    <option value={null}>All Time</option>
                    {#each decades as decade}
                      <option value={decade}>{decade}s</option>
                    {/each}
                 </select>
              </div>
           </div>

           <div class="overflow-x-auto no-scrollbar">
             <table class="w-full border-separate border-spacing-1">
                <thead>
                  <tr>
                    <th class="w-12"></th>
                    {#each days as day}
                      <th class="p-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">{day}</th>
                    {/each}
                  </tr>
                </thead>
                <tbody>
                  {#each hours as hour}
                    <tr>
                      <td class="text-right pr-4 text-[10px] font-black text-slate-300 uppercase tracking-widest">{hour}</td>
                      {#each days as day}
                        {@const count = getSlotCount(day, hour)}
                        <td 
                          class="h-12 rounded-lg border border-slate-100 dark:border-slate-800 transition-all hover:ring-2 hover:ring-indigo-500 group relative cursor-help"
                          style="background-color: {getHeatColor(count)}"
                        >
                           {#if count > 0}
                             <div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                                <span class="text-[10px] font-black text-white bg-slate-900/80 px-2 py-1 rounded shadow-xl">
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

           <div class="flex items-center justify-center space-x-4 pt-4 border-t border-slate-50 dark:border-slate-800/60">
              <div class="flex items-center space-x-2">
                 <div class="w-3 h-3 rounded bg-indigo-50 dark:bg-indigo-950/40"></div>
                 <span class="text-[10px] font-bold text-slate-400 uppercase">Low Density</span>
              </div>
              <div class="flex items-center space-x-2">
                 <div class="w-3 h-3 rounded bg-indigo-600"></div>
                 <span class="text-[10px] font-bold text-slate-400 uppercase">High Density</span>
              </div>
           </div>
        </div>
      {/if}

      <!-- Discovery Tab -->
      {#if activeTab === "discovery"}
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
           <div class="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm space-y-6 dark:bg-slate-900 dark:border-slate-800">
              <div class="flex items-center space-x-3 text-emerald-600 dark:text-emerald-400">
                <Sparkles size={24} />
                <h3 class="text-xl font-bold">New Horizons</h3>
              </div>
              <p class="text-sm text-slate-500 dark:text-slate-400">Recently introduced course codes in the last 2 years.</p>
              <div class="flex flex-wrap gap-2">
                {#each lifecycleData?.new || [] as code}
                   <a href="/course/{code}" class="px-3 py-1.5 bg-emerald-50 text-emerald-700 text-xs font-bold rounded-xl border border-emerald-100 hover:bg-emerald-100 transition-colors dark:bg-emerald-950/20 dark:text-emerald-400 dark:border-emerald-900/50">
                     {code}
                   </a>
                {/each}
              </div>
           </div>

           <div class="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm space-y-6 dark:bg-slate-900 dark:border-slate-800">
              <div class="flex items-center space-x-3 text-slate-400 dark:text-slate-600">
                <Skull size={24} />
                <h3 class="text-xl font-bold">The Graveyard</h3>
              </div>
              <p class="text-sm text-slate-500 dark:text-slate-400">Courses that haven't been offered in over 10 years.</p>
              <div class="flex flex-wrap gap-2 opacity-60 grayscale hover:grayscale-0 transition-all">
                {#each lifecycleData?.extinct || [] as code}
                   <a href="/course/{code}" class="px-3 py-1.5 bg-slate-50 text-slate-600 text-xs font-bold rounded-xl border border-slate-200 dark:bg-slate-950 dark:text-slate-500 dark:border-slate-800">
                     {code}
                   </a>
                {/each}
              </div>
           </div>
        </div>
      {/if}

      <!-- Forecast Tab -->
      {#if activeTab === "forecast"}
        <div class="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm space-y-8 dark:bg-slate-900 dark:border-slate-800">
          <div class="max-w-2xl">
            <h3 class="text-xl font-bold text-slate-800 dark:text-slate-100">Course-Specific Forecasting</h3>
            <p class="text-sm text-slate-500 mt-2 dark:text-slate-400">Enter a course code to see historical offering probabilities and most likely time slots.</p>
            <div class="flex mt-6 space-x-2">
              <div class="relative flex-1">
                <Search class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <input 
                  type="text" 
                  bind:value={forecastQuery}
                  placeholder="e.g. MIS 116"
                  class="w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-200 rounded-2xl outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-mono font-bold text-lg dark:bg-slate-950 dark:border-slate-800 dark:text-white transition-all"
                />
              </div>
              <button 
                onclick={getForecast}
                disabled={forecastLoading}
                class="px-8 bg-indigo-600 text-white rounded-2xl font-bold hover:bg-indigo-700 transition-all disabled:opacity-50 shadow-lg shadow-indigo-200 dark:shadow-none flex items-center space-x-2"
              >
                {#if forecastLoading}
                  <div class="animate-spin rounded-full h-5 w-5 border-2 border-white/20 border-t-white"></div>
                {:else}
                  <Zap size={20} />
                {/if}
                <span>Forecast</span>
              </button>
            </div>
          </div>

          {#if forecastError}
            <div class="p-6 bg-red-50 text-red-600 rounded-2xl flex items-center space-x-4 border border-red-100 dark:bg-red-950/20 dark:text-red-400 dark:border-red-950/50">
              <AlertCircle size={24} />
              <span class="font-bold">{forecastError}</span>
            </div>
          {/if}

          {#if forecastData}
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 pt-8 border-t border-slate-100 dark:border-slate-800">
              <div class="space-y-6">
                <h4 class="text-sm font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center space-x-2">
                  <Calendar size={18} class="text-indigo-600 dark:text-indigo-400" />
                  <span>Offering Probability</span>
                </h4>
                <div class="space-y-6">
                  {#each Object.entries(forecastData.offering_probability) as [sem, prob]}
                    <div class="space-y-2">
                      <div class="flex justify-between items-end">
                        <span class="text-base font-bold text-slate-700 dark:text-slate-300">{sem} Semester</span>
                        <span class="text-2xl font-black text-indigo-600 dark:text-indigo-400">{Number(prob).toFixed(0)}%</span>
                      </div>
                      <div class="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-3 overflow-hidden">
                        <div class="bg-indigo-600 h-full rounded-full transition-all duration-1000" style="width: {prob}%"></div>
                      </div>
                    </div>
                  {/each}
                </div>
              </div>

              <div class="space-y-6">
                <h4 class="text-sm font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center space-x-2">
                  <Clock size={18} class="text-indigo-600 dark:text-indigo-400" />
                  <span>Historical Slot Archetypes</span>
                </h4>
                <div class="space-y-3">
                  {#each forecastData.predicted_slots as slot}
                    <div class="flex items-center justify-between p-4 bg-slate-50 rounded-2xl border border-slate-100 dark:bg-slate-950 dark:border-slate-850 transition-transform hover:scale-[1.02]">
                      <div class="flex items-center space-x-4">
                        <div class="w-12 h-12 bg-white rounded-xl shadow-sm flex items-center justify-center font-black text-xl text-indigo-700 border border-slate-200 dark:bg-slate-900 dark:border-slate-800 dark:text-indigo-300">
                          {slot.day}
                        </div>
                        <div>
                          <div class="text-base font-bold text-slate-800 dark:text-slate-200">Hour {slot.hour}</div>
                          <div class="text-xs text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider">Historical Context</div>
                        </div>
                      </div>
                      <div class="text-right">
                        <div class="text-xs font-black text-slate-300 dark:text-slate-600 uppercase mb-1">Confidence</div>
                        <div class="text-2xl font-black text-indigo-600 dark:text-indigo-400">{(slot.confidence_score * 100).toFixed(0)}%</div>
                      </div>
                    </div>
                  {/each}
                  {#if forecastData.predicted_slots.length === 0}
                     <div class="text-center py-12 text-slate-400">
                       <History size={48} class="mx-auto opacity-10 mb-2" />
                       <p class="font-medium">No recent slot data available for prediction.</p>
                     </div>
                  {/if}
                </div>
              </div>
            </div>
          {/if}
        </div>
      {/if}
      
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
  .no-scrollbar::-webkit-scrollbar {
    display: none;
  }
  .no-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
</style>
