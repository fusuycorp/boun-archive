<script lang="ts">
  import { page } from "$app/state";
  import { AlertTriangle, Home, RotateCcw, Search, BookOpen } from "lucide-svelte";

  function handleReload() {
    if (typeof window !== "undefined") {
      window.location.reload();
    }
  }
</script>

<svelte:head>
  <title>{page.status} - BOUN Archive</title>
</svelte:head>

<div class="min-h-[75vh] flex items-center justify-center p-4 sm:p-6 lg:p-8">
  <div class="w-full max-w-xl mx-auto">
    <!-- Academic Card Surface -->
    <div 
      class="bg-[#f7f5ee] dark:bg-[#18181b] border border-[#dbd7cc] dark:border-[#27272a] rounded-2xl p-8 sm:p-10 shadow-sm relative overflow-hidden text-center"
      style="box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);"
    >
      <!-- Academic Gold Top Border Accent -->
      <div class="absolute top-0 left-0 right-0 h-1 bg-[#c5a059]"></div>

      <!-- Icon & Status Code Badge -->
      <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-[#eeece2] dark:bg-[#1f1f23] text-[#c5a059] mb-6 shadow-inner border border-[#dbd7cc]/50 dark:border-zinc-800">
        <AlertTriangle class="w-8 h-8 stroke-[1.75]" />
      </div>

      <div class="font-mono text-xs uppercase tracking-widest font-semibold text-[#c5a059] dark:text-[#c5a059] mb-2">
        Error {page.status}
      </div>

      <h1 class="text-3xl sm:text-4xl font-serif font-bold text-[#1c1b18] dark:text-zinc-100 mb-3 tracking-tight">
        {#if page.status === 404}
          Page Not Found
        {:else if page.status === 500}
          Internal Server Error
        {:else}
          Something Went Wrong
        {/if}
      </h1>

      <p class="text-sm sm:text-base text-zinc-600 dark:text-zinc-400 font-sans leading-relaxed max-w-md mx-auto mb-6">
        {page.error?.message || (page.status === 404 
          ? "The requested course, department, or archive record could not be found." 
          : "An unexpected system anomaly occurred while processing academic records.")}
      </p>

      <!-- Action Buttons -->
      <div class="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
        <button
          onclick={handleReload}
          class="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-[#c5a059] hover:bg-[#b08e4c] text-white font-medium text-sm transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-[#c5a059]/50"
        >
          <RotateCcw class="w-4 h-4" />
          <span>Try Again</span>
        </button>

        <a
          href="/"
          class="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-[#eeece2] hover:bg-[#e2dfd3] dark:bg-[#27272a] dark:hover:bg-[#323238] text-[#1c1b18] dark:text-zinc-200 font-medium text-sm transition-colors border border-[#dbd7cc] dark:border-zinc-700/80 focus:outline-none focus:ring-2 focus:ring-[#c5a059]/50"
        >
          <Home class="w-4 h-4" />
          <span>Return Home</span>
        </a>
      </div>

      <!-- Quick Navigation Links -->
      <div class="mt-8 pt-6 border-t border-[#dbd7cc]/70 dark:border-zinc-800 text-xs text-zinc-500 dark:text-zinc-400 flex items-center justify-center gap-4 flex-wrap">
        <a href="/search" class="inline-flex items-center gap-1.5 hover:text-[#c5a059] transition-colors">
          <Search class="w-3.5 h-3.5" />
          <span>Course Search</span>
        </a>
        <span class="text-zinc-300 dark:text-zinc-700">•</span>
        <a href="/departments" class="inline-flex items-center gap-1.5 hover:text-[#c5a059] transition-colors">
          <BookOpen class="w-3.5 h-3.5" />
          <span>Departments</span>
        </a>
      </div>
    </div>
  </div>
</div>
