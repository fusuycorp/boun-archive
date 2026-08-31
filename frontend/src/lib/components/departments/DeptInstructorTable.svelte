<script lang="ts">
  import { User, ChevronRight, ArrowUpDown } from "lucide-svelte";
  import type { DepartmentInstructor } from "$lib/types";

  interface Props {
    instructors: DepartmentInstructor[];
    sortColumn: keyof DepartmentInstructor;
    sortDirection: "asc" | "desc";
    onSort: (col: keyof DepartmentInstructor) => void;
  }

  let { instructors, sortColumn, sortDirection, onSort }: Props = $props();
</script>

<!-- Mobile Instructor Cards (< sm) -->
<div class="block sm:hidden divide-y divide-[#e5e0d8] dark:divide-[#1e293b]">
  {#each instructors as instructor}
    <div class="p-4 space-y-2.5">
      <div class="flex items-center justify-between">
        <a 
          href="/instructor/{instructor.id}"
          class="flex items-center space-x-3"
        >
          <div class="w-8 h-8 bg-[#f3efe6] rounded-full flex items-center justify-center text-[#525f7f] dark:bg-slate-800 dark:text-slate-400 shrink-0">
            <User size={14} />
          </div>
          <span class="text-sm font-semibold text-[#161e2e] dark:text-slate-200">{instructor.full_name}</span>
        </a>
        <a href="/instructor/{instructor.id}" class="text-[#525f7f] hover:text-[#002d72] dark:hover:text-[#8cc8ea]"><ChevronRight size={15} /></a>
      </div>

      <div class="grid grid-cols-3 gap-2 pt-2 border-t border-[#e5e0d8] dark:border-[#1e293b] text-center font-mono">
        <div class="p-1.5 bg-[#faf8f5] dark:bg-[#0a0e1a] rounded">
          <span class="block text-[8px] uppercase font-bold text-[#525f7f]">Last Term</span>
          <span class="text-xs font-semibold text-[#161e2e] dark:text-slate-300 truncate block">{instructor.last_term}</span>
        </div>
        <div class="p-1.5 bg-[#faf8f5] dark:bg-[#0a0e1a] rounded">
          <span class="block text-[8px] uppercase font-bold text-[#525f7f]">Classes</span>
          <span class="text-xs font-bold text-[#002d72] dark:text-[#8cc8ea]">{instructor.course_count}</span>
        </div>
        <div class="p-1.5 bg-[#faf8f5] dark:bg-[#0a0e1a] rounded">
          <span class="block text-[8px] uppercase font-bold text-[#525f7f]">Semesters</span>
          <span class="text-xs font-bold text-[#002d72] dark:text-[#8cc8ea]">{instructor.total_semesters}</span>
        </div>
      </div>
    </div>
  {/each}
</div>

<!-- Desktop Instructor Table (>= sm) -->
<div class="hidden sm:block overflow-x-auto">
  <table class="w-full text-left border-collapse">
    <thead>
      <tr class="bg-[#f3efe6]/60 dark:bg-[#0a0e1a] border-b border-[#e5e0d8] dark:border-[#1e293b]">
        <th class="p-4">
          <button onclick={() => onSort('full_name')} class="flex items-center space-x-1 font-mono text-[10px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider hover:text-[#002d72] dark:hover:text-slate-200 transition-colors cursor-pointer">
            <span>Instructor Name</span>
            {#if sortColumn === 'full_name'}{sortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
          </button>
        </th>
        <th class="p-4">
          <button onclick={() => onSort('last_term')} class="flex items-center space-x-1 font-mono text-[10px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider hover:text-[#002d72] dark:hover:text-slate-200 transition-colors cursor-pointer">
            <span>Last Term in Dept</span>
            {#if sortColumn === 'last_term'}{sortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
          </button>
        </th>
        <th class="p-4 text-center">
          <button onclick={() => onSort('course_count')} class="flex items-center justify-center space-x-1 font-mono text-[10px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider hover:text-[#002d72] dark:hover:text-slate-200 transition-colors cursor-pointer">
            <span>Classes</span>
            {#if sortColumn === 'course_count'}{sortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
          </button>
        </th>
        <th class="p-4 text-center">
          <button onclick={() => onSort('total_semesters')} class="flex items-center justify-center space-x-1 font-mono text-[10px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider hover:text-[#002d72] dark:hover:text-slate-200 transition-colors cursor-pointer">
            <span>Semesters</span>
            {#if sortColumn === 'total_semesters'}{sortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
          </button>
        </th>
        <th class="p-4"></th>
      </tr>
    </thead>
    <tbody class="divide-y divide-[#e5e0d8] dark:divide-[#1e293b]">
      {#each instructors as instructor}
        <tr class="hover:bg-[#f3efe6]/50 dark:hover:bg-slate-800/50 transition-colors group">
          <td class="p-4 whitespace-nowrap">
            <a 
              href="/instructor/{instructor.id}"
              class="flex items-center space-x-3 group/item"
            >
              <div class="w-7 h-7 bg-[#f3efe6] rounded-full flex items-center justify-center text-[#525f7f] dark:bg-slate-800 dark:text-slate-400 group-hover/item:bg-[#002d72]/10 group-hover/item:text-[#002d72] transition-colors">
                <User size={13} />
              </div>
              <span class="text-sm font-semibold text-[#161e2e] dark:text-slate-200 group-hover/item:text-[#002d72] dark:group-hover/item:text-[#8cc8ea] transition-colors">{instructor.full_name}</span>
            </a>
          </td>
          <td class="p-4 whitespace-nowrap"><span class="font-mono text-xs font-medium text-[#525f7f] dark:text-slate-400">{instructor.last_term}</span></td>
          <td class="p-4 text-center"><span class="font-mono text-xs font-semibold text-[#161e2e] dark:text-slate-300">{instructor.course_count}</span></td>
          <td class="p-4 text-center"><span class="font-mono text-xs font-semibold text-[#161e2e] dark:text-slate-300">{instructor.total_semesters}</span></td>
          <td class="p-4 text-right">
             <a href="/instructor/{instructor.id}" class="text-[#525f7f] hover:text-[#002d72] dark:text-slate-500 dark:hover:text-[#8cc8ea] transition-colors" aria-label="View instructor details"><ChevronRight size={14} /></a>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>
