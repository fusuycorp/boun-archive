import { browser } from "$app/environment";

interface CacheEntry<T> {
  value: T;
  expiresAt: number;
}

const DEFAULT_TTL_MS = 5 * 60 * 1000;
const MAX_ENTRIES = 20;

const responseCache = new Map<string, CacheEntry<unknown>>();
const inflightRequests = new Map<string, Promise<unknown>>();

function setBoundedEntry<T>(key: string, value: T, ttlMs: number): void {
  if (responseCache.size >= MAX_ENTRIES && !responseCache.has(key)) {
    const oldestKey = responseCache.keys().next().value;
    if (oldestKey !== undefined) responseCache.delete(oldestKey);
  }
  responseCache.set(key, { value, expiresAt: Date.now() + ttlMs });
}

/**
 * Bounded browser-side JSON TTL cache with in-flight deduplication for
 * slowly-changing metadata endpoints (/v1/terms, /v1/facets).
 */
export async function fetchJsonCached<T>(
  url: string,
  ttlMs = DEFAULT_TTL_MS,
  fetchImpl: typeof fetch = fetch
): Promise<T | null> {
  if (browser) {
    const cached = responseCache.get(url);
    if (cached && cached.expiresAt > Date.now()) {
      return cached.value as T;
    }
    const existing = inflightRequests.get(url);
    if (existing) {
      return existing as Promise<T | null>;
    }
  }

  const task = (async (): Promise<T | null> => {
    const res = await fetchImpl(url);
    if (!res.ok) return null;
    const data = (await res.json()) as T;
    if (browser) {
      setBoundedEntry(url, data, ttlMs);
    }
    return data;
  })();

  if (browser) {
    inflightRequests.set(url, task);
  }

  try {
    return await task;
  } finally {
    if (browser) {
      inflightRequests.delete(url);
    }
  }
}
