<script lang="ts">
  let { children } = $props();
  import "./layout.css";
  import { page } from "$app/state";
  import { onMount } from "svelte";
  import { 
    Search, 
    History, 
    LayoutGrid, 
    TrendingUp, 
    User, 
    CalendarDays, 
    BookOpen,
    Sun, 
    Moon,
    Menu,
    ChevronLeft,
    ChevronRight,
    PanelLeftClose,
    PanelLeftOpen
  } from "lucide-svelte";

  let isDark = $state(false);
  let isSidebarOpen = $state(true);

  const navItems = [
    { href: "/", label: "Dashboard", icon: LayoutGrid },
    { href: "/search", label: "Search", icon: Search },
    { href: "/departments", label: "Departments", icon: BookOpen },
    { href: "/calendar", label: "Weekly Planner", icon: CalendarDays },
    { href: "/ghost-schedule", label: "Ghost Schedule", icon: History },
    { href: "/trends", label: "Trends", icon: TrendingUp },
    { href: "/instructors", label: "Instructors", icon: User },
  ];

  onMount(() => {
    const savedTheme = localStorage.getItem("theme");
    const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    
    if (savedTheme === "dark" || (!savedTheme && systemPrefersDark)) {
      isDark = true;
      document.documentElement.classList.add("dark");
    } else {
      isDark = false;
      document.documentElement.classList.remove("dark");
    }

    const savedSidebar = localStorage.getItem("sidebar_open");
    if (savedSidebar !== null) {
      isSidebarOpen = savedSidebar === "true";
    }
  });

  function toggleTheme() {
    isDark = !isDark;
    if (isDark) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }

  function toggleSidebar() {
    isSidebarOpen = !isSidebarOpen;
    localStorage.setItem("sidebar_open", String(isSidebarOpen));
  }
</script>

<svelte:head>
  <title>BOUN Archive</title>
</svelte:head>

<div class="flex h-screen w-full bg-slate-50 font-sans text-slate-900 transition-colors duration-200 dark:bg-slate-950 dark:text-slate-100 overflow-hidden">
  <!-- Sidebar -->
  <aside 
    class="bg-white border-r border-slate-200 flex flex-col transition-all duration-300 ease-in-out dark:bg-slate-900 dark:border-slate-800 relative z-20 shrink-0 {isSidebarOpen ? 'w-64' : 'w-20'}"
  >
    <!-- Strict internal wrapper to prevent children from forcing width -->
    <div class="flex flex-col h-full w-full overflow-hidden">
        <div class="p-6 flex items-center {isSidebarOpen ? 'space-x-3' : 'justify-center'} shrink-0">
          <img src="/logo.png" alt="BOUN Archive Logo" class="h-10 w-10 rounded-lg shadow-sm border border-slate-100 dark:border-slate-800 object-cover shrink-0" />
          {#if isSidebarOpen}
            <div class="overflow-hidden whitespace-nowrap">
              <h1 class="text-base font-extrabold text-slate-900 tracking-tight leading-none dark:text-white">BOUN Archive</h1>
              <p class="text-[9px] text-slate-400 mt-1 uppercase tracking-widest font-black dark:text-slate-500">Academic Analytics</p>
            </div>
          {/if}
        </div>

        <nav class="flex-1 px-4 space-y-1 overflow-y-auto overflow-x-hidden custom-scrollbar">
          {#each navItems as item}
            <a 
              href={item.href} 
              title={!isSidebarOpen ? item.label : ""}
              class="flex items-center {isSidebarOpen ? 'space-x-3 px-4' : 'justify-center'} py-3 rounded-lg font-medium transition-all
              {page.url.pathname === item.href 
                ? 'bg-indigo-50 text-indigo-700 shadow-sm dark:bg-indigo-950/40 dark:text-indigo-400' 
                : 'text-slate-600 hover:bg-slate-50 hover:text-indigo-600 dark:text-slate-400 dark:hover:bg-slate-800/40 dark:hover:text-indigo-400'}"
            >
              <item.icon size={20} class="shrink-0" />
              {#if isSidebarOpen}
                <span class="overflow-hidden whitespace-nowrap">{item.label}</span>
              {/if}
            </a>
          {/each}
        </nav>

        {#if isSidebarOpen}
          <div class="p-4 border-t border-slate-100 text-[10px] text-slate-400 text-center dark:border-slate-800/60 dark:text-slate-500 shrink-0 overflow-hidden whitespace-nowrap">
            v1.0.0-alpha • 50 Years of Data
          </div>
        {/if}
    </div>

    <!-- Collapse Toggle Button (Outside hidden wrapper) -->
    <button 
      onclick={toggleSidebar}
      class="absolute -right-3 top-20 bg-white border border-slate-200 rounded-full p-1 text-slate-400 hover:text-indigo-600 shadow-sm dark:bg-slate-800 dark:border-slate-700 z-50 cursor-pointer"
    >
      {#if isSidebarOpen}
        <ChevronLeft size={14} />
      {:else}
        <ChevronRight size={14} />
      {/if}
    </button>
  </aside>

  <!-- Main Content -->
  <main class="flex-1 flex flex-col min-w-0">
    <header class="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shrink-0 transition-colors duration-200 dark:bg-slate-900 dark:border-slate-800">
      <div class="flex items-center space-x-4">
        <div class="text-sm font-medium text-slate-500 dark:text-slate-400 truncate">
          Bogazici University Historical Course Archive
        </div>
      </div>
      <div class="flex items-center space-x-4">
        <button 
          onclick={toggleTheme}
          class="p-2 text-slate-500 hover:text-indigo-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-indigo-400 dark:hover:bg-slate-800/60 rounded-lg transition-all"
          aria-label="Toggle theme"
        >
          {#if isDark}
            <Sun size={18} />
          {:else}
            <Moon size={18} />
          {/if}
        </button>
        <div class="hidden sm:block text-[10px] font-black text-emerald-500 uppercase tracking-widest bg-emerald-50 px-2 py-1 rounded border border-emerald-100 dark:bg-emerald-950/20 dark:text-emerald-400 dark:border-emerald-950/50">
          System Online
        </div>
      </div>
    </header>

    <div class="flex-1 overflow-y-auto p-8 custom-scrollbar">
      {@render children()}
    </div>
  </main>
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
