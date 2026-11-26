import type { PageLoad } from './$types';
import type { Instructor } from '$lib/types';

export const load: PageLoad = async () => {
  return {
    instructors: [] as Instructor[]
  };
};
