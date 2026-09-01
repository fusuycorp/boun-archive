import type { CourseHistoryItem, Department, InstructorHistoryItem } from "./types";

export const BOUN_ORG = {
  "@type": "CollegeOrUniversity",
  "@id": "https://archive.bogazici.app/#organization",
  "name": "Boğaziçi University",
  "alternateName": "Bogazici Universitesi",
  "url": "https://bogazici.edu.tr",
  "sameAs": "https://www.wikidata.org/wiki/Q853512"
};

export const DAY_SCHEMA_MAP: Record<string, string> = {
  M: "https://schema.org/Monday",
  T: "https://schema.org/Tuesday",
  W: "https://schema.org/Wednesday",
  Th: "https://schema.org/Thursday",
  F: "https://schema.org/Friday",
  St: "https://schema.org/Saturday",
  Su: "https://schema.org/Sunday"
};

export function generateWebSiteJsonLd(baseUrl = "https://archive.bogazici.app") {
  return {
    "@context": "https://schema.org",
    "@graph": [
      BOUN_ORG,
      {
        "@type": "WebSite",
        "@id": `${baseUrl}/#website`,
        "url": baseUrl,
        "name": "BOUN Archive",
        "description": "Historical academic catalog, course planner, and quota intelligence archive for Boğaziçi University.",
        "publisher": { "@id": "https://archive.bogazici.app/#organization" },
        "potentialAction": {
          "@type": "SearchAction",
          "target": {
            "@type": "EntryPoint",
            "urlTemplate": `${baseUrl}/search?q={search_term_string}`
          },
          "query-input": "required name=search_term_string"
        }
      }
    ]
  };
}

export function generateBreadcrumbJsonLd(
  crumbs: Array<{ name: string; url?: string }>,
  baseUrl = "https://archive.bogazici.app"
) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": crumbs.map((crumb, index) => ({
      "@type": "ListItem",
      "position": index + 1,
      "name": crumb.name,
      ...(crumb.url ? { "item": crumb.url.startsWith("http") ? crumb.url : `${baseUrl}${crumb.url}` } : {})
    }))
  };
}

export function generateCourseJsonLd(
  courseCode = "",
  history: CourseHistoryItem[] = [],
  latestInfo?: CourseHistoryItem | null,
  baseUrl = "https://archive.bogazici.app"
) {
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
      "@id": `${baseUrl}/course/${encodeURIComponent(code)}?term=${encodeURIComponent(item.term_id)}${item.section ? `&sec=${item.section}` : ""}#instance`,
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
      BOUN_ORG,
      {
        "@type": "Course",
        "@id": `${baseUrl}/course/${encodeURIComponent(code)}#course`,
        "courseCode": code,
        "name": primaryTitle,
        "provider": { "@id": "https://archive.bogazici.app/#organization" },
        ...(credits ? { "numberOfCredits": credits } : {}),
        ...(ects ? { "educationalCredentialAwarded": `ECTS ${ects}` } : {}),
        ...(deptCode ? {
          "department": {
            "@type": "EducationalOrganization",
            "name": deptCode,
            "url": `${baseUrl}/departments`
          }
        } : {}),
        "hasCourseInstance": instances
      },
      generateBreadcrumbJsonLd([
        { name: "Home", url: "/" },
        { name: "Departments", url: "/departments" },
        ...(deptCode ? [{ name: deptCode, url: `/departments` }] : []),
        { name: code, url: `/course/${encodeURIComponent(code)}` }
      ], baseUrl)
    ]
  };
}

export function generateInstructorJsonLd(
  instructorId: string | number = "",
  instructorName = "",
  history: InstructorHistoryItem[] = [],
  baseUrl = "https://archive.bogazici.app"
) {
  const idStr = String(instructorId);
  const taughtCourses = Array.from(new Set(history.map(h => h.course_code))).map(code => ({
    "@type": "Course",
    "courseCode": code,
    "url": `${baseUrl}/course/${encodeURIComponent(code)}`
  }));

  return {
    "@context": "https://schema.org",
    "@graph": [
      BOUN_ORG,
      {
        "@type": "Person",
        "@id": `${baseUrl}/instructor/${idStr}#person`,
        "name": instructorName,
        "jobTitle": "Faculty Instructor",
        "worksFor": { "@id": "https://archive.bogazici.app/#organization" },
        ...(taughtCourses.length > 0 ? { "hasCourse": taughtCourses } : {})
      },
      generateBreadcrumbJsonLd([
        { name: "Home", url: "/" },
        { name: "Instructors", url: "/instructors" },
        { name: instructorName, url: `/instructor/${idStr}` }
      ], baseUrl)
    ]
  };
}

export function generateDepartmentsJsonLd(
  departments: Department[],
  baseUrl = "https://archive.bogazici.app"
) {
  return {
    "@context": "https://schema.org",
    "@graph": [
      BOUN_ORG,
      {
        "@type": "ItemList",
        "@id": `${baseUrl}/departments#list`,
        "name": "Academic Departments at Boğaziçi University",
        "itemListElement": departments.map((dept, idx) => ({
          "@type": "ListItem",
          "position": idx + 1,
          "item": {
            "@type": "EducationalOrganization",
            "name": dept.bolum,
            "alternateName": dept.kisaadi,
            "parentOrganization": { "@id": "https://archive.bogazici.app/#organization" },
            "url": `${baseUrl}/departments`
          }
        }))
      }
    ]
  };
}
