-- Target PostgreSQL Schema for BOUN Archive

CREATE TABLE IF NOT EXISTS terms (
    id VARCHAR(15) PRIMARY KEY,
    academic_year VARCHAR(9) NOT NULL,
    semester_num INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS departments (
    kisaadi VARCHAR(10) PRIMARY KEY,
    bolum VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS instructors (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS rooms (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    building VARCHAR(50),
    capacity INTEGER
);

CREATE TABLE IF NOT EXISTS courses (
    id SERIAL PRIMARY KEY,
    term_id VARCHAR(15) REFERENCES terms(id),
    dept_kisaadi VARCHAR(10) REFERENCES departments(kisaadi),
    course_code VARCHAR(20) NOT NULL,
    section VARCHAR(5),
    title VARCHAR(255),
    instructor_id INTEGER REFERENCES instructors(id),
    credits INTEGER,
    ects INTEGER,
    delivery_method VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS course_slots (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id),
    day_code VARCHAR(10),
    slot_hour INTEGER,
    slot_title VARCHAR(255),
    room_id INTEGER REFERENCES rooms(id)
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_courses_term ON courses(term_id);
CREATE INDEX IF NOT EXISTS idx_courses_dept ON courses(dept_kisaadi);
CREATE INDEX IF NOT EXISTS idx_courses_code ON courses(course_code);
CREATE INDEX IF NOT EXISTS idx_courses_code_upper ON courses(UPPER(course_code));
CREATE INDEX IF NOT EXISTS idx_courses_instructor ON courses(instructor_id);
CREATE INDEX IF NOT EXISTS idx_courses_lookup ON courses(term_id, course_code, section);
CREATE INDEX IF NOT EXISTS idx_slots_course ON course_slots(course_id);
CREATE INDEX IF NOT EXISTS idx_slots_room ON course_slots(room_id);

CREATE TABLE IF NOT EXISTS quota_snapshots (
    id SERIAL PRIMARY KEY,
    term_id VARCHAR(15) REFERENCES terms(id),
    course_code VARCHAR(20) NOT NULL,
    section VARCHAR(5),
    department VARCHAR(100),
    status VARCHAR(50),
    quota VARCHAR(20),
    current VARCHAR(20),
    quota_numeric INTEGER,
    current_numeric INTEGER,
    is_consent BOOLEAN DEFAULT FALSE,
    is_unlimited BOOLEAN DEFAULT FALSE,
    available INTEGER,
    captured_at VARCHAR(50) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_quota_term ON quota_snapshots(term_id);
CREATE INDEX IF NOT EXISTS idx_quota_code ON quota_snapshots(course_code);
CREATE INDEX IF NOT EXISTS idx_quota_code_upper ON quota_snapshots(UPPER(course_code));
CREATE INDEX IF NOT EXISTS idx_quota_captured_at ON quota_snapshots(captured_at);
CREATE INDEX IF NOT EXISTS idx_quota_code_term_captured ON quota_snapshots(course_code, term_id, captured_at DESC);

CREATE TABLE IF NOT EXISTS course_changes (
    id SERIAL PRIMARY KEY,
    change_type VARCHAR(20) NOT NULL,
    term_id VARCHAR(15) NOT NULL,
    dept_kisaadi VARCHAR(10),
    course_code VARCHAR(20) NOT NULL,
    section VARCHAR(5),
    timestamp VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    details VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_changes_term ON course_changes(term_id);
CREATE INDEX IF NOT EXISTS idx_changes_code ON course_changes(course_code);
CREATE INDEX IF NOT EXISTS idx_changes_code_upper ON course_changes(UPPER(course_code));
CREATE INDEX IF NOT EXISTS idx_changes_timestamp ON course_changes(timestamp);
CREATE INDEX IF NOT EXISTS idx_changes_code_timestamp ON course_changes(course_code, timestamp DESC);

CREATE TABLE IF NOT EXISTS sync_state (
    feed_name VARCHAR(50) PRIMARY KEY,
    last_cursor VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
