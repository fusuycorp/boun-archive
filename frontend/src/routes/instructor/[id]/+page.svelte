<script lang="ts">
  import { page } from "$app/state";
  import { User, History, BookOpen, Clock, Calendar, Download, Info, ArrowLeft, Search, ArrowRight, ExternalLink } from "lucide-svelte";
  import { exportToCSV, formatSlotTime } from "$lib/utils";
  import { generateInstructorJsonLd } from "$lib/semantic";
  import type { InstructorHistoryItem, InstructorCourseSummary } from "$lib/types";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();

  let instructorId = $derived(data.instructorId || page.params.id || "");
  let legacyData = $derived(data.legacyData);
  let loading = $state(false);
  let error = $derived(data.error);

  let searchQuery = $state("");

  // Aggregate unique courses taught by this instructor (supports new backend field or derives from history)
  let coursesSummary = $derived.by<InstructorCourseSummary[]>(() => {
    if (legacyData?.courses_summary && legacyData.courses_summary.length > 0) {
      return legacyData.courses_summary;
    }
    if (!legacyData?.history) return [];
    const map = new Map<string, {
      course_code: string;
      title: string;
      sections: Set<string>;
      terms: Set<string>;
      latest_term: string;
      total_offerings: number;
    }>();
    for (const item of legacyData.history) {
      const code = item.course_code.trim();
      if (!code) continue;
      if (!map.has(code)) {
        map.set(code, {
          course_code: code,
          title: item.title || "",
          sections: new Set(),
          terms: new Set(),
          latest_term: item.term || "",
          total_offerings: 0
        });
      }
      const entry = map.get(code)!;
      if (item.section) entry.sections.add(item.section);
      if (item.term) entry.terms.add(item.term);
      if (!entry.latest_term || (item.term && item.term > entry.latest_term)) {
        entry.latest_term = item.term || "";
        if (item.title) entry.title = item.title;
      }
      entry.total_offerings++;
    }
    return Array.from(map.values())
      .map(v => ({
        course_code: v.course_code,
        title: v.title,
        sections: Array.from(v.sections).sort(),
        terms_count: v.terms.size,
        latest_term: v.latest_term,
        total_offerings: v.total_offerings
      }))
      .sort((a, b) => b.total_offerings - a.total_offerings);
  });

  let filteredCoursesSummary = $derived.by(() => {
    const list = coursesSummary;
    const q = searchQuery.trim().toLowerCase();
    if (!q) return list;
    const qNoSpace = q.replace(/\s+/g, "");
    return list.filter(c => {
      const code = c.course_code.toLowerCase();
      const raw = c.course_code.replace(/\s+/g, "").toLowerCase();
      const title = (c.title || "").toLowerCase();
      const secMatch = c.sections.some(s => {
        const fullSec = `${code}.${s}`.toLowerCase();
        const fullSecRaw = `${raw}.${s}`.toLowerCase();
        return s.toLowerCase() === q || fullSec.includes(q) || fullSecRaw.includes(qNoSpace);
      });
      return code.includes(q) || raw.includes(qNoSpace) || title.includes(q) || secMatch;
    });
  });

  let filteredHistory = $derived.by(() => {
    if (!legacyData?.history) return [];
    const q = searchQuery.trim().toLowerCase();
    if (!q) return legacyData.history;
    const qNoSpace = q.replace(/\s+/g, "");
    return legacyData.history.filter((item: InstructorHistoryItem) => {
      const sec = (item.section || "").toLowerCase();
      const code = item.course_code.toLowerCase();
      const fullCode = `${item.course_code}${item.section ? `.${item.section}` : ""}`.toLowerCase();
      const rawCode = item.course_code.replace(/\s+/g, "").toLowerCase();
      const rawFullCode = `${rawCode}${item.section ? `.${item.section}` : ""}`.toLowerCase();
      const title = (item.title || "").toLowerCase();
      const term = (item.term || "").toLowerCase();
      return (
        code.includes(q) ||
        rawCode.includes(qNoSpace) ||
        fullCode.includes(q) ||
        rawFullCode.includes(qNoSpace) ||
        title.includes(q) ||
        term.includes(q) ||
        (sec && sec === q)
      );
    });
  });

  function handleExport() {
    if (!legacyData || !legacyData.history || legacyData.history.length === 0) return;
    
    const exportData = legacyData.history.map((item: InstructorHistoryItem) => ({
      instructor: legacyData.instructor_name,
      term: item.term,
      course_code: item.course_code,
      section: item.section || "01",
      title: item.title
    }));
    
    exportToCSV(exportData, `boun_instructor_${legacyData.instructor_name.replace(/\s+/g, '_')}_history_${new Date().toISOString().split('T')[0]}`);
  }
