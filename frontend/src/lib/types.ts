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

export interface CommuteWarning {
  fromSlot: string;
  toSlot: string;
  fromCampus: string;
  toCampus: string;
  riskLevel: 'Impossible' | 'High' | 'Moderate' | 'Low';
  message: string;
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


