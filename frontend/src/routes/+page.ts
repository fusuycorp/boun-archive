import type { PageLoad } from './$types';
import { API_BASE } from '$lib/config';
import type { Department, DepartmentEvolution, SchedulingHeatmapSlot, SystemStatus } from '$lib/types';

export const load: PageLoad = async ({ fetch }) => {
  const [statsSearchRes, termsRes, deptsRes, evolutionRes, heatmapRes, statusRes] = await Promise.allSettled([
    fetch(`${API_BASE}/v1/search?limit=0`),
    fetch(`${API_BASE}/v1/terms`),
    fetch(`${API_BASE}/v1/departments`),
    fetch(`${API_BASE}/v1/analytics/macro/departments-evolution`),
    fetch(`${API_BASE}/v1/analytics/macro/scheduling-heatmap`),
    fetch(`${API_BASE}/v1/system/status`)
  ]);

  let totalCourses: number | null = null;
  let totalTerms: number | null = null;
  let totalDepts: number | null = null;
  let evolutionData: DepartmentEvolution | null = null;
  let heatmapData: SchedulingHeatmapSlot[] = [];
  let systemStatus: SystemStatus | null = null;
  let departments: Department[] = [];
  let hasError = false;

  if (statsSearchRes.status === 'fulfilled' && statsSearchRes.value.ok) {
    const searchData = await statsSearchRes.value.json();
    totalCourses = searchData?.totalHits ?? searchData?.estimatedTotalHits ?? null;
  } else {
    hasError = true;
  }

  if (termsRes.status === 'fulfilled' && termsRes.value.ok) {
    const termsData = await termsRes.value.json();
    if (Array.isArray(termsData) && termsData.length > 0) {
      totalTerms = termsData.length;
    }
  } else {
    hasError = true;
  }

  if (deptsRes.status === 'fulfilled' && deptsRes.value.ok) {
    const deptsData = await deptsRes.value.json();
    if (Array.isArray(deptsData) && deptsData.length > 0) {
      departments = deptsData;
      totalDepts = deptsData.length;
    }
  } else {
    hasError = true;
  }

  if (evolutionRes.status === 'fulfilled' && evolutionRes.value.ok) {
    evolutionData = await evolutionRes.value.json();
  }

  if (heatmapRes.status === 'fulfilled' && heatmapRes.value.ok) {
    heatmapData = await heatmapRes.value.json();
  }

  if (statusRes.status === 'fulfilled' && statusRes.value.ok) {
    systemStatus = await statusRes.value.json();
  }

  return {
    totalCourses,
    totalTerms,
    totalDepts,
    departments,
    evolutionData,
    heatmapData,
    systemStatus,
    hasError: hasError && totalCourses === null && totalTerms === null && totalDepts === null
  };
};
