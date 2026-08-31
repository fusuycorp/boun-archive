<script lang="ts">
  import { User, ArrowUpRight } from "lucide-svelte";
  import { goto } from "$app/navigation";
  import type { SearchCourseHit } from "$lib/types";

  interface Props {
    course: SearchCourseHit;
  }

  let { course }: Props = $props();

  function gotoCourse() {
    goto(`/course/${encodeURIComponent(course.course_code)}`);
  }
</script>

<div 
  role="link"
  tabindex="0"
  onclick={gotoCourse}
  onkeydown={(e) => { if (e.key === 'Enter') gotoCourse(); }}
  class="bg-white dark:bg-[#121827] p-4 rounded-xl border border-[#e5e0d8] dark:border-[#1e293b] shadow-2xs space-y-3 cursor-pointer hover:border-[#c5a059] dark:hover:border-[#8cc8ea]/50 transition-colors group"
>
  <div class="flex items-start justify-between gap-2">
    <div>
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
      <h3 class="font-serif text-sm font-bold text-[#161e2e] dark:text-slate-100 mt-1 leading-snug">
        {course.title || "Untitled Course"}
      </h3>
    </div>
    <span class="px-2 py-0.5 bg-[#f3efe6] dark:bg-slate-800 text-[#161e2e] dark:text-slate-300 rounded text-[10px] font-semibold shrink-0 font-mono">
      {course.term}
    </span>
  </div>

  <div class="flex flex-wrap items-center gap-y-1 gap-x-3 text-xs text-[#525f7f] dark:text-slate-400">
    <div class="flex items-center space-x-1">
      <User size={12} class="text-[#525f7f] shrink-0" />
      {#if course.instructor && course.instructor !== 'TBA'}
        <a 
          href={course.instructor_id ? `/instructor/${course.instructor_id}` : `/instructors?q=${encodeURIComponent(course.instructor)}`} 
          onclick={(e) => e.stopPropagation()}
          class="inline-flex items-center space-x-1 text-[#161e2e] dark:text-slate-300 hover:text-[#002d72] dark:hover:text-[#8cc8ea] hover:underline truncate max-w-[150px] group/inst font-medium"
          title="View instructor details"
        >
          <span class="truncate">{course.instructor}</span>
          <ArrowUpRight size={11} class="text-[#525f7f] group-hover/inst:text-[#002d72] dark:group-hover/inst:text-[#8cc8ea] shrink-0 opacity-70 group-hover/inst:opacity-100 transition-all" />
        </a>
      {:else}
        <span class="text-[#8a94a6] italic">TBA</span>
      {/if}
    </div>
    <div class="flex items-center space-x-2 text-[11px] font-mono">
      <span>{course.credits ?? 0} Cr</span>
      <span class="text-[#e5e0d8] dark:text-slate-700">•</span>
      <span>{course.ects ?? 0} ECTS</span>
    </div>
  </div>
</div>
