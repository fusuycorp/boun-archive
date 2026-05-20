<script lang="ts">
  let { children } = $props();
  import "../app.css";
  import { Search, History, LayoutGrid, TrendingUp, User } from "lucide-svelte";
</script>

<div class="flex h-screen bg-slate-50 font-sans text-slate-900">
  <!-- Sidebar -->
  <aside class="w-64 bg-white border-r border-slate-200 flex flex-col">
    <div class="p-6">
      <h1 class="text-xl font-bold text-indigo-600 tracking-tight">BOUN Archive</h1>
      <p class="text-xs text-slate-500 mt-1 uppercase tracking-widest font-semibold">Academic Analytics</p>
    </div>
    
    <nav class="flex-1 px-4 space-y-1">
      <a href="/" class="flex items-center space-x-3 px-4 py-3 rounded-lg bg-indigo-50 text-indigo-700 font-medium transition-colors">
        <LayoutGrid size={20} />
        <span>Dashboard</span>
      </a>
      <a href="/search" class="flex items-center space-x-3 px-4 py-3 rounded-lg text-slate-600 hover:bg-slate-100 transition-colors">
        <Search size={20} />
        <span>Search</span>
      </a>
      <a href="/ghost-schedule" class="flex items-center space-x-3 px-4 py-3 rounded-lg text-slate-600 hover:bg-slate-100 transition-colors">
        <History size={20} />
        <span>Ghost Schedule</span>
      </a>
      <a href="/trends" class="flex items-center space-x-3 px-4 py-3 rounded-lg text-slate-600 hover:bg-slate-100 transition-colors">
        <TrendingUp size={20} />
        <span>Trends</span>
      </a>
      <a href="/instructors" class="flex items-center space-x-3 px-4 py-3 rounded-lg text-slate-600 hover:bg-slate-100 transition-colors">
        <User size={20} />
        <span>Instructors</span>
      </a>
    </nav>

    <div class="p-4 border-t border-slate-100 text-[10px] text-slate-400 text-center">
      v1.0.0-alpha • 50 Years of Data
    </div>
  </aside>

  <!-- Main Content -->
  <main class="flex-1 overflow-y-auto">
    <header class="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 sticky top-0 z-10">
      <div class="text-sm text-slate-500">
        Bogazici University Historical Course Archive
      </div>
      <div class="flex items-center space-x-4">
        <button class="text-sm font-medium text-slate-600 hover:text-indigo-600">Documentation</button>
        <div class="h-8 w-8 rounded-full bg-slate-200"></div>
      </div>
    </header>

    <div class="p-8">
      {@render children()}
    </div>
  </main>
</div>
