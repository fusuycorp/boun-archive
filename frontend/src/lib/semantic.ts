import type { CourseHistoryItem, Department, InstructorHistoryItem } from "./types";

export const DEFAULT_BASE_URL = "https://bountools.com";

function buildBounOrg(baseUrl = DEFAULT_BASE_URL) {
  const cleanBase = baseUrl.replace(/\/$/, "");
  return {
    "@type": "CollegeOrUniversity",
    "@id": `${cleanBase}/#organization`,
    "name": "Boğaziçi University",
    "alternateName": "Bogazici Universitesi",
    "url": "https://bogazici.edu.tr",
    "sameAs": "https://www.wikidata.org/wiki/Q853512"
  };
}

export const BOUN_ORG = buildBounOrg();

export const DAY_SCHEMA_MAP: Record<string, string> = {
  M: "https://schema.org/Monday",
  T: "https://schema.org/Tuesday",
  W: "https://schema.org/Wednesday",
  Th: "https://schema.org/Thursday",
  F: "https://schema.org/Friday",
  St: "https://schema.org/Saturday",
  Su: "https://schema.org/Sunday"
};

export function generateWebSiteJsonLd(baseUrl = DEFAULT_BASE_URL) {
  const cleanBase = baseUrl.replace(/\/$/, "");
  const org = buildBounOrg(cleanBase);
  return {
    "@context": "https://schema.org",
    "@graph": [
      org,
      {
        "@type": "WebSite",
        "@id": `${cleanBase}/#website`,
        "url": cleanBase,
        "name": "BOUN Archive",
        "description": "Historical academic catalog, course planner, and quota intelligence archive for Boğaziçi University.",
        "publisher": { "@id": org["@id"] },
        "potentialAction": {
          "@type": "SearchAction",
          "target": {
            "@type": "EntryPoint",
            "urlTemplate": `${cleanBase}/search?q={search_term_string}`
          },
          "query-input": "required name=search_term_string"
        }
      }
    ]
  };
}

export function generateBreadcrumbJsonLd(
  crumbs: Array<{ name: string; url?: string }>,
  baseUrl = DEFAULT_BASE_URL
) {
  const cleanBase = baseUrl.replace(/\/$/, "");
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": crumbs.map((crumb, index) => ({
      "@type": "ListItem",
      "position": index + 1,
      "name": crumb.name,
      ...(crumb.url ? { "item": crumb.url.startsWith("http") ? crumb.url : `${cleanBase}${crumb.url}` } : {})
    }))
  };
}

export function generateCourseJsonLd(
  courseCode = "",
  history: CourseHistoryItem[] = [],
  latestInfo?: CourseHistoryItem | null,
  baseUrl = DEFAULT_BASE_URL
) {
  const cleanBase = baseUrl.replace(/\/$/, "");
  const org = buildBounOrg(cleanBase);
  const code = courseCode || "Course";
  const primaryTitle = latestInfo?.title || history[0]?.title || code;
  const deptCode = code.split(" ")[0] || "";
  const credits = latestInfo?.credits ?? history[0]?.credits;
  const ects = latestInfo?.ects ?? history[0]?.ects;

  const instances = history.map((item) => {
    const termYear = item.term_id ? item.term_id.split("/")[0] : "2026";
    const sec = item.section ? `.${item.section}` : "";
    return {
      "@type": "CourseInstance",
      "@id": `${cleanBase}/course/${encodeURIComponent(code)}?term=${encodeURIComponent(item.term_id)}${item.section ? `&sec=${item.section}` : ""}#instance`,
      "name": `${code}${sec} - ${item.title || primaryTitle}`,
      "courseMode": item.delivery_method?.toLowerCase().includes("online") ? "online" : "onsite",
      "startDate": `${termYear}-09-01`,
      ...(item.instructor && item.instructor !== "TBA" ? {
        "instructor": {
          "@type": "Person",
          "name": item.instructor
        }
      } : {}),
      ...(item.slots && item.slots.length > 0 ? {
        "courseSchedule": item.slots.map((s) => ({
          "@type": "Schedule",
          ...(s.day && DAY_SCHEMA_MAP[s.day] ? { "byDay": DAY_SCHEMA_MAP[s.day] } : {}),
          ...(s.hour ? {
            "startTime": `${(8 + s.hour).toString().padStart(2, "0")}:00`,
            "endTime": `${(9 + s.hour).toString().padStart(2, "0")}:00`
          } : {}),
          ...(s.room && s.room !== "N/A" ? {
            "location": {
              "@type": "Room",
              "name": s.room
            }
          } : {})
        }))
      } : {})
    };
  });

  return {
    "@context": "https://schema.org",
    "@graph": [
      org,
      {
        "@type": "Course",
        "@id": `${cleanBase}/course/${encodeURIComponent(code)}#course`,
        "courseCode": code,
        "name": primaryTitle,
        "provider": { "@id": org["@id"] },
        ...(credits ? { "numberOfCredits": credits } : {}),
        ...(ects ? { "educationalCredentialAwarded": `ECTS ${ects}` } : {}),
        ...(deptCode ? {
          "department": {
            "@type": "EducationalOrganization",
            "name": deptCode,
            "url": `${cleanBase}/departments`
          }
        } : {}),
        "hasCourseInstance": instances
      },
      generateBreadcrumbJsonLd([
        { name: "Home", url: "/" },
        { name: "Departments", url: "/departments" },
        ...(deptCode ? [{ name: deptCode, url: `/departments` }] : []),
        { name: code, url: `/course/${encodeURIComponent(code)}` }
      ], cleanBase)
    ]
  };
}

