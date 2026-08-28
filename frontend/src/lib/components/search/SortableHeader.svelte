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
  onclick={() => onSort(column)}
  class="p-4 text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider cursor-pointer hover:text-slate-700 dark:hover:text-slate-300 transition-colors select-none text-{align}"
>
  <div class="flex items-center space-x-1.5 {align === 'center' ? 'justify-center' : align === 'right' ? 'justify-end' : ''}">
    <span>{label}</span>
    {#if isCurrent}
      {#if currentDirection === "asc"}
        <ArrowUp size={14} class="text-[#002d72] dark:text-sky-400" />
      {:else}
        <ArrowDown size={14} class="text-[#002d72] dark:text-sky-400" />
      {/if}
    {:else}
      <ArrowUpDown size={14} class="opacity-30" />
    {/if}
  </div>
</th>