</script>

<svelte:head>
  <title>{legacyData?.instructor_name ? `${legacyData.instructor_name} - Instructor Profile` : 'Instructor Profile'} • BOUN Archive</title>
  <meta name="description" content="Academic teaching history, courses taught, and lecture slot preferences for {legacyData?.instructor_name || 'Faculty Member'} at Boğaziçi University." />
  <meta property="og:title" content="{legacyData?.instructor_name || 'Instructor'} • BOUN Archive" />
  <meta property="og:description" content="Explore historical courses and teaching footprint for {legacyData?.instructor_name || 'Faculty'} at Boğaziçi University." />
  <meta property="og:type" content="profile" />
  <meta property="og:url" content="https://archive.bogazici.app/instructor/{instructorId}" />
  {#if legacyData}
    {@html `<script type="application/ld+json">${JSON.stringify(generateInstructorJsonLd(instructorId || '', legacyData.instructor_name, legacyData.history))}<\/script>`}
  {/if}
</svelte:head>

<div class="max-w-6xl mx-auto space-y-6 sm:space-y-8">
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
    <div class="flex items-center space-x-3 sm:space-x-4">
      <a href="/instructors" class="p-2 bg-white border border-[#e5e0d8] rounded-lg text-[#525f7f] hover:text-[#002d72] hover:border-[#c5a059] transition-colors dark:bg-[#121827] dark:border-[#1e293b] dark:hover:text-slate-200 shadow-2xs" aria-label="Back to instructors">
        <ArrowLeft size={17} />
      </a>
      <div>
        <h1 class="font-serif text-2xl sm:text-3xl font-bold text-[#002d72] dark:text-slate-50 tracking-tight">Instructor Profile</h1>
        <p class="font-sans text-xs sm:text-sm text-[#525f7f] mt-0.5 dark:text-slate-400">Historical teaching footprint, course catalog, and lecture slot preferences.</p>
      </div>
    </div>
    
    {#if legacyData}
       <button 
          onclick={handleExport}
          class="flex items-center justify-center space-x-2 bg-white border border-[#e5e0d8] text-[#161e2e] px-4 py-2 rounded-lg text-xs font-semibold hover:bg-[#f3efe6] transition-colors shadow-2xs dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700 cursor-pointer w-full sm:w-auto"
       >
         <Download size={13} />
         <span>Export History CSV</span>
       </button>
    {/if}
  </div>

  {#if loading}
    <div class="py-20 flex flex-col items-center justify-center space-y-3">
      <div class="animate-spin rounded-full h-8 w-8 border-3 border-[#e5e0d8] border-t-[#002d72] dark:border-slate-800 dark:border-t-[#8cc8ea]"></div>
      <p class="text-[#525f7f] dark:text-slate-400 font-medium text-xs">Extracting instructor DNA...</p>
    </div>
  {:else if error}
    <div class="bg-white rounded-xl border border-dashed border-red-200 p-12 sm:p-20 flex flex-col items-center justify-center text-center dark:bg-[#121827] dark:border-red-900/30">
      <div class="w-14 h-14 bg-red-50 rounded-full flex items-center justify-center text-red-400 mb-4 dark:bg-red-950/40 dark:text-red-400">
        <Info size={28} />
      </div>
      <h3 class="font-serif text-xl sm:text-2xl font-bold text-[#161e2e] dark:text-slate-200">{error}</h3>
      <p class="text-[#525f7f] dark:text-slate-400 mt-2 max-w-sm text-xs sm:text-sm">We couldn't find any historical records for this instructor ID.</p>
      <a href="/instructors" class="mt-6 px-6 py-2.5 bg-[#002d72] text-white rounded-lg text-xs font-semibold shadow-2xs hover:bg-[#001b44] transition-colors">Back to Search</a>
    </div>
  {:else if legacyData}
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">
      <!-- Stats Summary Sidebar -->
      <aside class="lg:col-span-1 space-y-6">
        <div class="h-card bg-white p-5 sm:p-6 rounded-xl border border-[#e5e0d8] shadow-2xs space-y-6 dark:bg-[#121827] dark:border-[#1e293b]">
          <div class="flex flex-col items-center text-center">
             <div class="w-16 h-16 bg-[#002d72]/10 dark:bg-[#8cc8ea]/15 rounded-full flex items-center justify-center text-[#002d72] dark:text-[#8cc8ea] mb-3">
               <User size={28} />
             </div>
             <h2 class="p-name font-serif text-lg sm:text-xl font-bold text-[#002d72] dark:text-slate-100 leading-tight">{legacyData.instructor_name}</h2>
             <p class="p-job-title font-mono text-[10px] text-[#525f7f] font-semibold uppercase tracking-wider mt-1">Faculty Member</p>
             <span class="p-org hidden">Boğaziçi University</span>
          </div>

          <div class="grid grid-cols-3 gap-2 border-t border-[#e5e0d8] dark:border-[#1e293b] pt-5">
            <div class="text-center">
              <div class="font-serif text-xl sm:text-2xl font-bold text-[#161e2e] dark:text-slate-100">{legacyData.total_semesters_taught}</div>
              <div class="font-mono text-[9px] text-[#525f7f] dark:text-slate-400 uppercase tracking-wider">Semesters</div>
            </div>
            <div class="text-center">
              <div class="font-serif text-xl sm:text-2xl font-bold text-[#161e2e] dark:text-slate-100">{legacyData.total_courses_taught}</div>
              <div class="font-mono text-[9px] text-[#525f7f] dark:text-slate-400 uppercase tracking-wider">Offerings</div>
            </div>
            <div class="text-center">
              <div class="font-serif text-xl sm:text-2xl font-bold text-[#002d72] dark:text-[#8cc8ea]">{coursesSummary.length}</div>
              <div class="font-mono text-[9px] text-[#525f7f] dark:text-slate-400 uppercase tracking-wider">Courses</div>
            </div>
          </div>
        </div>

        <!-- Preferred Slots -->
        <div class="bg-white p-5 sm:p-6 rounded-xl border border-[#e5e0d8] shadow-2xs space-y-4 dark:bg-[#121827] dark:border-[#1e293b]">
          <h2 class="font-mono text-[10px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider flex items-center space-x-2">
            <Clock size={14} class="text-[#0080c9] dark:text-[#8cc8ea]" />
            <span>Preferred Lecture Slots</span>
          </h2>
          <div class="space-y-2 font-mono">
            {#each legacyData.preferred_slots as slot}
              <div class="flex items-center justify-between p-2.5 bg-[#faf8f5] rounded-lg border border-[#e5e0d8] dark:bg-[#0a0e1a] dark:border-[#1e293b]">
                 <div class="flex items-center space-x-2.5">
                   <span class="w-7 h-7 bg-white rounded flex items-center justify-center text-xs font-bold border border-[#e5e0d8] dark:bg-[#121827] dark:border-[#1e293b] dark:text-slate-200">{slot.day}</span>
                   <time class="text-xs font-semibold text-[#161e2e] dark:text-slate-300">{formatSlotTime(slot.hour)}</time>
                 </div>
                 <span class="text-xs font-bold text-[#002d72] dark:text-[#8cc8ea]">{slot.frequency}x</span>
              </div>
            {/each}
          </div>
        </div>
      </aside>

      <!-- Main Course Catalog & Timeline Section -->
      <section class="lg:col-span-2 space-y-6">
        <!-- Interactive Search Bar -->
        <div class="relative">
          <Search class="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#525f7f] pointer-events-none" size={15} />
          <input
            type="text"
            bind:value={searchQuery}
            placeholder="Filter courses by code, title, section (e.g. FA 489.01, Graphic Novel)..."
            class="w-full pl-10 pr-4 py-2.5 bg-white border border-[#e5e0d8] rounded-xl shadow-2xs text-xs sm:text-sm outline-none focus:ring-2 focus:ring-[#002d72]/20 focus:border-[#002d72] transition-all dark:bg-[#121827] dark:border-[#1e293b] dark:text-white dark:focus:border-[#8cc8ea]"
          />
          {#if searchQuery}
            <button
              onclick={() => searchQuery = ""}
              class="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-mono text-[#525f7f] hover:text-[#161e2e] dark:hover:text-white cursor-pointer"
            >
              Clear
            </button>
          {/if}
        </div>

        <!-- Courses Taught Catalog (Comprehensive & Distinct) -->
        <div class="bg-white p-5 sm:p-6 rounded-xl border border-[#e5e0d8] shadow-2xs dark:bg-[#121827] dark:border-[#1e293b] space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="font-mono text-[10px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider flex items-center space-x-2">
              <BookOpen size={14} class="text-[#0080c9] dark:text-[#8cc8ea]" />
              <span>Courses Taught Catalog</span>
            </h2>
            <span class="font-mono text-[10px] font-semibold text-[#525f7f] bg-[#faf8f5] dark:bg-[#0a0e1a] px-2 py-0.5 rounded border border-[#e5e0d8] dark:border-[#1e293b]">
              {filteredCoursesSummary.length} {filteredCoursesSummary.length === 1 ? 'Course' : 'Courses'}
            </span>
          </div>

          {#if filteredCoursesSummary.length === 0}
            <div class="text-center py-6 text-[#525f7f] text-xs">
              No courses matching "{searchQuery}".
            </div>
          {:else}
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {#each filteredCoursesSummary as course}
                <div class="p-3.5 bg-[#faf8f5] rounded-xl border border-[#e5e0d8] hover:border-[#c5a059] transition-all dark:bg-[#0a0e1a] dark:border-[#1e293b] dark:hover:border-[#8cc8ea]/40 flex flex-col justify-between space-y-2 group">
                  <div>
                    <div class="flex items-center justify-between gap-2">
                      <a href="/course/{encodeURIComponent(course.course_code)}" class="font-mono text-sm font-bold text-[#002d72] dark:text-[#8cc8ea] hover:underline flex items-center gap-1.5 flex-wrap">
                        <span>{course.course_code}</span>
                        {#each course.sections as sec}
                          <span class="px-1.5 py-0.2 bg-[#002d72]/10 text-[#002d72] dark:bg-[#8cc8ea]/15 dark:text-[#8cc8ea] font-mono text-[10px] font-bold rounded">.{sec}</span>
                        {/each}
                      </a>
                      <span class="font-mono text-[10px] font-bold text-[#525f7f] dark:text-slate-300 bg-white dark:bg-[#121827] px-2 py-0.5 rounded border border-[#e5e0d8] dark:border-[#1e293b] shrink-0">
                        {course.total_offerings}x
                      </span>
                    </div>
                    <p class="font-serif text-xs text-[#525f7f] dark:text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                      {course.title || "Course details"}
                    </p>
                  </div>

                  <div class="flex items-center justify-between pt-2 border-t border-[#e5e0d8]/60 dark:border-[#1e293b]/60 font-mono text-[10px]">
                    <span class="text-[#525f7f] dark:text-slate-400">Latest: <strong class="text-[#161e2e] dark:text-slate-200">{course.latest_term}</strong></span>
                    <a href="/course/{encodeURIComponent(course.course_code)}" class="text-[#0080c9] dark:text-[#8cc8ea] hover:underline flex items-center gap-1 font-semibold">
                      <span>View</span>
                      <ArrowRight size={10} />
                    </a>
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        </div>

        <!-- Teaching History Timeline -->
        <div class="bg-white p-5 sm:p-6 rounded-xl border border-[#e5e0d8] shadow-2xs dark:bg-[#121827] dark:border-[#1e293b] space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="font-mono text-[10px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider flex items-center space-x-2">
              <History size={14} class="text-[#0080c9] dark:text-[#8cc8ea]" />
              <span>Teaching History Timeline</span>
            </h2>
            <span class="font-mono text-[10px] font-semibold text-[#525f7f] bg-[#faf8f5] dark:bg-[#0a0e1a] px-2 py-0.5 rounded border border-[#e5e0d8] dark:border-[#1e293b]">
              {filteredHistory.length} {filteredHistory.length === 1 ? 'Offering' : 'Offerings'}
            </span>
          </div>
          
          {#if filteredHistory.length === 0}
            <div class="text-center py-8 text-[#525f7f] text-xs">
              No historical offerings found for "{searchQuery}".
            </div>
          {:else}
            <div class="space-y-2.5 max-h-[500px] overflow-y-auto pr-1 custom-scrollbar">
              {#each filteredHistory as item}
                <article class="flex items-start space-x-3 p-3 rounded-lg border border-[#e5e0d8] hover:border-[#c5a059] hover:bg-[#f3efe6]/50 transition-colors dark:border-[#1e293b] dark:hover:bg-slate-800/50">
                  <div class="text-[10px] font-mono font-semibold text-[#161e2e] bg-[#f3efe6] px-2.5 py-0.5 rounded border border-[#e5e0d8] whitespace-nowrap dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300">
                    {item.term}
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center space-x-2 flex-wrap">
                      <a href="/course/{encodeURIComponent(item.course_code)}" class="font-mono text-xs font-bold text-[#002d72] dark:text-slate-100 hover:text-[#0080c9] dark:hover:text-[#8cc8ea] transition-colors">
                        {item.course_code}{item.section ? `.${item.section}` : ''}
                      </a>
                      {#if item.section}
                        <span class="px-1.5 py-0.2 bg-[#002d72]/10 text-[#002d72] dark:bg-[#8cc8ea]/15 dark:text-[#8cc8ea] font-mono text-[9px] font-bold rounded uppercase">
                          Sec {item.section}
                        </span>
                      {/if}
                    </div>
                    <div class="font-serif text-xs text-[#525f7f] dark:text-slate-400 mt-0.5 truncate">{item.title}</div>
                  </div>
                </article>
              {/each}
            </div>
          {/if}
        </div>
      </section>
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
  }
  :global(.dark) .custom-scrollbar::-webkit-scrollbar-thumb {
    background: #334155;
  }
</style>
