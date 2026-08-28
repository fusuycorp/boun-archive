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
      const res = await fetch(`${API_BASE}/v1/analytics/instructor/${instructorId}/legacy`);
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

<div class="max-w-6xl mx-auto space-y-6 sm:space-y-8">
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
    <div class="flex items-center space-x-3 sm:space-x-4">
      <a href="/instructors" class="p-2 bg-white border border-slate-200/80 rounded-xl text-slate-400 hover:text-[#002d72] hover:border-[#002d72]/20 transition-all dark:bg-[#0f172a] dark:border-slate-800 shadow-2xs" aria-label="Back to instructors">
        <ArrowLeft size={18} />
      </a>
      <div>
        <h2 class="text-2xl sm:text-3xl font-black text-slate-800 dark:text-slate-100 tracking-tight">Instructor DNA</h2>
        <p class="text-xs sm:text-sm text-slate-500 mt-0.5 dark:text-slate-400">Historical teaching history and academic footprint.</p>
      </div>
    </div>
    
    {#if legacyData}
       <button 
          onclick={handleExport}
          class="flex items-center justify-center space-x-2 bg-white border border-slate-200/80 text-slate-600 px-4 py-2 rounded-xl text-xs font-bold hover:bg-slate-50 hover:text-[#002d72] transition-colors shadow-2xs dark:bg-[#0f172a] dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800/80 cursor-pointer w-full sm:w-auto"
       >
         <Download size={14} />
         <span>Export History CSV</span>
       </button>
    {/if}
  </div>

  {#if loading}
    <div class="py-20 flex flex-col items-center justify-center space-y-4">
      <div class="animate-spin rounded-full h-10 w-10 border-4 border-slate-100 border-t-[#002d72] dark:border-slate-800 dark:border-t-sky-400"></div>
      <p class="text-slate-500 dark:text-slate-400 font-medium text-sm">Extracting academic DNA...</p>
    </div>
  {:else if error}
    <div class="bg-white rounded-3xl border-2 border-dashed border-red-200 p-12 sm:p-24 flex flex-col items-center justify-center text-center dark:bg-[#0f172a] dark:border-red-900/30">
      <div class="w-16 sm:w-20 h-16 sm:h-20 bg-red-50 rounded-full flex items-center justify-center text-red-300 mb-4 sm:mb-6 dark:bg-red-950 dark:text-red-900">
        <Info size={36} />
      </div>
      <h3 class="text-xl sm:text-2xl font-bold text-slate-800 dark:text-slate-200">{error}</h3>
      <p class="text-slate-500 dark:text-slate-400 mt-2 max-w-sm text-xs sm:text-sm">We couldn't find any historical records for this instructor ID.</p>
      <a href="/instructors" class="mt-6 px-6 sm:px-8 py-2.5 sm:py-3 bg-[#002d72] text-white rounded-2xl text-xs sm:text-sm font-bold shadow-xs hover:bg-[#001f52] transition-colors">Back to Search</a>
    </div>
  {:else if legacyData}
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">
      <!-- Stats Summary -->
      <div class="lg:col-span-1 space-y-6">
        <div class="bg-white p-5 sm:p-8 rounded-2xl sm:rounded-3xl border border-slate-200/80 shadow-2xs space-y-6 dark:bg-[#0f172a] dark:border-slate-800/80">
          <div class="flex flex-col items-center text-center">
             <div class="w-16 sm:w-20 h-16 sm:h-20 bg-[#002d72]/10 dark:bg-sky-500/15 rounded-full flex items-center justify-center text-[#002d72] dark:text-sky-400 mb-3 sm:mb-4">
               <User size={32} class="sm:w-10 sm:h-10" />
             </div>
             <h3 class="text-lg sm:text-xl font-bold text-slate-800 dark:text-slate-100 leading-tight">{legacyData.instructor_name}</h3>
             <p class="text-xs text-slate-400 font-medium uppercase tracking-widest mt-1">Instructor Legacy</p>
          </div>

          <div class="grid grid-cols-2 gap-4 border-t border-slate-50 dark:border-slate-800/60 pt-6">
            <div class="text-center">
              <div class="text-xl sm:text-2xl font-black text-[#002d72] dark:text-sky-400">{legacyData.total_semesters_taught}</div>
              <div class="text-[9px] sm:text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase">Semesters</div>
            </div>
            <div class="text-center">
              <div class="text-xl sm:text-2xl font-black text-[#002d72] dark:text-sky-400">{legacyData.total_courses_taught}</div>
              <div class="text-[9px] sm:text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase">Total Classes</div>
            </div>
          </div>
        </div>

        <!-- Preferred Slots -->
        <div class="bg-white p-5 sm:p-6 rounded-2xl border border-slate-200/80 shadow-2xs space-y-4 dark:bg-[#0f172a] dark:border-slate-800/80">
          <h4 class="text-xs sm:text-sm font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center space-x-2">
            <Clock size={16} class="text-[#0080c9] dark:text-sky-400" />
            <span>Preferred Slots</span>
          </h4>
          <div class="space-y-2">
            {#each legacyData.preferred_slots as slot}
              <div class="flex items-center justify-between p-2.5 sm:p-3 bg-slate-50 rounded-xl border border-slate-100 dark:bg-slate-950 dark:border-slate-800/60">
                 <div class="flex items-center space-x-3">
                   <span class="w-7 h-7 sm:w-8 sm:h-8 bg-white rounded flex items-center justify-center text-xs font-bold border border-slate-200 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-200">{slot.day}</span>
                   <span class="text-xs sm:text-sm font-bold text-slate-700 dark:text-slate-300">Hour {slot.hour}</span>
                 </div>
                 <span class="text-xs font-black text-[#002d72] dark:text-sky-400">{slot.frequency}x</span>
              </div>
            {/each}
          </div>
        </div>
      </div>

      <!-- Teaching History -->
      <div class="lg:col-span-2 space-y-6">
        <div class="bg-white p-5 sm:p-8 rounded-2xl sm:rounded-3xl border border-slate-200/80 shadow-2xs dark:bg-[#0f172a] dark:border-slate-800/80">
          <h4 class="text-xs sm:text-sm font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center space-x-2 mb-4 sm:mb-6">
            <History size={16} class="text-[#0080c9] dark:text-sky-400" />
            <span>Teaching History Timeline</span>
          </h4>
          
          <div class="space-y-3 max-h-[500px] sm:max-h-[600px] overflow-y-auto pr-1 custom-scrollbar">
            {#each legacyData.history as item}
              <div class="flex items-start space-x-3 sm:space-x-4 p-3 sm:p-4 rounded-xl border border-slate-50 hover:border-[#002d72]/20 hover:bg-[#002d72]/5 transition-all dark:border-slate-800/40 dark:hover:border-sky-500/30 dark:hover:bg-sky-500/10">
                <div class="text-[11px] sm:text-xs font-black text-[#002d72] bg-white px-2.5 sm:px-3 py-1 rounded-full border border-[#002d72]/20 whitespace-nowrap dark:bg-slate-900 dark:border-sky-500/40 dark:text-sky-300 font-mono">
                  {item.term}
                </div>
                <div class="flex-1 min-w-0">
                  <a href="/course/{item.course_code}" class="text-xs sm:text-sm font-bold text-slate-800 dark:text-slate-200 hover:text-[#0080c9] dark:hover:text-sky-300 transition-colors block truncate">
                    {item.course_code}
                  </a>
                  <div class="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400 mt-0.5 truncate">{item.title}</div>
                </div>
              </div>
            {/each}
          </div>
        </div>

        <!-- Most Frequent -->
        <div class="bg-white p-5 sm:p-8 rounded-2xl sm:rounded-3xl border border-slate-200/80 shadow-2xs dark:bg-[#0f172a] dark:border-slate-800/80">
           <h4 class="text-xs sm:text-sm font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center space-x-2 mb-4 sm:mb-6">
            <BookOpen size={16} class="text-[#0080c9] dark:text-sky-400" />
            <span>Most Frequent Courses</span>
          </h4>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
            {#each Object.entries(legacyData.most_frequent_courses) as [code, count]}
               <div class="flex items-center justify-between p-3 sm:p-4 bg-slate-50 rounded-xl border border-slate-100 dark:bg-slate-950 dark:border-slate-800">
                  <a href="/course/{code}" class="text-xs sm:text-sm font-black text-slate-700 dark:text-slate-300 hover:text-[#0080c9] dark:hover:text-sky-300 transition-colors">{code}</a>
                  <div class="flex items-center space-x-1.5">
                    <div class="text-[9px] text-slate-400 dark:text-slate-500 font-bold uppercase">Taught</div>
                    <span class="text-base sm:text-lg font-black text-[#002d72] dark:text-sky-400">{count}x</span>
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
