<script lang="ts">
  import {
    Chart,
    LineController,
    LineElement,
    PointElement,
    LinearScale,
    CategoryScale,
    Filler,
    Tooltip,
    Legend,
    type ChartData
  } from "chart.js";
  import { Line } from "svelte-chartjs";

  Chart.register(
    LineController,
    LineElement,
    PointElement,
    LinearScale,
    CategoryScale,
    Filler,
    Tooltip,
    Legend
  );

  interface Props {
    data: ChartData<"line", number[], string>;
  }

  let { data }: Props = $props();
</script>

<Line
  {data}
  options={{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "bottom",
        labels: { boxWidth: 10, font: { size: 10, family: "IBM Plex Sans, system-ui, sans-serif" } }
      }
    },
    scales: {
      y: { grid: { color: "rgba(140,160,180,0.12)" } },
      x: { grid: { display: false } }
    }
  }}
/>
