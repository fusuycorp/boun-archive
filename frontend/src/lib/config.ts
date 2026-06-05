import { env } from '$env/dynamic/public';

// Resolve public backend URL at runtime (client-side and server-side).
// Defaults to local development URL if not specified.
export const API_BASE = env.PUBLIC_API_URL || '';
