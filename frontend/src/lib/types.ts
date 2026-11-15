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
  instructor?: Instructor | null;
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
  has_syllabus?: boolean;
  slots?: SearchCourseSlot[];
}

export interface GhostScheduleItem {
  day_code: string;
  slot_hour: number;
  room_name: string;
  building?: string | null;
  campus?: string | null;
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

export interface InstructorCourseSummary {
  course_code: string;
  title: string;
  sections: string[];
  terms_count: number;
  latest_term: string;
  total_offerings: number;
}

export interface InstructorHistoryItem {
  term: string;
  course_code: string;
  section?: string | null;
  title: string;
}

export interface InstructorLegacy {
  instructor_name: string;
  total_semesters_taught: number;
  total_courses_taught: number;
  most_frequent_courses: Record<string, number>;
  preferred_slots: InstructorPreferredSlot[];
  history: InstructorHistoryItem[];
  courses_summary?: InstructorCourseSummary[];
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
  instructor_id?: number | null;
  credits?: number;
  ects?: number;
  delivery_method?: string;
  has_syllabus?: boolean;
  syllabus_url?: string | null;
  desc_url?: string | null;
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

export interface ScheduleOptimizationRequest {
  term_id: string;
  target_courses: string[];
  candidate_electives?: string[];
  num_electives_needed?: number;
  avoid_days?: string[];
  min_hour?: number;
  max_hour?: number;
  max_campus_days?: number | null;
  max_results?: number;
}

export interface TimetableSection {
  course_code: string;
  section: string;
  title?: string | null;
  instructor?: string | null;
  credits?: number | null;
  ects?: number | null;
  slots: SearchCourseSlot[];
}

export interface TimetableCombination {
  score: number;
  total_credits: number;
  total_ects: number;
  campus_days: string[];
  total_gap_hours: number;
  sections: TimetableSection[];
}

export interface ScheduleOptimizationResponse {
  term_id: string;
  success: boolean;
  total_combinations_found: number;
  combinations: TimetableCombination[];
  message?: string | null;
}

export interface CourseCatalogInfo {
  course_code: string;
  found: boolean;
  title?: string | null;
  en_url?: string | null;
  tr_url?: string | null;
  en_text?: string | null;
  tr_text?: string | null;
  canonical_text?: string | null;
  updated_at?: string | null;
}

export interface CourseSyllabusDetail {
  course_id: number;
  term_id: string;
  course_code: string;
  section?: string | null;
  has_syllabus: boolean;
  syllabus_url?: string | null;
  desc_url?: string | null;
  syllabus_text: string;
}



