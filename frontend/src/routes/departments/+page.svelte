<script lang="ts">
  import { onMount } from "svelte";
  import { BookOpen, Search, ArrowRight, ChevronRight, Hash, ArrowUpDown, User, Download } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import { exportToCSV } from "$lib/utils";

  let departments = $state<any[]>([]);
  let selectedDept = $state<string | null>(null);
  let uniqueCourses = $state<any[]>([]);
  let deptInstructors = $state<any[]>([]);
  let loading = $state(false);
  let deptSearch = $state("");
  let viewMode = $state<"courses" | "instructors">("courses");

  // Sorting - Courses
  let courseSortColumn = $state("latest_term");
  let courseSortDirection = $state<"asc" | "desc">("desc");

  // Sorting - Instructors
  let instructorSortColumn = $state("last_term");
  let instructorSortDirection = $state<"asc" | "desc">("desc");

  async function fetchDepartments() {
    try {
      const res = await fetch(`${API_BASE}/v1/departments`);
      if (res.ok) {
        departments = await res.json();
      }
    } catch (e) {
      console.error("Failed to fetch departments", e);
    }
    
    // Restore state if available
    const savedDept = sessionStorage.getItem("dept_selected");
    const savedView = sessionStorage.getItem("dept_view_mode") as any;
    
    if (savedView) viewMode = savedView;

    if (savedDept) {
      selectedDept = savedDept;
      const savedCourses = sessionStorage.getItem(`dept_courses_${savedDept}`);
      if (savedCourses) {
        uniqueCourses = JSON.parse(savedCourses);
      } else {
        fetchUniqueCourses(savedDept);
      }

      const savedInstructors = sessionStorage.getItem(`dept_instructors_${savedDept}`);
      if (savedInstructors) {
        deptInstructors = JSON.parse(savedInstructors);
      } else {
        fetchDeptInstructors(savedDept);
      }
    }
  }

  async function fetchUniqueCourses(deptCode: string) {
    try {
      const res = await fetch(`${API_BASE}/v1/departments/${deptCode}/unique-courses`);
      const data = await res.json();
      uniqueCourses = data.map((c: any) => ({
        ...c,
        latest_term: c.terms[0] || ""
      }));
      sessionStorage.setItem(`dept_courses_${deptCode}`, JSON.stringify(uniqueCourses));
    } catch (e) {
      console.error(e);
    }
  }

  async function fetchDeptInstructors(deptCode: string) {
    try {
      const res = await fetch(`${API_BASE}/v1/departments/${deptCode}/instructors`);
      const data = await res.json();
      deptInstructors = data;
      sessionStorage.setItem(`dept_instructors_${deptCode}`, JSON.stringify(deptInstructors));
    } catch (e) {
      console.error(e);
    }
  }

  async function handleDeptSelect(deptCode: string) {
    loading = true;
    selectedDept = deptCode;
    sessionStorage.setItem("dept_selected", deptCode);
    
    await Promise.all([
      fetchUniqueCourses(deptCode),
      fetchDeptInstructors(deptCode)
    ]);
    
    loading = false;
  }

  function handleCourseSort(column: string) {
    if (courseSortColumn === column) {
      courseSortDirection = courseSortDirection === "asc" ? "desc" : "asc";
    } else {
      courseSortColumn = column;
      courseSortDirection = column === "latest_term" ? "desc" : "asc";
    }
  }

  function handleInstructorSort(column: string) {
    if (instructorSortColumn === column) {
      instructorSortDirection = instructorSortDirection === "asc" ? "desc" : "asc";
    } else {
      instructorSortColumn = column;
      instructorSortDirection = column === "last_term" ? "desc" : "asc";
    }
  }

  function setViewMode(mode: "courses" | "instructors") {
    viewMode = mode;
    sessionStorage.setItem("dept_view_mode", mode);
  }

  function handleExport() {
    if (viewMode === 'courses') {
      if (uniqueCourses.length === 0) return;
      const exportData = sortedCourses.map(c => ({
        course_code: c.course_code,
        title: c.title,
        latest_term: c.latest_term,
        all_terms: c.terms.join('; ')
      }));
      exportToCSV(exportData, `boun_dept_${selectedDept}_courses_${new Date().toISOString().split('T')[0]}`);
    } else {
      if (deptInstructors.length === 0) return;
      const exportData = sortedInstructors.map(i => ({
        full_name: i.full_name,
        last_term: i.last_term,
        course_count: i.course_count,
        total_semesters: i.total_semesters
      }));
      exportToCSV(exportData, `boun_dept_${selectedDept}_instructors_${new Date().toISOString().split('T')[0]}`);
    }
  }

  onMount(fetchDepartments);

  const filteredDepts = $derived(
    departments.filter(d => 
      d.kisaadi.toLowerCase().includes(deptSearch.toLowerCase()) || 
      d.bolum.toLowerCase().includes(deptSearch.toLowerCase())
    )
  );

  const sortedCourses = $derived(
    [...uniqueCourses].sort((a, b) => {
      const valA = a[courseSortColumn];
      const valB = b[courseSortColumn];
      if (valA < valB) return courseSortDirection === "asc" ? -1 : 1;
      if (valA > valB) return courseSortDirection === "asc" ? 1 : -1;
      return 0;
    })
  );

  const sortedInstructors = $derived(
    [...deptInstructors].sort((a, b) => {
      const valA = a[instructorSortColumn];
      const valB = b[instructorSortColumn];
      if (valA < valB) return instructorSortDirection === "asc" ? -1 : 1;
      if (valA > valB) return instructorSortDirection === "asc" ? 1 : -1;
      return 0;
    })
  );
