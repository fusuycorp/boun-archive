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

  const scrapeFreshness = $derived.by(() => {
    if (!systemStatus) {
      return { 
        text: "Scraped: Checking...", 
        statusClass: "slate", 
        tooltip: "Checking upstream portal scrape status..." 
      };
    }

    const ts = systemStatus?.last_scraped_at || systemStatus?.upstream_scrape_time || systemStatus?.latest_scrape_time;
    if (!ts) {
      return { 
        text: "Scraped: Unknown", 
        statusClass: "slate", 
        tooltip: "No recorded portal scrape run available" 
      };
    }

    try {
      const date = new Date(ts.includes("T") ? ts : ts.replace(" ", "T") + "Z");
      if (isNaN(date.getTime())) {
        return { 
          text: `Scraped: ${ts}`, 
          statusClass: "slate", 
          tooltip: `Scrape timestamp: ${ts}` 
        };
      }

      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffSecs = Math.floor(diffMs / 1000);
      const diffMins = Math.floor(diffSecs / 60);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      let text = "Scraped just now";
      if (diffSecs >= 0 && diffSecs < 60) {
        text = "Scraped just now";
      } else if (diffMins > 0 && diffMins < 60) {
        text = `Scraped ${diffMins}m ago`;
      } else if (diffHours > 0 && diffHours < 24) {
        text = `Scraped ${diffHours}h ago`;
      } else if (diffDays > 0 && diffDays < 7) {
        text = `Scraped ${diffDays}d ago`;
      } else {
        text = `Scraped ${date.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
      }

      let statusClass = "emerald";
      if (systemStatus?.is_stale || diffHours >= 24) {
        statusClass = "rose";
      } else if (diffHours >= 6) {
        statusClass = "amber";
      }

      const portalTime = date.toLocaleString("en-US", { 
        month: "short", 
        day: "numeric", 
        year: "numeric",
        hour: "2-digit", 
        minute: "2-digit",
        timeZoneName: "short" 
      });
      const syncTs = systemStatus?.last_sync_at || systemStatus?.last_sync_time;
      const syncTime = syncTs ? new Date(syncTs).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", timeZoneName: "short" }) : 'Active';
      const tooltip = `Last Scraper Run: ${portalTime} (${text})\nArchive Sync: ${syncTime}${systemStatus?.is_stale ? ' (Stale >24h)' : ''}`;

      return { text, statusClass, tooltip };
    } catch {
      return { 
        text: `Scraped: ${ts}`, 
        statusClass: "slate", 
        tooltip: `Scrape timestamp: ${ts}` 
      };
    }
  });

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

<div class="min-h-screen w-full bg-[#eeece2] text-[#1c1b18] transition-colors duration-200 dark:bg-[#121214] dark:text-neutral-100 flex flex-col antialiased selection:bg-[#c5a059]/25 selection:text-[#1c1b18] dark:selection:bg-[#c5a059]/30 dark:selection:text-amber-200">
  <!-- Top Navigation Header -->
  <header class="sticky top-0 z-40 w-full bg-[#eeece2]/90 dark:bg-[#121214]/90 backdrop-blur-md border-b border-[#dbd7cc] dark:border-[#27272a] shadow-2xs transition-colors duration-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
      <!-- Left: Logo & Brand -->
      <a href="/" class="flex items-center space-x-3 group shrink-0" aria-label="BOUN Archive Home">
        <img 
          src="/logo.png" 
          alt="Boğaziçi University Crest" 
          class="h-9 w-9 rounded-lg shadow-2xs border border-[#dbd7cc] dark:border-[#27272a] object-cover shrink-0 group-hover:scale-105 transition-transform duration-200" 
        />
        <div class="flex flex-col">
          <div class="flex items-center gap-1.5">
            <span class="font-serif text-lg font-bold tracking-tight text-[#1c1b18] dark:text-neutral-50 leading-none">
              BOUN Archive
            </span>
            <span class="hidden sm:inline-block font-mono text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-900 dark:bg-amber-400/10 dark:text-amber-300 border border-amber-500/25">
              50y
            </span>
          </div>
          <span class="font-sans text-[9px] font-semibold uppercase tracking-widest text-[#746f65] dark:text-neutral-500 mt-0.5">
            Boğaziçi University
          </span>
        </div>
      </a>

      <!-- Center: Desktop Navigation Links -->
      <nav class="hidden lg:flex items-center space-x-1" aria-label="Main Navigation">
        {#each navItems as item}
          {@const isActive = page.url.pathname === item.href}
          <a 
            href={item.href} 
            class="flex items-center space-x-2 px-3 py-2 rounded-lg text-xs xl:text-sm font-semibold transition-colors duration-150
            {isActive 
              ? 'bg-[#dedacb] text-[#1c1b18] dark:bg-[#1f1f23] dark:text-neutral-100 shadow-2xs' 
              : 'text-[#5c5850] hover:text-[#1c1b18] hover:bg-[#e4e1d4] dark:text-neutral-400 dark:hover:text-neutral-200 dark:hover:bg-[#18181b]'}"
          >
            <item.icon size={15} class="shrink-0 {isActive ? 'text-[#002d72] dark:text-amber-400' : 'text-[#8a857a] dark:text-neutral-500'}" />
            <span>{item.label}</span>
          </a>
        {/each}
      </nav>

      <!-- Right: Utilities (Scrape Time, Theme Toggle, Mobile Menu) -->
      <div class="flex items-center space-x-2 sm:space-x-3 shrink-0">
        <!-- Live Scrape Time Badge -->
        <div 
          class="hidden sm:inline-flex items-center gap-1.5 font-mono text-[11px] font-medium px-2.5 py-1 rounded-md border shadow-2xs select-none transition-colors duration-150 {
            scrapeFreshness.statusClass === 'emerald'
              ? 'text-emerald-800 bg-emerald-500/10 border-emerald-600/20 dark:text-emerald-400 dark:bg-emerald-500/10 dark:border-emerald-500/20'
              : scrapeFreshness.statusClass === 'amber'
              ? 'text-amber-900 bg-amber-500/10 border-amber-600/20 dark:text-amber-300 dark:bg-amber-500/10 dark:border-amber-500/20'
              : scrapeFreshness.statusClass === 'rose'
              ? 'text-rose-800 bg-rose-500/10 border-rose-600/20 dark:text-rose-400 dark:bg-rose-500/10 dark:border-rose-500/20'
              : 'text-[#746f65] bg-[#dbd7cc]/30 border-[#dbd7cc] dark:text-neutral-400 dark:bg-neutral-800/40 dark:border-neutral-700/40'
          }"
          title={scrapeFreshness.tooltip}
        >
          <span class="inline-block w-1.5 h-1.5 rounded-full shrink-0 animate-pulse {
            scrapeFreshness.statusClass === 'emerald'
              ? 'bg-emerald-600 dark:bg-emerald-500'
              : scrapeFreshness.statusClass === 'amber'
              ? 'bg-amber-600 dark:bg-amber-500'
              : scrapeFreshness.statusClass === 'rose'
              ? 'bg-rose-600 dark:bg-rose-500'
              : 'bg-neutral-400 dark:bg-neutral-500'
          }"></span>
          <span class="tracking-tight">{scrapeFreshness.text}</span>
        </div>

        <!-- Dark/Light Theme Toggle -->
        <button 
          onclick={toggleTheme}
          class="p-2 text-[#5c5850] hover:text-[#1c1b18] hover:bg-[#e4e1d4] dark:text-neutral-400 dark:hover:text-neutral-200 dark:hover:bg-[#18181b] rounded-lg transition-colors cursor-pointer"
          aria-label="Toggle dark/light theme"
          title={isDark ? "Switch to light theme" : "Switch to dark theme"}
        >
          {#if isDark}
            <Sun size={17} class="text-amber-400" />
          {:else}
            <Moon size={17} class="text-[#5c5850]" />
          {/if}
        </button>

        <!-- Mobile Menu Trigger -->
        <button 
          onclick={() => isMobileDrawerOpen = !isMobileDrawerOpen}
          class="lg:hidden p-2 text-[#5c5850] hover:text-[#1c1b18] hover:bg-[#e4e1d4] dark:text-neutral-400 dark:hover:text-neutral-200 dark:hover:bg-[#18181b] rounded-lg transition-colors cursor-pointer"
          aria-label="Open mobile navigation menu"
        >
          {#if isMobileDrawerOpen}
            <X size={19} />
          {:else}
            <Menu size={19} />
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
      class="lg:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-xs transition-opacity duration-300 cursor-pointer"
    ></div>
  {/if}

  <!-- Mobile Off-Canvas Drawer -->
  <aside 
    class="lg:hidden fixed inset-y-0 left-0 z-50 w-72 bg-[#f7f5ee] dark:bg-[#18181b] border-r border-[#dbd7cc] dark:border-[#27272a] shadow-2xl flex flex-col transition-transform duration-300 ease-in-out transform {isMobileDrawerOpen ? 'translate-x-0' : '-translate-x-full'}"
    aria-label="Mobile Navigation Drawer"
  >
    <div class="p-5 flex items-center justify-between border-b border-[#dbd7cc] dark:border-[#27272a] shrink-0">
      <div class="flex items-center space-x-3">
        <img src="/logo.png" alt="BOUN Logo" class="h-9 w-9 rounded-lg shadow-2xs border border-[#dbd7cc] dark:border-[#27272a] object-cover shrink-0" />
        <div>
          <h2 class="font-serif text-base font-bold text-[#1c1b18] tracking-tight leading-none dark:text-neutral-50">BOUN Archive</h2>
          <p class="font-sans text-[9px] text-[#746f65] mt-1 uppercase tracking-widest font-semibold dark:text-neutral-500">Academic Analytics</p>
        </div>
      </div>
      <button 
        onclick={closeMobileDrawer}
        class="p-2 text-[#746f65] hover:text-[#1c1b18] dark:hover:text-neutral-200 rounded-lg cursor-pointer"
        aria-label="Close menu"
      >
        <X size={19} />
      </button>
    </div>

    <!-- Scrape status banner in mobile drawer -->
    <div class="px-4 py-3 bg-[#e7e4d9] dark:bg-[#121214] border-b border-[#dbd7cc] dark:border-[#27272a] flex items-center justify-between text-xs font-medium">
      <span class="text-[#5c5850] dark:text-neutral-400">Portal Sync Status</span>
      <div class="flex items-center gap-1.5 font-mono text-[11px] font-semibold {
        scrapeFreshness.statusClass === 'emerald'
          ? 'text-emerald-800 dark:text-emerald-400'
          : scrapeFreshness.statusClass === 'amber'
          ? 'text-amber-900 dark:text-amber-300'
          : 'text-rose-800 dark:text-rose-400'
      }">
        <span class="inline-block w-1.5 h-1.5 rounded-full shrink-0 animate-pulse {
          scrapeFreshness.statusClass === 'emerald'
            ? 'bg-emerald-600 dark:bg-emerald-500'
            : scrapeFreshness.statusClass === 'amber'
            ? 'bg-amber-600 dark:bg-amber-500'
            : 'bg-rose-600 dark:bg-rose-500'
        }"></span>
        <span>{scrapeFreshness.text}</span>
      </div>
    </div>

    <nav class="flex-1 px-3 py-4 space-y-1 overflow-y-auto custom-scrollbar">
      {#each navItems as item}
        {@const isActive = page.url.pathname === item.href}
        <a 
          href={item.href} 
          onclick={closeMobileDrawer}
          class="flex items-center space-x-3 px-4 py-3 rounded-xl font-semibold text-sm transition-colors
          {isActive 
            ? 'bg-[#dedacb] text-[#1c1b18] shadow-2xs dark:bg-[#27272a] dark:text-neutral-100' 
            : 'text-[#5c5850] hover:bg-[#e4e1d4] hover:text-[#1c1b18] dark:text-neutral-400 dark:hover:bg-[#232328] dark:hover:text-neutral-200'}"
        >
          <item.icon size={17} class="shrink-0 {isActive ? 'text-[#002d72] dark:text-amber-400' : 'text-[#8a857a] dark:text-neutral-500'}" />
          <span>{item.label}</span>
        </a>
      {/each}
    </nav>

    <div class="p-4 border-t border-[#dbd7cc] text-[10px] text-[#746f65] text-center dark:border-[#27272a] dark:text-neutral-500 shrink-0">
      Boğaziçi University Academic Catalog • 50 Years
    </div>
  </aside>

  <!-- Main Content Container -->
  <main class="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 transition-colors duration-200">
    {@render children()}
  </main>

  <!-- Subtle Footer -->
  <footer class="w-full border-t border-[#dbd7cc] dark:border-[#27272a] py-6 text-center text-xs text-[#746f65] dark:text-neutral-500 transition-colors duration-200">
    <div class="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
      <div class="flex items-center space-x-2">
        <span class="font-bold text-[#45423b] dark:text-neutral-300">BOUN Course Archive</span>
        <span>•</span>
        <span>Boğaziçi University Academic Analytics</span>
      </div>
      <div class="font-mono text-[11px] text-[#746f65] dark:text-neutral-500">
        Historical Corpus (1970–Present) & Real-time Feeds
      </div>
    </div>
  </footer>
</div>

