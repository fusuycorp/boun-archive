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

// Exact official semester start ("Classes begin") and end ("Classes end" / "Last day of classes")
// sourced from https://academiccalendar.bogazici.edu.tr (akademiktakvim.bogazici.edu.tr)
const OFFICIAL_TERM_BOUNDS: Record<string, { start: [number, number, number]; untilUtc: string }> = {
  "2014-2015-1": { start: [2014, 9, 22], untilUtc: "20141224T235959Z" },
  "2014-2015-2": { start: [2015, 2, 9], untilUtc: "20150513T235959Z" },
  "2014-2015-3": { start: [2015, 6, 18], untilUtc: "20150805T235959Z" },
  "2015-2016-1": { start: [2015, 9, 28], untilUtc: "20151225T235959Z" },
  "2015-2016-2": { start: [2016, 2, 8], untilUtc: "20160513T235959Z" },
  "2015-2016-3": { start: [2016, 6, 16], untilUtc: "20160805T235959Z" },
  "2016-2017-1": { start: [2016, 9, 19], untilUtc: "20161216T235959Z" },
  "2016-2017-2": { start: [2017, 2, 6], untilUtc: "20170515T235959Z" },
  "2016-2017-3": { start: [2017, 6, 15], untilUtc: "20170801T235959Z" },
  "2017-2018-1": { start: [2017, 9, 18], untilUtc: "20171215T235959Z" },
  "2017-2018-2": { start: [2018, 2, 5], untilUtc: "20180511T235959Z" },
  "2017-2018-3": { start: [2018, 6, 25], untilUtc: "20180807T235959Z" },
  "2018-2019-1": { start: [2018, 9, 20], untilUtc: "20181219T235959Z" },
  "2018-2019-2": { start: [2019, 2, 7], untilUtc: "20190515T235959Z" },
  "2018-2019-3": { start: [2019, 6, 24], untilUtc: "20190806T235959Z" },
  "2019-2020-1": { start: [2019, 9, 19], untilUtc: "20191218T235959Z" },
  "2019-2020-2": { start: [2020, 2, 6], untilUtc: "20200612T235959Z" },
  "2019-2020-3": { start: [2020, 8, 4], untilUtc: "20200914T235959Z" },
  "2020-2021-1": { start: [2020, 10, 22], untilUtc: "20210120T235959Z" },
  "2020-2021-2": { start: [2021, 3, 18], untilUtc: "20210616T235959Z" },
  "2020-2021-3": { start: [2021, 7, 16], untilUtc: "20210903T235959Z" },
  "2021-2022-1": { start: [2021, 10, 6], untilUtc: "20220104T235959Z" },
  "2021-2022-2": { start: [2022, 2, 23], untilUtc: "20220524T235959Z" },
  "2021-2022-3": { start: [2022, 6, 24], untilUtc: "20220816T235959Z" },
  "2022-2023-1": { start: [2022, 9, 28], untilUtc: "20221227T235959Z" },
  "2022-2023-2": { start: [2023, 2, 20], untilUtc: "20230518T235959Z" },
  "2022-2023-3": { start: [2023, 6, 20], untilUtc: "20230811T235959Z" },
  "2023-2024-1": { start: [2023, 9, 27], untilUtc: "20231226T235959Z" },
  "2023-2024-2": { start: [2024, 2, 12], untilUtc: "20240517T235959Z" },
  "2023-2024-3": { start: [2024, 6, 25], untilUtc: "20240812T235959Z" },
  "2024-2025-1": { start: [2024, 9, 23], untilUtc: "20241220T235959Z" },
  "2024-2025-2": { start: [2025, 2, 10], untilUtc: "20250516T235959Z" },
  "2024-2025-3": { start: [2025, 6, 24], untilUtc: "20250811T235959Z" },
  "2025-2026-1": { start: [2025, 9, 22], untilUtc: "20251219T235959Z" },
  "2025-2026-2": { start: [2026, 2, 9], untilUtc: "20260515T235959Z" },
  "2025-2026-3": { start: [2026, 6, 24], untilUtc: "20260812T235959Z" },
  "2026-2027-1": { start: [2026, 9, 21], untilUtc: "20261211T235959Z" },
  "2026-2027-2": { start: [2027, 1, 18], untilUtc: "20270422T235959Z" },
  "2026-2027-3": { start: [2027, 6, 30], untilUtc: "20270810T235959Z" }
};

function resolveSemesterBounds(termId?: string | null): {
  start: [number, number, number];
  untilUtc: string;
} {
  if (termId) {
    const clean = termId.trim().replace(/\//g, "-");
    if (OFFICIAL_TERM_BOUNDS[clean]) {
      return OFFICIAL_TERM_BOUNDS[clean];
    }
    const parts = clean.split("-");
    const startYr = parseInt(parts[0], 10);
    const sem = parts.length >= 2 ? parseInt(parts[parts.length - 1], 10) : 1;
    if (!isNaN(startYr)) {
      const calYear = parts.length > 2 && sem >= 2 ? startYr + 1 : startYr;
      if (sem === 2) {
        const d = new Date(Date.UTC(calYear, 1, 9));
        const offset = (1 - d.getUTCDay() + 7) % 7;
        return { start: [calYear, 2, 9 + offset], untilUtc: `${calYear}0515T235959Z` };
      } else if (sem === 3) {
        const d = new Date(Date.UTC(calYear, 5, 22));
        const offset = (1 - d.getUTCDay() + 7) % 7;
        return { start: [calYear, 6, 22 + offset], untilUtc: `${calYear}0812T235959Z` };
      } else {
        const d = new Date(Date.UTC(startYr, 8, 18));
        const offset = (1 - d.getUTCDay() + 7) % 7;
        return { start: [startYr, 9, 18 + offset], untilUtc: `${startYr}1220T235959Z` };
      }
    }
  }
  return OFFICIAL_TERM_BOUNDS["2026-2027-1"];
}

function formatFirstOccurrenceDate(start: [number, number, number], dayOffset: number): string {
  const [yr, mo, dy] = start;
  const startUtc = new Date(Date.UTC(yr, mo - 1, dy));
  // Convert JS getUTCDay (Sun=0..Sat=6) to Monday-based (Mon=0..Sun=6)
  const startMondayBased = (startUtc.getUTCDay() + 6) % 7;
  const daysAhead = (dayOffset - startMondayBased + 7) % 7;
  const firstDate = new Date(Date.UTC(yr, mo - 1, dy + daysAhead));
  const y = firstDate.getUTCFullYear();
  const m = String(firstDate.getUTCMonth() + 1).padStart(2, "0");
  const d = String(firstDate.getUTCDate()).padStart(2, "0");
  return `${y}${m}${d}`;
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
  const { start: defaultStart, untilUtc: defaultUntilUtc } = resolveSemesterBounds(termHint);

  courses.forEach((course) => {
    const rawCourse = course as any;
    const courseTerm = rawCourse.term_id || rawCourse.term || termHint;
    const { start, untilUtc } = courseTerm ? resolveSemesterBounds(courseTerm) : { start: defaultStart, untilUtc: defaultUntilUtc };
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

      const dateStr = formatFirstOccurrenceDate(start, dayOffset);
      const startHour = 8 + Number(slotHour);
      const endHour = 9 + Number(slotHour);

      const dtStart = `${dateStr}T${startHour.toString().padStart(2, "0")}0000`;
      const dtEnd = `${dateStr}T${endHour.toString().padStart(2, "0")}0000`;
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
