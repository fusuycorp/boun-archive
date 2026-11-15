import type { PageLoad } from './$types';
import { API_BASE } from '$lib/config';
import type { CourseCatalogInfo, CourseHistoryItem, QuotaSnapshot } from '$lib/types';

export const load: PageLoad = async ({ params, fetch }) => {
  const code = params.code || '';
  const encodedCode = encodeURIComponent(code.trim());

  let history: CourseHistoryItem[] = [];
  let quotas: QuotaSnapshot[] = [];
  let catalog: CourseCatalogInfo | null = null;
  let loadError: string | null = null;

  try {
    const [histRes, quotaRes, catalogRes] = await Promise.allSettled([
      fetch(`${API_BASE}/v1/courses/history/${encodedCode}`),
      fetch(`${API_BASE}/v1/courses/${encodedCode}/quota`),
      fetch(`${API_BASE}/v1/courses/catalog/${encodedCode}`)
    ]);

    if (histRes.status === 'fulfilled' && histRes.value.ok) {
      history = await histRes.value.json();
    } else if (histRes.status === 'fulfilled' && histRes.value.status === 404) {
      loadError = 'Course history not found';
    } else {
      loadError = 'Failed to fetch course history';
    }

    if (quotaRes.status === 'fulfilled' && quotaRes.value.ok) {
      quotas = await quotaRes.value.json();
    }

    if (catalogRes.status === 'fulfilled' && catalogRes.value.ok) {
      catalog = await catalogRes.value.json();
    }
  } catch (e) {
    loadError = e instanceof Error ? e.message : 'Failed to fetch course data';
  }

  return {
    courseCode: code,
    history,
    quotas,
    catalog,
    error: loadError
  };
};