export function generateInstructorJsonLd(
  instructorId: string | number = "",
  instructorName = "",
  history: InstructorHistoryItem[] = [],
  baseUrl = DEFAULT_BASE_URL
) {
  const cleanBase = baseUrl.replace(/\/$/, "");
  const org = buildBounOrg(cleanBase);
  const idStr = String(instructorId);
  const taughtCourses = Array.from(new Set(history.map(h => h.course_code))).map(code => ({
    "@type": "Course",
    "courseCode": code,
    "url": `${cleanBase}/course/${encodeURIComponent(code)}`
  }));

  return {
    "@context": "https://schema.org",
    "@graph": [
      org,
      {
        "@type": "Person",
        "@id": `${cleanBase}/instructor/${idStr}#person`,
        "name": instructorName,
        "jobTitle": "Faculty Instructor",
        "worksFor": { "@id": org["@id"] },
        ...(taughtCourses.length > 0 ? { "hasCourse": taughtCourses } : {})
      },
      generateBreadcrumbJsonLd([
        { name: "Home", url: "/" },
        { name: "Instructors", url: "/instructors" },
        { name: instructorName, url: `/instructor/${idStr}` }
      ], cleanBase)
    ]
  };
}

export function generateDepartmentsJsonLd(
  departments: Department[],
  baseUrl = DEFAULT_BASE_URL
) {
  const cleanBase = baseUrl.replace(/\/$/, "");
  const org = buildBounOrg(cleanBase);
  return {
    "@context": "https://schema.org",
    "@graph": [
      org,
      {
        "@type": "ItemList",
        "@id": `${cleanBase}/departments#list`,
        "name": "Academic Departments at Boğaziçi University",
        "itemListElement": departments.map((dept, idx) => ({
          "@type": "ListItem",
          "position": idx + 1,
          "item": {
            "@type": "EducationalOrganization",
            "name": dept.bolum,
            "alternateName": dept.kisaadi,
            "parentOrganization": { "@id": org["@id"] },
            "url": `${cleanBase}/departments`
          }
        }))
      }
    ]
  };
}

/**
 * Serializes data into a secure JSON string suitable for embedding inside <script> tags.
 * Escapes '<', '>', and '&' to Unicode escapes to prevent HTML breakout and XSS vulnerabilities.
 */
export function serializeJsonLd(data: unknown): string {
  return JSON.stringify(data)
    .replace(/</g, "\\u003c")
    .replace(/>/g, "\\u003e")
    .replace(/&/g, "\\u0026");
}
