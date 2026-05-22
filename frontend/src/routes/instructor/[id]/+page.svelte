<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/state";
  import { User, History, BookOpen, Clock, Calendar, Download, Info, ArrowLeft } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import { exportToCSV } from "$lib/utils";

  let instructorId = $derived(page.params.id);
  let legacyData = $state<any>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);

  async function fetchInstructorDNA() {
    if (!instructorId) return;
    loading = true;
    error = null;
    try {
      const res = await fetch(`${API_BASE}/api/v1/analytics/instructor/${instructorId}/legacy`);
      if (!res.ok) throw new Error("Instructor DNA not found");
      legacyData = await res.json();
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  function handleExport() {
    if (!legacyData || legacyData.history.length === 0) return;
    
    const exportData = legacyData.history.map((item: any) => ({
      instructor: legacyData.instructor_name,
      term: item.term,
      course_code: item.course_code,
      title: item.title
    }));
    
    exportToCSV(exportData, `boun_instructor_${legacyData.instructor_name.replace(/\s+/g, '_')}_history_${new Date().toISOString().split('T')[0]}`);
  }

  onMount(fetchInstructorDNA);
</script>

<div class="max-w-6xl mx-auto space-y-8">
  <div class="flex items-center justify-between">
    <div class="flex items-center space-x-4">
      <a href="/instructors" class="p-2 bg-white border border-slate-200 rounded-xl text-slate-400 hover:text-indigo-600 hover:border-indigo-100 transition-all dark:bg-slate-900 dark:border-slate-800">
        <ArrowLeft size={20} />
      </a>
      <div>
        <h2 class="text-3xl font-bold text-slate-800 dark:text-slate-100">Instructor DNA</h2>
        <p class="text-slate-500 mt-1 dark:text-slate-400">Historical teaching history and academic footprint.</p>
      </div>
    </div>
    
    {#if legacyData}
       <button 
          onclick={handleExport}
          class="flex items-center space-x-2 bg-white border border-slate-200 text-slate-600 px-4 py-2 rounded-xl text-xs font-bold hover:bg-slate-50 transition-colors shadow-sm dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700"
       >
         <Download size={14} />
         <span>Export History CSV</span>
       </button>
    {/if}
  </div>

  {#if loading}
    <div class="py-24 flex flex-col items-center justify-center space-y-4">
      <div class="animate-spin rounded-full h-12 w-12 border-4 border-slate-100 border-t-indigo-600 dark:border-slate-800 dark:border-t-indigo-500"></div>
      <p class="text-slate-500 dark:text-slate-400 font-medium">Extracting academic DNA...</p>
    </div>
  {:else if error}
    <div class="bg-white rounded-3xl border-2 border-dashed border-red-200 p-24 flex flex-col items-center justify-center text-center dark:bg-slate-900 dark:border-red-900/30">
      <div class="w-20 h-20 bg-red-50 rounded-full flex items-center justify-center text-red-300 mb-6 dark:bg-red-950 dark:text-red-900">
        <Info size={40} />
      </div>
      <h3 class="text-2xl font-bold text-slate-800 dark:text-slate-200">{error}</h3>
      <p class="text-slate-500 dark:text-slate-400 mt-2 max-w-sm">We couldn't find any historical records for this instructor ID.</p>
      <a href="/instructors" class="mt-8 px-8 py-3 bg-indigo-600 text-white rounded-2xl font-bold shadow-xl shadow-indigo-200 dark:shadow-none hover:bg-indigo-700 transition-colors">Back to Search</a>
    </div>
  {:else if legacyData}
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Stats Summary -->
      <div class="lg:col-span-1 space-y-6">
        <div class="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6 dark:bg-slate-900 dark:border-slate-800">
          <div class="flex flex-col items-center text-center">
             <div class="w-20 h-20 bg-indigo-50 dark:bg-indigo-950/40 rounded-full flex items-center justify-center text-indigo-600 dark:text-indigo-400 mb-4">
               <User size={40} />
             </div>
             <h3 class="text-xl font-bold text-slate-800 dark:text-slate-100 leading-tight">{legacyData.instructor_name}</h3>
             <p class="text-sm text-slate-400 font-medium uppercase tracking-widest mt-1">Instructor Legacy</p>
          </div>

          <div class="grid grid-cols-2 gap-4 border-t border-slate-50 dark:border-slate-800/60 pt-6">
            <div class="text-center">
              <div class="text-2xl font-black text-indigo-600 dark:text-indigo-400">{legacyData.total_semesters_taught}</div>
              <div class="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase">Semesters</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-black text-indigo-600 dark:text-indigo-400">{legacyData.total_courses_taught}</div>
              <div class="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase">Total Classes</div>
            </div>
          </div>
        </div>

        <!-- Preferred Slots -->
        <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4 dark:bg-slate-900 dark:border-slate-800">
          <h4 class="text-sm font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center space-x-2">
            <Clock size={16} class="text-indigo-500 dark:text-indigo-400" />
            <span>Preferred Slots</span>
          </h4>
          <div class="space-y-2">
            {#each legacyData.preferred_slots as slot}
              <div class="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100 dark:bg-slate-950 dark:border-slate-800/60">
                 <div class="flex items-center space-x-3">
                   <span class="w-8 h-8 bg-white rounded flex items-center justify-center text-xs font-bold border border-slate-200 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-200">{slot.day}</span>
                   <span class="text-sm font-bold text-slate-700 dark:text-slate-300">Hour {slot.hour}</span>
                 </div>
                 <span class="text-xs font-black text-indigo-600 dark:text-indigo-400">{slot.frequency}x</span>
              </div>
            {/each}
          </div>
        </div>
      </div>

      <!-- Teaching History -->
      <div class="lg:col-span-2 space-y-6">
        <div class="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm dark:bg-slate-900 dark:border-slate-800">
          <h4 class="text-sm font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center space-x-2 mb-6">
            <History size={18} class="text-indigo-500 dark:text-indigo-400" />
            <span>Teaching History Timeline</span>
          </h4>
          
          <div class="space-y-4 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
            {#each legacyData.history as item}
              <div class="flex items-start space-x-4 p-4 rounded-xl border border-slate-50 hover:border-indigo-100 hover:bg-indigo-50/30 transition-all dark:border-slate-800/40 dark:hover:border-indigo-950/40 dark:hover:bg-indigo-950/15">
                <div class="text-xs font-black text-indigo-600 bg-white px-3 py-1 rounded-full border border-indigo-100 whitespace-nowrap dark:bg-slate-900 dark:border-indigo-900/40 dark:text-indigo-400">
                  {item.term}
                </div>
                <div class="flex-1">
                  <a href="/course/{item.course_code}" class="text-sm font-bold text-slate-800 dark:text-slate-200 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                    {item.course_code}
                  </a>
                  <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{item.title}</div>
                </div>
              </div>
            {/each}
          </div>
        </div>

        <!-- Most Frequent -->
        <div class="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm dark:bg-slate-900 dark:border-slate-800">
           <h4 class="text-sm font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center space-x-2 mb-6">
            <BookOpen size={18} class="text-indigo-500 dark:text-indigo-400" />
            <span>Most Frequent Courses</span>
          </h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            {#each Object.entries(legacyData.most_frequent_courses) as [code, count]}
               <div class="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-100 dark:bg-slate-950 dark:border-slate-850">
                  <a href="/course/{code}" class="text-sm font-black text-slate-700 dark:text-slate-350 hover:text-indigo-600 transition-colors">{code}</a>
                  <div class="flex items-center space-x-2">
                    <div class="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase">Taught</div>
                    <span class="text-lg font-black text-indigo-600 dark:text-indigo-400">{count}x</span>
                  </div>
               </div>
            {/each}
          </div>
        </div>
      </div>
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
</style>
