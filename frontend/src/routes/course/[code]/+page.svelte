<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/state";
  import { Calendar, User, Clock, MapPin, Hash, BookOpen, ChevronRight, Info } from "lucide-svelte";
  import { API_BASE } from "$lib/config";

  let courseCode = $derived(page.params.code);
  let history = $state<any[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  async function fetchHistory() {
    if (!courseCode) return;
    
    loading = true;
    error = null;
    try {
      // Use encodeURIComponent to handle spaces and special characters safely
      const encodedCode = encodeURIComponent(courseCode.trim());
      const res = await fetch(`${API_BASE}/api/v1/courses/history/${encodedCode}`);
      
      if (!res.ok) {
        if (res.status === 404) {
          throw new Error("Course history not found");
        }
        throw new Error("Failed to fetch course history");
      }
      
      history = await res.json();
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  onMount(fetchHistory);

  // Group by term
  const groupedHistory = $derived(
    history.reduce((acc: any, curr: any) => {
      if (!acc[curr.term_id]) acc[curr.term_id] = [];
      acc[curr.term_id].push(curr);
      return acc;
    }, {})
  );

  const latestInfo = $derived(history.length > 0 ? history[0] : null);
</script>

<div class="max-w-6xl mx-auto space-y-8">
  {#if loading}
    <div class="py-24 flex flex-col items-center justify-center space-y-4">
      <div class="animate-spin rounded-full h-12 w-12 border-4 border-slate-100 border-t-indigo-600 dark:border-slate-800 dark:border-t-indigo-500"></div>
      <p class="text-slate-500 dark:text-slate-400 font-medium">Retrieving historical records...</p>
    </div>
  {:else if error}
    <div class="bg-white rounded-3xl border-2 border-dashed border-red-200 p-24 flex flex-col items-center justify-center text-center dark:bg-slate-900 dark:border-red-900/30">
      <div class="w-20 h-20 bg-red-50 rounded-full flex items-center justify-center text-red-300 mb-6 dark:bg-red-950 dark:text-red-900">
        <Info size={40} />
      </div>
      <h3 class="text-2xl font-bold text-slate-800 dark:text-slate-200">{error}</h3>
      <p class="text-slate-500 dark:text-slate-400 mt-2 max-w-sm">We couldn't find any historical data for the course code "{courseCode}".</p>
      <div class="flex space-x-4 mt-8">
        <a href="/search" class="px-8 py-3 bg-indigo-600 text-white rounded-2xl font-bold shadow-xl shadow-indigo-200 dark:shadow-none hover:bg-indigo-700 transition-colors">Back to Search</a>
        <button onclick={fetchHistory} class="px-8 py-3 bg-white border border-slate-200 text-slate-600 rounded-2xl font-bold hover:bg-slate-50 transition-colors">Retry</button>
      </div>
    </div>
  {:else}
    <!-- Header -->
    <header class="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm dark:bg-slate-900 dark:border-slate-800">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div class="space-y-4">
          <div class="flex items-center space-x-3">
            <span class="px-3 py-1 bg-indigo-600 text-white text-xs font-black rounded-lg uppercase tracking-wider shadow-lg shadow-indigo-200 dark:shadow-none">{courseCode}</span>
            <span class="text-xs font-black text-slate-300 dark:text-slate-600 uppercase tracking-widest">Historical Archive</span>
          </div>
          <h1 class="text-4xl font-black text-slate-800 dark:text-slate-100 leading-tight">{latestInfo?.title}</h1>
          <div class="flex flex-wrap gap-6 text-sm">
             <div class="flex items-center space-x-2 text-slate-500 dark:text-slate-400 font-bold">
               <BookOpen size={16} class="text-indigo-500" />
               <span>{latestInfo?.credits} Credits</span>
             </div>
             <div class="flex items-center space-x-2 text-slate-500 dark:text-slate-400 font-bold">
               <Hash size={16} class="text-indigo-500" />
               <span>{latestInfo?.ects} ECTS</span>
             </div>
             <div class="flex items-center space-x-2 text-slate-500 dark:text-slate-400 font-bold">
               <Calendar size={16} class="text-indigo-500" />
               <span>Offered in {Object.keys(groupedHistory).length} Semesters</span>
             </div>
          </div>
        </div>
      </div>
    </header>

    <!-- History Timeline -->
    <div class="space-y-12">
      {#each Object.keys(groupedHistory) as term}
        <section class="space-y-4">
          <div class="flex items-center space-x-4">
            <h2 class="text-xl font-black text-slate-800 dark:text-slate-100 uppercase tracking-widest flex items-center space-x-3">
               <span class="w-2 h-8 bg-indigo-600 rounded-full"></span>
               <span>{term}</span>
            </h2>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {#each groupedHistory[term] as section}
              <div class="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm hover:border-indigo-300 dark:bg-slate-900 dark:border-slate-800 dark:hover:border-indigo-500/50 transition-all group">
                <div class="flex items-center justify-between mb-4">
                  <div class="px-2 py-1 bg-slate-50 text-slate-500 text-[10px] font-black rounded uppercase dark:bg-slate-950 dark:text-slate-400">Section {section.section}</div>
                  <div class="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest">{section.delivery_method || 'Standard'}</div>
                </div>
                
                <div class="space-y-4">
                  <div class="flex items-start space-x-3">
                    <User size={18} class="text-indigo-500 mt-0.5 shrink-0" />
                    <div>
                      <p class="text-[10px] font-black text-slate-300 dark:text-slate-600 uppercase tracking-widest">Instructor</p>
                      <p class="text-sm font-bold text-slate-700 dark:text-slate-200">{section.instructor}</p>
                    </div>
                  </div>

                  <div class="flex items-start space-x-3">
                    <Clock size={18} class="text-indigo-500 mt-0.5 shrink-0" />
                    <div class="w-full">
                      <p class="text-[10px] font-black text-slate-300 dark:text-slate-600 uppercase tracking-widest">Schedule & Room</p>
                      <div class="space-y-2 mt-1">
                        {#each section.slots as slot}
                          <div class="flex items-center justify-between text-xs bg-slate-50 p-2 rounded-lg dark:bg-slate-950/50 border border-slate-100 dark:border-slate-800">
                             <div class="flex items-center space-x-2">
                               <span class="font-black text-indigo-600 dark:text-indigo-400 w-4">{slot.day}</span>
                               <span class="text-slate-600 dark:text-slate-300">Slot {slot.hour}</span>
                             </div>
                             <div class="flex items-center space-x-1 text-slate-400 dark:text-slate-500">
                               <MapPin size={10} />
                               <span class="truncate max-w-[80px] font-bold">{slot.room}</span>
                             </div>
                          </div>
                        {/each}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            {/each}
          </div>
        </section>
      {/each}
    </div>
  {/if}
</div>
