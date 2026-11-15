<script lang="ts">
  import { ArrowUp, ArrowDown, ArrowUpDown } from "lucide-svelte";

  interface Props {
    column: string;
    label: string;
    currentSort: string;
    currentDirection: "asc" | "desc";
    onSort: (column: string) => void;
    align?: "left" | "center" | "right";
  }

  let { column, label, currentSort, currentDirection, onSort, align = "left" }: Props = $props();

  let isCurrent = $derived(currentSort === column);
</script>

<th 
  scope="col"
  aria-sort={isCurrent ? (currentDirection === "asc" ? "ascending" : "descending") : undefined}
  class="p-0 text-xs font-semibold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider select-none"
>
  <button
    type="button"
    onclick={() => onSort(column)}
    class="w-full p-4 flex items-center space-x-1.5 hover:text-[#002d72] dark:hover:text-slate-200 transition-colors cursor-pointer uppercase tracking-wider text-{align} {align === 'center' ? 'justify-center' : align === 'right' ? 'justify-end' : ''}"
  >
    <span>{label}</span>
    {#if isCurrent}
      {#if currentDirection === "asc"}
        <ArrowUp size={13} aria-hidden="true" class="text-[#002d72] dark:text-[#8cc8ea] shrink-0" />
      {:else}
        <ArrowDown size={13} aria-hidden="true" class="text-[#002d72] dark:text-[#8cc8ea] shrink-0" />
      {/if}
    {:else}
      <ArrowUpDown size={13} aria-hidden="true" class="opacity-30 shrink-0" />
    {/if}
  </button>
</th>
