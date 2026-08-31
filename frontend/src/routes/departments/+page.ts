import type { PageLoad } from './$types';
import { API_BASE } from '$lib/config';
import type { Department, Term } from '$lib/types';

export const load: PageLoad = async ({ fetch }) => {
  const [deptsRes, termsRes] = await Promise.allSettled([
    fetch(`${API_BASE}/v1/departments`),
    fetch(`${API_BASE}/v1/terms`)
  ]);

  let departments: Department[] = [];
  let terms: Term[] = [];

  if (deptsRes.status === 'fulfilled' && deptsRes.value.ok) {
    departments = await deptsRes.value.json();
  }

  if (termsRes.status === 'fulfilled' && termsRes.value.ok) {
    terms = await termsRes.value.json();
  }

  return {
    departments,
    terms
  };
};
