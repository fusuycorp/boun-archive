import type { PageLoad } from './$types';
import { API_BASE } from '$lib/config';
import type { Instructor } from '$lib/types';

export const load: PageLoad = async ({ fetch }) => {
  let initialInstructors: Instructor[] = [];
  try {
    const res = await fetch(`${API_BASE}/v1/instructors`);
    if (res.ok) {
      initialInstructors = await res.json();
    }
  } catch (e) {
    console.error('Failed to load initial instructors', e);
  }

  return {
    instructors: initialInstructors
  };
};
