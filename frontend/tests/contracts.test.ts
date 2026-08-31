import { describe, it, expect } from "bun:test";
import { readFileSync } from "fs";
import type {
  Term,
  Department,
  DepartmentUniqueCourse,
  DepartmentInstructor,
  Instructor,
  InstructorLegacy,
  Course,
  CourseHistoryItem,
  QuotaSnapshot,
  CourseChange,
  SearchResponse,
  SearchCourseHit,
  GhostScheduleItem,
  DepartmentEvolution,
  SchedulingHeatmapSlot,
  SystemStatus,
  FacetDistribution
} from "../src/lib/types";

const rawPayloads = JSON.parse(readFileSync("/tmp/raw_api_payloads.json", "utf-8"));

describe("TypeScript API Contract Compatibility Suite", () => {
  it("validates /v1/terms payload matches Term[]", () => {
    const terms: Term[] = rawPayloads.terms;
    expect(Array.isArray(terms)).toBe(true);
    expect(terms.length).toBeGreaterThanOrEqual(1);
    for (const t of terms) {
      expect(typeof t.id).toBe("string");
      expect(typeof t.academic_year).toBe("string");
      expect(typeof t.semester_num).toBe("number");
    }
  });

  it("validates /v1/departments payload matches Department[]", () => {
    const depts: Department[] = rawPayloads.departments;
    expect(Array.isArray(depts)).toBe(true);
    expect(depts.length).toBeGreaterThanOrEqual(1);
    for (const d of depts) {
      expect(typeof d.kisaadi).toBe("string");
      expect(typeof d.bolum).toBe("string");
    }
  });

  it("validates /v1/departments/{dept}/unique-courses payload matches DepartmentUniqueCourse[]", () => {
    const courses: DepartmentUniqueCourse[] = rawPayloads.department_unique_courses;
    expect(Array.isArray(courses)).toBe(true);
    expect(courses.length).toBeGreaterThanOrEqual(1);
    for (const c of courses) {
      expect(typeof c.course_code).toBe("string");
      expect(typeof c.title).toBe("string");
      expect(Array.isArray(c.terms)).toBe(true);
      for (const term of c.terms) {
        expect(typeof term).toBe("string");
      }
    }
  });

  it("validates /v1/departments/{dept}/instructors payload matches DepartmentInstructor[]", () => {
    const instructors: DepartmentInstructor[] = rawPayloads.department_instructors;
    expect(Array.isArray(instructors)).toBe(true);
    expect(instructors.length).toBeGreaterThanOrEqual(1);
    for (const inst of instructors) {
      expect(typeof inst.id).toBe("number");
      expect(typeof inst.full_name).toBe("string");
      expect(typeof inst.last_term).toBe("string");
      expect(typeof inst.course_count).toBe("number");
      expect(typeof inst.total_semesters).toBe("number");
    }
  });

  it("validates /v1/instructors payload matches Instructor[]", () => {
    const instructors: Instructor[] = rawPayloads.instructors;
    expect(Array.isArray(instructors)).toBe(true);
    expect(instructors.length).toBeGreaterThanOrEqual(1);
    for (const inst of instructors) {
      expect(typeof inst.id).toBe("number");
      expect(typeof inst.full_name).toBe("string");
    }
  });

  it("validates /v1/instructors/{id} payload matches Instructor", () => {
    const inst: Instructor = rawPayloads.instructor_detail;
    expect(typeof inst.id).toBe("number");
    expect(typeof inst.full_name).toBe("string");
  });

  it("validates /v1/analytics/instructor/{id}/legacy payload matches InstructorLegacy", () => {
    const legacy: InstructorLegacy = rawPayloads.instructor_legacy;
    expect(typeof legacy.instructor_name).toBe("string");
    expect(typeof legacy.total_semesters_taught).toBe("number");
    expect(typeof legacy.total_courses_taught).toBe("number");
    expect(typeof legacy.most_frequent_courses).toBe("object");
    expect(Array.isArray(legacy.preferred_slots)).toBe(true);
    for (const s of legacy.preferred_slots) {
      expect(typeof s.day).toBe("string");
      expect(typeof s.hour).toBe("number");
      expect(typeof s.frequency).toBe("number");
    }
    expect(Array.isArray(legacy.history)).toBe(true);
    for (const h of legacy.history) {
      expect(typeof h.term).toBe("string");
      expect(typeof h.course_code).toBe("string");
      expect(typeof h.title).toBe("string");
    }
  });

  it("validates /v1/courses/{id} payload matches Course", () => {
    const course: Course = rawPayloads.course_detail;
    expect(typeof course.id).toBe("number");
    expect(typeof course.term_id).toBe("string");
    expect(typeof course.dept_kisaadi).toBe("string");
    expect(typeof course.course_code).toBe("string");
    expect(course.slots).toBeDefined();
    if (course.slots) {
      expect(Array.isArray(course.slots)).toBe(true);
      for (const slot of course.slots) {
        expect(typeof slot.id).toBe("number");
        expect(typeof slot.day_code).toBe("string");
        expect(typeof slot.slot_hour).toBe("number");
      }
    }
  });

  it("validates /v1/courses/history/{code} payload matches CourseHistoryItem[]", () => {
    const history: CourseHistoryItem[] = rawPayloads.course_history;
    expect(Array.isArray(history)).toBe(true);
    expect(history.length).toBeGreaterThanOrEqual(1);
    for (const item of history) {
      expect(typeof item.id).toBe("number");
      expect(typeof item.term_id).toBe("string");
      expect(Array.isArray(item.slots)).toBe(true);
      for (const slot of item.slots) {
        expect(typeof slot.day).toBe("string");
        expect(typeof slot.hour).toBe("number");
        expect(typeof slot.room).toBe("string");
      }
    }
  });

  it("validates /v1/courses/{code}/quota payload matches QuotaSnapshot[]", () => {
    const quotas: QuotaSnapshot[] = rawPayloads.course_quota;
    expect(Array.isArray(quotas)).toBe(true);
    expect(quotas.length).toBeGreaterThanOrEqual(1);
    for (const q of quotas) {
      expect(typeof q.id).toBe("number");
      expect(typeof q.term_id).toBe("string");
      expect(typeof q.course_code).toBe("string");
      expect(typeof q.is_consent).toBe("boolean");
      expect(typeof q.is_unlimited).toBe("boolean");
      expect(typeof q.captured_at).toBe("string");
    }
  });

  it("validates /v1/courses/{code}/changes payload matches CourseChange[]", () => {
    const changes: CourseChange[] = rawPayloads.course_changes;
    expect(Array.isArray(changes)).toBe(true);
    expect(changes.length).toBeGreaterThanOrEqual(1);
    for (const c of changes) {
      expect(typeof c.id).toBe("number");
      expect(typeof c.change_type).toBe("string");
      expect(typeof c.term_id).toBe("string");
      expect(typeof c.course_code).toBe("string");
      expect(typeof c.timestamp).toBe("string");
    }
  });

  it("validates /v1/search payload matches SearchResponse", () => {
    const search: SearchResponse = rawPayloads.search;
    expect(Array.isArray(search.hits)).toBe(true);
    expect(search.hits.length).toBeGreaterThanOrEqual(1);
    for (const hit of search.hits) {
      expect(typeof hit.id).toBe("number");
      expect(typeof hit.course_code).toBe("string");
      expect(typeof hit.title).toBe("string");
      expect(typeof hit.term).toBe("string");
      expect(typeof hit.dept_code).toBe("string");
      if (hit.slots) {
        for (const slot of hit.slots) {
          expect(typeof slot.day_code).toBe("string");
          expect(typeof slot.slot_hour).toBe("number");
        }
      }
    }
    expect(typeof search.offset).toBe("number");
    expect(typeof search.limit).toBe("number");
  });

  it("validates /v1/facets payload matches FacetDistribution", () => {
    const facets: FacetDistribution = rawPayloads.facets;
    expect(typeof facets).toBe("object");
    expect(typeof facets.term).toBe("object");
    expect(typeof facets.dept_code).toBe("object");
  });

  it("validates /v1/analytics/ghost-schedule/{term} payload matches GhostScheduleItem[]", () => {
    const items: GhostScheduleItem[] = rawPayloads.ghost_schedule;
    expect(Array.isArray(items)).toBe(true);
    expect(items.length).toBeGreaterThanOrEqual(1);
    for (const item of items) {
      expect(typeof item.day_code).toBe("string");
      expect(typeof item.slot_hour).toBe("number");
      expect(typeof item.room_name).toBe("string");
      expect(typeof item.course_code).toBe("string");
      expect(typeof item.dept_kisaadi).toBe("string");
    }
  });

  it("validates /v1/analytics/macro/departments-evolution payload matches DepartmentEvolution", () => {
    const evo: DepartmentEvolution = rawPayloads.department_evolution;
    expect(Array.isArray(evo.years)).toBe(true);
    expect(typeof evo.departments).toBe("object");
    expect(typeof evo.departments.CMPE).toBe("object");
  });

  it("validates /v1/analytics/macro/scheduling-heatmap payload matches SchedulingHeatmapSlot[]", () => {
    const heatmap: SchedulingHeatmapSlot[] = rawPayloads.scheduling_heatmap;
    expect(Array.isArray(heatmap)).toBe(true);
    expect(heatmap.length).toBeGreaterThanOrEqual(1);
    for (const slot of heatmap) {
      expect(typeof slot.day_code).toBe("string");
      expect(typeof slot.slot_hour).toBe("number");
      expect(typeof slot.count).toBe("number");
    }
  });

  it("validates /v1/system/status and /v1/sync/status payload matches SystemStatus", () => {
    const status: SystemStatus = rawPayloads.system_status;
    expect(typeof status.status).toBe("string");
    expect(typeof status.is_stale).toBe("boolean");
    expect(typeof status.feeds).toBe("object");
  });
});
