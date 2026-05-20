<script lang="ts">
  import { TrendingUp, LayoutGrid } from "lucide-svelte";
  const stats = [
    { label: "Total Courses", value: "136,939", change: "+12%", trend: "up" },
    { label: "Total Slots", value: "326,812", change: "+5%", trend: "up" },
    { label: "Unique Instructors", value: "2,625", change: "+2%", trend: "up" },
    { label: "Years of Data", value: "50+", change: "Historical", trend: "neutral" },
  ];
</script>

<div class="space-y-8">
  <div class="flex items-end justify-between">
    <div>
      <h2 class="text-3xl font-bold text-slate-800 dark:text-slate-100">University Overview</h2>
      <p class="text-slate-500 mt-2 dark:text-slate-400">Historical trends and global university metrics.</p>
    </div>
    <div class="flex space-x-2">
      <button class="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium hover:bg-slate-50 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800/60">Export Data</button>
      <button class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors">Update Index</button>
    </div>
  </div>

  <!-- Stats Grid -->
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
    {#each stats as stat}
      <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm transition-colors duration-200 dark:bg-slate-900 dark:border-slate-800">
        <p class="text-sm text-slate-500 font-medium dark:text-slate-400">{stat.label}</p>
        <div class="flex items-baseline justify-between mt-2">
          <h3 class="text-2xl font-bold text-slate-900 dark:text-white">{stat.value}</h3>
          <span class="text-xs font-semibold px-2 py-1 rounded-full 
            {stat.trend === 'up' 
              ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/20 dark:text-emerald-400' 
              : 'bg-slate-50 text-slate-600 dark:bg-slate-800 dark:text-slate-400'}">
            {stat.change}
          </span>
        </div>
      </div>
    {/each}
  </div>

  <!-- Chart Placeholder -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <div class="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200 shadow-sm h-96 flex flex-col items-center justify-center text-slate-400 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-500">
      <div class="mb-4"><TrendingUp size={48} /></div>
      <p class="font-medium text-lg text-slate-600 dark:text-slate-300">Department Growth (1970 - 2024)</p>
      <p class="text-sm dark:text-slate-400">Connect to backend to visualize 50-year trends</p>
    </div>
    
    <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm h-96 flex flex-col items-center justify-center text-slate-400 text-center dark:bg-slate-900 dark:border-slate-800 dark:text-slate-500">
       <div class="mb-4"><LayoutGrid size={48} /></div>
       <p class="font-medium text-lg text-slate-600 dark:text-slate-300">Global Campus Activity</p>
       <p class="text-sm px-4 dark:text-slate-400">Heatmap of building utilization across all historical terms</p>
    </div>
  </div>
</div>
