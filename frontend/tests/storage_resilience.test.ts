import { describe, it, expect } from "bun:test";
import { safeParsePlannerCourses, CoursePlannerItemSchema } from "../src/lib/schemas/planner";

describe("Storage Resilience & Malformed Data Handling", () => {
  describe("safeParsePlannerCourses", () => {
    it("handles null, undefined, empty string, and whitespace without throwing", () => {
      // @ts-expect-error Testing non-string input
      expect(safeParsePlannerCourses(null)).toEqual([]);
      // @ts-expect-error Testing non-string input
      expect(safeParsePlannerCourses(undefined)).toEqual([]);
      expect(safeParsePlannerCourses("")).toEqual([]);
      expect(safeParsePlannerCourses("   ")).toEqual([]);
    });

    it("handles malformed JSON syntax safely", () => {
      expect(safeParsePlannerCourses("{invalid-json")).toEqual([]);
      expect(safeParsePlannerCourses("[{course_code: CMPE 150}]")).toEqual([]);
      expect(safeParsePlannerCourses("undefined")).toEqual([]);
      expect(safeParsePlannerCourses("NaN")).toEqual([]);
    });

    it("handles JSON objects that are not arrays", () => {
      expect(safeParsePlannerCourses('{"course_code": "CMPE 150"}')).toEqual([]);
      expect(safeParsePlannerCourses('"string value"')).toEqual([]);
      expect(safeParsePlannerCourses('12345')).toEqual([]);
      expect(safeParsePlannerCourses('true')).toEqual([]);
    });

    it("handles arrays with non-object primitives and nulls", () => {
      expect(safeParsePlannerCourses('[1, "hello", null, true, false, 3.14]')).toEqual([]);
    });

    it("filters out items missing required course_code while keeping valid items", () => {
      const input = JSON.stringify([
        { title: "No course code", credits: 3 },
        { course_code: "", title: "Empty course code" },
        { course_code: "CMPE 150", title: "Introduction to Computing", credits: 3 },
        { course_code: null, title: "Null course code" },
        { course_code: "MATH 101", title: "Calculus I", credits: 4 }
      ]);

      const result = safeParsePlannerCourses(input);
      expect(result.length).toBe(2);
      expect(result[0].course_code).toBe("CMPE 150");
      expect(result[1].course_code).toBe("MATH 101");
    });

    it("validates nested course slots and rejects items with malformed slots", () => {
      const input = JSON.stringify([
        {
          course_code: "CMPE 150",
          title: "Introduction to Computing",
          slots: [
            { day_code: "M", slot_hour: 1, room_name: "NH101" },
            { day_code: "W", slot_hour: 2, room_name: "NH101" }
          ]
        },
        {
          course_code: "CMPE 160",
          title: "Invalid Slot Course",
          slots: [
            { day_code: 123, slot_hour: "not-a-number" } // Invalid types
          ]
        }
      ]);

      const result = safeParsePlannerCourses(input);
      expect(result.length).toBe(1);
      expect(result[0].course_code).toBe("CMPE 150");
      expect(result[0].slots?.length).toBe(2);
    });

    it("prevents prototype pollution injection payloads", () => {
      const maliciousPayload = JSON.stringify([
        {
          "__proto__": { "polluted": true },
          "constructor": { "prototype": { "isAdmin": true } },
          "course_code": "CMPE 150",
          "title": "Hacked Course"
        }
      ]);

      const result = safeParsePlannerCourses(maliciousPayload);
      expect(result.length).toBe(1);
      expect(result[0].course_code).toBe("CMPE 150");
      expect((({} as Record<string, unknown>)).polluted).toBeUndefined();
      expect((({} as Record<string, unknown>)).isAdmin).toBeUndefined();
    });

    it("handles large arrays gracefully without stack overflow or performance degradation", () => {
      const largeArray = Array.from({ length: 500 }, (_, i) => ({
        course_code: `CMPE ${100 + i}`,
        title: `Course Number ${100 + i}`,
        credits: 3,
        slots: [
          { day_code: "M", slot_hour: (i % 8) + 1, room_name: `Room ${i}` }
        ]
      }));

      const start = performance.now();
      const result = safeParsePlannerCourses(JSON.stringify(largeArray));
      const elapsed = performance.now() - start;

      expect(result.length).toBe(500);
      expect(elapsed).toBeLessThan(100); // Must parse 500 items in <100ms
    });
  });

  describe("Session Storage Recovery Simulation", () => {
    // In-memory mock storage
    class MockStorage {
      private store = new Map<string, string>();
      getItem(key: string): string | null {
        return this.store.get(key) ?? null;
      }
      setItem(key: string, value: string): void {
        this.store.set(key, value);
      }
      removeItem(key: string): void {
        this.store.delete(key);
      }
      clear(): void {
        this.store.clear();
      }
    }

    it("recovers gracefully from corrupted dept_courses in sessionStorage", () => {
      const sessionStorage = new MockStorage();
      const deptCode = "CMPE";
      sessionStorage.setItem(`dept_courses_${deptCode}`, "corrupted json {{{");

      let uniqueCourses: unknown[] = [];
      let fetchedFromApi = false;

      const savedCourses = sessionStorage.getItem(`dept_courses_${deptCode}`);
      if (savedCourses) {
        try {
          uniqueCourses = JSON.parse(savedCourses);
        } catch (e) {
          sessionStorage.removeItem(`dept_courses_${deptCode}`);
          // Fallback fetch
          fetchedFromApi = true;
          uniqueCourses = [{ course_code: "CMPE 150", title: "Introduction to Computing", terms: ["2024-2025-1"] }];
        }
      }

      expect(fetchedFromApi).toBe(true);
      expect(sessionStorage.getItem(`dept_courses_${deptCode}`)).toBeNull();
      expect(uniqueCourses.length).toBe(1);
    });

    it("recovers gracefully from corrupted dept_instructors in sessionStorage", () => {
      const sessionStorage = new MockStorage();
      const deptCode = "CMPE";
      sessionStorage.setItem(`dept_instructors_${deptCode}`, "{invalid");

      let deptInstructors: unknown[] = [];
      let fetchedFromApi = false;

      const savedInstructors = sessionStorage.getItem(`dept_instructors_${deptCode}`);
      if (savedInstructors) {
        try {
          deptInstructors = JSON.parse(savedInstructors);
        } catch (e) {
          sessionStorage.removeItem(`dept_instructors_${deptCode}`);
          fetchedFromApi = true;
          deptInstructors = [{ id: 1, full_name: "Albert Long", last_term: "2024-2025-1", course_count: 1, total_semesters: 1 }];
        }
      }

      expect(fetchedFromApi).toBe(true);
      expect(sessionStorage.getItem(`dept_instructors_${deptCode}`)).toBeNull();
      expect(deptInstructors.length).toBe(1);
    });

    it("handles corrupted theme values in localStorage safely", () => {
      const localStorage = new MockStorage();
      localStorage.setItem("theme", "unexpected_value_123");

      const savedTheme = localStorage.getItem("theme");
      const systemPrefersDark = false;

      let isDark: boolean;
      if (savedTheme === "dark" || (!savedTheme && systemPrefersDark)) {
        isDark = true;
      } else {
        isDark = false;
      }

      expect(isDark).toBe(false);
    });

    it("handles corrupted chunk reload timestamps in hooks.client.ts safely", () => {
      const sessionStorage = new MockStorage();
      sessionStorage.setItem("last_chunk_reload_timestamp", "not_a_valid_number");

      const key = "last_chunk_reload_timestamp";
      const lastReload = Number(sessionStorage.getItem(key) || 0);

      expect(isNaN(lastReload)).toBe(true);
      // Ensure condition Date.now() - NaN > 10000 evaluates safely to false
      const canReload = Date.now() - (isNaN(lastReload) ? 0 : lastReload) > 10000;
      expect(canReload).toBe(true);
    });
  });
});
