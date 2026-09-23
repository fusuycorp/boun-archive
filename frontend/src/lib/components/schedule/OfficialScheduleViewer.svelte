<script lang="ts">
  import { 
    Search, 
    ExternalLink, 
    Calendar, 
    Check, 
    Copy, 
    RotateCcw, 
    Globe, 
    ArrowUpRight,
    School,
    BookOpen
  } from "lucide-svelte";
  import { 
    OFFICIAL_SEMESTERS, 
    OFFICIAL_DEPARTMENTS, 
    buildOfficialScheduleUrl,
    type OfficialDepartment 
  } from "$lib/data/officialSchedule";

  // State
  let selectedSemester = $state("2026/2027-1");
  let selectedDeptKey = $state("CMPE-COMPUTER+ENGINEERING");
  let searchQuery = $state("");
  let copied = $state(false);
  let iframeKey = $state(0);
  let isFrameLoading = $state(true);

  // Active department derived from selected key
  const activeDept = $derived.by((): OfficialDepartment => {
    const found = OFFICIAL_DEPARTMENTS.find(d => `${d.kisaadi}-${d.bolum}` === selectedDeptKey);
    return found || OFFICIAL_DEPARTMENTS[0];
  });

  // Current official schedule URL
  const activeUrl = $derived(
    buildOfficialScheduleUrl(selectedSemester, activeDept.kisaadi, activeDept.bolum)
  );

  // Filtered department directory
  const filteredDepartments = $derived(
    OFFICIAL_DEPARTMENTS.filter(d => {
      const q = searchQuery.toLowerCase().trim();
      if (!q) return true;
      return (
        d.kisaadi.toLowerCase().includes(q) ||
        d.name.toLowerCase().includes(q) ||
        d.bolum.toLowerCase().includes(q)
      );
    })
  );

  // Quick select common departments
  const popularCodes = ["CMPE", "EE", "IE", "ME", "MATH", "EC", "MIS", "PSY", "BIO", "PHYS"];

  function selectDept(dept: OfficialDepartment) {
    selectedDeptKey = `${dept.kisaadi}-${dept.bolum}`;
    isFrameLoading = true;
    iframeKey += 1;
  }

  function reloadFrame() {
    isFrameLoading = true;
    iframeKey += 1;
  }

  function openInNewTab(url: string = activeUrl) {
    window.open(url, "_blank", "noopener,noreferrer");
  }

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(activeUrl);
      copied = true;
      setTimeout(() => {
        copied = false;
      }, 2000);
    } catch (e) {
      console.error("Clipboard copy failed", e);
    }
  }
</script>

