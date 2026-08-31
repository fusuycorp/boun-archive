export interface Term {
  id: string;
  academic_year: string;
  semester_num: number;
}

export interface Department {
  kisaadi: string;
  bolum: string;
}

export interface Instructor {
  id: number;
  full_name: string;
}

export interface Room {
  id: number;
  name: string;
  building?: string;
  capacity?: number;
}

export interface CourseSlot {
  id?: number;
  course_id?: number;
  day_code?: string | null;
  slot_hour?: number | null;
  slot_title?: string | null;
  room_id?: number | null;
  room_name?: string | null;
  room?: Room;
}

export interface Course {
  id: number;
  term_id: string;
  dept_kisaadi: string;
  course_code: string;
  section?: string | null;
  title?: string | null;
  instructor_id?: number | null;
  instructor_name?: string | null;
  credits?: number | null;
  ects?: number | null;
  delivery_method?: string | null;
  slots?: CourseSlot[];
}

export interface SearchCourseSlot {
  day_code: string;
  slot_hour: number;
  slot_title?: string | null;
  room_name?: string | null;
}

export interface SearchCourseHit {
  id: number;
  course_code: string;
  title: string;
  section?: string | null;
  term: string;
  department?: string | null;
  dept_code: string;
  instructor?: string | null;
  instructor_id?: number | null;
  credits?: number | null;
  ects?: number | null;
  delivery_method?: string | null;
  slots?: SearchCourseSlot[];
}

export interface GhostScheduleItem {
  day_code: string;
  slot_hour: number;
  room_name: string;
  course_code: string;
  dept_kisaadi: string;
}

export type FacetDistribution = Record<string, Record<string, number>>;

export interface SearchResponse {
  hits: SearchCourseHit[];
  facetDistribution?: FacetDistribution;
  totalHits?: number;
  estimatedTotalHits?: number;
  processingTimeMs?: number;
  offset?: number;
  limit?: number;
}

export interface DepartmentUniqueCourse {
  course_code: string;
  title: string;
  terms: string[];
  latest_term?: string;
}

export interface DepartmentInstructor {
  id: number;
  full_name: string;
  last_term: string;
  course_count: number;
  total_semesters: number;
}

export interface InstructorPreferredSlot {
  day: string;
  hour: number;
  frequency: number;
}

export interface InstructorHistoryItem {
  term: string;
  course_code: string;
  title: string;
}

export interface InstructorLegacy {
  instructor_name: string;
  total_semesters_taught: number;
  total_courses_taught: number;
  most_frequent_courses: Record<string, number>;
  preferred_slots: InstructorPreferredSlot[];
  history: InstructorHistoryItem[];
}

export interface DepartmentEvolution {
  years: string[];
  departments: Record<string, Record<string, number>>;
}

export interface SchedulingHeatmapSlot {
  day_code: string;
  slot_hour: number;
  count: number;
}

export interface QuotaSnapshot {
  id: number;
  term_id: string;
  course_code: string;
  section?: string;
  department?: string;
  status?: string;
  quota?: string;
  current?: string;
  quota_numeric?: number;
  current_numeric?: number;
  is_consent: boolean;
  is_unlimited: boolean;
  available?: number;
  captured_at: string;
}

export interface CourseChange {
  id: number;
  change_type: string;
  term_id: string;
  dept_kisaadi?: string;
  course_code: string;
  section?: string;
  timestamp: string;
  old_value?: string;
  new_value?: string;
  details?: string;
}

export interface CourseHistorySlot {
  day: string;
  hour: number;
  room: string;
  title?: string;
}

export interface CourseHistoryItem {
  id: number;
  term_id: string;
  section?: string;
  title?: string;
  instructor?: string;
  credits?: number;
  ects?: number;
  delivery_method?: string;
  slots: CourseHistorySlot[];
}

export interface FeedState {
  last_cursor?: string | null;
  updated_at?: string | null;
}

export interface UpstreamRunInfo {
  run_id?: string | null;
  term?: string | null;
  status?: string | null;
  total_courses?: number | null;
  changes_detected?: number | null;
  completed_at?: string | null;
  started_at?: string | null;
}

export interface SystemStatus {
  status: string;
  last_scraped_at?: string | null;
  last_sync_at?: string | null;
  latest_scrape_time?: string | null;
  upstream_scrape_time?: string | null;
  last_sync_time?: string | null;
  is_stale?: boolean;
  upstream_run?: UpstreamRunInfo | null;
  feeds?: Record<string, FeedState>;
}



