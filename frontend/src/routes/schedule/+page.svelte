<script lang="ts">
  import type { Component } from "svelte";
  import { page } from "$app/state";
  import { goto } from "$app/navigation";
  import { 
    Calendar, 
    Globe, 
    LayoutGrid
  } from "lucide-svelte";

  // Tab mode: 'official' (OBIKAS iframes & links) or 'matrix' (All classes, rooms & campus heatmap)
  let activeTab = $state<"official" | "matrix">(
    page.url.searchParams.get("tab") === "matrix" ? "matrix" : "official"
  );

  let OfficialViewerComponent = $state<Component | null>(null);
  let MatrixComponent = $state<Component | null>(null);
  let officialLoadError = $state<string | null>(null);
  let matrixLoadError = $state<string | null>(null);
  let loadingOfficial = $state(false);
  let loadingMatrix = $state(false);
  let tabOfficial = $state<HTMLButtonElement | null>(null);
  let tabMatrix = $state<HTMLButtonElement | null>(null);

  function loadOfficialTab() {
    if (OfficialViewerComponent || loadingOfficial) return;
    loadingOfficial = true;
    officialLoadError = null;
    import("$lib/components/schedule/OfficialScheduleViewer.svelte")
      .then((m) => {
        OfficialViewerComponent = m.default;
      })
      .catch((err) => {
        officialLoadError =
          err instanceof Error ? err.message : "Failed to load Official Schedule view.";
      })
      .finally(() => {
        loadingOfficial = false;
      });
  }

  function loadMatrixTab() {
    if (MatrixComponent || loadingMatrix) return;
    loadingMatrix = true;
    matrixLoadError = null;
    import("$lib/components/schedule/ClassroomScheduleMatrix.svelte")
      .then((m) => {
        MatrixComponent = m.default;
      })
      .catch((err) => {
        matrixLoadError =
          err instanceof Error ? err.message : "Failed to load Classroom Schedule Matrix.";
      })
      .finally(() => {
        loadingMatrix = false;
      });
  }

  $effect(() => {
    if (activeTab === "official" && !OfficialViewerComponent && !officialLoadError) {
      loadOfficialTab();
    } else if (activeTab === "matrix" && !MatrixComponent && !matrixLoadError) {
      loadMatrixTab();
    }
  });

  function setTab(tab: "official" | "matrix") {
    activeTab = tab;
    const url = new URL(window.location.href);
    url.searchParams.set("tab", tab);
    goto(url.toString(), { replaceState: true, noScroll: true, keepFocus: true });
  }

  function handleTabKeydown(e: KeyboardEvent, current: "official" | "matrix") {
    if (e.key === "ArrowRight" || e.key === "ArrowLeft" || e.key === "Home" || e.key === "End") {
      e.preventDefault();
      const next =
        e.key === "Home"
          ? "official"
          : e.key === "End"
          ? "matrix"
          : current === "official"
          ? "matrix"
          : "official";
      setTab(next);
      (next === "official" ? tabOfficial : tabMatrix)?.focus();
    }
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
    <div
      role="tablist"
      aria-label="Class schedule views"
      class="inline-flex p-1 bg-[#ede8dc]/80 dark:bg-slate-900/80 rounded-xl border border-[#e5e0d8] dark:border-[#1e293b] shadow-2xs self-start lg:self-auto shrink-0"
    >
      <button 
        bind:this={tabOfficial}
        id="schedule-tab-official"
        type="button"
        role="tab"
        aria-selected={activeTab === "official"}
        aria-controls="schedule-panel-official"
        tabindex={activeTab === "official" ? 0 : -1}
        onclick={() => setTab("official")}
        onkeydown={(e) => handleTabKeydown(e, "official")}
        class="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer border-b-2 {
          activeTab === 'official' 
            ? 'bg-white text-[#002d72] border-[#002d72] shadow-2xs dark:bg-[#121827] dark:text-[#8cc8ea] dark:border-[#8cc8ea]' 
            : 'border-transparent text-[#525f7f] hover:text-[#002d72] dark:text-slate-400 dark:hover:text-slate-200'
        }"
      >
        <Globe size={14} aria-hidden="true" class={activeTab === 'official' ? 'text-[#c5a059]' : ''} />
        <span>Official Schedule</span>
        <span class="font-mono text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-[#002d72]/10 text-[#002d72] dark:bg-[#8cc8ea]/15 dark:text-[#8cc8ea]">
          OBIKAS
        </span>
      </button>

      <button 
        bind:this={tabMatrix}
        id="schedule-tab-matrix"
        type="button"
        role="tab"
        aria-selected={activeTab === "matrix"}
        aria-controls="schedule-panel-matrix"
        tabindex={activeTab === "matrix" ? 0 : -1}
        onclick={() => setTab("matrix")}
        onkeydown={(e) => handleTabKeydown(e, "matrix")}
        class="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer border-b-2 {
          activeTab === 'matrix' 
            ? 'bg-white text-[#002d72] border-[#002d72] shadow-2xs dark:bg-[#121827] dark:text-[#8cc8ea] dark:border-[#8cc8ea]' 
            : 'border-transparent text-[#525f7f] hover:text-[#002d72] dark:text-slate-400 dark:hover:text-slate-200'
        }"
      >
        <LayoutGrid size={14} aria-hidden="true" class={activeTab === 'matrix' ? 'text-[#c5a059]' : ''} />
        <span>All Classes & Classrooms</span>
        <span class="font-mono text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-[#c5a059]/20 text-[#9a7632] dark:text-[#e5a823]">
          Matrix
        </span>
      </button>
    </div>
  </div>

  <!-- Feature Content Switch -->
  {#if activeTab === "official"}
    <div id="schedule-panel-official" role="tabpanel" aria-labelledby="schedule-tab-official">
      {#if OfficialViewerComponent}
        <OfficialViewerComponent />
      {:else if officialLoadError}
        <div role="alert" class="p-8 rounded-xl bg-white dark:bg-[#121827] border border-rose-200 dark:border-rose-900/60 text-center space-y-3">
          <p class="text-sm font-semibold text-rose-700 dark:text-rose-400">Failed to load Official Schedule viewer</p>
          <p class="text-xs text-[#525f7f] dark:text-slate-400">{officialLoadError}</p>
          <button
            type="button"
            onclick={loadOfficialTab}
            class="inline-flex items-center px-4 py-2 rounded-lg bg-[#002d72] text-white text-xs font-semibold hover:bg-[#001b44] cursor-pointer"
          >
            Retry
          </button>
        </div>
      {:else}
        <div class="h-96 rounded-xl bg-white dark:bg-[#121827] border border-[#e5e0d8] dark:border-[#1e293b] animate-pulse"></div>
      {/if}
    </div>
  {:else}
    <div id="schedule-panel-matrix" role="tabpanel" aria-labelledby="schedule-tab-matrix">
      {#if MatrixComponent}
        <MatrixComponent />
      {:else if matrixLoadError}
        <div role="alert" class="p-8 rounded-xl bg-white dark:bg-[#121827] border border-rose-200 dark:border-rose-900/60 text-center space-y-3">
          <p class="text-sm font-semibold text-rose-700 dark:text-rose-400">Failed to load Classroom Schedule Matrix</p>
          <p class="text-xs text-[#525f7f] dark:text-slate-400">{matrixLoadError}</p>
          <button
            type="button"
            onclick={loadMatrixTab}
            class="inline-flex items-center px-4 py-2 rounded-lg bg-[#002d72] text-white text-xs font-semibold hover:bg-[#001b44] cursor-pointer"
          >
            Retry
          </button>
        </div>
      {:else}
        <div class="h-96 rounded-xl bg-white dark:bg-[#121827] border border-[#e5e0d8] dark:border-[#1e293b] animate-pulse"></div>
      {/if}
    </div>
  {/if}
</div>
