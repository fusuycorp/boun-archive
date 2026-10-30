import type { CoursePlannerItem } from "./schemas/planner";
import type { CourseHistoryItem, Course } from "./types";

const DAY_ICAL_MAP: Record<string, string> = {
  M: "MO",
  T: "TU",
  W: "WE",
  Th: "TH",
  F: "FR",
  St: "SA",
  Su: "SU"
};

const DAY_OFFSET_MAP: Record<string, number> = {
  M: 0,
  T: 1,
  W: 2,
  Th: 3,
  F: 4,
  St: 5,
  Su: 6
};

export interface GenericScheduleSlot {
  day_code?: string | null;
  day?: string | null;
  slot_hour?: number | null;
  hour?: number | null;
  room_name?: string | null;
  room?: string | null;
  slot_title?: string | null;
}

export interface GenericCourseSchedule {
  course_code?: string | null;
  section?: string | null;
  title?: string | null;
  instructor?: string | null;
  instructor_name?: string | null;
  slots?: GenericScheduleSlot[] | null;
}

const VTIMEZONE_ISTANBUL = [
  "BEGIN:VTIMEZONE",
  "TZID:Europe/Istanbul",
  "BEGIN:STANDARD",
  "TZOFFSETFROM:+0300",
  "TZOFFSETTO:+0300",
  "TZNAME:+03",
  "DTSTART:19700101T000000",
  "END:STANDARD",
  "END:VTIMEZONE"
].join("\r\n");

function escapeIcalText(val: unknown): string {
  if (val === null || val === undefined) return "";
  return String(val)
    .replace(/\\/g, "\\\\")
    .replace(/;/g, "\\;")
    .replace(/,/g, "\\,")
    .replace(/\r?\n/g, "\\n");
}

function resolveSemesterBounds(termId?: string | null): {
  baseYear: number;
  baseMonth: number;
  baseMonday: number;
  untilUtc: string;
} {
  if (termId) {
    const clean = termId.trim().replace(/\//g, "-");
    const parts = clean.split("-");
    const startYr = parseInt(parts[0], 10);
    const sem = parts.length >= 2 ? parseInt(parts[parts.length - 1], 10) : 1;
    if (!isNaN(startYr)) {
      const calYear = parts.length > 2 && sem >= 2 ? startYr + 1 : startYr;
      if (sem === 2) {
        const d = new Date(Date.UTC(calYear, 1, 15));
        const offset = (1 - d.getUTCDay() + 7) % 7;
        return { baseYear: calYear, baseMonth: 2, baseMonday: 15 + offset, untilUtc: `${calYear}0615T235959Z` };
      } else if (sem === 3) {
        const d = new Date(Date.UTC(calYear, 5, 22));
        const offset = (1 - d.getUTCDay() + 7) % 7;
        return { baseYear: calYear, baseMonth: 6, baseMonday: 22 + offset, untilUtc: `${calYear}0825T235959Z` };
      } else {
        const d = new Date(Date.UTC(startYr, 8, 18));
        const offset = (1 - d.getUTCDay() + 7) % 7;
        return { baseYear: startYr, baseMonth: 9, baseMonday: 18 + offset, untilUtc: `${startYr + 1}0125T235959Z` };
      }
    }
  }
  return { baseYear: 2026, baseMonth: 9, baseMonday: 21, untilUtc: "20270125T235959Z" };
}

/**
 * Generates an RFC 5545 compliant iCalendar string (.ics) from a list of courses and slots.
 */
export function generateICS(
  courses: Array<GenericCourseSchedule | CoursePlannerItem | CourseHistoryItem | Course>,
  calendarTitle = "BOUN Weekly Schedule",
  fallbackCode = "Course"
): string {
  const events: string[] = [];
  const nowStr = new Date().toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";

  const firstCourse = courses[0] as any;
  const termHint = firstCourse?.term_id || firstCourse?.term || null;
  const { baseYear, baseMonth, baseMonday, untilUtc } = resolveSemesterBounds(termHint);

  courses.forEach((course) => {
    const rawCourse = course as any;
    const slots: any[] = rawCourse.slots || [];
    const code = rawCourse.course_code || fallbackCode;
    const instructor = rawCourse.instructor || rawCourse.instructor_name || "N/A";
    const title = rawCourse.title || code;
    const sec = rawCourse.section ? `.${rawCourse.section}` : "";

    slots.forEach((slot: any, slotIdx: number) => {
      if (slot.disabled) return;
      const dayCode = slot.day_code || slot.day;
      const slotHour = slot.slot_hour ?? slot.hour;
      if (!dayCode || !slotHour) return;

      const byDay = DAY_ICAL_MAP[dayCode];
      const dayOffset = DAY_OFFSET_MAP[dayCode] ?? 0;
      if (!byDay) return;

      const eventDay = baseMonday + dayOffset;
      const startHour = 8 + Number(slotHour);
      const endHour = 9 + Number(slotHour);

      const dtStart = `${baseYear}${baseMonth.toString().padStart(2, "0")}${eventDay.toString().padStart(2, "0")}T${startHour.toString().padStart(2, "0")}0000`;
      const dtEnd = `${baseYear}${baseMonth.toString().padStart(2, "0")}${eventDay.toString().padStart(2, "0")}T${endHour.toString().padStart(2, "0")}0000`;
      const uid = `${code}${sec}-${dayCode}-${slotHour}-${slotIdx}@archive.bogazici.app`;

      const location = slot.room_name || slot.room || "TBA";
      const summaryEscaped = escapeIcalText(`${code}${sec} - ${title}`);
      const locationEscaped = escapeIcalText(location);
      const description = `Course: ${escapeIcalText(code + sec)}\\nTitle: ${escapeIcalText(title)}\\nInstructor: ${escapeIcalText(instructor)}\\nRoom: ${locationEscaped}`;

      events.push([
        "BEGIN:VEVENT",
        `UID:${uid}`,
        `DTSTAMP:${nowStr}`,
        `DTSTART;TZID=Europe/Istanbul:${dtStart}`,
        `DTEND;TZID=Europe/Istanbul:${dtEnd}`,
        `RRULE:FREQ=WEEKLY;BYDAY=${byDay};UNTIL=${untilUtc}`,
        `SUMMARY:${summaryEscaped}`,
        `LOCATION:${locationEscaped}`,
        `DESCRIPTION:${description}`,
        "STATUS:CONFIRMED",
        "END:VEVENT"
      ].join("\r\n"));
    });
  });

  return [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//BOUN Archive//Course Planner 1.0//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    `X-WR-CALNAME:${escapeIcalText(calendarTitle)}`,
    "X-WR-TIMEZONE:Europe/Istanbul",
    VTIMEZONE_ISTANBUL,
    ...events,
    "END:VCALENDAR"
  ].join("\r\n") + "\r\n";
}

/**
 * Triggers a browser download of an .ics calendar file.
 */
export function downloadICS(icsContent: string, filename: string) {
  if (!icsContent) return;
  const blob = new Blob([icsContent], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", `${filename.endsWith(".ics") ? filename : `${filename}.ics`}`);
  link.style.visibility = "hidden";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
