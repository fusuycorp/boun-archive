<script lang="ts">
  import { User, Calendar, MapPin } from "lucide-svelte";

  interface Props {
    course: any;
  }

  let { course }: Props = $props();
</script>

<div class="bg-white dark:bg-[#0f172a] p-4 rounded-2xl border border-slate-200/80 dark:border-slate-800/80 shadow-2xs space-y-3">
  <div class="flex items-start justify-between gap-2">
    <div>
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
      <h3 class="text-xs font-bold text-slate-800 dark:text-slate-100 mt-1 leading-snug">
        {course.title || "Untitled Course"}
      </h3>
    </div>
    <span class="px-2 py-0.5 bg-[#002d72]/10 dark:bg-sky-500/15 text-[#002d72] dark:text-sky-300 rounded text-[10px] font-bold shrink-0 font-mono">
      {course.term}
    </span>
  </div>

  <div class="flex flex-wrap items-center gap-y-1 gap-x-3 text-xs text-slate-500 dark:text-slate-400">
    <div class="flex items-center space-x-1">
      <User size={12} class="text-slate-400 shrink-0" />
      {#if course.instructor && course.instructor !== 'TBA'}
        <a href="/instructors?q={encodeURIComponent(course.instructor)}" class="hover:text-[#0080c9] dark:hover:text-sky-400 truncate max-w-[150px]">
          {course.instructor}
        </a>
      {:else}
        <span class="text-slate-400 italic">TBA</span>
      {/if}
    </div>
    <div class="flex items-center space-x-2 text-[11px] font-mono">
      <span>{course.credits ?? 0} Cr</span>
      <span class="text-slate-300 dark:text-slate-700">•</span>
      <span>{course.ects ?? 0} ECTS</span>
    </div>
  </div>

  {#if course.slots && course.slots.length > 0}
    <div class="flex flex-wrap gap-1.5 pt-1 border-t border-slate-100 dark:border-slate-800/60">
      {#each course.slots as slot}
        <span class="inline-flex items-center space-x-1 px-1.5 py-0.5 bg-slate-50 dark:bg-slate-950 border border-slate-200/80 dark:border-slate-800 rounded text-[10px] font-mono text-slate-600 dark:text-slate-300">
          <Calendar size={10} class="text-slate-400" />
          <span>{slot.day_code} {slot.slot_hour}</span>
          {#if slot.room_name && slot.room_name !== 'N/A'}
            <span class="text-slate-300 dark:text-slate-700">|</span>
            <MapPin size={9} class="text-slate-400" />
            <span class="truncate max-w-[60px]">{slot.room_name}</span>
          {/if}
        </span>
      {/each}
    </div>
  {/if}
</div>
