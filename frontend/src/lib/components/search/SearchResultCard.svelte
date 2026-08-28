<script lang="ts">
  import { User, Calendar, MapPin } from "lucide-svelte";

  interface Props {
    course: any;
  }

  let { course }: Props = $props();
</script>

<div class="bg-[#f7f5ee] dark:bg-[#18181b] p-4 rounded-xl border border-[#dbd7cc] dark:border-[#27272a] shadow-2xs space-y-3">
  <div class="flex items-start justify-between gap-2">
    <div>
      <div class="flex items-center space-x-2">
        <a 
          href="/course/{encodeURIComponent(course.course_code)}" 
          class="font-mono text-sm font-bold text-[#002d72] dark:text-neutral-100 hover:text-[#0080c9] dark:hover:text-amber-400 hover:underline"
        >
          {course.course_code}
        </a>
        {#if course.section}
          <span class="px-1.5 py-0.5 bg-[#e7e4d9] dark:bg-[#27272a] text-[#45423b] dark:text-neutral-300 rounded text-[10px] font-mono font-semibold">
            .{course.section}
          </span>
        {/if}
      </div>
      <h3 class="font-serif text-sm font-bold text-[#1c1b18] dark:text-neutral-100 mt-1 leading-snug">
        {course.title || "Untitled Course"}
      </h3>
    </div>
    <span class="px-2 py-0.5 bg-[#e7e4d9] dark:bg-[#27272a] text-[#45423b] dark:text-neutral-300 rounded text-[10px] font-semibold shrink-0 font-mono">
      {course.term}
    </span>
  </div>

  <div class="flex flex-wrap items-center gap-y-1 gap-x-3 text-xs text-[#5c5850] dark:text-neutral-400">
    <div class="flex items-center space-x-1">
      <User size={12} class="text-[#746f65] shrink-0" />
      {#if course.instructor && course.instructor !== 'TBA'}
        <a href="/instructors?q={encodeURIComponent(course.instructor)}" class="hover:text-[#002d72] dark:hover:text-amber-400 truncate max-w-[150px]">
          {course.instructor}
        </a>
      {:else}
        <span class="text-[#8a857a] italic">TBA</span>
      {/if}
    </div>
    <div class="flex items-center space-x-2 text-[11px] font-mono">
      <span>{course.credits ?? 0} Cr</span>
      <span class="text-[#c8c3b5] dark:text-neutral-700">•</span>
      <span>{course.ects ?? 0} ECTS</span>
    </div>
  </div>

  {#if course.slots && course.slots.length > 0}
    <div class="flex flex-wrap gap-1.5 pt-1 border-t border-[#dbd7cc]/70 dark:border-[#27272a]">
      {#each course.slots as slot}
        <span class="inline-flex items-center space-x-1 px-1.5 py-0.5 bg-[#eeece2] dark:bg-[#121214] border border-[#dbd7cc] dark:border-[#27272a] rounded text-[10px] font-mono text-[#45423b] dark:text-neutral-300">
          <Calendar size={10} class="text-[#746f65]" />
          <span>{slot.day_code} {slot.slot_hour}</span>
          {#if slot.room_name && slot.room_name !== 'N/A'}
            <span class="text-[#c8c3b5] dark:text-neutral-700">|</span>
            <MapPin size={9} class="text-[#746f65]" />
            <span class="truncate max-w-[50px]">{slot.room_name}</span>
          {/if}
        </span>
      {/each}
    </div>
  {/if}
</div>
