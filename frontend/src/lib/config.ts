import { env } from '$env/dynamic/public';
import { browser } from '$app/environment';

/**
 * Resolves the API base URL.
 * - In the browser: If PUBLIC_API_URL points to a loopback/internal host (e.g. localhost, 127.0.0.1, backend:8000)
 *   while the user is accessing from a remote domain/host, automatically fallback to '/api' so requests route
 *   through the reverse proxy.
 * - On server (SSR): Uses PUBLIC_API_URL or defaults to '/api'.
 */
function resolveApiBase(): string {
  const configured = env.PUBLIC_API_URL?.trim().replace(/\/+$/, '');

  if (browser) {
    if (configured && (configured.includes('localhost') || configured.includes('127.0.0.1') || configured.includes('backend:'))) {
      if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
        return '/api';
      }
    }
  }

  return configured || '/api';
}

export const API_BASE = resolveApiBase();

