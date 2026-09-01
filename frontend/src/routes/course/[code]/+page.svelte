<script lang="ts">
  import { page } from "$app/state";
  import { Calendar, User, Clock, MapPin, Hash, BookOpen, Info, Users, Activity, Download } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import { formatSlotTime } from "$lib/utils";
  import { generateCourseJsonLd } from "$lib/semantic";
  import { generateICS, downloadICS } from "$lib/ical";
  import type { QuotaSnapshot, CourseHistoryItem } from "$lib/types";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();

  let courseCode = $derived(data.courseCode || page.params.code || "");
  let history = $state<CourseHistoryItem[]>([]);
  let quotas = $state<QuotaSnapshot[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);

  $effect(() => {
    history = data.history ?? [];
    quotas = data.quotas ?? [];
    error = data.error ?? null;
  });

  async function fetchCourseData(targetCode?: string) {
    const code = targetCode || courseCode;
    if (!code) return;
    
    loading = true;
    error = null;
    try {
      const encodedCode = encodeURIComponent(code.trim());
      
      const [histRes, quotaRes] = await Promise.allSettled([
        fetch(`${API_BASE}/v1/courses/history/${encodedCode}`),
        fetch(`${API_BASE}/v1/courses/${encodedCode}/quota`)
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

    } catch (e) {
      error = e instanceof Error ? e.message : "An unexpected error occurred";
    } finally {
      loading = false;
    }
  }

  // Group by term
  const groupedHistory = $derived(
    history.reduce((acc: Record<string, CourseHistoryItem[]>, curr) => {
      if (!acc[curr.term_id]) acc[curr.term_id] = [];
      acc[curr.term_id].push(curr);
      return acc;
    }, {})
  );

  const latestInfo = $derived(history.length > 0 ? history[0] : null);

  function exportScheduleICS() {
    if (!history || history.length === 0) return;
    const latestTerm = latestInfo?.term_id;
    const latestCourses = history.filter(h => h.term_id === latestTerm);
    const icsString = generateICS(latestCourses.length > 0 ? latestCourses : history, `${courseCode} Schedule`, courseCode);
    downloadICS(icsString, `boun_${courseCode.replace(/\s+/g, '_')}_schedule`);
  }
</script>

<svelte:head>
  <title>{courseCode} {latestInfo?.title ? `- ${latestInfo.title}` : ''} • BOUN Archive</title>
  <meta name="description" content="Academic offering history, instructors, credits, timetable slots, and quota records for {courseCode} ({latestInfo?.title || ''}) at Boğaziçi University." />
  <meta property="og:title" content="{courseCode}: {latestInfo?.title || 'Course Details'} • BOUN Archive" />
  <meta property="og:description" content="Explore course offerings, syllabus credits, instructors, and quota history for {courseCode} at Boğaziçi University." />
  <meta property="og:url" content="https://archive.bogazici.app/course/{encodeURIComponent(courseCode || '')}" />
  <meta property="og:type" content="article" />
  <meta name="DC.title" content="{courseCode}: {latestInfo?.title || ''}" />
  <meta name="DC.creator" content="Boğaziçi University" />
  <meta name="DC.identifier" content="https://archive.bogazici.app/course/{encodeURIComponent(courseCode || '')}" />
  <meta name="DC.type" content="Course" />
  {@html `<script type="application/ld+json">${JSON.stringify(generateCourseJsonLd(courseCode || '', history, latestInfo))}<\/script>`}
</svelte:head>

<div class="max-w-6xl mx-auto space-y-6 sm:space-y-8">
  {#if loading}
    <div class="py-20 flex flex-col items-center justify-center space-y-3">
      <div class="animate-spin rounded-full h-8 w-8 border-3 border-[#e5e0d8] border-t-[#002d72] dark:border-slate-800 dark:border-t-[#8cc8ea]"></div>
      <p class="text-[#525f7f] dark:text-slate-400 font-medium text-xs">Retrieving historical records...</p>
    </div>
  {:else if error}
    <div class="bg-white rounded-xl border border-dashed border-red-200 p-12 sm:p-20 flex flex-col items-center justify-center text-center dark:bg-[#121827] dark:border-red-900/30">
      <div class="w-14 h-14 bg-red-50 rounded-full flex items-center justify-center text-red-400 mb-4 dark:bg-red-950/40 dark:text-red-400">
        <Info size={28} />
      </div>
      <h2 class="font-serif text-xl sm:text-2xl font-bold text-[#161e2e] dark:text-slate-200">{error}</h2>
      <p class="text-[#525f7f] dark:text-slate-400 mt-2 max-w-sm text-xs sm:text-sm">We couldn't find any historical data for the course code "{courseCode}".</p>
      <div class="flex flex-wrap justify-center gap-3 mt-6">
        <a href="/search" class="px-6 py-2.5 bg-[#002d72] text-white rounded-lg text-xs font-semibold shadow-2xs hover:bg-[#001b44] transition-colors">Back to Search</a>
        <button onclick={() => fetchCourseData()} class="px-6 py-2.5 bg-white border border-[#e5e0d8] text-[#161e2e] rounded-lg text-xs font-semibold hover:bg-[#f3efe6] dark:bg-slate-800 dark:border-slate-700 dark:text-slate-200 transition-colors cursor-pointer">Retry</button>
      </div>
    </div>
  {:else}
    <!-- Header -->
    <header class="bg-white rounded-xl border border-[#e5e0d8] p-5 sm:p-7 shadow-2xs dark:bg-[#121827] dark:border-[#1e293b]">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div class="space-y-3">
          <div class="flex items-center space-x-3">
            <span class="px-2.5 py-1 bg-[#002d72] text-white font-mono text-xs font-bold rounded uppercase tracking-wider shadow-2xs dark:bg-[#8cc8ea]/15 dark:text-[#8cc8ea] dark:border dark:border-[#8cc8ea]/30">{courseCode}</span>
            <span class="font-mono text-[10px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-widest">Academic Catalog</span>
          </div>
          <h1 class="font-serif text-2xl sm:text-4xl font-bold text-[#002d72] dark:text-slate-50 leading-tight">{latestInfo?.title}</h1>
          <div class="flex flex-wrap gap-4 sm:gap-6 text-xs font-mono">
             <div class="flex items-center space-x-1.5 text-[#525f7f] dark:text-slate-400">
               <BookOpen size={14} class="text-[#0080c9] dark:text-[#8cc8ea] shrink-0" />
               <span>{latestInfo?.credits ?? '—'} Credits</span>
             </div>
             <div class="flex items-center space-x-1.5 text-[#525f7f] dark:text-slate-400">
               <Hash size={14} class="text-[#0080c9] dark:text-[#8cc8ea] shrink-0" />
               <span>{latestInfo?.ects ?? '—'} ECTS</span>
             </div>
             <div class="flex items-center space-x-1.5 text-[#525f7f] dark:text-slate-400">
               <Calendar size={14} class="text-[#0080c9] dark:text-[#8cc8ea] shrink-0" />
               <span>Offered in {Object.keys(groupedHistory).length} Semesters</span>
             </div>
          </div>
        </div>

        {#if history.length > 0}
          <div class="flex items-center gap-2">
            <button
              onclick={exportScheduleICS}
              class="flex items-center space-x-2 bg-[#faf8f5] dark:bg-[#0a0e1a] border border-[#e5e0d8] dark:border-[#1e293b] text-[#002d72] dark:text-[#8cc8ea] px-4 py-2.5 rounded-lg text-xs font-semibold hover:bg-[#e5e0d8]/50 dark:hover:bg-slate-800 transition-colors shadow-2xs cursor-pointer"
              title="Download RFC 5545 iCalendar file for Google Calendar / Apple Calendar"
            >
              <Download size={14} />
              <span>Export iCal (.ics)</span>
            </button>
          </div>
        {/if}
      </div>
    </header>

    <!-- Live Quota Section (if available) -->
    {#if quotas.length > 0}
      <section class="bg-white dark:bg-[#121827] rounded-xl border border-[#e5e0d8] dark:border-[#1e293b] p-5 sm:p-6 shadow-2xs space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div class="flex items-center space-x-3">
            <span class="p-2 bg-[#002d72] dark:bg-slate-800 text-white dark:text-[#8cc8ea] rounded-lg shadow-2xs shrink-0">
              <Users size={16} />
            </span>
            <div>
              <h2 class="font-serif text-base sm:text-lg font-bold text-[#002d72] dark:text-slate-100 tracking-tight">Live Term Quotas</h2>
              <p class="font-sans text-[11px] sm:text-xs text-[#525f7f] dark:text-slate-400">Current registration portal capacity for {quotas[0].term_id}</p>
            </div>
          </div>
          <div class="flex items-center space-x-1.5 font-mono text-[11px] font-medium text-emerald-800 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-600/20 px-2.5 py-1 rounded-md w-fit">
            <Activity size={12} class="animate-pulse" />
            <span>Updated {quotas[0].captured_at}</span>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {#each quotas as q}
            <div class="bg-[#faf8f5] dark:bg-[#0a0e1a] rounded-xl border border-[#e5e0d8] dark:border-[#1e293b] p-4 space-y-3 shadow-2xs">
              <div class="flex items-center justify-between">
                <span class="px-2 py-0.5 bg-[#e5e0d8] dark:bg-slate-800 text-[#161e2e] dark:text-slate-200 font-mono text-xs font-bold rounded">
                  Sec {q.section || '01'}
                </span>
                <span class="font-mono text-[11px] font-semibold px-2 py-0.5 rounded border {q.status === 'Open' || (q.available ?? 0) > 0 ? 'bg-emerald-500/10 text-emerald-800 border-emerald-600/20 dark:text-emerald-400' : 'bg-rose-500/10 text-rose-800 border-rose-600/20 dark:text-rose-400'}">
                  {q.status || (q.available && q.available > 0 ? 'Open' : 'Full')}
                </span>
              </div>

              {#if q.department}
                <p class="text-xs text-[#525f7f] dark:text-slate-400 font-medium truncate font-mono">Dept: <span class="font-bold text-[#161e2e] dark:text-slate-200">{q.department}</span></p>
              {/if}

              <div class="grid grid-cols-3 gap-1.5 pt-2 border-t border-[#e5e0d8] dark:border-[#1e293b] text-center font-mono">
                <div class="p-1.5 bg-white dark:bg-[#121827] rounded border border-[#e5e0d8] dark:border-[#1e293b]">
                  <span class="block text-[8px] uppercase font-bold text-[#525f7f]">Quota</span>
                  <span class="text-xs sm:text-sm font-bold text-[#161e2e] dark:text-slate-200">{q.quota ?? '—'}</span>
                </div>
                <div class="p-1.5 bg-white dark:bg-[#121827] rounded border border-[#e5e0d8] dark:border-[#1e293b]">
                  <span class="block text-[8px] uppercase font-bold text-[#525f7f]">Current</span>
                  <span class="text-xs sm:text-sm font-bold text-[#161e2e] dark:text-slate-200">{q.current ?? '—'}</span>
                </div>
                <div class="p-1.5 bg-white dark:bg-[#121827] rounded border border-[#e5e0d8] dark:border-[#1e293b]">
                  <span class="block text-[8px] uppercase font-bold text-[#525f7f]">Available</span>
                  <span class="text-xs sm:text-sm font-bold {q.available && q.available > 0 ? 'text-emerald-800 dark:text-emerald-400' : 'text-[#525f7f]'}">
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

    <!-- History Timeline -->
    <div class="space-y-6 sm:space-y-8">
      {#each Object.keys(groupedHistory) as term}
        <section class="space-y-3">
          <div class="flex items-center space-x-2.5">
            <span class="w-1.5 h-5 bg-[#002d72] dark:bg-[#8cc8ea] rounded-full"></span>
            <h2 class="font-mono text-base font-bold text-[#002d72] dark:text-slate-100 uppercase tracking-wider">{term}</h2>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {#each groupedHistory[term] as section}
              <article class="bg-white rounded-xl border border-[#e5e0d8] p-4 sm:p-5 shadow-2xs hover:border-[#c5a059] dark:bg-[#121827] dark:border-[#1e293b] dark:hover:border-[#8cc8ea]/40 transition-colors group space-y-3">
                <div class="flex items-center justify-between">
                  <div class="px-2 py-0.5 bg-[#f3efe6] dark:bg-slate-800 text-[#161e2e] dark:text-slate-300 text-[10px] font-mono font-bold rounded uppercase">Section {section.section}</div>
                  <div class="text-[9px] font-mono font-semibold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider">{section.delivery_method || 'Standard'}</div>
                </div>
                
                <div class="space-y-2.5">
                  <div class="flex items-start space-x-2.5">
                    <User size={14} class="text-[#525f7f] mt-0.5 shrink-0" />
                    <div>
                      <p class="font-mono text-[9px] text-[#525f7f] uppercase tracking-wider">Instructor</p>
                      <p class="text-xs sm:text-sm font-semibold text-[#161e2e] dark:text-slate-200">{section.instructor}</p>
                    </div>
                  </div>

                  <div class="flex items-start space-x-2.5">
                    <Clock size={14} class="text-[#525f7f] mt-0.5 shrink-0" />
                    <div class="w-full">
                      <p class="font-mono text-[9px] text-[#525f7f] uppercase tracking-wider">Schedule & Room</p>
                      <div class="space-y-1 mt-1 font-mono">
                        {#each section.slots as slot}
                          <div class="flex items-center justify-between text-xs bg-[#faf8f5] p-1.5 rounded dark:bg-[#0a0e1a] border border-[#e5e0d8] dark:border-[#1e293b]">
                             <div class="flex items-center space-x-1.5">
                                <span class="font-bold text-[#002d72] dark:text-[#8cc8ea] w-4">{slot.day}</span>
                                <time class="text-[#525f7f] dark:text-slate-400">{formatSlotTime(slot.hour)}</time>
                             </div>
                             <div class="flex items-center space-x-1 text-[#525f7f] truncate max-w-[100px]">
                                <MapPin size={9} class="shrink-0" />
                                <span class="truncate font-semibold">{slot.room}</span>
                             </div>
                          </div>
                        {/each}
                      </div>
                    </div>
                  </div>
                </div>
              </article>
            {/each}
          </div>
        </section>
      {/each}
    </div>
  {/if}
</div>
