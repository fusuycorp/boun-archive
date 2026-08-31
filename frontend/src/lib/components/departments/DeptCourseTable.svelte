<script lang="ts">
  import { ArrowRight, ArrowUpDown } from "lucide-svelte";
  import type { DepartmentUniqueCourse } from "$lib/types";

  interface Props {
    courses: DepartmentUniqueCourse[];
    sortColumn: keyof DepartmentUniqueCourse | "latest_term";
    sortDirection: "asc" | "desc";
    onSort: (col: keyof DepartmentUniqueCourse | "latest_term") => void;
  }

  let { courses, sortColumn, sortDirection, onSort }: Props = $props();
</script>

<!-- Mobile Course Cards (< sm) -->
<div class="block sm:hidden divide-y divide-[#e5e0d8] dark:divide-[#1e293b]">
  {#each courses as course}
    <div class="p-4 space-y-2">
      <div class="flex items-start justify-between gap-2">
        <div>
          <span class="font-mono text-sm font-bold text-[#002d72] dark:text-slate-100">{course.course_code}</span>
          <h4 class="font-serif text-sm font-bold text-[#161e2e] dark:text-slate-100 mt-0.5">{course.title}</h4>
        </div>
        <span class="text-[10px] font-semibold px-2 py-0.5 bg-[#f3efe6] dark:bg-slate-800 text-[#161e2e] dark:text-slate-300 rounded font-mono shrink-0">
          {course.latest_term}
        </span>
      </div>

      <div class="flex flex-wrap gap-1 pt-1">
        {#each course.terms.slice(0, 3) as term}
          <span class="px-1.5 py-0.5 bg-[#faf8f5] text-[#161e2e] text-[9px] font-mono font-medium rounded dark:bg-[#0a0e1a] dark:text-slate-400 border border-[#e5e0d8] dark:border-[#1e293b]">{term}</span>
        {/each}
        {#if course.terms.length > 3}
          <span class="px-1.5 py-0.5 bg-[#c5a059]/15 text-[#9a7632] text-[9px] font-mono font-bold rounded dark:bg-[#c5a059]/20 dark:text-[#e5a823] border border-[#c5a059]/30">+{course.terms.length - 3} MORE</span>
        {/if}
      </div>

      <div class="pt-2 text-right">
        <a href="/course/{course.course_code}" class="inline-flex items-center space-x-1 text-xs font-semibold text-[#002d72] dark:text-[#8cc8ea] hover:underline">
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
      <tr class="bg-[#f3efe6]/60 dark:bg-[#0a0e1a] border-b border-[#e5e0d8] dark:border-[#1e293b]">
        <th class="p-4">
          <button onclick={() => onSort('course_code')} class="flex items-center space-x-1 font-mono text-[10px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider hover:text-[#002d72] dark:hover:text-slate-200 transition-colors cursor-pointer">
            <span>Code</span>
            {#if sortColumn === 'course_code'}{sortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
          </button>
        </th>
        <th class="p-4">
          <button onclick={() => onSort('title')} class="flex items-center space-x-1 font-mono text-[10px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider hover:text-[#002d72] dark:hover:text-slate-200 transition-colors cursor-pointer">
            <span>Title</span>
            {#if sortColumn === 'title'}{sortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
          </button>
        </th>
        <th class="p-4">
          <button onclick={() => onSort('latest_term')} class="flex items-center space-x-1 font-mono text-[10px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider hover:text-[#002d72] dark:hover:text-slate-200 transition-colors cursor-pointer">
            <span>Latest Term</span>
            {#if sortColumn === 'latest_term'}{sortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
          </button>
        </th>
        <th class="p-4 font-mono text-[10px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider">Active Semesters</th>
        <th class="p-4"></th>
      </tr>
    </thead>
    <tbody class="divide-y divide-[#e5e0d8] dark:divide-[#1e293b]">
      {#each courses as course}
        <tr class="hover:bg-[#f3efe6]/50 dark:hover:bg-slate-800/50 transition-colors group">
          <td class="p-4 whitespace-nowrap"><span class="font-mono text-sm font-bold text-[#002d72] dark:text-slate-100">{course.course_code}</span></td>
          <td class="p-4"><span class="font-serif text-sm font-medium text-[#161e2e] dark:text-slate-200">{course.title}</span></td>
          <td class="p-4 whitespace-nowrap"><span class="font-mono text-xs font-medium text-[#525f7f] dark:text-slate-400">{course.latest_term}</span></td>
          <td class="p-4">
            <div class="flex flex-wrap gap-1">
              {#each course.terms.slice(0, 3) as term}
                <span class="px-1.5 py-0.5 bg-[#faf8f5] text-[#161e2e] text-[9px] font-mono font-medium rounded dark:bg-[#0a0e1a] dark:text-slate-400 border border-[#e5e0d8] dark:border-[#1e293b]">{term}</span>
              {/each}
              {#if course.terms.length > 3}
                <span class="px-1.5 py-0.5 bg-[#c5a059]/15 text-[#9a7632] text-[9px] font-mono font-bold rounded dark:bg-[#c5a059]/20 dark:text-[#e5a823] border border-[#c5a059]/30">+{course.terms.length - 3} MORE</span>
              {/if}
            </div>
          </td>
          <td class="p-4 text-right">
            <a href="/course/{course.course_code}" class="inline-flex items-center space-x-1.5 text-xs font-semibold text-[#525f7f] hover:text-[#002d72] dark:hover:text-[#8cc8ea] transition-colors">
              <span>History</span> <ArrowRight size={13} />
            </a>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>