</script>

<div class="space-y-6 sm:space-y-8">
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
    <div>
      <h1 class="font-serif text-2xl sm:text-3xl font-bold text-[#1c1b18] dark:text-neutral-50 tracking-tight">Department Archive</h1>
      <p class="font-sans text-xs sm:text-sm text-[#746f65] dark:text-neutral-400 mt-1">Explore course catalogs and faculty rosters across decades of academic history.</p>
    </div>
  </div>

  <!-- Mobile Department Selector (lg:hidden) -->
  <div class="block lg:hidden bg-[#f7f5ee] p-4 rounded-xl border border-[#dbd7cc] shadow-2xs dark:bg-[#18181b] dark:border-[#27272a] space-y-2">
    <label for="mobile-dept-select" class="font-mono text-[9px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider px-1">Choose Department</label>
    <div class="relative">
      <select 
        id="mobile-dept-select"
        value={selectedDept || ""} 
        onchange={(e) => handleDeptSelect(e.currentTarget.value)}
        class="w-full p-2.5 bg-[#eeece2] border border-[#dbd7cc] rounded-lg text-xs font-semibold text-[#1c1b18] outline-none focus:ring-1 focus:ring-[#c5a059] dark:bg-[#121214] dark:border-[#27272a] dark:text-neutral-200 cursor-pointer font-mono"
      >
        <option value="" disabled>-- Select a Department --</option>
        {#each departments as dept}
          <option value={dept.kisaadi}>{dept.kisaadi} - {dept.bolum}</option>
        {/each}
      </select>
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-4 gap-6 lg:gap-8">
    <!-- Desktop Sidebar: Dept List -->
    <aside class="hidden lg:block space-y-4">
      <div class="bg-[#f7f5ee] rounded-xl border border-[#dbd7cc] shadow-2xs overflow-hidden dark:bg-[#18181b] dark:border-[#27272a] flex flex-col h-[calc(100vh-200px)] sticky top-24">
        <div class="p-3.5 border-b border-[#dbd7cc] dark:border-[#27272a] bg-[#e7e4d9]/50 dark:bg-[#121214]">
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-[#746f65]" size={15} />
            <input 
              type="text" 
              bind:value={deptSearch}
              placeholder="Search departments..."
              class="w-full pl-9 pr-3 py-2 bg-[#f7f5ee] border border-[#dbd7cc] rounded-lg text-xs outline-none focus:ring-1 focus:ring-[#c5a059] focus:border-[#c5a059] dark:bg-[#121214] dark:border-[#27272a] dark:text-white transition-all"
            />
          </div>
        </div>
        
        <div class="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1">
          {#each filteredDepts as dept}
            <button 
              onclick={() => handleDeptSelect(dept.kisaadi)}
              class="w-full text-left p-2.5 rounded-lg transition-colors group cursor-pointer
              {selectedDept === dept.kisaadi 
                ? 'bg-[#dedacb] text-[#1c1b18] dark:bg-[#27272a] dark:text-neutral-100 shadow-2xs' 
                : 'text-[#45423b] dark:text-neutral-300 hover:bg-[#edeae0] dark:hover:bg-[#232328]'}"
            >
              <div class="flex items-center justify-between">
                <div class="flex flex-col">
                  <span class="font-mono text-[10px] font-bold uppercase tracking-wider opacity-70 {selectedDept === dept.kisaadi ? 'text-[#002d72] dark:text-amber-400 font-black' : ''}">{dept.kisaadi}</span>
                  <span class="text-xs font-semibold truncate max-w-[180px]">{dept.bolum}</span>
                </div>
                <ChevronRight size={14} class="opacity-0 group-hover:opacity-100 transition-opacity text-[#746f65]" />
              </div>
            </button>
          {/each}
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="lg:col-span-3 space-y-6">
      {#if loading}
        <div class="bg-[#f7f5ee] rounded-xl border border-[#dbd7cc] p-20 flex flex-col items-center justify-center space-y-3 dark:bg-[#18181b] dark:border-[#27272a]">
          <div class="animate-spin rounded-full h-8 w-8 border-3 border-[#dbd7cc] border-t-[#002d72] dark:border-neutral-800 dark:border-t-amber-400"></div>
          <p class="text-[#746f65] dark:text-neutral-400 font-medium text-xs">Retrieving department archive...</p>
        </div>
      {:else if selectedDept}
        <div class="bg-[#f7f5ee] rounded-xl border border-[#dbd7cc] shadow-2xs overflow-hidden dark:bg-[#18181b] dark:border-[#27272a]">
          <div class="p-4 sm:p-5 border-b border-[#dbd7cc] dark:border-[#27272a] flex flex-col sm:flex-row sm:items-center justify-between bg-[#e7e4d9]/50 dark:bg-[#121214] gap-4">
            <div class="flex items-center space-x-3">
              <div class="w-9 h-9 bg-[#002d72] dark:bg-[#27272a] rounded-lg flex items-center justify-center text-white dark:text-amber-400 shadow-2xs shrink-0">
                {#if viewMode === 'courses'}
                   <BookOpen size={18} />
                {:else}
                   <User size={18} />
                {/if}
              </div>
              <div>
                <h2 class="font-serif text-lg sm:text-xl font-bold text-[#1c1b18] dark:text-neutral-100">{selectedDept} {viewMode === 'courses' ? 'Courses' : 'Instructors'}</h2>
                <p class="font-mono text-xs text-[#746f65] dark:text-neutral-400">
                   {viewMode === 'courses' ? uniqueCourses.length : deptInstructors.length} historical records
                </p>
              </div>
            </div>

            <div class="flex flex-wrap items-center gap-2 sm:gap-3">
              <!-- Tab Switcher -->
              <div class="flex bg-[#dedacb] dark:bg-[#27272a] p-1 rounded-lg">
                 <button 
                  onclick={() => setViewMode('courses')}
                  class="px-3 py-1 text-xs font-semibold rounded-md transition-colors cursor-pointer {viewMode === 'courses' ? 'bg-[#f7f5ee] text-[#1c1b18] shadow-2xs dark:bg-[#18181b] dark:text-white' : 'text-[#5c5850] hover:text-[#1c1b18] dark:text-neutral-400'}"
                 >Courses</button>
                 <button 
                  onclick={() => setViewMode('instructors')}
                  class="px-3 py-1 text-xs font-semibold rounded-md transition-colors cursor-pointer {viewMode === 'instructors' ? 'bg-[#f7f5ee] text-[#1c1b18] shadow-2xs dark:bg-[#18181b] dark:text-white' : 'text-[#5c5850] hover:text-[#1c1b18] dark:text-neutral-400'}"
                 >Instructors</button>
              </div>

              <button 
                  onclick={handleExport}
                  class="flex items-center space-x-1.5 bg-[#f7f5ee] border border-[#dbd7cc] text-[#45423b] px-3 py-1.5 rounded-lg text-xs font-semibold hover:bg-[#dedacb] transition-colors shadow-2xs dark:bg-[#27272a] dark:border-[#3f3f46] dark:text-neutral-300 dark:hover:bg-[#232328] cursor-pointer"
              >
                <Download size={13} />
                <span>Export CSV</span>
              </button>
            </div>
          </div>
          
          {#if viewMode === 'courses'}
            <!-- Mobile Course Cards (< sm) -->
            <div class="block sm:hidden divide-y divide-[#dbd7cc]/70 dark:divide-[#27272a]">
              {#each sortedCourses as course}
                <div class="p-4 space-y-2">
                  <div class="flex items-start justify-between gap-2">
                    <div>
                      <span class="font-mono text-sm font-bold text-[#002d72] dark:text-neutral-100">{course.course_code}</span>
                      <h4 class="font-serif text-sm font-bold text-[#1c1b18] dark:text-neutral-100 mt-0.5">{course.title}</h4>
                    </div>
                    <span class="text-[10px] font-semibold px-2 py-0.5 bg-[#e7e4d9] dark:bg-[#27272a] text-[#45423b] dark:text-neutral-300 rounded font-mono shrink-0">
                      {course.latest_term}
                    </span>
                  </div>

                  <div class="flex flex-wrap gap-1 pt-1">
                    {#each course.terms.slice(0, 3) as term}
                      <span class="px-1.5 py-0.5 bg-[#eeece2] text-[#45423b] text-[9px] font-mono font-medium rounded dark:bg-[#121214] dark:text-neutral-400 border border-[#dbd7cc] dark:border-[#27272a]">{term}</span>
                    {/each}
                    {#if course.terms.length > 3}
                      <span class="px-1.5 py-0.5 bg-amber-500/10 text-amber-950 text-[9px] font-mono font-bold rounded dark:bg-amber-400/10 dark:text-amber-300 border border-amber-500/20">+{course.terms.length - 3} MORE</span>
                    {/if}
                  </div>

                  <div class="pt-2 text-right">
                    <a href="/course/{course.course_code}" class="inline-flex items-center space-x-1 text-xs font-semibold text-[#002d72] dark:text-amber-400 hover:underline">
                      <span>View History</span> <ArrowRight size={13} />
                    </a>
                  </div>
                </div>
              {/each}
            </div>

            <!-- Desktop Course Table (>= sm) -->
            <div class="hidden sm:block overflow-x-auto">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="bg-[#e7e4d9]/60 dark:bg-[#121214] border-b border-[#dbd7cc] dark:border-[#27272a]">
                    <th class="p-4">
                      <button onclick={() => handleCourseSort('course_code')} class="flex items-center space-x-1 font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider hover:text-[#1c1b18] dark:hover:text-neutral-200 transition-colors cursor-pointer">
                        <span>Code</span>
                        {#if courseSortColumn === 'course_code'}{courseSortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
                      </button>
                    </th>
                    <th class="p-4">
                      <button onclick={() => handleCourseSort('title')} class="flex items-center space-x-1 font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider hover:text-[#1c1b18] dark:hover:text-neutral-200 transition-colors cursor-pointer">
                        <span>Title</span>
                        {#if courseSortColumn === 'title'}{courseSortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
                      </button>
                    </th>
                    <th class="p-4">
                      <button onclick={() => handleCourseSort('latest_term')} class="flex items-center space-x-1 font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider hover:text-[#1c1b18] dark:hover:text-neutral-200 transition-colors cursor-pointer">
                        <span>Latest Term</span>
                        {#if courseSortColumn === 'latest_term'}{courseSortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
                      </button>
                    </th>
                    <th class="p-4 font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider">Active Semesters</th>
                    <th class="p-4"></th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-[#dbd7cc]/70 dark:divide-[#27272a]">
                  {#each sortedCourses as course}
                    <tr class="hover:bg-[#edeae0] dark:hover:bg-[#232328] transition-colors group">
                      <td class="p-4 whitespace-nowrap"><span class="font-mono text-sm font-bold text-[#002d72] dark:text-neutral-100">{course.course_code}</span></td>
                      <td class="p-4"><span class="font-serif text-sm font-medium text-[#1c1b18] dark:text-neutral-200">{course.title}</span></td>
                      <td class="p-4 whitespace-nowrap"><span class="font-mono text-xs font-medium text-[#746f65] dark:text-neutral-400">{course.latest_term}</span></td>
                      <td class="p-4">
                        <div class="flex flex-wrap gap-1">
                          {#each course.terms.slice(0, 3) as term}
                            <span class="px-1.5 py-0.5 bg-[#eeece2] text-[#45423b] text-[9px] font-mono font-medium rounded dark:bg-[#121214] dark:text-neutral-400 border border-[#dbd7cc] dark:border-[#27272a]">{term}</span>
                          {/each}
                          {#if course.terms.length > 3}
                            <span class="px-1.5 py-0.5 bg-amber-500/10 text-amber-950 text-[9px] font-mono font-bold rounded dark:bg-amber-400/10 dark:text-amber-300 border border-amber-500/20">+{course.terms.length - 3} MORE</span>
                          {/if}
                        </div>
                      </td>
                      <td class="p-4 text-right">
                        <a href="/course/{course.course_code}" class="inline-flex items-center space-x-1.5 text-xs font-semibold text-[#746f65] hover:text-[#002d72] dark:hover:text-amber-400 transition-colors">
                          <span>History</span> <ArrowRight size={13} />
                        </a>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {:else}
            <!-- Mobile Instructor Cards (< sm) -->
            <div class="block sm:hidden divide-y divide-[#dbd7cc]/70 dark:divide-[#27272a]">
              {#each sortedInstructors as instructor}
                <div class="p-4 space-y-2.5">
                  <div class="flex items-center justify-between">
                    <a 
                      href="/instructor/{instructor.id}"
                      class="flex items-center space-x-3"
                    >
                      <div class="w-8 h-8 bg-[#e7e4d9] rounded-full flex items-center justify-center text-[#746f65] dark:bg-[#27272a] dark:text-neutral-400 shrink-0">
                        <User size={14} />
                      </div>
                      <span class="text-sm font-semibold text-[#1c1b18] dark:text-neutral-200">{instructor.full_name}</span>
                    </a>
                    <a href="/instructor/{instructor.id}" class="text-[#746f65] hover:text-[#1c1b18] dark:hover:text-amber-400"><ChevronRight size={15} /></a>
                  </div>

                  <div class="grid grid-cols-3 gap-2 pt-2 border-t border-[#dbd7cc]/70 dark:border-[#27272a] text-center font-mono">
                    <div class="p-1.5 bg-[#eeece2] dark:bg-[#121214] rounded">
                      <span class="block text-[8px] uppercase font-bold text-[#746f65]">Last Term</span>
                      <span class="text-xs font-semibold text-[#45423b] dark:text-neutral-300 truncate block">{instructor.last_term}</span>
                    </div>
                    <div class="p-1.5 bg-[#eeece2] dark:bg-[#121214] rounded">
                      <span class="block text-[8px] uppercase font-bold text-[#746f65]">Classes</span>
                      <span class="text-xs font-bold text-[#002d72] dark:text-amber-400">{instructor.course_count}</span>
                    </div>
                    <div class="p-1.5 bg-[#eeece2] dark:bg-[#121214] rounded">
                      <span class="block text-[8px] uppercase font-bold text-[#746f65]">Semesters</span>
                      <span class="text-xs font-bold text-[#002d72] dark:text-amber-400">{instructor.total_semesters}</span>
                    </div>
                  </div>
                </div>
              {/each}
            </div>

            <!-- Desktop Instructor Table (>= sm) -->
            <div class="hidden sm:block overflow-x-auto">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="bg-[#e7e4d9]/60 dark:bg-[#121214] border-b border-[#dbd7cc] dark:border-[#27272a]">
                    <th class="p-4">
                      <button onclick={() => handleInstructorSort('full_name')} class="flex items-center space-x-1 font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider hover:text-[#1c1b18] dark:hover:text-neutral-200 transition-colors cursor-pointer">
                        <span>Instructor Name</span>
                        {#if instructorSortColumn === 'full_name'}{instructorSortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
                      </button>
                    </th>
                    <th class="p-4">
                      <button onclick={() => handleInstructorSort('last_term')} class="flex items-center space-x-1 font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider hover:text-[#1c1b18] dark:hover:text-neutral-200 transition-colors cursor-pointer">
                        <span>Last Term in Dept</span>
                        {#if instructorSortColumn === 'last_term'}{instructorSortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
                      </button>
                    </th>
                    <th class="p-4 text-center">
                      <button onclick={() => handleInstructorSort('course_count')} class="flex items-center justify-center space-x-1 font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider hover:text-[#1c1b18] dark:hover:text-neutral-200 transition-colors cursor-pointer">
                        <span>Classes</span>
                        {#if instructorSortColumn === 'course_count'}{instructorSortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
                      </button>
                    </th>
                    <th class="p-4 text-center">
                      <button onclick={() => handleInstructorSort('total_semesters')} class="flex items-center justify-center space-x-1 font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider hover:text-[#1c1b18] dark:hover:text-neutral-200 transition-colors cursor-pointer">
                        <span>Semesters</span>
                        {#if instructorSortColumn === 'total_semesters'}{instructorSortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
                      </button>
                    </th>
                    <th class="p-4"></th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-[#dbd7cc]/70 dark:divide-[#27272a]">
                  {#each sortedInstructors as instructor}
                    <tr class="hover:bg-[#edeae0] dark:hover:bg-[#232328] transition-colors group">
                      <td class="p-4 whitespace-nowrap">
                        <a 
                          href="/instructor/{instructor.id}"
                          class="flex items-center space-x-3 group/item"
                        >
                          <div class="w-7 h-7 bg-[#e7e4d9] rounded-full flex items-center justify-center text-[#746f65] dark:bg-[#27272a] dark:text-neutral-400 group-hover/item:bg-[#002d72]/10 group-hover/item:text-[#002d72] transition-colors">
                            <User size={13} />
                          </div>
                          <span class="text-sm font-semibold text-[#1c1b18] dark:text-neutral-200 group-hover/item:text-[#002d72] dark:group-hover/item:text-amber-400 transition-colors">{instructor.full_name}</span>
                        </a>
                      </td>
                      <td class="p-4 whitespace-nowrap"><span class="font-mono text-xs font-medium text-[#746f65] dark:text-neutral-400">{instructor.last_term}</span></td>
                      <td class="p-4 text-center"><span class="font-mono text-xs font-semibold text-[#45423b] dark:text-neutral-300">{instructor.course_count}</span></td>
                      <td class="p-4 text-center"><span class="font-mono text-xs font-semibold text-[#45423b] dark:text-neutral-300">{instructor.total_semesters}</span></td>
                      <td class="p-4 text-right">
                         <a href="/instructor/{instructor.id}" class="text-[#746f65] hover:text-[#002d72] dark:text-neutral-500 dark:hover:text-amber-400 transition-colors" aria-label="View instructor details"><ChevronRight size={14} /></a>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        </div>
      {:else}
        <div class="bg-[#f7f5ee] rounded-2xl border border-dashed border-[#dbd7cc] p-12 sm:p-24 flex flex-col items-center justify-center text-center dark:bg-[#18181b] dark:border-neutral-800">
          <div class="w-16 h-16 bg-[#e7e4d9] rounded-full flex items-center justify-center text-[#746f65] mb-4 dark:bg-[#27272a] dark:text-neutral-500">
            <BookOpen size={28} />
          </div>
          <h3 class="font-serif text-xl sm:text-2xl font-bold text-[#1c1b18] dark:text-neutral-200">Select a Department</h3>
          <p class="font-sans text-xs sm:text-sm text-[#746f65] dark:text-neutral-400 mt-2 max-w-sm">Choose an academic department from the list to view its complete historical curriculum and instructor index.</p>
        </div>
      {/if}
    </main>
  </div>
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
