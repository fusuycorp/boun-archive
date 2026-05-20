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
    day_code VARCHAR(2),
    slot_hour INTEGER,
    room_id INTEGER REFERENCES rooms(id)
);

-- Indices for performance
CREATE INDEX idx_courses_term ON courses(term_id);
CREATE INDEX idx_courses_dept ON courses(dept_kisaadi);
CREATE INDEX idx_courses_code ON courses(course_code);
CREATE INDEX idx_slots_course ON course_slots(course_id);
CREATE INDEX idx_slots_room ON course_slots(room_id);
