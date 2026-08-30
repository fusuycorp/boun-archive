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
  day_code: string;
  slot_hour: number;
  slot_title?: string;
  room?: Room;
}

export interface Course {
  id: number;
  term_id: string;
  dept_kisaadi: string;
  course_code: string;
  section: string;
  title: string;
  instructor_id?: number;
  instructor_name?: string;
  credits?: number;
  ects?: number;
  delivery_method?: string;
  slots?: CourseSlot[];
}

export interface GhostScheduleItem {
  id: number;
  course_code: string;
  section: string;
  title: string;
  term_id: string;
  dept_kisaadi: string;
  day_code: string;
  slot_hour: number;
  room_name: string;
}

export interface SearchResponse {
  hits: Course[];
  facetDistribution?: Record<string, Record<string, number>>;
  totalHits?: number;
  estimatedTotalHits?: number;
  processingTimeMs?: number;
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


