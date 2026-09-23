<script lang="ts">
  import { page } from "$app/state";
  import { goto } from "$app/navigation";
  import { 
    Calendar, 
    Globe, 
    LayoutGrid, 
    Building2, 
    Sparkles 
  } from "lucide-svelte";
  import OfficialScheduleViewer from "$lib/components/schedule/OfficialScheduleViewer.svelte";
  import ClassroomScheduleMatrix from "$lib/components/schedule/ClassroomScheduleMatrix.svelte";

  // Tab mode: 'official' (OBIKAS iframes & links) or 'matrix' (All classes, rooms & campus heatmap)
  let activeTab = $state<"official" | "matrix">(
    page.url.searchParams.get("tab") === "matrix" ? "matrix" : "official"
  );

  function setTab(tab: "official" | "matrix") {
    activeTab = tab;
    const url = new URL(window.location.href);
    url.searchParams.set("tab", tab);
    goto(url.toString(), { replaceState: true, noScroll: true, keepFocus: true });
  }
</script>

<svelte:head>
  <title>Class Schedule • BOUN Archive</title>
  <meta 
    name="description" 
    content="Official Boğaziçi University academic schedule portal, OBIKAS iframe viewer, and campus classroom occupancy matrix." 
  />
  <meta property="og:title" content="Class Schedule • BOUN Archive" />
  <meta 
    property="og:description" 
    content="Access official Boğaziçi course schedules and explore classroom utilization across all campuses and timetable slots." 
  />
</svelte:head>

<div class="space-y-6 max-w-7xl mx-auto">
  <!-- Page Header & Feature Switcher -->
  <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#e5e0d8] dark:border-[#1e293b] pb-5">
    <div>
      <div class="flex items-center gap-2">
        <span class="inline-flex items-center justify-center p-1.5 rounded-lg bg-[#002d72]/10 text-[#002d72] dark:bg-[#8cc8ea]/15 dark:text-[#8cc8ea]">
          <Calendar size={22} />
        </span>
        <h1 class="font-serif text-2xl sm:text-3xl font-bold text-[#002d72] dark:text-slate-50 tracking-tight">
          Class Schedule
        </h1>
      </div>
      <p class="mt-1.5 text-xs sm:text-sm text-[#525f7f] dark:text-slate-400">
        Access official OBIKAS registration schedules or inspect physical classroom occupancy across all campuses.
      </p>
    </div>

    <!-- Dual Feature Switcher Tabs -->
    <div class="inline-flex p-1 bg-[#ede8dc]/80 dark:bg-slate-900/80 rounded-xl border border-[#e5e0d8] dark:border-[#1e293b] shadow-2xs self-start lg:self-auto shrink-0">
      <button 
        type="button"
        onclick={() => setTab("official")}
        class="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer {
          activeTab === 'official' 
            ? 'bg-white text-[#002d72] shadow-2xs dark:bg-[#121827] dark:text-[#8cc8ea]' 
            : 'text-[#525f7f] hover:text-[#002d72] dark:text-slate-400 dark:hover:text-slate-200'
        }"
      >
        <Globe size={14} class={activeTab === 'official' ? 'text-[#c5a059]' : ''} />
        <span>Official Schedule</span>
        <span class="font-mono text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-[#002d72]/10 text-[#002d72] dark:bg-[#8cc8ea]/15 dark:text-[#8cc8ea]">
          OBIKAS
        </span>
      </button>

      <button 
        type="button"
        onclick={() => setTab("matrix")}
        class="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer {
          activeTab === 'matrix' 
            ? 'bg-white text-[#002d72] shadow-2xs dark:bg-[#121827] dark:text-[#8cc8ea]' 
            : 'text-[#525f7f] hover:text-[#002d72] dark:text-slate-400 dark:hover:text-slate-200'
        }"
      >
        <LayoutGrid size={14} class={activeTab === 'matrix' ? 'text-[#c5a059]' : ''} />
        <span>All Classes & Classrooms</span>
        <span class="font-mono text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-[#c5a059]/20 text-[#9a7632] dark:text-[#e5a823]">
          Matrix
        </span>
      </button>
    </div>
  </div>

  <!-- Feature Content Switch -->
  {#if activeTab === "official"}
    <OfficialScheduleViewer />
  {:else}
    <ClassroomScheduleMatrix />
  {/if}
</div>
