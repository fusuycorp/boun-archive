import type { RequestHandler } from "./$types";
import { API_BASE } from "$lib/config";

export const GET: RequestHandler = async ({ fetch }) => {
  const baseUrl = "https://bountools.com";
  const today = new Date().toISOString().split("T")[0];

  const staticUrls = [
    { loc: `${baseUrl}/`, priority: "1.0", changefreq: "daily" },
    { loc: `${baseUrl}/search`, priority: "0.9", changefreq: "daily" },
    { loc: `${baseUrl}/departments`, priority: "0.8", changefreq: "weekly" },
    { loc: `${baseUrl}/calendar`, priority: "0.8", changefreq: "weekly" },
    { loc: `${baseUrl}/schedule`, priority: "0.8", changefreq: "weekly" },
    { loc: `${baseUrl}/ghost-schedule`, priority: "0.7", changefreq: "weekly" },
    { loc: `${baseUrl}/instructors`, priority: "0.8", changefreq: "weekly" },
  ];

  const dynamicUrls: Array<{ loc: string; priority: string; changefreq: string }> = [];

  try {
    const instRes = await fetch(`${API_BASE}/v1/instructors?limit=500`);

    if (instRes.ok) {
      const insts = await instRes.json();
      if (Array.isArray(insts)) {
        for (const inst of insts.slice(0, 500)) {
          if (inst.id) {
            dynamicUrls.push({
              loc: `${baseUrl}/instructor/${inst.id}`,
              priority: "0.5",
              changefreq: "monthly"
            });
          }
        }
      }
    }
  } catch {
    // If backend is unreachable during build or static evaluation, gracefully fallback to static URLs
  }

  const allUrls = [...staticUrls, ...dynamicUrls];
  // Deduplicate by loc
  const seen = new Set<string>();
  const uniqueUrls = allUrls.filter(u => {
    if (seen.has(u.loc)) return false;
    seen.add(u.loc);
    return true;
  });

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${uniqueUrls.map(u => `  <url>
    <loc>${u.loc}</loc>
    <lastmod>${today}</lastmod>
    <changefreq>${u.changefreq}</changefreq>
    <priority>${u.priority}</priority>
  </url>`).join("\n")}
</urlset>`;

  return new Response(xml, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "public, max-age=3600, s-maxage=86400"
    }
  });
};
