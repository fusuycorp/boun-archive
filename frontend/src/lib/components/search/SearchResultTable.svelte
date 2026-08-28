<script lang="ts">
  import { User, Calendar, MapPin } from "lucide-svelte";
  import SortableHeader from "./SortableHeader.svelte";

  interface Props {
    results: any[];
    sortColumn: string;
    sortDirection: "asc" | "desc";
    onSort: (col: string) => void;
  }

  let { results, sortColumn, sortDirection, onSort }: Props = $props();
</script>

<div class="bg-white rounded-2xl border border-slate-200/80 shadow-2xs overflow-hidden dark:bg-[#0f172a] dark:border-slate-800/80">
  <div class="overflow-x-auto">
    <table class="w-full text-left border-collapse">
      <thead>
        <tr class="border-b border-slate-100 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-950/50">
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
          <th class="p-4 text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Instructor</th>
          <th class="p-4 text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Schedule & Rooms</th>
          <th class="p-4 text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider text-center">Cr</th>
          <th class="p-4 text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider text-center">ECTS</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-100 dark:divide-slate-800/80">
        {#each results as course}
          <tr class="hover:bg-slate-50/80 transition-colors group dark:hover:bg-slate-800/40">
            <td class="p-4 text-xs font-bold text-slate-500 dark:text-slate-400 whitespace-nowrap font-mono">
              {course.term}
            </td>
            <td class="p-4">
              <div class="flex items-center space-x-2">
                <a 
                  href="/course/{encodeURIComponent(course.course_code)}" 
                  class="font-mono text-sm font-black text-[#002d72] dark:text-sky-400 hover:text-[#0080c9] dark:hover:text-sky-300 hover:underline"
                >
                  {course.course_code}
                </a>
                {#if course.section}
                  <span class="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 rounded text-[10px] font-mono font-bold">
                    .{course.section}
                  </span>
                {/if}
              </div>
              <div class="text-xs text-slate-500 dark:text-slate-400 truncate max-w-xs sm:max-w-md font-medium mt-0.5">
                {course.title || "Untitled Course"}
              </div>
            </td>
            <td class="p-4 text-xs text-slate-600 dark:text-slate-300 font-medium">
              <div class="flex items-center space-x-1.5">
                <User size={13} class="text-slate-400 shrink-0" />
                {#if course.instructor && course.instructor !== 'TBA'}
                  <a 
                    href="/instructors?q={encodeURIComponent(course.instructor)}" 
                    class="hover:text-[#0080c9] dark:hover:text-sky-400 hover:underline truncate max-w-[140px]"
                  >
                    {course.instructor}
                  </a>
                {:else}
                  <span class="text-slate-400 italic">TBA</span>
                {/if}
              </div>
            </td>
            <td class="p-4">
              <div class="flex flex-wrap gap-1.5 max-w-xs">
                {#if course.slots && course.slots.length > 0}
                  {#each course.slots as slot}
                    <span class="inline-flex items-center space-x-1 px-1.5 py-0.5 bg-slate-50 dark:bg-slate-950 border border-slate-200/80 dark:border-slate-800 rounded text-[10px] font-mono text-slate-600 dark:text-slate-300">
                      <Calendar size={10} class="text-slate-400" />
                      <span>{slot.day_code} {slot.slot_hour}</span>
                      {#if slot.room_name && slot.room_name !== 'N/A'}
                        <span class="text-slate-300 dark:text-slate-700">|</span>
                        <MapPin size={9} class="text-slate-400" />
                        <span class="truncate max-w-[50px]">{slot.room_name}</span>
                      {/if}
                    </span>
                  {/each}
                {:else}
                  <span class="text-slate-400 text-xs italic">No schedule</span>
                {/if}
              </div>
            </td>
            <td class="p-4 text-xs font-mono font-bold text-center text-slate-700 dark:text-slate-300">
              {course.credits ?? 0}
            </td>
            <td class="p-4 text-xs font-mono font-bold text-center text-slate-700 dark:text-slate-300">
              {course.ects ?? 0}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>
