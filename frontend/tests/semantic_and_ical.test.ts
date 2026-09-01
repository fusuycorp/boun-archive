import { describe, it, expect } from "bun:test";
import {
  generateWebSiteJsonLd,
  generateBreadcrumbJsonLd,
  generateCourseJsonLd,
  generateInstructorJsonLd,
  generateDepartmentsJsonLd
} from "../src/lib/semantic";
import { generateICS } from "../src/lib/ical";
import type { CourseHistoryItem, Department, InstructorHistoryItem } from "../src/lib/types";

describe("Semantic Web & Schema.org JSON-LD Generation", () => {
  it("generates valid WebSite and Organization JSON-LD graph", () => {
    const jsonLd: any = generateWebSiteJsonLd("https://archive.bogazici.app");
    expect(jsonLd["@context"]).toBe("https://schema.org");
    expect(Array.isArray(jsonLd["@graph"])).toBe(true);

    const org = (jsonLd["@graph"] as any[]).find((item: any) => item["@type"] === "CollegeOrUniversity");
    expect(org).toBeDefined();
    expect(org?.name).toBe("Boğaziçi University");
    expect(org?.sameAs).toBe("https://www.wikidata.org/wiki/Q853512");

    const site = (jsonLd["@graph"] as any[]).find((item: any) => item["@type"] === "WebSite");
    expect(site).toBeDefined();
    expect(site?.potentialAction?.["@type"]).toBe("SearchAction");
  });

  it("generates valid BreadcrumbList JSON-LD", () => {
    const crumbs = [
      { name: "Home", url: "/" },
      { name: "Departments", url: "/departments" },
      { name: "CMPE 150", url: "/course/CMPE%20150" }
    ];
    const jsonLd = generateBreadcrumbJsonLd(crumbs, "https://archive.bogazici.app");
    expect(jsonLd["@type"]).toBe("BreadcrumbList");
    expect(jsonLd.itemListElement.length).toBe(3);
    expect(jsonLd.itemListElement[0].position).toBe(1);
    expect(jsonLd.itemListElement[0].name).toBe("Home");
    expect(jsonLd.itemListElement[2].item).toBe("https://archive.bogazici.app/course/CMPE%20150");
  });

  it("generates valid Course and CourseInstance JSON-LD with schedules", () => {
    const mockHistory: CourseHistoryItem[] = [
      {
        id: 101,
        term_id: "2026/2027-1",
        section: "01",
        title: "Introduction to Computing",
        instructor: "Prof. John Doe",
        credits: 3,
        ects: 6,
        delivery_method: "In-Person",
        slots: [
          { day: "M", hour: 1, room: "BMB 217" },
          { day: "W", hour: 2, room: "BMB 217" }
        ]
      }
    ];

    const jsonLd: any = generateCourseJsonLd("CMPE 150", mockHistory, mockHistory[0], "https://archive.bogazici.app");
    expect(jsonLd["@context"]).toBe("https://schema.org");
    const course: any = (jsonLd["@graph"] as any[]).find((item: any) => item["@type"] === "Course");
    expect(course).toBeDefined();
    expect(course?.courseCode).toBe("CMPE 150");
    expect(course?.name).toBe("Introduction to Computing");
    expect(course?.numberOfCredits).toBe(3);
    expect(course?.educationalCredentialAwarded).toBe("ECTS 6");

    expect(course?.hasCourseInstance.length).toBe(1);
    const instance = course?.hasCourseInstance[0];
    expect(instance.courseMode).toBe("onsite");
    expect(instance.instructor?.name).toBe("Prof. John Doe");
    expect(instance.courseSchedule.length).toBe(2);
    expect(instance.courseSchedule[0].byDay).toBe("https://schema.org/Monday");
    expect(instance.courseSchedule[0].startTime).toBe("09:00");
    expect(instance.courseSchedule[0].location?.name).toBe("BMB 217");
  });

  it("generates valid Instructor Person JSON-LD with taught courses", () => {
    const mockHistory: InstructorHistoryItem[] = [
      { term: "2026/2027-1", course_code: "CMPE 150", title: "Intro to Computing" },
      { term: "2025/2026-2", course_code: "CMPE 250", title: "Data Structures" }
    ];

    const jsonLd: any = generateInstructorJsonLd(42, "Prof. Albert Long", mockHistory, "https://archive.bogazici.app");
    const person: any = (jsonLd["@graph"] as any[]).find((item: any) => item["@type"] === "Person");
    expect(person).toBeDefined();
    expect(person?.name).toBe("Prof. Albert Long");
    expect(person?.hasCourse.length).toBe(2);
    expect(person?.hasCourse[0].courseCode).toBe("CMPE 150");
  });

  it("generates valid Departments ItemList JSON-LD", () => {
    const depts: Department[] = [
      { kisaadi: "CMPE", bolum: "Computer Engineering" },
      { kisaadi: "MATH", bolum: "Mathematics" }
    ];

    const jsonLd: any = generateDepartmentsJsonLd(depts, "https://archive.bogazici.app");
    const list: any = (jsonLd["@graph"] as any[]).find((item: any) => item["@type"] === "ItemList");
    expect(list).toBeDefined();
    expect(list?.itemListElement.length).toBe(2);
    expect(list?.itemListElement[0].item?.name).toBe("Computer Engineering");
    expect(list?.itemListElement[0].item?.alternateName).toBe("CMPE");
  });
});

describe("RFC 5545 iCalendar (.ics) Generation", () => {
  it("generates standard RFC 5545 VCALENDAR and VEVENT entries with recurring rules", () => {
    const courses = [
      {
        course_code: "CMPE 150",
        section: "01",
        title: "Introduction to Computing",
        instructor: "Prof. John Doe",
        slots: [
          { day_code: "M", slot_hour: 1, room_name: "BMB 217" },
          { day_code: "W", slot_hour: 3, room_name: "NH 101" }
        ]
      }
    ];

    const ics = generateICS(courses, "Test Semester Schedule");
    expect(ics.startsWith("BEGIN:VCALENDAR\r\n")).toBe(true);
    expect(ics.includes("VERSION:2.0\r\n")).toBe(true);
    expect(ics.includes("PRODID:-//BOUN Archive//Course Planner 1.0//EN\r\n")).toBe(true);
    expect(ics.includes("X-WR-CALNAME:Test Semester Schedule\r\n")).toBe(true);
    expect(ics.includes("BEGIN:VEVENT\r\n")).toBe(true);
    expect(ics.includes("SUMMARY:CMPE 150.01 - Introduction to Computing\r\n")).toBe(true);
    expect(ics.includes("LOCATION:BMB 217\r\n")).toBe(true);
    expect(ics.includes("RRULE:FREQ=WEEKLY;BYDAY=MO;UNTIL=20270125T235959Z\r\n")).toBe(true);
    expect(ics.includes("RRULE:FREQ=WEEKLY;BYDAY=WE;UNTIL=20270125T235959Z\r\n")).toBe(true);
    expect(ics.endsWith("END:VCALENDAR\r\n")).toBe(true);
  });

  it("handles courses with missing or empty slots gracefully", () => {
    const courses = [
      {
        course_code: "MATH 101",
        section: "02",
        title: "Calculus I",
        slots: []
      }
    ];

    const ics = generateICS(courses);
    expect(ics.includes("BEGIN:VCALENDAR")).toBe(true);
    expect(ics.includes("BEGIN:VEVENT")).toBe(false);
    expect(ics.includes("END:VCALENDAR")).toBe(true);
  });
});
