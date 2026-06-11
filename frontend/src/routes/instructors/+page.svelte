<script lang="ts">
  import { onMount } from "svelte";
  import { User, Search, History, BookOpen, Clock, Calendar, ArrowRight } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import { goto } from "$app/navigation";

  let query = $state("");
  let instructors = $state<any[]>([]);
  let loading = $state(false);

  async function searchInstructors() {
    if (query.length < 2) {
      instructors = [];
      return;
    }
    const res = await fetch(`${API_BASE}/v1/instructors?q=${query}`);
    instructors = await res.json();
  }

  function selectInstructor(id: number) {
    goto(`/instructor/${id}`);
  }

  let timeout: any;
  function handleInput() {
    clearTimeout(timeout);
    timeout = setTimeout(searchInstructors, 300);
  }
</script>

<div class="space-y-8 max-w-4xl mx-auto">
  <div class="text-center space-y-4 py-12">
    <div class="inline-flex p-4 bg-indigo-50 dark:bg-indigo-950/40 rounded-3xl text-indigo-600 dark:text-indigo-400 mb-2">
      <User size={48} />
    </div>
    <h2 class="text-4xl font-black text-slate-800 dark:text-slate-100">Instructor Archive</h2>
    <p class="text-slate-500 max-w-lg mx-auto dark:text-slate-400 font-medium text-lg">Search and explore the historical teaching history and academic footprints of Bogazici faculty.</p>
  </div>

  <!-- Search -->
  <div class="relative group">
    <Search class="absolute left-6 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-indigo-500 transition-colors" size={24} />
    <input
      type="text"
      bind:value={query}
      oninput={handleInput}
      placeholder="Search for an instructor (e.g. SEMA SAKARYA)..."
      class="w-full pl-16 pr-6 py-6 bg-white border border-slate-200 rounded-3xl shadow-xl outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 text-xl transition-all dark:bg-slate-900 dark:border-slate-800 dark:text-white"
    />
    
    {#if instructors.length > 0}
      <div class="absolute w-full mt-4 bg-white border border-slate-200 rounded-3xl shadow-2xl z-50 overflow-hidden dark:bg-slate-900 dark:border-slate-800">
        <div class="p-3 border-b border-slate-50 bg-slate-50/50 dark:bg-slate-950/50 dark:border-slate-800">
           <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest px-3">Top Matches</span>
        </div>
        {#each instructors as inst}
          <button 
            onclick={() => selectInstructor(inst.id)}
            class="w-full text-left px-6 py-4 hover:bg-indigo-50 border-b border-slate-50 last:border-0 flex items-center justify-between group dark:hover:bg-indigo-900/20 dark:border-slate-800 transition-colors"
          >
            <div class="flex items-center space-x-4">
              <div class="w-10 h-10 bg-slate-100 rounded-full flex items-center justify-center text-slate-400 group-hover:bg-white dark:bg-slate-800 dark:text-slate-600 transition-colors">
                 <User size={20} />
              </div>
              <span class="font-bold text-slate-700 dark:text-slate-200 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">{inst.full_name}</span>
            </div>
            <ArrowRight size={18} class="text-slate-300 opacity-0 group-hover:opacity-100 -translate-x-4 group-hover:translate-x-0 transition-all" />
          </button>
        {/each}
      </div>
    {/if}
  </div>

  <!-- Featured / Recent (Optional future enhancement) -->
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 pt-12">
     <div class="p-8 bg-white rounded-3xl border border-slate-200 dark:bg-slate-900 dark:border-slate-800">
        <h4 class="text-sm font-black text-slate-400 uppercase tracking-widest mb-4">Historical Reach</h4>
        <p class="text-2xl font-bold text-slate-800 dark:text-slate-100">Across 50 years of academic cycles.</p>
     </div>
     <div class="p-8 bg-indigo-600 rounded-3xl text-white shadow-xl shadow-indigo-200 dark:shadow-none">
        <h4 class="text-sm font-black text-indigo-200 uppercase tracking-widest mb-4">Data Coverage</h4>
        <p class="text-2xl font-bold">140,000+ course instances mapped to instructors.</p>
     </div>
  </div>
</div>
