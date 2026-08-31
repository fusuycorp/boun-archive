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
  class="p-4 text-xs font-semibold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:text-[#002d72] dark:hover:text-slate-200 transition-colors select-none text-{align}"
>
  <div class="flex items-center space-x-1.5 {align === 'center' ? 'justify-center' : align === 'right' ? 'justify-end' : ''}">
    <span>{label}</span>
    {#if isCurrent}
      {#if currentDirection === "asc"}
        <ArrowUp size={13} class="text-[#002d72] dark:text-[#8cc8ea]" />
      {:else}
        <ArrowDown size={13} class="text-[#002d72] dark:text-[#8cc8ea]" />
      {/if}
    {:else}
      <ArrowUpDown size={13} class="opacity-30" />
    {/if}
  </div>
</th>
