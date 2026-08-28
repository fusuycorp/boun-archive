import { z } from "zod";

export const CoursePlannerSlotSchema = z.object({
  id: z.number().optional().nullable(),
  course_id: z.number().optional().nullable(),
  day_code: z.string(),
  slot_hour: z.number(),
  room_name: z.string().optional().nullable(),
  slot_title: z.string().optional().nullable(),
  room: z
    .object({
      id: z.number().optional().nullable(),
      name: z.string().optional().nullable(),
      building: z.string().optional().nullable(),
      capacity: z.number().optional().nullable(),
    })
    .optional()
    .nullable(),
  room_id: z.number().optional().nullable(),
});

export const CoursePlannerItemSchema = z.object({
  id: z.union([z.number(), z.string()]).optional().nullable(),
  course_code: z.string().min(1),
  title: z.string().optional().nullable().default(""),
  section: z.string().optional().nullable().default(""),
  term: z.string().optional().nullable(),
  term_id: z.string().optional().nullable(),
  dept_kisaadi: z.string().optional().nullable(),
  instructor_id: z.number().optional().nullable(),
  instructor_name: z.string().optional().nullable(),
  credits: z.number().optional().nullable(),
  ects: z.number().optional().nullable(),
  delivery_method: z.string().optional().nullable(),
  slots: z.array(CoursePlannerSlotSchema).optional().default([]),
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
    for (const item of raw) {
      if (!item || typeof item !== "object") continue;
      const result = CoursePlannerItemSchema.safeParse(item);
      if (result.success) {
        validCourses.push(result.data);
      }
    }

    return validCourses;
  } catch {
    return [];
  }
}
