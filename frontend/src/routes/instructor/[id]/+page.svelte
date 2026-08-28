<script lang="ts">
  import { page } from "$app/state";
  import { User, History, BookOpen, Clock, Calendar, Download, Info, ArrowLeft } from "lucide-svelte";
  import { exportToCSV } from "$lib/utils";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();

  let instructorId = $derived(data.instructorId || page.params.id);
  let legacyData = $derived(data.legacyData);
  let loading = $state(false);
  let error = $derived(data.error);

  function handleExport() {
    if (!legacyData || !legacyData.history || legacyData.history.length === 0) return;
    
    const exportData = legacyData.history.map((item: any) => ({
      instructor: legacyData.instructor_name,
      term: item.term,
      course_code: item.course_code,
      title: item.title
    }));
    
    exportToCSV(exportData, `boun_instructor_${legacyData.instructor_name.replace(/\s+/g, '_')}_history_${new Date().toISOString().split('T')[0]}`);
  }
</script>

<div class="max-w-6xl mx-auto space-y-6 sm:space-y-8">
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
    <div class="flex items-center space-x-3 sm:space-x-4">
      <a href="/instructors" class="p-2 bg-[#f7f5ee] border border-[#dbd7cc] rounded-lg text-[#746f65] hover:text-[#1c1b18] hover:border-[#c8c3b5] transition-colors dark:bg-[#18181b] dark:border-[#27272a] dark:hover:text-neutral-200 shadow-2xs" aria-label="Back to instructors">
        <ArrowLeft size={17} />
      </a>
      <div>
        <h1 class="font-serif text-2xl sm:text-3xl font-bold text-[#1c1b18] dark:text-neutral-50 tracking-tight">Instructor DNA</h1>
        <p class="font-sans text-xs sm:text-sm text-[#746f65] mt-0.5 dark:text-neutral-400">Historical teaching footprint and curricular legacy.</p>
      </div>
    </div>
    
    {#if legacyData}
       <button 
          onclick={handleExport}
          class="flex items-center justify-center space-x-2 bg-[#f7f5ee] border border-[#dbd7cc] text-[#45423b] px-4 py-2 rounded-lg text-xs font-semibold hover:bg-[#dedacb] transition-colors shadow-2xs dark:bg-[#18181b] dark:border-[#27272a] dark:text-neutral-300 dark:hover:bg-[#232328] cursor-pointer w-full sm:w-auto"
       >
         <Download size={13} />
         <span>Export History CSV</span>
       </button>
    {/if}
  </div>

  {#if loading}
    <div class="py-20 flex flex-col items-center justify-center space-y-3">
      <div class="animate-spin rounded-full h-8 w-8 border-3 border-[#dbd7cc] border-t-[#002d72] dark:border-neutral-800 dark:border-t-amber-400"></div>
      <p class="text-[#746f65] dark:text-neutral-400 font-medium text-xs">Extracting instructor DNA...</p>
    </div>
  {:else if error}
    <div class="bg-[#f7f5ee] rounded-xl border border-dashed border-red-200 p-12 sm:p-20 flex flex-col items-center justify-center text-center dark:bg-[#18181b] dark:border-red-900/30">
      <div class="w-14 h-14 bg-red-50 rounded-full flex items-center justify-center text-red-400 mb-4 dark:bg-red-950/40 dark:text-red-400">
        <Info size={28} />
      </div>
      <h3 class="font-serif text-xl sm:text-2xl font-bold text-[#1c1b18] dark:text-neutral-200">{error}</h3>
      <p class="text-[#746f65] dark:text-neutral-400 mt-2 max-w-sm text-xs sm:text-sm">We couldn't find any historical records for this instructor ID.</p>
      <a href="/instructors" class="mt-6 px-6 py-2.5 bg-[#002d72] text-white rounded-lg text-xs font-semibold shadow-2xs hover:bg-[#001f52] transition-colors">Back to Search</a>
    </div>
  {:else if legacyData}
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">
      <!-- Stats Summary -->
      <div class="lg:col-span-1 space-y-6">
        <div class="bg-[#f7f5ee] p-5 sm:p-6 rounded-xl border border-[#dbd7cc] shadow-2xs space-y-6 dark:bg-[#18181b] dark:border-[#27272a]">
          <div class="flex flex-col items-center text-center">
             <div class="w-16 h-16 bg-[#002d72]/10 dark:bg-amber-400/10 rounded-full flex items-center justify-center text-[#002d72] dark:text-amber-400 mb-3">
               <User size={28} />
             </div>
             <h2 class="font-serif text-lg sm:text-xl font-bold text-[#1c1b18] dark:text-neutral-100 leading-tight">{legacyData.instructor_name}</h2>
             <p class="font-mono text-[10px] text-[#746f65] font-semibold uppercase tracking-wider mt-1">Faculty Member</p>
          </div>

          <div class="grid grid-cols-2 gap-4 border-t border-[#dbd7cc] dark:border-[#27272a] pt-5">
            <div class="text-center">
              <div class="font-serif text-2xl sm:text-3xl font-bold text-[#1c1b18] dark:text-neutral-100">{legacyData.total_semesters_taught}</div>
              <div class="font-mono text-[10px] text-[#746f65] dark:text-neutral-500 uppercase tracking-wider">Semesters</div>
            </div>
            <div class="text-center">
              <div class="font-serif text-2xl sm:text-3xl font-bold text-[#1c1b18] dark:text-neutral-100">{legacyData.total_courses_taught}</div>
              <div class="font-mono text-[10px] text-[#746f65] dark:text-neutral-500 uppercase tracking-wider">Classes</div>
            </div>
          </div>
        </div>

        <!-- Preferred Slots -->
        <div class="bg-[#f7f5ee] p-5 sm:p-6 rounded-xl border border-[#dbd7cc] shadow-2xs space-y-4 dark:bg-[#18181b] dark:border-[#27272a]">
          <h2 class="font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider flex items-center space-x-2">
            <Clock size={14} class="text-[#0080c9] dark:text-amber-400" />
            <span>Preferred Lecture Slots</span>
          </h2>
          <div class="space-y-2 font-mono">
            {#each legacyData.preferred_slots as slot}
              <div class="flex items-center justify-between p-2.5 bg-[#eeece2] rounded-lg border border-[#dbd7cc] dark:bg-[#121214] dark:border-[#27272a]">
                 <div class="flex items-center space-x-2.5">
                   <span class="w-7 h-7 bg-[#f7f5ee] rounded flex items-center justify-center text-xs font-bold border border-[#dbd7cc] dark:bg-[#18181b] dark:border-[#27272a] dark:text-neutral-200">{slot.day}</span>
                   <span class="text-xs font-semibold text-[#45423b] dark:text-neutral-300">Hour {slot.hour}</span>
                 </div>
                 <span class="text-xs font-bold text-[#002d72] dark:text-amber-400">{slot.frequency}x</span>
              </div>
            {/each}
          </div>
        </div>
      </div>

      <!-- Teaching History -->
      <div class="lg:col-span-2 space-y-6">
        <div class="bg-[#f7f5ee] p-5 sm:p-6 rounded-xl border border-[#dbd7cc] shadow-2xs dark:bg-[#18181b] dark:border-[#27272a]">
          <h2 class="font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider flex items-center space-x-2 mb-4">
            <History size={14} class="text-[#0080c9] dark:text-amber-400" />
            <span>Teaching History Timeline</span>
          </h2>
          
          <div class="space-y-2.5 max-h-[480px] sm:max-h-[560px] overflow-y-auto pr-1 custom-scrollbar">
            {#each legacyData.history as item}
              <div class="flex items-start space-x-3 p-3 rounded-lg border border-[#dbd7cc]/70 hover:border-[#dbd7cc] hover:bg-[#edeae0] transition-colors dark:border-[#27272a] dark:hover:bg-[#232328]">
                <div class="text-[10px] font-mono font-semibold text-[#45423b] bg-[#e7e4d9] px-2.5 py-0.5 rounded border border-[#dbd7cc] whitespace-nowrap dark:bg-[#121214] dark:border-[#27272a] dark:text-neutral-300">
                  {item.term}
                </div>
                <div class="flex-1 min-w-0">
                  <a href="/course/{item.course_code}" class="font-mono text-xs font-bold text-[#002d72] dark:text-neutral-100 hover:text-[#0080c9] dark:hover:text-amber-400 transition-colors block truncate">
                    {item.course_code}
                  </a>
                  <div class="font-serif text-xs text-[#5c5850] dark:text-neutral-400 mt-0.5 truncate">{item.title}</div>
                </div>
              </div>
            {/each}
          </div>
        </div>

        <!-- Most Frequent -->
        <div class="bg-[#f7f5ee] p-5 sm:p-6 rounded-xl border border-[#dbd7cc] shadow-2xs dark:bg-[#18181b] dark:border-[#27272a]">
           <h2 class="font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider flex items-center space-x-2 mb-4">
            <BookOpen size={14} class="text-[#0080c9] dark:text-amber-400" />
            <span>Most Frequently Taught Courses</span>
          </h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {#each Object.entries(legacyData.most_frequent_courses) as [code, count]}
               <div class="flex items-center justify-between p-3 bg-[#eeece2] rounded-lg border border-[#dbd7cc] dark:bg-[#121214] dark:border-[#27272a]">
                  <a href="/course/{code}" class="font-mono text-xs font-bold text-[#1c1b18] dark:text-neutral-200 hover:text-[#002d72] dark:hover:text-amber-400 transition-colors">{code}</a>
                  <div class="flex items-center space-x-1.5 font-mono">
                    <span class="text-[9px] text-[#746f65] uppercase font-semibold">Taught</span>
                    <span class="text-sm font-bold text-[#002d72] dark:text-amber-400">{count}x</span>
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
