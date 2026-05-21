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
    Moon 
  } from "lucide-svelte";

  let isDark = $state(false);

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
</script>

<div class="flex h-screen bg-slate-50 font-sans text-slate-900 transition-colors duration-200 dark:bg-slate-950 dark:text-slate-100">
  <!-- Sidebar -->
  <aside class="w-64 bg-white border-r border-slate-200 flex flex-col transition-colors duration-200 dark:bg-slate-900 dark:border-slate-800">
    <div class="p-6 flex items-center space-x-3">
      <img src="/logo.png" alt="BOUN Archive Logo" class="h-10 w-10 rounded-lg shadow-sm border border-slate-100 dark:border-slate-800 object-cover" />
      <div>
        <h1 class="text-base font-extrabold text-slate-900 tracking-tight leading-none dark:text-white">BOUN Archive</h1>
        <p class="text-[9px] text-slate-400 mt-1 uppercase tracking-widest font-black dark:text-slate-500">Academic Analytics</p>
      </div>
    </div>

    <nav class="flex-1 px-4 space-y-1">
      {#each navItems as item}
        <a 
          href={item.href} 
          class="flex items-center space-x-3 px-4 py-3 rounded-lg font-medium transition-all
          {page.url.pathname === item.href 
            ? 'bg-indigo-50 text-indigo-700 shadow-sm dark:bg-indigo-950/40 dark:text-indigo-400' 
            : 'text-slate-600 hover:bg-slate-50 hover:text-indigo-600 dark:text-slate-400 dark:hover:bg-slate-800/40 dark:hover:text-indigo-400'}"
        >
          <item.icon size={20} />
          <span>{item.label}</span>
        </a>
      {/each}
    </nav>

    <div class="p-4 border-t border-slate-100 text-[10px] text-slate-400 text-center dark:border-slate-800/60 dark:text-slate-500">
      v1.0.0-alpha • 50 Years of Data
    </div>
  </aside>

  <!-- Main Content -->
  <main class="flex-1 overflow-y-auto">
    <header class="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 sticky top-0 z-10 transition-colors duration-200 dark:bg-slate-900 dark:border-slate-800">
      <div class="text-sm font-medium text-slate-500 dark:text-slate-400">
        Bogazici University Historical Course Archive
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
        <div class="text-[10px] font-black text-emerald-500 uppercase tracking-widest bg-emerald-50 px-2 py-1 rounded border border-emerald-100 dark:bg-emerald-950/20 dark:text-emerald-400 dark:border-emerald-950/50">
          System Online
        </div>
      </div>
    </header>

    <div class="p-8">
      {@render children()}
    </div>
  </main>
</div>
