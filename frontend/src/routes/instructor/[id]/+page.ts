import type { PageLoad } from './$types';
import { API_BASE } from '$lib/config';
import type { InstructorLegacy } from '$lib/types';

export const load: PageLoad = async ({ params, fetch }) => {
  const id = params.id;
  let legacyData: InstructorLegacy | null = null;
  let loadError: string | null = null;

  if (!/^\d+$/.test(id)) {
    return {
      instructorId: id,
      legacyData: null,
      error: 'Instructor DNA not found'
    };
  }

  try {
    const res = await fetch(`${API_BASE}/v1/analytics/instructor/${encodeURIComponent(id)}/legacy`);
    if (res.ok) {
      legacyData = await res.json();
    } else if (res.status === 404) {
      loadError = 'Instructor DNA not found';
    } else {
      loadError = 'Failed to load instructor data';
    }
  } catch (e) {
    loadError = e instanceof Error ? e.message : 'Failed to load instructor data';
  }

  return {
    instructorId: id,
    legacyData,
    error: loadError
  };
};
