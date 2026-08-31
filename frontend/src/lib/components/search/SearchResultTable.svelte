<script lang="ts">
  import { User, ArrowUpRight } from "lucide-svelte";
  import { goto } from "$app/navigation";
  import type { SearchCourseHit } from "$lib/types";
  import SortableHeader from "./SortableHeader.svelte";

  interface Props {
    results: SearchCourseHit[];
    sortColumn: string;
    sortDirection: "asc" | "desc";
    onSort: (col: string) => void;
  }

  let { results, sortColumn, sortDirection, onSort }: Props = $props();

  function gotoCourse(code: string) {
    goto(`/course/${encodeURIComponent(code)}`);
  }
</script>

<div class="bg-white rounded-xl border border-[#e5e0d8] shadow-2xs overflow-hidden dark:bg-[#121827] dark:border-[#1e293b]">
  <div class="overflow-x-auto">
    <table class="w-full text-left border-collapse">
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
          <th class="p-4 text-xs font-semibold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider">Instructor</th>
          <th class="p-4 text-xs font-semibold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider text-center">Cr</th>
          <th class="p-4 text-xs font-semibold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider text-center">ECTS</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-[#e5e0d8] dark:divide-[#1e293b]">
        {#each results as course}
          <tr 
            role="link"
            tabindex="0"
            onclick={() => gotoCourse(course.course_code)}
            onkeydown={(e) => { if (e.key === 'Enter') gotoCourse(course.course_code); }}
            class="hover:bg-[#f3efe6]/50 transition-colors group dark:hover:bg-slate-800/50 cursor-pointer"
          >
            <td class="p-4 text-xs font-mono font-medium text-[#525f7f] dark:text-slate-400 whitespace-nowrap">
              {course.term}
            </td>
            <td class="p-4">
              <div class="flex items-center space-x-2">
                <a 
                  href="/course/{encodeURIComponent(course.course_code)}" 
                  onclick={(e) => e.stopPropagation()}
                  class="font-mono text-sm font-bold text-[#002d72] dark:text-slate-100 hover:text-[#0080c9] dark:hover:text-[#8cc8ea] hover:underline"
                >
                  {course.course_code}
                </a>
                {#if course.section}
                  <span class="px-1.5 py-0.5 bg-[#f3efe6] dark:bg-slate-800 text-[#161e2e] dark:text-slate-300 rounded text-[10px] font-mono font-semibold">
                    .{course.section}
                  </span>
                {/if}
              </div>
              <div class="font-serif text-sm text-[#161e2e] dark:text-slate-200 truncate max-w-xs sm:max-w-md font-medium mt-0.5">
                {course.title || "Untitled Course"}
              </div>
            </td>
            <td class="p-4 text-xs text-[#161e2e] dark:text-slate-300 font-medium">
              <div class="flex items-center space-x-1.5">
                <User size={13} class="text-[#525f7f] shrink-0" />
                {#if course.instructor && course.instructor !== 'TBA'}
                  <a 
                    href={course.instructor_id ? `/instructor/${course.instructor_id}` : `/instructors?q=${encodeURIComponent(course.instructor)}`} 
                    onclick={(e) => e.stopPropagation()}
                    class="inline-flex items-center space-x-1 text-[#161e2e] dark:text-slate-300 hover:text-[#002d72] dark:hover:text-[#8cc8ea] hover:underline truncate max-w-[160px] group/inst font-medium"
                    title="View instructor details"
                  >
                    <span class="truncate">{course.instructor}</span>
                    <ArrowUpRight size={12} class="text-[#525f7f] group-hover/inst:text-[#002d72] dark:group-hover/inst:text-[#8cc8ea] shrink-0 opacity-70 group-hover/inst:opacity-100 transition-all" />
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
