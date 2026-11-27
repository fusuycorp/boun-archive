import type { HandleFetch } from "@sveltejs/kit";
import { env } from "$env/dynamic/private";

export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
  const reqUrl = new URL(request.url);
  if (
    reqUrl.origin === event.url.origin &&
    (reqUrl.pathname === "/api" || reqUrl.pathname.startsWith("/api/"))
  ) {
    const internalBase = (env.INTERNAL_API_URL || "http://backend:8000").replace(/\/+$/, "");
    const suffix = reqUrl.pathname.slice(4) || "/";
    const rewrittenUrl = `${internalBase}${suffix}${reqUrl.search}`;
    request = new Request(rewrittenUrl, request);
  }

  return fetch(request);
};
