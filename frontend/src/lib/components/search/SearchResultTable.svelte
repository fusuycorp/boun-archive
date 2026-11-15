<script lang="ts">
  import { User, ArrowUpRight } from "lucide-svelte";
  import type { SearchCourseHit } from "$lib/types";
  import SortableHeader from "./SortableHeader.svelte";

  interface Props {
    results: SearchCourseHit[];
    sortColumn: string;
    sortDirection: "asc" | "desc";
    onSort: (col: string) => void;
  }

  let { results, sortColumn, sortDirection, onSort }: Props = $props();
</script>

<div class="bg-white rounded-xl border border-[#e5e0d8] shadow-2xs overflow-hidden dark:bg-[#121827] dark:border-[#1e293b]">
  <div class="overflow-x-auto" role="region" aria-labelledby="search-results-caption">
    <table class="w-full text-left border-collapse">
      <caption id="search-results-caption" class="sr-only">Course search results table</caption>
      <thead>
        <tr class="border-b border-[#e5e0d8] bg-[#f3efe6]/60 dark:border-[#1e293b] dark:bg-[#0a0e1a]">
          <SortableHeader 
            column="term" 
            label="Term" 
            currentSort={sortColumn} 
            currentDirection={sortDirection} 
            {onSort} 
          />
          <SortableHeader 
            column="course_code" 
            label="Code & Title" 
            currentSort={sortColumn} 
            currentDirection={sortDirection} 
            {onSort} 
          />
          <th scope="col" class="p-4 text-xs font-semibold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider">Instructor</th>
          <th scope="col" class="p-4 text-xs font-semibold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider text-center">Cr</th>
          <th scope="col" class="p-4 text-xs font-semibold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider text-center">ECTS</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-[#e5e0d8] dark:divide-[#1e293b]">
        {#each results as course}
          <tr class="hover:bg-[#f3efe6]/50 transition-colors group dark:hover:bg-slate-800/50">
            <td class="p-4 text-xs font-mono font-medium text-[#525f7f] dark:text-slate-400 whitespace-nowrap">
              {course.term}
            </td>
            <td class="p-4">
              <div class="flex items-center space-x-2">
                <a 
                  href="/course/{encodeURIComponent(course.course_code)}" 
                  class="font-mono text-sm font-bold text-[#002d72] dark:text-slate-100 hover:text-[#0080c9] dark:hover:text-[#8cc8ea] hover:underline"
                >
                  {course.course_code}
                </a>
                {#if course.section}
                  <span class="px-1.5 py-0.5 bg-[#f3efe6] dark:bg-slate-800 text-[#161e2e] dark:text-slate-300 rounded text-[10px] font-mono font-semibold">
                    .{course.section}
                  </span>
                {/if}
                {#if course.has_syllabus}
                  <span class="px-1.5 py-0.5 bg-emerald-500/10 text-emerald-800 dark:bg-emerald-400/10 dark:text-emerald-300 border border-emerald-600/20 rounded text-[10px] font-mono font-semibold">
                    Syllabus
                  </span>
                {/if}
              </div>
              <a
                href="/course/{encodeURIComponent(course.course_code)}"
                class="block font-serif text-sm text-[#161e2e] dark:text-slate-200 truncate max-w-xs sm:max-w-md font-medium mt-0.5 hover:text-[#002d72] dark:hover:text-[#8cc8ea] hover:underline"
              >
                {course.title || "Untitled Course"}
              </a>
            </td>
            <td class="p-4 text-xs text-[#161e2e] dark:text-slate-300 font-medium">
              <div class="flex items-center space-x-1.5">
                <User size={13} aria-hidden="true" class="text-[#525f7f] shrink-0" />
                {#if course.instructor && course.instructor !== 'TBA'}
                  <a 
                    href={course.instructor_id ? `/instructor/${course.instructor_id}` : `/instructors?q=${encodeURIComponent(course.instructor)}`} 
                    class="inline-flex items-center space-x-1 text-[#161e2e] dark:text-slate-300 hover:text-[#002d72] dark:hover:text-[#8cc8ea] hover:underline truncate max-w-[160px] group/inst font-medium"
                    title="View instructor details"
                  >
                    <span class="truncate">{course.instructor}</span>
                    <ArrowUpRight size={12} aria-hidden="true" class="text-[#525f7f] group-hover/inst:text-[#002d72] dark:group-hover/inst:text-[#8cc8ea] shrink-0 opacity-70 group-hover/inst:opacity-100 transition-all" />
                  </a>
                {:else}
                  <span class="text-[#8a94a6] italic">TBA</span>
                {/if}
              </div>
            </td>
            <td class="p-4 text-xs font-mono font-medium text-center text-[#161e2e] dark:text-slate-300">
              {course.credits ?? 0}
            </td>
            <td class="p-4 text-xs font-mono font-medium text-center text-[#161e2e] dark:text-slate-300">
              {course.ects ?? 0}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>
