import { z } from "zod";

const RawRoomSchema = z
  .object({
    id: z.number().optional().nullable(),
    name: z.string().optional().nullable(),
    building: z.string().optional().nullable(),
    capacity: z.number().optional().nullable(),
  })
  .optional()
  .nullable();

const RawCoursePlannerSlotSchema = z.object({
  id: z.number().optional().nullable(),
  course_id: z.number().optional().nullable(),
  day_code: z.string().optional().nullable(),
  slot_hour: z.number().optional().nullable(),
  room_name: z.string().optional().nullable(),
  slot_title: z.string().optional().nullable(),
  room: RawRoomSchema,
  room_id: z.number().optional().nullable(),
  disabled: z.boolean().optional().default(false),
});

export const CoursePlannerSlotSchema = z.object({
  id: z.number().optional().nullable(),
  course_id: z.number().optional().nullable(),
  day_code: z.string().min(1),
  slot_hour: z.number().int().min(1).max(14),
  room_name: z.string().optional().nullable(),
  slot_title: z.string().optional().nullable(),
  room: RawRoomSchema,
  room_id: z.number().optional().nullable(),
  disabled: z.boolean().optional().default(false),
});

const InstructorFieldSchema = z
  .union([
    z.string(),
    z.object({
      id: z.number().optional().nullable(),
      full_name: z.string().optional().nullable(),
    }),
  ])
  .optional()
  .nullable()
  .transform((val) => {
    if (typeof val === "string") return val;
    if (val && typeof val === "object") return val.full_name ?? null;
    return null;
  });

export const CoursePlannerItemSchema = z
  .object({
    id: z.union([z.number(), z.string()]).optional().nullable(),
    course_code: z.string().min(1),
    title: z.string().optional().nullable().default(""),
    section: z.string().optional().nullable().default(""),
    term: z.string().optional().nullable(),
    term_id: z.string().optional().nullable(),
    dept_kisaadi: z.string().optional().nullable(),
    instructor_id: z.number().optional().nullable(),
    instructor_name: z.string().optional().nullable(),
    instructor: InstructorFieldSchema,
    credits: z.number().optional().nullable(),
    ects: z.number().optional().nullable(),
    delivery_method: z.string().optional().nullable(),
    slots: z
      .array(RawCoursePlannerSlotSchema)
      .optional()
      .default([])
      .transform((slots) =>
        slots
          .filter(
            (s): s is typeof s & { day_code: string; slot_hour: number } =>
              typeof s.day_code === "string" &&
              s.day_code.trim().length > 0 &&
              typeof s.slot_hour === "number" &&
              Number.isInteger(s.slot_hour) &&
              s.slot_hour >= 1 &&
              s.slot_hour <= 14
          )
          .map((s) => ({
            ...s,
            day_code: s.day_code.trim(),
            room_name: s.room_name ?? s.room?.name ?? null,
          }))
      ),
  })
  .transform((c) => {
    const resolvedInstructor = c.instructor_name || c.instructor || null;
    return {
      ...c,
      instructor_name: resolvedInstructor,
      instructor: resolvedInstructor,
    };
  });

export const CoursePlannerListSchema = z.array(CoursePlannerItemSchema);

export type CoursePlannerSlot = z.infer<typeof CoursePlannerSlotSchema>;
export type CoursePlannerItem = z.infer<typeof CoursePlannerItemSchema>;

/**
 * Safely parses and validates planner courses from a raw JSON string.
 * Corrupt or invalid course entries are filtered out; returns empty array on failure.
 */
export function safeParsePlannerCourses(jsonString: string): CoursePlannerItem[] {
  if (!jsonString || typeof jsonString !== "string") {
    return [];
  }

  try {
    const raw = JSON.parse(jsonString);
    if (!Array.isArray(raw)) {
      return [];
    }

    const validCourses: CoursePlannerItem[] = [];
    const seen = new Set<string>();
    for (const item of raw) {
      if (!item || typeof item !== "object") continue;
      const result = CoursePlannerItemSchema.safeParse(item);
      if (result.success) {
        const c = result.data;
        const key = `${c.course_code.trim().toUpperCase()}_${(c.section || "01").trim()}`;
        if (!seen.has(key)) {
          seen.add(key);
          validCourses.push(c);
        }
      }
    }

    return validCourses;
  } catch {
    return [];
  }
}
