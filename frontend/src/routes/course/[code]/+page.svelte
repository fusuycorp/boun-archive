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
    <div class="py-20 flex flex-col items-center justify-center space-y-3">
      <div class="animate-spin rounded-full h-8 w-8 border-3 border-[#dbd7cc] border-t-[#002d72] dark:border-neutral-800 dark:border-t-amber-400"></div>
      <p class="text-[#746f65] dark:text-neutral-400 font-medium text-xs">Retrieving historical records...</p>
    </div>
  {:else if error}
    <div class="bg-[#f7f5ee] rounded-xl border border-dashed border-red-200 p-12 sm:p-20 flex flex-col items-center justify-center text-center dark:bg-[#18181b] dark:border-red-900/30">
      <div class="w-14 h-14 bg-red-50 rounded-full flex items-center justify-center text-red-400 mb-4 dark:bg-red-950/40 dark:text-red-400">
        <Info size={28} />
      </div>
      <h2 class="font-serif text-xl sm:text-2xl font-bold text-[#1c1b18] dark:text-neutral-200">{error}</h2>
      <p class="text-[#746f65] dark:text-neutral-400 mt-2 max-w-sm text-xs sm:text-sm">We couldn't find any historical data for the course code "{courseCode}".</p>
      <div class="flex flex-wrap justify-center gap-3 mt-6">
        <a href="/search" class="px-6 py-2.5 bg-[#002d72] text-white rounded-lg text-xs font-semibold shadow-2xs hover:bg-[#001f52] transition-colors">Back to Search</a>
        <button onclick={() => fetchCourseData()} class="px-6 py-2.5 bg-[#f7f5ee] border border-[#dbd7cc] text-[#45423b] rounded-lg text-xs font-semibold hover:bg-[#dedacb] dark:bg-[#27272a] dark:border-[#3f3f46] dark:text-neutral-200 transition-colors cursor-pointer">Retry</button>
      </div>
    </div>
  {:else}
    <!-- Header -->
    <header class="bg-[#f7f5ee] rounded-xl border border-[#dbd7cc] p-5 sm:p-7 shadow-2xs dark:bg-[#18181b] dark:border-[#27272a]">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div class="space-y-3">
          <div class="flex items-center space-x-3">
            <span class="px-2.5 py-1 bg-[#002d72] text-white font-mono text-xs font-bold rounded uppercase tracking-wider shadow-2xs dark:bg-amber-400/10 dark:text-amber-300 dark:border dark:border-amber-400/20">{courseCode}</span>
            <span class="font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-widest">Academic Catalog</span>
          </div>
          <h1 class="font-serif text-2xl sm:text-4xl font-bold text-[#1c1b18] dark:text-neutral-50 leading-tight">{latestInfo?.title}</h1>
          <div class="flex flex-wrap gap-4 sm:gap-6 text-xs font-mono">
             <div class="flex items-center space-x-1.5 text-[#5c5850] dark:text-neutral-400">
               <BookOpen size={14} class="text-[#0080c9] dark:text-amber-400 shrink-0" />
               <span>{latestInfo?.credits} Credits</span>
             </div>
             <div class="flex items-center space-x-1.5 text-[#5c5850] dark:text-neutral-400">
               <Hash size={14} class="text-[#0080c9] dark:text-amber-400 shrink-0" />
               <span>{latestInfo?.ects} ECTS</span>
             </div>
             <div class="flex items-center space-x-1.5 text-[#5c5850] dark:text-neutral-400">
               <Calendar size={14} class="text-[#0080c9] dark:text-amber-400 shrink-0" />
               <span>Offered in {Object.keys(groupedHistory).length} Semesters</span>
             </div>
          </div>
        </div>
      </div>
    </header>

    <!-- Live Quota Section (if available) -->
    {#if quotas.length > 0}
      <section class="bg-[#f7f5ee] dark:bg-[#18181b] rounded-xl border border-[#dbd7cc] dark:border-[#27272a] p-5 sm:p-6 shadow-2xs space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div class="flex items-center space-x-3">
            <span class="p-2 bg-[#002d72] dark:bg-[#27272a] text-white dark:text-amber-400 rounded-lg shadow-2xs shrink-0">
              <Users size={16} />
            </span>
            <div>
              <h2 class="font-serif text-base sm:text-lg font-bold text-[#1c1b18] dark:text-neutral-100 tracking-tight">Live Term Quotas</h2>
              <p class="font-sans text-[11px] sm:text-xs text-[#746f65] dark:text-neutral-400">Current registration portal capacity for {quotas[0].term_id}</p>
            </div>
          </div>
          <div class="flex items-center space-x-1.5 font-mono text-[11px] font-medium text-emerald-800 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-600/20 px-2.5 py-1 rounded-md w-fit">
            <Activity size={12} class="animate-pulse" />
            <span>Updated {quotas[0].captured_at}</span>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {#each quotas as q}
            <div class="bg-[#eeece2]/60 dark:bg-[#121214] rounded-xl border border-[#dbd7cc] dark:border-[#27272a] p-4 space-y-3 shadow-2xs">
              <div class="flex items-center justify-between">
                <span class="px-2 py-0.5 bg-[#dedacb] dark:bg-[#27272a] text-[#1c1b18] dark:text-neutral-200 font-mono text-xs font-bold rounded">
                  Sec {q.section || '01'}
                </span>
                <span class="font-mono text-[11px] font-semibold px-2 py-0.5 rounded border {q.status === 'Open' || (q.available ?? 0) > 0 ? 'bg-emerald-500/10 text-emerald-800 border-emerald-600/20 dark:text-emerald-400' : 'bg-rose-500/10 text-rose-800 border-rose-600/20 dark:text-rose-400'}">
                  {q.status || (q.available && q.available > 0 ? 'Open' : 'Full')}
                </span>
              </div>

              {#if q.department}
                <p class="text-xs text-[#746f65] dark:text-neutral-400 font-medium truncate font-mono">Dept: <span class="font-bold text-[#1c1b18] dark:text-neutral-200">{q.department}</span></p>
              {/if}

              <div class="grid grid-cols-3 gap-1.5 pt-2 border-t border-[#dbd7cc] dark:border-[#27272a] text-center font-mono">
                <div class="p-1.5 bg-[#f7f5ee] dark:bg-[#18181b] rounded border border-[#dbd7cc]/70 dark:border-[#27272a]">
                  <span class="block text-[8px] uppercase font-bold text-[#746f65]">Quota</span>
                  <span class="text-xs sm:text-sm font-bold text-[#1c1b18] dark:text-neutral-200">{q.quota ?? '—'}</span>
                </div>
                <div class="p-1.5 bg-[#f7f5ee] dark:bg-[#18181b] rounded border border-[#dbd7cc]/70 dark:border-[#27272a]">
                  <span class="block text-[8px] uppercase font-bold text-[#746f65]">Current</span>
                  <span class="text-xs sm:text-sm font-bold text-[#1c1b18] dark:text-neutral-200">{q.current ?? '—'}</span>
                </div>
                <div class="p-1.5 bg-[#f7f5ee] dark:bg-[#18181b] rounded border border-[#dbd7cc]/70 dark:border-[#27272a]">
                  <span class="block text-[8px] uppercase font-bold text-[#746f65]">Available</span>
                  <span class="text-xs sm:text-sm font-bold {q.available && q.available > 0 ? 'text-emerald-800 dark:text-emerald-400' : 'text-[#746f65]'}">
                    {q.available ?? '0'}
                  </span>
                </div>
              </div>

              {#if q.is_consent || q.is_unlimited}
                <div class="flex flex-wrap gap-1.5 pt-1 font-mono text-[9px]">
                  {#if q.is_consent}
                    <span class="px-2 py-0.5 bg-amber-500/10 text-amber-950 dark:bg-amber-400/10 dark:text-amber-300 rounded border border-amber-500/20 font-semibold">Consent Required</span>
                  {/if}
                  {#if q.is_unlimited}
                    <span class="px-2 py-0.5 bg-sky-500/10 text-sky-950 dark:bg-sky-400/10 dark:text-sky-300 rounded border border-sky-500/20 font-semibold">Unlimited</span>
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
      <section class="bg-[#f7f5ee] rounded-xl border border-[#dbd7cc] dark:bg-[#18181b] dark:border-[#27272a] p-5 sm:p-6 shadow-2xs space-y-4">
        <div class="flex items-center space-x-3">
          <span class="p-2 bg-[#002d72]/10 dark:bg-[#27272a] text-[#002d72] dark:text-amber-400 rounded-lg">
            <History size={16} />
          </span>
          <h2 class="font-serif text-base sm:text-lg font-bold text-[#1c1b18] dark:text-neutral-100 tracking-tight">Recent Schedule Audit Log</h2>
        </div>

        <div class="space-y-2">
          {#each changes as ch}
            <div class="flex flex-col sm:flex-row sm:items-center justify-between p-3 bg-[#eeece2] dark:bg-[#121214] rounded-lg border border-[#dbd7cc] dark:border-[#27272a] gap-2 font-mono">
              <div class="flex items-center space-x-2.5">
                <span class="px-2 py-0.5 text-[10px] font-bold uppercase rounded border {ch.change_type === 'added' ? 'bg-emerald-500/10 text-emerald-900 border-emerald-600/20 dark:text-emerald-400' : ch.change_type === 'modified' ? 'bg-amber-500/10 text-amber-950 border-amber-500/20 dark:text-amber-300' : 'bg-rose-500/10 text-rose-900 border-rose-600/20 dark:text-rose-400'}">
                  {ch.change_type}
                </span>
                <span class="text-xs text-[#1c1b18] dark:text-neutral-200">
                  Section {ch.section || 'All'} · {ch.details || 'Course updated'}
                </span>
              </div>
              <span class="text-[10px] text-[#746f65] dark:text-neutral-500">
                {ch.timestamp}
              </span>
            </div>
          {/each}
        </div>
      </section>
    {/if}

    <!-- History Timeline -->
    <div class="space-y-6 sm:space-y-8">
      {#each Object.keys(groupedHistory) as term}
        <section class="space-y-3">
          <div class="flex items-center space-x-2.5">
            <span class="w-1.5 h-5 bg-[#002d72] dark:bg-amber-400 rounded-full"></span>
            <h2 class="font-mono text-base font-bold text-[#1c1b18] dark:text-neutral-100 uppercase tracking-wider">{term}</h2>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {#each groupedHistory[term] as section}
              <div class="bg-[#f7f5ee] rounded-xl border border-[#dbd7cc] p-4 sm:p-5 shadow-2xs hover:border-[#c8c3b5] dark:bg-[#18181b] dark:border-[#27272a] dark:hover:border-neutral-700 transition-colors group space-y-3">
                <div class="flex items-center justify-between">
                  <div class="px-2 py-0.5 bg-[#e7e4d9] dark:bg-[#27272a] text-[#45423b] dark:text-neutral-300 text-[10px] font-mono font-bold rounded uppercase">Section {section.section}</div>
                  <div class="text-[9px] font-mono font-semibold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider">{section.delivery_method || 'Standard'}</div>
                </div>
                
                <div class="space-y-2.5">
                  <div class="flex items-start space-x-2.5">
                    <User size={14} class="text-[#746f65] mt-0.5 shrink-0" />
                    <div>
                      <p class="font-mono text-[9px] text-[#746f65] uppercase tracking-wider">Instructor</p>
                      <p class="text-xs sm:text-sm font-semibold text-[#1c1b18] dark:text-neutral-200">{section.instructor}</p>
                    </div>
                  </div>

                  <div class="flex items-start space-x-2.5">
                    <Clock size={14} class="text-[#746f65] mt-0.5 shrink-0" />
                    <div class="w-full">
                      <p class="font-mono text-[9px] text-[#746f65] uppercase tracking-wider">Schedule & Room</p>
                      <div class="space-y-1 mt-1 font-mono">
                        {#each section.slots as slot}
                          <div class="flex items-center justify-between text-xs bg-[#eeece2] p-1.5 rounded dark:bg-[#121214] border border-[#dbd7cc] dark:border-[#27272a]">
                             <div class="flex items-center space-x-1.5">
                               <span class="font-bold text-[#002d72] dark:text-amber-400 w-4">{slot.day}</span>
                               <span class="text-[#5c5850] dark:text-neutral-400">Slot {slot.hour}</span>
                             </div>
                             <div class="flex items-center space-x-1 text-[#746f65] truncate max-w-[100px]">
                               <MapPin size={9} class="shrink-0" />
                               <span class="truncate font-semibold">{slot.room}</span>
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

