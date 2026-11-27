import type { PageLoad } from './$types';
import { API_BASE } from '$lib/config';
import type { DepartmentEvolution, SchedulingHeatmapSlot } from '$lib/types';

export const load: PageLoad = async ({ fetch }) => {
  const [statsSearchRes, termsRes, deptsRes, evolutionRes, heatmapRes] = await Promise.allSettled([
    fetch(`${API_BASE}/v1/search?limit=0`),
    fetch(`${API_BASE}/v1/terms`),
    fetch(`${API_BASE}/v1/departments`),
    fetch(`${API_BASE}/v1/analytics/macro/departments-evolution`),
    fetch(`${API_BASE}/v1/analytics/macro/scheduling-heatmap`)
  ]);

  let totalCourses: number | null = null;
  let totalTerms: number | null = null;
  let totalDepts: number | null = null;
  let evolutionData: DepartmentEvolution | null = null;
  let heatmapData: SchedulingHeatmapSlot[] = [];
  let hasError = false;

  if (statsSearchRes.status === 'fulfilled' && statsSearchRes.value.ok) {
    try {
      const searchData = await statsSearchRes.value.json();
      totalCourses = searchData?.totalHits ?? searchData?.estimatedTotalHits ?? null;
    } catch {
      hasError = true;
    }
  } else {
    hasError = true;
  }

  if (termsRes.status === 'fulfilled' && termsRes.value.ok) {
    try {
      const termsData = await termsRes.value.json();
      if (Array.isArray(termsData) && termsData.length > 0) {
        totalTerms = termsData.length;
      }
    } catch {
      hasError = true;
    }
  } else {
    hasError = true;
  }

  if (deptsRes.status === 'fulfilled' && deptsRes.value.ok) {
    try {
      const deptsData = await deptsRes.value.json();
      if (Array.isArray(deptsData) && deptsData.length > 0) {
        totalDepts = deptsData.length;
      }
    } catch {
      hasError = true;
    }
  } else {
    hasError = true;
  }

  if (evolutionRes.status === 'fulfilled' && evolutionRes.value.ok) {
    try {
      evolutionData = await evolutionRes.value.json();
    } catch {
      evolutionData = null;
    }
  }

  if (heatmapRes.status === 'fulfilled' && heatmapRes.value.ok) {
    try {
      const parsedHeatmap = await heatmapRes.value.json();
      heatmapData = Array.isArray(parsedHeatmap) ? parsedHeatmap : [];
    } catch {
      heatmapData = [];
    }
  }

  return {
    totalCourses,
    totalTerms,
    totalDepts,
    evolutionData,
    heatmapData,
    hasError: hasError && totalCourses === null && totalTerms === null && totalDepts === null
  };
};
