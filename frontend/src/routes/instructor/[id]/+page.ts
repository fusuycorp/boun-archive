import type { PageLoad } from './$types';
import { API_BASE } from '$lib/config';

export const load: PageLoad = async ({ params, fetch }) => {
  const id = params.id;
  let legacyData: any = null;
  let loadError: string | null = null;

  try {
    const res = await fetch(`${API_BASE}/v1/analytics/instructor/${id}/legacy`);
    if (res.ok) {
      legacyData = await res.json();
    } else if (res.status === 404) {
      loadError = 'Instructor DNA not found';
    } else {
      loadError = 'Failed to load instructor data';
    }
  } catch (e: any) {
    loadError = e?.message || 'Failed to load instructor data';
  }

  return {
    instructorId: id,
    legacyData,
    error: loadError
  };
};
