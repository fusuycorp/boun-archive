import { describe, it, expect } from "vitest";
import {
  safeParsePlannerCourses,
  CoursePlannerItemSchema,
  CoursePlannerSlotSchema,
  type CoursePlannerItem,
} from "../src/lib/schemas/planner";

describe("Planner Schema & Boundary Validation", () => {
  it("parses valid course payload correctly", () => {
    const raw = JSON.stringify([
      {
        id: 101,
        course_code: "CMPE 150",
        title: "Introduction to Computing",
        section: "01",
        slots: [
          {
            day_code: "M",
            slot_hour: 3,
            room_name: "NH 101",
            slot_title: "Lecture",
          },
        ],
      },
    ]);

    const result = safeParsePlannerCourses(raw);
    expect(result).toHaveLength(1);
    expect(result[0].course_code).toBe("CMPE 150");
    expect(result[0].slots).toHaveLength(1);
    expect(result[0].slots[0].day_code).toBe("M");
    expect(result[0].slots[0].slot_hour).toBe(3);
  });

  it("handles malformed JSON strings gracefully without throwing", () => {
    expect(safeParsePlannerCourses("{not-valid-json")).toEqual([]);
    expect(safeParsePlannerCourses("")).toEqual([]);
    expect(safeParsePlannerCourses("null")).toEqual([]);
    expect(safeParsePlannerCourses('{"not": "an array"}')).toEqual([]);
  });

  it("prunes corrupted items while keeping valid courses", () => {
    const raw = JSON.stringify([
      {
        id: 1,
        course_code: "CMPE 150",
        title: "Valid Course",
      },
      {
        // Missing course_code (invalid)
        id: 2,
        title: "Invalid Course",
      },
      null,
      "string-item",
      {
        id: 3,
        course_code: "MATH 101",
        title: "Calculus I",
      },
    ]);

    const result = safeParsePlannerCourses(raw);
    expect(result).toHaveLength(2);
    expect(result.map((c) => c.course_code)).toEqual(["CMPE 150", "MATH 101"]);
  });

  it("populates default values for optional fields", () => {
    const course = CoursePlannerItemSchema.parse({
      course_code: "PHYS 101",
    });

    expect(course.course_code).toBe("PHYS 101");
    expect(course.title).toBe("");
    expect(course.section).toBe("");
    expect(course.slots).toEqual([]);
  });
});
