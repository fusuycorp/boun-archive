<script lang="ts">
  import { Search, TrendingUp, Calendar, Clock, AlertCircle } from "lucide-svelte";
  import { API_BASE } from "$lib/config";

  let query = $state("");
  let prediction = $state<any>(null);
  let loading = $state(false);
  let error = $state("");

  async function getPrediction() {
    if (!query) return;
    loading = true;
    error = "";
    prediction = null;
    try {
      const res = await fetch(`${API_BASE}/api/v1/predict/course/${query.toUpperCase()}`);
      if (!res.ok) throw new Error("Course not found in historical records");
      prediction = await res.json();
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  }
</script>

<div class="space-y-8">
  <div>
    <h2 class="text-3xl font-bold text-slate-800 dark:text-slate-100">Trend Engine</h2>
    <p class="text-slate-500 mt-2 dark:text-slate-400">Predictive course scheduling based on 50 years of data.</p>
  </div>

  <div class="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6 dark:bg-slate-900 dark:border-slate-800">
    <div class="max-w-md">
      <label class="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest">Enter Course Code</label>
      <div class="flex mt-2 space-x-2">
        <input 
          type="text" 
          bind:value={query}
          placeholder="e.g. INTT514"
          class="flex-1 p-3 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 font-mono font-bold dark:bg-slate-950 dark:border-slate-800 dark:text-white"
        />
        <button 
          onclick={getPrediction}
          class="px-6 py-3 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 transition-colors flex items-center space-x-2"
        >
          <TrendingUp size={18} />
          <span>Forecast</span>
        </button>
      </div>
    </div>

    {#if loading}
      <div class="py-12 flex justify-center">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 dark:border-indigo-500"></div>
      </div>
    {/if}

    {#if error}
      <div class="p-4 bg-red-50 text-red-600 rounded-xl flex items-center space-x-3 border border-red-100 dark:bg-red-950/20 dark:text-red-400 dark:border-red-950/50">
        <AlertCircle size={20} />
        <span class="font-medium">{error}</span>
      </div>
    {/if}

    {#if prediction}
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 pt-6 border-t border-slate-100 dark:border-slate-800">
        <!-- Offering Probability -->
        <div class="space-y-4">
          <h3 class="text-lg font-bold text-slate-800 dark:text-slate-100 flex items-center space-x-2">
            <Calendar size={20} class="text-indigo-600 dark:text-indigo-400" />
            <span>Offering Probability</span>
          </h3>
          <div class="space-y-3">
            {#each Object.entries(prediction.offering_probability) as [sem, prob]}
              <div>
                <div class="flex justify-between text-sm font-bold mb-1">
                  <span class="text-slate-600 dark:text-slate-300">{sem}</span>
                  <span class="text-indigo-600 dark:text-indigo-400">{Number(prob).toFixed(1)}%</span>
                </div>
                <div class="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2">
                  <div class="bg-indigo-600 h-2 rounded-full" style="width: {prob}%"></div>
                </div>
              </div>
            {/each}
          </div>
        </div>

        <!-- Predicted Slots -->
        <div class="space-y-4">
          <h3 class="text-lg font-bold text-slate-800 dark:text-slate-100 flex items-center space-x-2">
            <Clock size={20} class="text-indigo-600 dark:text-indigo-400" />
            <span>Most Likely Slots</span>
          </h3>
          <div class="space-y-2">
            {#each prediction.predicted_slots as slot}
              <div class="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-100 dark:bg-slate-950 dark:border-slate-850">
                <div class="flex items-center space-x-4">
                  <div class="w-10 h-10 bg-white rounded-lg flex items-center justify-center font-bold text-indigo-700 border border-slate-200 dark:bg-slate-900 dark:border-slate-800 dark:text-indigo-300">
                    {slot.day}
                  </div>
                  <div>
                    <div class="text-sm font-bold text-slate-800 dark:text-slate-200">Hour {slot.hour}</div>
                    <div class="text-xs text-slate-500 dark:text-slate-400 font-medium">Historical Confidence</div>
                  </div>
                </div>
                <div class="text-right">
                  <div class="text-lg font-black text-indigo-600 dark:text-indigo-400">{(slot.confidence_score * 100).toFixed(0)}%</div>
                </div>
              </div>
            {/each}
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>
