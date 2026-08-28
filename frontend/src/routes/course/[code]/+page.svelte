<script lang="ts">
  import { page } from "$app/state";
  import { Calendar, User, Clock, MapPin, Hash, BookOpen, Info, Users, History, Activity } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import type { QuotaSnapshot, CourseChange, CourseHistoryItem } from "$lib/types";

  let courseCode = $derived(page.params.code);
  let history = $state<CourseHistoryItem[]>([]);
  let quotas = $state<QuotaSnapshot[]>([]);
  let changes = $state<CourseChange[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  async function fetchCourseData(targetCode?: string) {
    const code = targetCode || courseCode;
    if (!code) return;
    
    loading = true;
    error = null;
    try {
      const encodedCode = encodeURIComponent(code.trim());
      
      const [histRes, quotaRes, changeRes] = await Promise.allSettled([
        fetch(`${API_BASE}/v1/courses/history/${encodedCode}`),
        fetch(`${API_BASE}/v1/courses/${encodedCode}/quota`),
        fetch(`${API_BASE}/v1/courses/${encodedCode}/changes?limit=20`)
      ]);

      if (histRes.status === "fulfilled" && histRes.value.ok) {
        history = await histRes.value.json();
      } else if (histRes.status === "fulfilled" && histRes.value.status === 404) {
        throw new Error("Course history not found");
      } else {
        throw new Error("Failed to fetch course history");
      }

      if (quotaRes.status === "fulfilled" && quotaRes.value.ok) {
        quotas = await quotaRes.value.json();
      } else {
        quotas = [];
      }

      if (changeRes.status === "fulfilled" && changeRes.value.ok) {
        changes = await changeRes.value.json();
      } else {
        changes = [];
      }

    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  // Reactively re-fetch when courseCode changes (including on client-side routing)
  $effect(() => {
    if (courseCode) {
      fetchCourseData(courseCode);
    }
  });

  // Group by term
  const groupedHistory = $derived(
    history.reduce((acc: Record<string, CourseHistoryItem[]>, curr) => {
      if (!acc[curr.term_id]) acc[curr.term_id] = [];
      acc[curr.term_id].push(curr);
      return acc;
    }, {})
  );

  const latestInfo = $derived(history.length > 0 ? history[0] : null);
</script>

<div class="max-w-6xl mx-auto space-y-6 sm:space-y-8">
  {#if loading}
    <div class="py-20 flex flex-col items-center justify-center space-y-4">
      <div class="animate-spin rounded-full h-10 w-10 border-4 border-slate-100 border-t-[#002d72] dark:border-slate-800 dark:border-t-sky-400"></div>
      <p class="text-slate-500 dark:text-slate-400 font-medium text-sm">Retrieving historical records...</p>
    </div>
  {:else if error}
    <div class="bg-white rounded-3xl border-2 border-dashed border-red-200 p-12 sm:p-24 flex flex-col items-center justify-center text-center dark:bg-[#0f172a] dark:border-red-900/30">
      <div class="w-16 sm:w-20 h-16 sm:h-20 bg-red-50 rounded-full flex items-center justify-center text-red-300 mb-4 sm:mb-6 dark:bg-red-950 dark:text-red-900">
        <Info size={36} />
      </div>
      <h3 class="text-xl sm:text-2xl font-bold text-slate-800 dark:text-slate-200">{error}</h3>
      <p class="text-slate-500 dark:text-slate-400 mt-2 max-w-sm text-xs sm:text-sm">We couldn't find any historical data for the course code "{courseCode}".</p>
      <div class="flex flex-wrap justify-center gap-3 mt-6 sm:mt-8">
        <a href="/search" class="px-6 sm:px-8 py-2.5 sm:py-3 bg-[#002d72] text-white rounded-2xl text-xs sm:text-sm font-bold shadow-xs hover:bg-[#001f52] transition-colors">Back to Search</a>
        <button onclick={() => fetchCourseData()} class="px-6 sm:px-8 py-2.5 sm:py-3 bg-white border border-slate-200 text-slate-600 rounded-2xl text-xs sm:text-sm font-bold hover:bg-slate-50 transition-colors cursor-pointer">Retry</button>
      </div>
    </div>
  {:else}
    <!-- Header -->
    <header class="bg-white rounded-2xl sm:rounded-3xl border border-slate-200/80 p-5 sm:p-8 shadow-2xs dark:bg-[#0f172a] dark:border-slate-800/80">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div class="space-y-3 sm:space-y-4">
          <div class="flex items-center space-x-3">
            <span class="px-3 py-1 bg-[#002d72] text-white text-xs font-black rounded-lg uppercase tracking-wider shadow-xs dark:shadow-none">{courseCode}</span>
            <span class="text-xs font-black text-slate-300 dark:text-slate-600 uppercase tracking-widest">Historical Archive</span>
          </div>
          <h1 class="text-2xl sm:text-4xl font-black text-slate-800 dark:text-slate-100 leading-tight">{latestInfo?.title}</h1>
          <div class="flex flex-wrap gap-4 sm:gap-6 text-xs sm:text-sm">
             <div class="flex items-center space-x-1.5 text-slate-500 dark:text-slate-400 font-bold">
               <BookOpen size={16} class="text-[#0080c9] dark:text-sky-400 shrink-0" />
               <span>{latestInfo?.credits} Credits</span>
             </div>
             <div class="flex items-center space-x-1.5 text-slate-500 dark:text-slate-400 font-bold">
               <Hash size={16} class="text-[#0080c9] dark:text-sky-400 shrink-0" />
               <span>{latestInfo?.ects} ECTS</span>
             </div>
             <div class="flex items-center space-x-1.5 text-slate-500 dark:text-slate-400 font-bold">
               <Calendar size={16} class="text-[#0080c9] dark:text-sky-400 shrink-0" />
               <span>Offered in {Object.keys(groupedHistory).length} Semesters</span>
             </div>
          </div>
        </div>
      </div>
    </header>

    <!-- Live Quota Section (if available) -->
    {#if quotas.length > 0}
      <section class="bg-gradient-to-br from-[#002d72]/5 to-white dark:from-[#0f172a] dark:to-[#0f172a]/60 rounded-2xl sm:rounded-3xl border border-[#002d72]/15 dark:border-slate-800 p-5 sm:p-8 shadow-2xs space-y-4 sm:space-y-6">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div class="flex items-center space-x-3">
            <span class="p-2 bg-[#002d72] text-white rounded-xl shadow-xs shrink-0">
              <Users size={18} />
            </span>
            <div>
              <h2 class="text-base sm:text-lg font-black text-slate-800 dark:text-slate-100 tracking-tight">Live Term Quotas</h2>
              <p class="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400">Current registration portal snapshot for {quotas[0].term_id}</p>
            </div>
          </div>
          <div class="flex items-center space-x-1.5 text-xs font-semibold text-[#002d72] dark:text-sky-300 bg-[#002d72]/10 dark:bg-sky-500/15 px-3 py-1 rounded-full w-fit">
            <Activity size={13} class="animate-pulse" />
            <span>Updated {quotas[0].captured_at}</span>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {#each quotas as q}
            <div class="bg-white dark:bg-slate-950/60 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-4 sm:p-5 space-y-3 shadow-2xs">
              <div class="flex items-center justify-between">
                <span class="px-2.5 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-black rounded-lg">
                  Sec {q.section || '01'}
                </span>
                <span class="text-xs font-bold px-2 py-0.5 rounded-full {q.status === 'Open' || (q.available ?? 0) > 0 ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400' : 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-400'}">
                  {q.status || (q.available && q.available > 0 ? 'Open' : 'Full')}
                </span>
              </div>

              {#if q.department}
                <p class="text-xs text-slate-500 dark:text-slate-400 font-medium truncate">Department: <span class="font-bold text-slate-700 dark:text-slate-300">{q.department}</span></p>
              {/if}

              <div class="grid grid-cols-3 gap-1.5 pt-2 border-t border-slate-100 dark:border-slate-800/80 text-center">
                <div class="p-2 bg-slate-50 dark:bg-slate-900 rounded-xl">
                  <span class="block text-[9px] uppercase font-bold text-slate-400">Quota</span>
                  <span class="text-xs sm:text-sm font-black text-slate-800 dark:text-slate-200">{q.quota ?? '—'}</span>
                </div>
                <div class="p-2 bg-slate-50 dark:bg-slate-900 rounded-xl">
                  <span class="block text-[9px] uppercase font-bold text-slate-400">Current</span>
                  <span class="text-xs sm:text-sm font-black text-slate-800 dark:text-slate-200">{q.current ?? '—'}</span>
                </div>
                <div class="p-2 bg-slate-50 dark:bg-slate-900 rounded-xl">
                  <span class="block text-[9px] uppercase font-bold text-slate-400">Available</span>
                  <span class="text-xs sm:text-sm font-black {q.available && q.available > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-500'}">
                    {q.available ?? '0'}
                  </span>
                </div>
              </div>

              {#if q.is_consent || q.is_unlimited}
                <div class="flex flex-wrap gap-1.5 pt-1">
                  {#if q.is_consent}
                    <span class="text-[10px] font-bold px-2 py-0.5 bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400 rounded-md">Consent Required</span>
                  {/if}
                  {#if q.is_unlimited}
                    <span class="text-[10px] font-bold px-2 py-0.5 bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400 rounded-md">Unlimited</span>
                  {/if}
                </div>
              {/if}
            </div>
          {/each}
        </div>
      </section>
    {/if}

    <!-- Recent Schedule Changes (if available) -->
    {#if changes.length > 0}
      <section class="bg-white rounded-2xl sm:rounded-3xl border border-slate-200/80 dark:bg-[#0f172a] dark:border-slate-800/80 p-5 sm:p-8 shadow-2xs space-y-4">
        <div class="flex items-center space-x-3">
          <span class="p-2 bg-[#002d72]/10 dark:bg-sky-500/15 text-[#002d72] dark:text-sky-400 rounded-xl">
            <History size={18} />
          </span>
          <h2 class="text-base sm:text-lg font-black text-slate-800 dark:text-slate-100 tracking-tight">Recent Schedule Changes</h2>
        </div>

        <div class="space-y-2.5">
          {#each changes as ch}
            <div class="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 sm:p-4 bg-slate-50 dark:bg-slate-950/50 rounded-2xl border border-slate-100 dark:border-slate-800 gap-2">
              <div class="flex items-center space-x-2.5">
                <span class="px-2 py-0.5 text-[10px] sm:text-xs font-black uppercase rounded {ch.change_type === 'added' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' : ch.change_type === 'modified' ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300' : 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'}">
                  {ch.change_type}
                </span>
                <span class="text-xs font-bold text-slate-700 dark:text-slate-200">
                  Section {ch.section || 'All'} · {ch.details || 'Course updated'}
                </span>
              </div>
              <span class="text-[10px] sm:text-[11px] text-slate-400 dark:text-slate-500 font-mono">
                {ch.timestamp}
              </span>
            </div>
          {/each}
        </div>
      </section>
    {/if}

    <!-- History Timeline -->
    <div class="space-y-8 sm:space-y-12">
      {#each Object.keys(groupedHistory) as term}
        <section class="space-y-3 sm:space-y-4">
          <div class="flex items-center space-x-3">
            <span class="w-1.5 sm:w-2 h-6 sm:h-8 bg-[#002d72] dark:bg-sky-500 rounded-full"></span>
            <h2 class="text-lg sm:text-xl font-black text-slate-800 dark:text-slate-100 uppercase tracking-widest">{term}</h2>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {#each groupedHistory[term] as section}
              <div class="bg-white rounded-2xl border border-slate-200/80 p-4 sm:p-6 shadow-2xs hover:border-[#0080c9] dark:bg-[#0f172a] dark:border-slate-800/80 dark:hover:border-sky-500/50 transition-all group">
                <div class="flex items-center justify-between mb-3 sm:mb-4">
                  <div class="px-2 py-0.5 bg-slate-50 text-slate-500 text-[10px] font-black rounded uppercase dark:bg-slate-950 dark:text-slate-400">Section {section.section}</div>
                  <div class="text-[9px] sm:text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest">{section.delivery_method || 'Standard'}</div>
                </div>
                
                <div class="space-y-3 sm:space-y-4">
                  <div class="flex items-start space-x-3">
                    <User size={16} class="text-[#0080c9] dark:text-sky-400 mt-0.5 shrink-0" />
                    <div>
                      <p class="text-[9px] font-black text-slate-300 dark:text-slate-600 uppercase tracking-widest">Instructor</p>
                      <p class="text-xs sm:text-sm font-bold text-slate-700 dark:text-slate-200">{section.instructor}</p>
                    </div>
                  </div>

                  <div class="flex items-start space-x-3">
                    <Clock size={16} class="text-[#0080c9] dark:text-sky-400 mt-0.5 shrink-0" />
                    <div class="w-full">
                      <p class="text-[9px] font-black text-slate-300 dark:text-slate-600 uppercase tracking-widest">Schedule & Room</p>
                      <div class="space-y-1.5 mt-1">
                        {#each section.slots as slot}
                          <div class="flex items-center justify-between text-xs bg-slate-50 p-2 rounded-lg dark:bg-slate-950/50 border border-slate-100 dark:border-slate-800">
                             <div class="flex items-center space-x-1.5">
                               <span class="font-black text-[#002d72] dark:text-sky-400 w-4">{slot.day}</span>
                               <span class="text-slate-600 dark:text-slate-300">Slot {slot.hour}</span>
                             </div>
                             <div class="flex items-center space-x-1 text-slate-400 dark:text-slate-500 truncate max-w-[100px]">
                               <MapPin size={10} class="shrink-0" />
                               <span class="truncate font-bold">{slot.room}</span>
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