<div class="space-y-6">
  <!-- Selection Control Box -->
  <div class="p-5 sm:p-6 bg-white dark:bg-[#121827] rounded-xl border border-[#e5e0d8] dark:border-[#1e293b] shadow-2xs space-y-5">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Semester Dropdown -->
      <div>
        <label for="semester-select" class="block font-mono text-[11px] font-bold uppercase tracking-wider text-[#525f7f] dark:text-slate-400 mb-1.5">
          Academic Term (Semester)
        </label>
        <div class="relative">
          <select 
            id="semester-select"
            bind:value={selectedSemester}
            onchange={() => reloadFrame()}
            class="w-full px-3.5 py-2.5 bg-[#faf8f5] dark:bg-[#0a0e1a] border border-[#e5e0d8] dark:border-[#1e293b] rounded-lg text-sm text-[#161e2e] dark:text-slate-100 focus:outline-hidden focus:ring-2 focus:ring-[#002d72]/20 dark:focus:ring-[#8cc8ea]/20 transition-colors"
          >
            {#each OFFICIAL_SEMESTERS as sem}
              <option value={sem.value}>{sem.label}</option>
            {/each}
          </select>
        </div>
      </div>

      <!-- Department Selector -->
      <div>
        <label for="dept-select" class="block font-mono text-[11px] font-bold uppercase tracking-wider text-[#525f7f] dark:text-slate-400 mb-1.5">
          Department / Academic Program
        </label>
        <div class="relative">
          <select 
            id="dept-select"
            bind:value={selectedDeptKey}
            onchange={() => reloadFrame()}
            class="w-full px-3.5 py-2.5 bg-[#faf8f5] dark:bg-[#0a0e1a] border border-[#e5e0d8] dark:border-[#1e293b] rounded-lg text-sm text-[#161e2e] dark:text-slate-100 focus:outline-hidden focus:ring-2 focus:ring-[#002d72]/20 dark:focus:ring-[#8cc8ea]/20 transition-colors"
          >
            {#each OFFICIAL_DEPARTMENTS as dept}
              <option value={`${dept.kisaadi}-${dept.bolum}`}>
                [{dept.kisaadi}] {dept.name}
              </option>
            {/each}
          </select>
        </div>
      </div>
    </div>

    <!-- Quick Department Shortcut Pills -->
    <div class="pt-2 border-t border-[#e5e0d8]/60 dark:border-[#1e293b]/60 flex flex-wrap items-center gap-1.5">
      <span class="text-xs font-semibold text-[#525f7f] dark:text-slate-400 mr-1 flex items-center gap-1">
        <School size={13} />
        Quick Pick:
      </span>
      {#each popularCodes as code}
        {@const deptMatch = OFFICIAL_DEPARTMENTS.find(d => d.kisaadi === code)}
        {#if deptMatch}
          {@const isCurrent = activeDept.kisaadi === code}
          <button 
            type="button"
            onclick={() => selectDept(deptMatch)}
            class="px-2.5 py-1 text-xs font-mono font-medium rounded-md border transition-all cursor-pointer {
              isCurrent 
                ? 'bg-[#002d72] text-white border-[#002d72] shadow-2xs dark:bg-[#8cc8ea] dark:text-[#0a0e1a] dark:border-[#8cc8ea]' 
                : 'bg-[#faf8f5] text-[#525f7f] border-[#e5e0d8] hover:text-[#002d72] hover:border-[#c5a059] dark:bg-[#0a0e1a] dark:text-slate-400 dark:border-slate-800 dark:hover:text-slate-200'
            }"
          >
            {code}
          </button>
        {/if}
      {/each}
    </div>

    <!-- Action Bar -->
    <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-3 border-t border-[#e5e0d8]/60 dark:border-[#1e293b]/60">
      <div class="flex items-center gap-2 text-xs text-[#525f7f] dark:text-slate-400 overflow-hidden text-ellipsis whitespace-nowrap">
        <Globe size={14} class="shrink-0 text-[#c5a059]" />
        <span class="font-mono text-[11px] truncate select-all">{activeUrl}</span>
      </div>

      <div class="flex items-center gap-2 shrink-0">
        <!-- Copy Direct Link Button -->
        <button 
          type="button"
          onclick={copyLink}
          class="inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border border-[#e5e0d8] text-[#525f7f] hover:text-[#002d72] hover:bg-[#faf8f5] dark:border-[#1e293b] dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-800/60 transition-colors cursor-pointer"
          title="Copy direct registration URL"
        >
          {#if copied}
            <Check size={14} class="text-emerald-600" />
            <span class="text-emerald-700 dark:text-emerald-400 font-semibold">Copied!</span>
          {:else}
            <Copy size={14} />
            <span>Copy Link</span>
          {/if}
        </button>

        <!-- Refresh Frame Button -->
        <button 
          type="button"
          onclick={reloadFrame}
          class="p-2 text-[#525f7f] hover:text-[#002d72] hover:bg-[#faf8f5] dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-800/60 border border-[#e5e0d8] dark:border-[#1e293b] rounded-lg transition-colors cursor-pointer"
          aria-label="Reload schedule frame"
          title="Reload frame"
        >
          <RotateCcw size={15} />
        </button>

        <!-- Primary: Open in New Tab -->
        <button 
          type="button"
          onclick={() => openInNewTab()}
          class="inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-[#002d72] text-white text-xs font-semibold rounded-lg shadow-2xs hover:bg-[#001f52] transition-colors cursor-pointer dark:bg-[#8cc8ea] dark:text-[#0a0e1a] dark:hover:bg-[#a6d8f2]"
        >
          <span>Open in New Tab</span>
          <ExternalLink size={14} />
        </button>
      </div>
    </div>
  </div>

  <!-- Interactive Embedded Schedule Viewer -->
  <div class="bg-white dark:bg-[#121827] rounded-xl border border-[#e5e0d8] dark:border-[#1e293b] shadow-2xs overflow-hidden">
    <!-- Top Bar of Viewer -->
    <div class="px-5 py-3.5 bg-[#faf8f5] dark:bg-[#0f172a] border-b border-[#e5e0d8] dark:border-[#1e293b] flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <span class="font-mono text-xs font-bold px-2 py-0.5 rounded bg-[#002d72]/10 text-[#002d72] dark:bg-[#8cc8ea]/15 dark:text-[#8cc8ea]">
          {activeDept.kisaadi}
        </span>
        <span class="font-serif text-sm font-bold text-[#161e2e] dark:text-slate-100">
          {activeDept.name}
        </span>
        <span class="text-xs text-[#525f7f] dark:text-slate-400">
          • {selectedSemester}
        </span>
      </div>

      <div class="flex items-center gap-2">
        <button 
          type="button"
          onclick={() => openInNewTab()}
          class="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-[#002d72] hover:bg-[#002d72]/5 rounded-md dark:text-[#8cc8ea] dark:hover:bg-slate-800 transition-colors cursor-pointer"
        >
          <span>Open Official Page</span>
          <ArrowUpRight size={13} />
        </button>
      </div>
    </div>

    <!-- Iframe Container -->
    <div class="relative w-full h-[750px] sm:h-[850px] bg-[#faf8f5] dark:bg-[#0a0e1a]">
      {#if isFrameLoading}
        <div class="absolute inset-0 flex flex-col items-center justify-center bg-white/80 dark:bg-[#121827]/80 backdrop-blur-2xs z-10 space-y-3">
          <div class="w-8 h-8 border-3 border-[#002d72]/30 border-t-[#002d72] dark:border-[#8cc8ea]/30 dark:border-t-[#8cc8ea] rounded-full animate-spin"></div>
          <p class="text-xs font-medium text-[#525f7f] dark:text-slate-400">
            Loading official schedule from registration.boun.edu.tr...
          </p>
        </div>
      {/if}

      {#key iframeKey}
        <iframe 
          src={activeUrl}
          title="Official Course Schedule for {activeDept.name}"
          sandbox="allow-same-origin allow-scripts allow-forms"
          class="w-full h-full border-0"
          onload={() => { isFrameLoading = false; }}
        ></iframe>
      {/key}
    </div>

    <!-- Footer Notice with Fallback Guidance -->
    <div class="p-3 bg-[#faf8f5] dark:bg-[#0f172a] border-t border-[#e5e0d8] dark:border-[#1e293b] flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-[#525f7f] dark:text-slate-400">
      <p>
        Source: Official Boğaziçi University Registration System (<a href="https://registration.boun.edu.tr" target="_blank" rel="noopener noreferrer" class="underline hover:text-[#002d72] dark:hover:text-[#8cc8ea]">registration.boun.edu.tr</a>).
      </p>
      <p class="text-[11px]">
        If in-page loading is blocked by your browser network or cross-site policy, please use <strong>Open in New Tab</strong>.
      </p>
    </div>
  </div>

  <!-- Department Catalog & Quick Launch Grid -->
  <div class="bg-white dark:bg-[#121827] rounded-xl border border-[#e5e0d8] dark:border-[#1e293b] shadow-2xs p-5 sm:p-6 space-y-4">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div>
        <h2 class="font-serif text-lg font-bold text-[#002d72] dark:text-slate-100 flex items-center gap-2">
          <BookOpen size={18} />
          Complete Department Directory
        </h2>
        <p class="text-xs text-[#525f7f] dark:text-slate-400 mt-0.5">
          Click any department to switch the live preview above, or launch directly in a new tab.
        </p>
      </div>

      <!-- Search Input -->
      <div class="relative w-full sm:w-72">
        <Search size={15} class="absolute left-3 top-1/2 -translate-y-1/2 text-[#8a94a6] dark:text-slate-500" />
        <input 
          type="text" 
          bind:value={searchQuery}
          placeholder="Filter by code or department name..."
          class="w-full pl-9 pr-3.5 py-2 text-xs bg-[#faf8f5] dark:bg-[#0a0e1a] border border-[#e5e0d8] dark:border-[#1e293b] rounded-lg text-[#161e2e] dark:text-slate-100 placeholder-[#8a94a6] focus:outline-hidden focus:ring-2 focus:ring-[#002d72]/20 dark:focus:ring-[#8cc8ea]/20 transition-colors"
        />
      </div>
    </div>

    <!-- Department Cards Grid -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 max-h-[500px] overflow-y-auto pr-1">
      {#each filteredDepartments as dept}
        {@const isSelected = activeDept.kisaadi === dept.kisaadi && activeDept.bolum === dept.bolum}
        {@const deptUrl = buildOfficialScheduleUrl(selectedSemester, dept.kisaadi, dept.bolum)}
        <div 
          class="group p-3 rounded-lg border transition-all flex items-center justify-between gap-3 {
            isSelected
              ? 'bg-[#002d72]/5 border-[#002d72]/30 dark:bg-[#8cc8ea]/10 dark:border-[#8cc8ea]/30'
              : 'bg-[#faf8f5]/60 hover:bg-[#faf8f5] border-[#e5e0d8]/80 hover:border-[#c5a059] dark:bg-[#0a0e1a]/60 dark:hover:bg-[#0a0e1a] dark:border-slate-800 dark:hover:border-slate-700'
          }"
        >
          <button 
            type="button"
            onclick={() => selectDept(dept)}
            class="flex items-center gap-2.5 text-left min-w-0 flex-1 cursor-pointer"
          >
            <span class="font-mono text-xs font-bold px-2 py-1 rounded-md shrink-0 {
              isSelected 
                ? 'bg-[#002d72] text-white dark:bg-[#8cc8ea] dark:text-[#0a0e1a]' 
                : 'bg-[#e5e0d8]/70 text-[#002d72] dark:bg-slate-800 dark:text-slate-300 group-hover:bg-[#c5a059]/20'
            }">
              {dept.kisaadi}
            </span>
            <div class="min-w-0 flex-1">
              <p class="text-xs font-semibold text-[#161e2e] dark:text-slate-100 truncate group-hover:text-[#002d72] dark:group-hover:text-[#8cc8ea] transition-colors">
                {dept.name}
              </p>
              <p class="font-mono text-[10px] text-[#525f7f] dark:text-slate-400 truncate">
                {dept.kisaadi} • {selectedSemester}
              </p>
            </div>
          </button>

          <div class="flex items-center gap-1 shrink-0">
            <button 
              type="button"
              onclick={() => selectDept(dept)}
              class="px-2 py-1 text-[11px] font-semibold rounded-md text-[#002d72] hover:bg-[#002d72]/10 dark:text-[#8cc8ea] dark:hover:bg-slate-800 transition-colors cursor-pointer"
              title="View in embedded frame"
            >
              View
            </button>
            <button 
              type="button"
              onclick={() => openInNewTab(deptUrl)}
              class="p-1.5 text-[#525f7f] hover:text-[#002d72] dark:text-slate-400 dark:hover:text-slate-200 hover:bg-[#002d72]/5 dark:hover:bg-slate-800 rounded-md transition-colors cursor-pointer"
              title="Open in new tab"
              aria-label="Open {dept.name} schedule in new tab"
            >
              <ExternalLink size={13} />
            </button>
          </div>
        </div>
      {/each}

      {#if filteredDepartments.length === 0}
        <div class="col-span-full py-8 text-center text-xs text-[#525f7f] dark:text-slate-400">
          No departments found matching "{searchQuery}".
        </div>
      {/if}
    </div>
  </div>
</div>
