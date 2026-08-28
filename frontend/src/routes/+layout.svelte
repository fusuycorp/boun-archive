<script lang="ts">
  let { children } = $props();
  import "./layout.css";
  import { page } from "$app/state";
  import { onMount } from "svelte";
  import { 
    Search, 
    History, 
    LayoutGrid, 
    User, 
    CalendarDays, 
    BookOpen,
    Sun, 
    Moon,
    Menu,
    X
  } from "lucide-svelte";

  import { API_BASE } from "$lib/config";
  import type { SystemStatus } from "$lib/types";

  let isDark = $state(false);
  let isMobileDrawerOpen = $state(false);
  let systemStatus = $state<SystemStatus | null>(null);

  const navItems = [
    { href: "/", label: "Dashboard", icon: LayoutGrid },
    { href: "/search", label: "Search", icon: Search },
    { href: "/departments", label: "Departments", icon: BookOpen },
    { href: "/calendar", label: "Weekly Planner", icon: CalendarDays },
    { href: "/ghost-schedule", label: "Ghost Schedule", icon: History },
    { href: "/instructors", label: "Instructors", icon: User },
  ];

  function formatScrapeTime(isoString?: string | null): string {
    if (!isoString) return "Scraped: Live";
    try {
      const date = new Date(isoString.includes("T") ? isoString : isoString.replace(" ", "T") + "Z");
      if (isNaN(date.getTime())) return `Scraped: ${isoString}`;

      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffSecs = Math.floor(diffMs / 1000);
      const diffMins = Math.floor(diffSecs / 60);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffSecs >= 0 && diffSecs < 60) {
        return "Scraped just now";
      } else if (diffMins > 0 && diffMins < 60) {
        return `Scraped ${diffMins}m ago`;
      } else if (diffHours > 0 && diffHours < 24) {
        return `Scraped ${diffHours}h ago`;
      } else if (diffDays > 0 && diffDays < 7) {
        return `Scraped ${diffDays}d ago`;
      } else {
        return `Scraped ${date.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
      }
    } catch {
      return `Scraped: ${isoString}`;
    }
  }

  async function fetchSystemStatus() {
    try {
      const res = await fetch(`${API_BASE}/v1/system/status`);
      if (res.ok) {
        systemStatus = await res.json();
      }
    } catch {
      // Retain existing state on transient fetch failure
    }
  }

  onMount(() => {
    fetchSystemStatus();
    const statusInterval = setInterval(fetchSystemStatus, 60000);

    const savedTheme = localStorage.getItem("theme");
    const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    
    if (savedTheme === "dark" || (!savedTheme && systemPrefersDark)) {
      isDark = true;
      document.documentElement.classList.add("dark");
    } else {
      isDark = false;
      document.documentElement.classList.remove("dark");
    }

    return () => {
      clearInterval(statusInterval);
    };
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

  function closeMobileDrawer() {
    isMobileDrawerOpen = false;
  }
</script>

<svelte:head>
  <title>BOUN Archive • Boğaziçi University Academic Catalog</title>
</svelte:head>

<div class="min-h-screen w-full bg-slate-50 font-sans text-slate-900 transition-colors duration-200 dark:bg-[#0a0f1d] dark:text-slate-100 flex flex-col antialiased selection:bg-[#0080c9]/20 selection:text-[#002d72] dark:selection:bg-sky-500/30 dark:selection:text-sky-200">
  <!-- Top Navigation Header -->
  <header class="sticky top-0 z-40 w-full bg-white/95 dark:bg-[#0a0f1d]/95 backdrop-blur-md border-b border-slate-200/80 dark:border-slate-800/80 shadow-2xs transition-colors duration-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
      <!-- Left: Logo & Brand -->
      <a href="/" class="flex items-center space-x-3 group shrink-0" aria-label="BOUN Archive Home">
        <img 
          src="/logo.png" 
          alt="Boğaziçi University Crest" 
          class="h-9 w-9 rounded-lg shadow-2xs border border-slate-200/80 dark:border-slate-700/80 object-cover shrink-0 group-hover:scale-105 transition-transform duration-200" 
        />
        <div class="flex flex-col">
          <div class="flex items-center gap-1.5">
            <span class="text-base font-black tracking-tight text-[#002d72] dark:text-white leading-none">
              BOUN Archive
            </span>
            <span class="hidden sm:inline-block text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-700 dark:bg-amber-400/10 dark:text-amber-300 border border-amber-500/20">
              50y
            </span>
          </div>
          <span class="text-[9px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mt-0.5">
            Boğaziçi University
          </span>
        </div>
      </a>

      <!-- Center: Desktop Navigation Links -->
      <nav class="hidden lg:flex items-center space-x-1 xl:space-x-1.5" aria-label="Main Navigation">
        {#each navItems as item}
          {@const isActive = page.url.pathname === item.href}
          <a 
            href={item.href} 
            class="flex items-center space-x-2 px-3 py-2 rounded-lg text-xs xl:text-sm font-semibold transition-all duration-150
            {isActive 
              ? 'bg-[#002d72]/10 text-[#002d72] dark:bg-sky-500/15 dark:text-sky-300 shadow-2xs' 
              : 'text-slate-600 hover:text-[#002d72] hover:bg-slate-100/80 dark:text-slate-400 dark:hover:text-sky-300 dark:hover:bg-slate-800/60'}"
          >
            <item.icon size={16} class="shrink-0 {isActive ? 'text-[#002d72] dark:text-sky-300' : 'text-slate-400 dark:text-slate-500'}" />
            <span>{item.label}</span>
          </a>
        {/each}
      </nav>

      <!-- Right: Utilities (Scrape Time, Theme Toggle, Mobile Menu) -->
      <div class="flex items-center space-x-2 sm:space-x-3 shrink-0">
        <!-- Live Scrape Time Badge -->
        <div 
          class="hidden sm:inline-flex items-center gap-1.5 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-200/80 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-900/60 shadow-2xs select-none"
          title={systemStatus?.latest_scrape_time ? `Latest scrape: ${systemStatus.latest_scrape_time}` : "Scraper status: Live sync"}
        >
          <span class="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0"></span>
          <span class="tracking-tight">{formatScrapeTime(systemStatus?.latest_scrape_time)}</span>
        </div>

        <!-- Dark/Light Theme Toggle -->
        <button 
          onclick={toggleTheme}
          class="p-2 text-slate-500 hover:text-[#002d72] hover:bg-slate-100 dark:text-slate-400 dark:hover:text-sky-300 dark:hover:bg-slate-800/70 rounded-lg transition-colors cursor-pointer"
          aria-label="Toggle dark/light theme"
          title={isDark ? "Switch to light theme" : "Switch to dark theme"}
        >
          {#if isDark}
            <Sun size={18} class="text-amber-400" />
          {:else}
            <Moon size={18} class="text-slate-600" />
          {/if}
        </button>

        <!-- Mobile Menu Trigger -->
        <button 
          onclick={() => isMobileDrawerOpen = !isMobileDrawerOpen}
          class="lg:hidden p-2 text-slate-600 hover:text-[#002d72] hover:bg-slate-100 dark:text-slate-400 dark:hover:text-sky-300 dark:hover:bg-slate-800/70 rounded-lg transition-colors cursor-pointer"
          aria-label="Open mobile navigation menu"
        >
          {#if isMobileDrawerOpen}
            <X size={20} />
          {:else}
            <Menu size={20} />
          {/if}
        </button>
      </div>
    </div>
  </header>

  <!-- Mobile Off-Canvas Drawer Backdrop -->
  {#if isMobileDrawerOpen}
    <div 
      role="button"
      tabindex="0"
      aria-label="Close navigation overlay"
      onclick={closeMobileDrawer}
      onkeydown={(e) => (e.key === 'Escape' || e.key === 'Enter') && closeMobileDrawer()}
      class="lg:hidden fixed inset-0 z-40 bg-slate-950/60 backdrop-blur-xs transition-opacity duration-300 cursor-pointer"
    ></div>
  {/if}

  <!-- Mobile Off-Canvas Drawer -->
  <aside 
    class="lg:hidden fixed inset-y-0 left-0 z-50 w-72 bg-white dark:bg-[#0f172a] border-r border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col transition-transform duration-300 ease-in-out transform {isMobileDrawerOpen ? 'translate-x-0' : '-translate-x-full'}"
    aria-label="Mobile Navigation Drawer"
  >
    <div class="p-5 flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 shrink-0">
      <div class="flex items-center space-x-3">
        <img src="/logo.png" alt="BOUN Logo" class="h-9 w-9 rounded-lg shadow-2xs border border-slate-100 dark:border-slate-800 object-cover shrink-0" />
        <div>
          <h2 class="text-base font-extrabold text-[#002d72] tracking-tight leading-none dark:text-white">BOUN Archive</h2>
          <p class="text-[9px] text-slate-400 mt-1 uppercase tracking-widest font-black dark:text-slate-500">Academic Analytics</p>
        </div>
      </div>
      <button 
        onclick={closeMobileDrawer}
        class="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg cursor-pointer"
        aria-label="Close menu"
      >
        <X size={20} />
      </button>
    </div>

    <!-- Scrape status banner in mobile drawer -->
    <div class="px-4 py-3 bg-slate-50 dark:bg-slate-900/60 border-b border-slate-100 dark:border-slate-800/60 flex items-center justify-between text-xs font-semibold">
      <span class="text-slate-500 dark:text-slate-400">Portal Sync Status</span>
      <div class="flex items-center gap-1.5 text-emerald-700 dark:text-emerald-400 font-bold">
        <span class="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
        <span>{formatScrapeTime(systemStatus?.latest_scrape_time)}</span>
      </div>
    </div>

    <nav class="flex-1 px-3 py-4 space-y-1 overflow-y-auto custom-scrollbar">
      {#each navItems as item}
        {@const isActive = page.url.pathname === item.href}
        <a 
          href={item.href} 
          onclick={closeMobileDrawer}
          class="flex items-center space-x-3 px-4 py-3 rounded-xl font-semibold text-sm transition-all
          {isActive 
            ? 'bg-[#002d72]/10 text-[#002d72] shadow-2xs dark:bg-sky-500/15 dark:text-sky-300' 
            : 'text-slate-600 hover:bg-slate-50 hover:text-[#002d72] dark:text-slate-400 dark:hover:bg-slate-800/60 dark:hover:text-sky-300'}"
        >
          <item.icon size={18} class="shrink-0 {isActive ? 'text-[#002d72] dark:text-sky-300' : 'text-slate-400 dark:text-slate-500'}" />
          <span>{item.label}</span>
        </a>
      {/each}
    </nav>

    <div class="p-4 border-t border-slate-100 text-[10px] text-slate-400 text-center dark:border-slate-800/60 dark:text-slate-500 shrink-0">
      Boğaziçi University Academic Catalog • 50 Years
    </div>
  </aside>

  <!-- Main Content Container -->
  <main class="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 transition-colors duration-200">
    {@render children()}
  </main>

  <!-- Subtle Footer -->
  <footer class="w-full border-t border-slate-200/70 dark:border-slate-800/70 py-6 text-center text-xs text-slate-400 dark:text-slate-500 transition-colors duration-200">
    <div class="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
      <div class="flex items-center space-x-2">
        <span class="font-bold text-slate-600 dark:text-slate-300">BOUN Course Archive</span>
        <span>•</span>
        <span>Boğaziçi University Academic Analytics</span>
      </div>
      <div class="text-[11px] text-slate-400 dark:text-slate-500">
        Historical Data (1970–Present) & Real-time Scraper Feeds
      </div>
    </div>
  </footer>
</div>

