<script lang="ts">
  import { Sparkles, X, Plus, AlertTriangle, CheckCircle2, Clock } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import type {
    ScheduleOptimizationRequest,
    ScheduleOptimizationResponse,
    TimetableCombination,
    TimetableSection
  } from "$lib/types";

  type OptimizerState =
    | { status: "idle" }
    | { status: "solving"; abort: AbortController }
    | { status: "solved"; combinations: TimetableCombination[]; totalFound: number; selectedIdx: number }
    | { status: "empty"; message: string }
    | { status: "error"; httpCode: number | null; message: string };

  interface Props {
    open: boolean;
    selectedTerm: string;
    initialTargetCourses: string[];
    onClose: () => void;
    onApplySchedule: (sections: TimetableSection[]) => void;
  }

  let { open, selectedTerm, initialTargetCourses, onClose, onApplySchedule }: Props = $props();

  let dialogEl = $state<HTMLDialogElement | null>(null);
  let requiredCourses = $state<string[]>([]);
  let requiredInput = $state("");
  let electiveCourses = $state<string[]>([]);
  let electiveInput = $state("");
  let electivesNeeded = $state(0);
  let avoidDays = $state<string[]>([]);
  let minHour = $state(1);
  let maxHour = $state(14);
  let maxCampusDays = $state<string>("");
  let optimizerState = $state<OptimizerState>({ status: "idle" });

  const DAY_OPTIONS = [
    { code: "M", label: "Mon" },
    { code: "T", label: "Tue" },
    { code: "W", label: "Wed" },
    { code: "Th", label: "Thu" },
    { code: "F", label: "Fri" },
    { code: "St", label: "Sat" }
  ];

  const HOUR_OPTIONS = Array.from({ length: 14 }, (_, i) => i + 1);

  $effect(() => {
    if (!dialogEl) return;
    if (open) {
      if (requiredCourses.length === 0 && initialTargetCourses.length > 0) {
        requiredCourses = initialTargetCourses.slice(0, 10);
      }
      if (!dialogEl.open) dialogEl.showModal();
    } else {
      abortSolving();
      if (dialogEl.open) dialogEl.close();
    }
  });

  function abortSolving() {
    if (optimizerState.status === "solving") {
      optimizerState.abort.abort();
      optimizerState = { status: "idle" };
    }
  }

  function handleDialogClose() {
    abortSolving();
    onClose();
  }

  function normalizeCodeList(raw: string): string[] {
    return raw
      .split(",")
      .map((s) => s.trim().replace(/\s+/g, " ").toUpperCase())
      .filter(Boolean);
  }

  function addCourseCodes(target: "required" | "elective") {
    const raw = target === "required" ? requiredInput : electiveInput;
    const incoming = normalizeCodeList(raw);
    if (incoming.length === 0) return;

    if (target === "required") {
      const merged = Array.from(new Set([...requiredCourses, ...incoming])).slice(0, 10);
      requiredCourses = merged;
      electiveCourses = electiveCourses.filter((c) => !merged.includes(c));
      requiredInput = "";
    } else {
      const merged = Array.from(
        new Set([...electiveCourses, ...incoming.filter((c) => !requiredCourses.includes(c))])
      ).slice(0, 10);
      electiveCourses = merged;
      if (electivesNeeded > merged.length) electivesNeeded = merged.length;
      if (electivesNeeded === 0 && merged.length > 0) electivesNeeded = 1;
      electiveInput = "";
    }
  }

  function removeCourseCode(target: "required" | "elective", code: string) {
    if (target === "required") {
      requiredCourses = requiredCourses.filter((c) => c !== code);
    } else {
      electiveCourses = electiveCourses.filter((c) => c !== code);
      if (electivesNeeded > electiveCourses.length) electivesNeeded = electiveCourses.length;
    }
  }

  function syncFromPlanner() {
    requiredCourses = initialTargetCourses.slice(0, 10);
    electiveCourses = electiveCourses.filter((c) => !requiredCourses.includes(c));
    optimizerState = { status: "idle" };
  }

  function toggleAvoidDay(dayCode: string) {
    avoidDays = avoidDays.includes(dayCode)
      ? avoidDays.filter((d) => d !== dayCode)
      : [...avoidDays, dayCode];
  }

  function validateInputs(): string | null {
    if (!selectedTerm) return "Select an academic semester before solving.";
    if (requiredCourses.length < 1 || requiredCourses.length > 10) {
      return "Add between 1 and 10 required course codes.";
    }
    if (minHour > maxHour) return "Earliest slot hour cannot exceed latest slot hour.";
    if (electiveCourses.length > 10) return "Candidate electives are limited to 10 courses.";
    if (electivesNeeded > electiveCourses.length) {
      return "Electives needed cannot exceed the candidate electives list.";
    }
    return null;
  }

  async function solveSchedule() {
    if (requiredInput.trim()) addCourseCodes("required");
    if (electiveInput.trim()) addCourseCodes("elective");

    const validationError = validateInputs();
    if (validationError) {
      optimizerState = { status: "error", httpCode: null, message: validationError };
      return;
    }

    abortSolving();
    const abort = new AbortController();
    const timeoutId = setTimeout(
      () => abort.abort(new DOMException("Solver request timed out", "TimeoutError")),
      6500
    );
    optimizerState = { status: "solving", abort };

    const parsedMaxDays = maxCampusDays ? Number(maxCampusDays) : null;
    const payload: ScheduleOptimizationRequest = {
      term_id: selectedTerm,
      target_courses: requiredCourses,
      candidate_electives: electiveCourses,
      num_electives_needed: electiveCourses.length > 0 ? electivesNeeded : 0,
      avoid_days: avoidDays,
      min_hour: minHour,
      max_hour: maxHour,
      max_campus_days: parsedMaxDays,
      max_results: 5
    };

    try {
      const res = await fetch(`${API_BASE}/v1/optimizer/schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: abort.signal
      });

      if (!res.ok) {
        let errDetail = `Solver failed (HTTP ${res.status})`;
        try {
          const errJson = await res.json();
          if (typeof errJson?.detail === "string") errDetail = errJson.detail;
        } catch {}
        optimizerState = { status: "error", httpCode: res.status, message: errDetail };
        return;
      }

      const data: ScheduleOptimizationResponse = await res.json();
      if (!data.success || data.combinations.length === 0) {
        optimizerState = {
          status: "empty",
          message: data.message || "No conflict-free combinations matched these constraints."
        };
        return;
      }

      optimizerState = {
        status: "solved",
        combinations: data.combinations,
        totalFound: data.total_combinations_found,
        selectedIdx: 0
      };
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") {
        const timedOut = String(abort.signal.reason || "").includes("Timeout");
        optimizerState = timedOut
          ? { status: "error", httpCode: 504, message: "Solver exceeded the 6.5s request timeout." }
          : { status: "idle" };
        return;
      }
      optimizerState = {
        status: "error",
        httpCode: null,
        message: e instanceof Error ? e.message : "Network error while running schedule optimizer."
      };
    } finally {
      clearTimeout(timeoutId);
    }
  }

  function applySelectedCombination() {
    if (optimizerState.status !== "solved") return;
    const combo = optimizerState.combinations[optimizerState.selectedIdx];
    if (!combo) return;
    onApplySchedule(combo.sections);
    onClose();
  }
</script>

<dialog
  bind:this={dialogEl}
  aria-labelledby="optimizer-dialog-title"
  onclose={handleDialogClose}
  onclick={(e) => {
    if (e.target === e.currentTarget) e.currentTarget.close();
  }}
  class="open:flex flex-col m-auto p-0 w-[calc(100vw-2rem)] max-w-3xl max-h-[90dvh] rounded-2xl bg-white dark:bg-[#121827] border border-[#e5e0d8] dark:border-[#1e293b] shadow-2xl text-inherit backdrop:bg-black/60 backdrop:backdrop-blur-xs"
>
  <div class="flex flex-col max-h-[90dvh] w-full overflow-hidden">
    <!-- Modal Header -->
    <div class="p-4 sm:p-5 border-b border-[#e5e0d8] dark:border-[#1e293b] bg-[#f3efe6]/60 dark:bg-[#0a0e1a] flex items-center justify-between gap-3 shrink-0">
      <div class="flex items-center gap-2.5">
        <span class="p-2 rounded-lg bg-[#002d72]/10 text-[#002d72] dark:bg-[#8cc8ea]/15 dark:text-[#8cc8ea]">
          <Sparkles size={18} />
        </span>
        <div>
          <h2 id="optimizer-dialog-title" class="font-serif text-lg font-bold text-[#002d72] dark:text-slate-100">
            CSP Auto-Scheduler
          </h2>
          <p class="font-mono text-[11px] text-[#525f7f] dark:text-slate-400">
            Term {selectedTerm || "—"} • Minimizes gap hours & campus days
          </p>
        </div>
      </div>
      <button
        type="button"
        onclick={handleDialogClose}
        class="p-1.5 text-[#525f7f] hover:text-[#002d72] dark:hover:text-slate-200 rounded-lg cursor-pointer"
        aria-label="Close optimizer"
      >
        <X size={18} />
      </button>
    </div>

    <!-- Scrollable Form & Results Body -->
    <div class="p-4 sm:p-5 space-y-5 overflow-y-auto custom-scrollbar flex-1">
      <!-- Required Courses -->
      <div class="space-y-2">
        <div class="flex items-center justify-between">
          <label for="opt-required-input" class="font-mono text-xs font-bold uppercase tracking-wider text-[#161e2e] dark:text-slate-200">
            Required Courses ({requiredCourses.length}/10)
          </label>
          {#if initialTargetCourses.length > 0}
            <button
              type="button"
              onclick={syncFromPlanner}
              class="font-mono text-[11px] font-semibold text-[#0080c9] dark:text-[#8cc8ea] hover:underline cursor-pointer"
            >
              Sync from Planner ({initialTargetCourses.length})
            </button>
          {/if}
        </div>
        <div class="flex gap-2">
          <input
            id="opt-required-input"
            type="text"
            bind:value={requiredInput}
            onkeydown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addCourseCodes("required");
              }
            }}
            placeholder="Add course code (e.g. CMPE 150, MATH 101)"
            class="flex-1 px-3 py-2 bg-[#faf8f5] dark:bg-[#0a0e1a] border border-[#e5e0d8] dark:border-[#1e293b] rounded-lg text-xs font-mono uppercase outline-none focus:ring-2 focus:ring-[#002d72]/20"
          />
          <button
            type="button"
            onclick={() => addCourseCodes("required")}
            disabled={requiredCourses.length >= 10}
            class="inline-flex items-center gap-1 px-3 py-2 rounded-lg bg-[#002d72] text-white text-xs font-semibold hover:bg-[#001b44] disabled:opacity-40 cursor-pointer"
          >
            <Plus size={13} />
            <span>Add</span>
          </button>
        </div>
        {#if requiredCourses.length > 0}
          <div class="flex flex-wrap gap-1.5 pt-1">
            {#each requiredCourses as code}
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#002d72]/10 text-[#002d72] dark:bg-[#8cc8ea]/15 dark:text-[#8cc8ea] font-mono text-xs font-bold">
                {code}
                <button
                  type="button"
                  onclick={() => removeCourseCode("required", code)}
                  class="hover:text-rose-600 cursor-pointer"
                  aria-label="Remove {code}"
                >
                  <X size={12} />
                </button>
              </span>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Candidate Electives -->
      <div class="space-y-2 border-t border-[#e5e0d8] dark:border-[#1e293b] pt-4">
        <div class="flex items-center justify-between gap-2 flex-wrap">
          <label for="opt-elective-input" class="font-mono text-xs font-bold uppercase tracking-wider text-[#161e2e] dark:text-slate-200">
            Optional Candidate Electives ({electiveCourses.length}/10)
          </label>
          {#if electiveCourses.length > 0}
            <label class="inline-flex items-center gap-1.5 font-mono text-xs text-[#525f7f] dark:text-slate-400">
              <span>Pick</span>
              <input
                type="number"
                min="0"
                max={electiveCourses.length}
                bind:value={electivesNeeded}
                class="w-14 px-2 py-1 bg-[#faf8f5] dark:bg-[#0a0e1a] border border-[#e5e0d8] dark:border-[#1e293b] rounded text-xs text-center font-bold"
              />
              <span>of {electiveCourses.length}</span>
            </label>
          {/if}
        </div>
        <div class="flex gap-2">
          <input
            id="opt-elective-input"
            type="text"
            bind:value={electiveInput}
            onkeydown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addCourseCodes("elective");
              }
            }}
            placeholder="Optional elective pool (e.g. HIST 105, HUM 101)"
            class="flex-1 px-3 py-2 bg-[#faf8f5] dark:bg-[#0a0e1a] border border-[#e5e0d8] dark:border-[#1e293b] rounded-lg text-xs font-mono uppercase outline-none focus:ring-2 focus:ring-[#002d72]/20"
          />
          <button
            type="button"
            onclick={() => addCourseCodes("elective")}
            disabled={electiveCourses.length >= 10}
            class="inline-flex items-center gap-1 px-3 py-2 rounded-lg border border-[#e5e0d8] dark:border-[#1e293b] text-xs font-semibold hover:bg-[#f3efe6] dark:hover:bg-slate-800 disabled:opacity-40 cursor-pointer"
          >
            <Plus size={13} />
            <span>Add</span>
          </button>
        </div>
        {#if electiveCourses.length > 0}
          <div class="flex flex-wrap gap-1.5 pt-1">
            {#each electiveCourses as code}
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#c5a059]/15 text-[#9a7632] dark:text-[#e5a823] font-mono text-xs font-bold">
                {code}
                <button
                  type="button"
                  onclick={() => removeCourseCode("elective", code)}
                  class="hover:text-rose-600 cursor-pointer"
                  aria-label="Remove elective {code}"
                >
                  <X size={12} />
                </button>
              </span>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Constraints Grid -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 border-t border-[#e5e0d8] dark:border-[#1e293b] pt-4">
        <div class="space-y-1.5 sm:col-span-1">
          <span class="block font-mono text-[10px] font-bold uppercase tracking-wider text-[#525f7f] dark:text-slate-400">
            Avoid Days
          </span>
          <div class="flex flex-wrap gap-1.5">
            {#each DAY_OPTIONS as day}
              {@const blocked = avoidDays.includes(day.code)}
              <button
                type="button"
                onclick={() => toggleAvoidDay(day.code)}
                aria-pressed={blocked}
                class="px-2 py-1 rounded-md font-mono text-xs font-semibold border transition-colors cursor-pointer {blocked ? 'bg-rose-600 text-white border-rose-600' : 'bg-[#faf8f5] dark:bg-[#0a0e1a] border-[#e5e0d8] dark:border-[#1e293b] text-[#525f7f] dark:text-slate-300'}"
              >
                {day.label}
              </button>
            {/each}
          </div>
        </div>

        <div class="space-y-1.5">
          <span class="block font-mono text-[10px] font-bold uppercase tracking-wider text-[#525f7f] dark:text-slate-400">
            Slot Window (1–14)
          </span>
          <div class="flex items-center gap-2">
            <select
              aria-label="Earliest slot hour"
              bind:value={minHour}
              class="flex-1 p-2 bg-[#faf8f5] dark:bg-[#0a0e1a] border border-[#e5e0d8] dark:border-[#1e293b] rounded-lg text-xs font-mono"
            >
              {#each HOUR_OPTIONS as h}
                <option value={h}>Slot {h} ({String(8 + h).padStart(2, "0")}:00)</option>
              {/each}
            </select>
            <span class="text-xs text-[#525f7f]">to</span>
            <select
              aria-label="Latest slot hour"
              bind:value={maxHour}
              class="flex-1 p-2 bg-[#faf8f5] dark:bg-[#0a0e1a] border border-[#e5e0d8] dark:border-[#1e293b] rounded-lg text-xs font-mono"
            >
              {#each HOUR_OPTIONS as h}
                <option value={h}>Slot {h} ({String(8 + h).padStart(2, "0")}:00)</option>
              {/each}
            </select>
          </div>
        </div>

        <div class="space-y-1.5">
          <label for="opt-max-campus-days" class="block font-mono text-[10px] font-bold uppercase tracking-wider text-[#525f7f] dark:text-slate-400">
            Max Campus Days
          </label>
          <select
            id="opt-max-campus-days"
            bind:value={maxCampusDays}
            class="w-full p-2 bg-[#faf8f5] dark:bg-[#0a0e1a] border border-[#e5e0d8] dark:border-[#1e293b] rounded-lg text-xs font-mono"
          >
            <option value="">Any (No Limit)</option>
            {#each [1, 2, 3, 4, 5, 6] as d}
              <option value={String(d)}>At most {d} {d === 1 ? "day" : "days"}</option>
            {/each}
          </select>
        </div>
      </div>

      <!-- Solver Status / Results -->
      {#if optimizerState.status === "error"}
        <div role="alert" class="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800 flex items-start gap-2.5 text-xs text-rose-800 dark:text-rose-200">
          <AlertTriangle size={16} class="shrink-0 mt-0.5" />
          <div>
            <p class="font-semibold">{optimizerState.httpCode ? `HTTP ${optimizerState.httpCode}` : "Validation / Network Error"}</p>
            <p>{optimizerState.message}</p>
          </div>
        </div>
      {:else if optimizerState.status === "empty"}
        <div role="status" class="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-xs text-amber-900 dark:text-amber-200">
          {optimizerState.message}
        </div>
      {:else if optimizerState.status === "solved"}
        <div class="space-y-3 border-t border-[#e5e0d8] dark:border-[#1e293b] pt-4">
          <div class="flex items-center justify-between">
            <span class="inline-flex items-center gap-1.5 font-mono text-xs font-bold text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 size={15} />
              <span>Showing top {optimizerState.combinations.length} of {optimizerState.totalFound} conflict-free combinations</span>
            </span>
          </div>

          <div class="space-y-2.5">
            {#each optimizerState.combinations as combo, idx}
              {@const isSelected = optimizerState.selectedIdx === idx}
              <button
                type="button"
                onclick={() => {
                  if (optimizerState.status === "solved") {
                    optimizerState = { ...optimizerState, selectedIdx: idx };
                  }
                }}
                aria-pressed={isSelected}
                class="w-full text-left p-3.5 rounded-xl border transition-all cursor-pointer {isSelected ? 'border-[#002d72] bg-[#002d72]/5 dark:border-[#8cc8ea] dark:bg-[#8cc8ea]/10 ring-1 ring-[#002d72] dark:ring-[#8cc8ea]' : 'border-[#e5e0d8] dark:border-[#1e293b] hover:bg-[#faf8f5] dark:hover:bg-slate-800/40'}"
              >
                <div class="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-black/5 dark:border-white/5">
                  <div class="flex items-center gap-2 font-mono text-xs font-bold text-[#002d72] dark:text-[#8cc8ea]">
                    <span>Option #{idx + 1}</span>
                    <span class="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-800 dark:text-emerald-300 text-[10px]">
                      Score {combo.score}
                    </span>
                  </div>
                  <div class="flex flex-wrap items-center gap-3 font-mono text-[11px] text-[#525f7f] dark:text-slate-300">
                    <span>{combo.total_credits} Cr / {combo.total_ects} ECTS</span>
                    <span class="inline-flex items-center gap-1">
                      <Clock size={11} /> {combo.total_gap_hours}h gaps
                    </span>
                    <span>Days: {combo.campus_days.join(", ") || "—"}</span>
                  </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pt-2">
                  {#each combo.sections as sec}
                    <div class="text-[11px] font-mono bg-white/70 dark:bg-[#0a0e1a]/70 px-2.5 py-1.5 rounded-lg border border-[#e5e0d8]/70 dark:border-[#1e293b]">
                      <div class="font-bold text-[#161e2e] dark:text-slate-100">
                        {sec.course_code}.{sec.section}
                        <span class="font-sans font-normal text-[#525f7f] dark:text-slate-400"> • {sec.instructor || "TBA"}</span>
                      </div>
                      <div class="text-[10px] text-[#525f7f] dark:text-slate-400 truncate">
                        {sec.slots.map((s) => `${s.day_code}${s.slot_hour}`).join(" ") || "Unscheduled"}
                      </div>
                    </div>
                  {/each}
                </div>
              </button>
            {/each}
          </div>
        </div>
      {/if}
    </div>

    <!-- Modal Footer Actions -->
    <div class="p-4 border-t border-[#e5e0d8] dark:border-[#1e293b] bg-[#f3efe6]/60 dark:bg-[#0a0e1a] flex flex-wrap items-center justify-between gap-2 shrink-0">
      <button
        type="button"
        onclick={handleDialogClose}
        class="px-4 py-2 rounded-lg border border-[#e5e0d8] dark:border-[#1e293b] text-xs font-semibold text-[#525f7f] dark:text-slate-300 hover:bg-white dark:hover:bg-slate-800 cursor-pointer"
      >
        Cancel
      </button>

      <div class="flex items-center gap-2">
        <button
          type="button"
          onclick={solveSchedule}
          disabled={optimizerState.status === "solving"}
          class="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#002d72] text-white text-xs font-semibold hover:bg-[#001b44] disabled:opacity-50 cursor-pointer"
        >
          <Sparkles size={13} class={optimizerState.status === "solving" ? "animate-spin" : ""} />
          <span>{optimizerState.status === "solving" ? "Solving..." : "Find Optimal Schedules"}</span>
        </button>

        {#if optimizerState.status === "solved"}
          <button
            type="button"
            onclick={applySelectedCombination}
            class="px-4 py-2 rounded-lg bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-700 shadow-2xs cursor-pointer"
          >
            Apply Schedule
          </button>
        {/if}
      </div>
    </div>
  </div>
</dialog>
