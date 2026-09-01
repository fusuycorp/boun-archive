from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone
import json

DAY_ICAL_MAP = {
    "M": "MO",
    "T": "TU",
    "W": "WE",
    "Th": "TH",
    "F": "FR",
    "St": "SA",
    "Su": "SU",
}

DAY_OFFSET_MAP = {
    "M": 0,
    "T": 1,
    "W": 2,
    "Th": 3,
    "F": 4,
    "St": 5,
    "Su": 6,
}

BOUN_ORG_JSONLD = {
    "@type": "CollegeOrUniversity",
    "@id": "https://archive.bogazici.app/#organization",
    "name": "Boğaziçi University",
    "alternateName": "Bogazici Universitesi",
    "url": "https://bogazici.edu.tr",
    "sameAs": "https://www.wikidata.org/wiki/Q853512"
}

def course_history_to_json_ld(
    course_code: str,
    history: List[Dict[str, Any]],
    base_url: str = "https://archive.bogazici.app"
) -> Dict[str, Any]:
    latest = history[0] if history else {}
    title = latest.get("title") or course_code
    dept_code = course_code.split()[0] if " " in course_code else ""
    credits = latest.get("credits")
    ects = latest.get("ects")

    instances = []
    for item in history:
        term_id = item.get("term_id", "")
        term_year = term_id.split("/")[0] if "/" in term_id else "2026"
        sec = item.get("section") or ""
        inst_name = item.get("instructor")
        inst_obj = {
            "@type": "Person",
            "name": inst_name
        } if inst_name and inst_name != "TBA" else None

        slots = item.get("slots", [])
        schedule_slots = []
        for s in slots:
            day = s.get("day")
            hour = s.get("hour")
            room = s.get("room")
            slot_entry = {"@type": "Schedule"}
            if hour:
                slot_entry["startTime"] = f"{(8 + int(hour)):02d}:00"
                slot_entry["endTime"] = f"{(9 + int(hour)):02d}:00"
            if room and room != "N/A":
                slot_entry["location"] = {"@type": "Room", "name": room}
            schedule_slots.append(slot_entry)

        instance = {
            "@type": "CourseInstance",
            "@id": f"{base_url}/course/{course_code}?term={term_id}&sec={sec}#instance",
            "name": f"{course_code}.{sec} - {item.get('title') or title}",
            "startDate": f"{term_year}-09-01",
            "courseMode": "online" if "online" in str(item.get("delivery_method", "")).lower() else "onsite",
        }
        if inst_obj:
            instance["instructor"] = inst_obj
        if schedule_slots:
            instance["courseSchedule"] = schedule_slots
        instances.append(instance)

    return {
        "@context": "https://schema.org",
        "@graph": [
            BOUN_ORG_JSONLD,
            {
                "@type": "Course",
                "@id": f"{base_url}/course/{course_code}#course",
                "courseCode": course_code,
                "name": title,
                "provider": {"@id": "https://archive.bogazici.app/#organization"},
                **({"numberOfCredits": credits} if credits else {}),
                **({"educationalCredentialAwarded": f"ECTS {ects}"} if ects else {}),
                **({"department": {"@type": "EducationalOrganization", "name": dept_code}} if dept_code else {}),
                "hasCourseInstance": instances
            }
        ]
    }

def instructor_to_json_ld(
    instructor_id: int,
    full_name: str,
    base_url: str = "https://archive.bogazici.app"
) -> Dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@graph": [
            BOUN_ORG_JSONLD,
            {
                "@type": "Person",
                "@id": f"{base_url}/instructor/{instructor_id}#person",
                "name": full_name,
                "jobTitle": "Faculty Instructor",
                "worksFor": {"@id": "https://archive.bogazici.app/#organization"}
            }
        ]
    }

def departments_to_json_ld(
    departments: List[Dict[str, Any]],
    base_url: str = "https://archive.bogazici.app"
) -> Dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@graph": [
            BOUN_ORG_JSONLD,
            {
                "@type": "ItemList",
                "@id": f"{base_url}/departments#list",
                "name": "Academic Departments at Boğaziçi University",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": idx + 1,
                        "item": {
                            "@type": "EducationalOrganization",
                            "name": d.get("bolum"),
                            "alternateName": d.get("kisaadi"),
                            "parentOrganization": {"@id": "https://archive.bogazici.app/#organization"},
                            "url": f"{base_url}/departments"
                        }
                    }
                    for idx, d in enumerate(departments)
                ]
            }
        ]
    }

def generate_course_schedule_ics(
    course_code: str,
    history_or_course: List[Dict[str, Any]],
    calendar_title: Optional[str] = None
) -> str:
    cal_title = calendar_title or f"BOUN {course_code} Schedule"
    now_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    
    # Semester reference: Fall 2026 starting Monday 2026-09-21
    base_year = 2026
    base_month = 9
    base_monday = 21

    events = []
    # Filter to most recent term if history list provided
    if history_or_course:
        latest_term = history_or_course[0].get("term_id")
        target_items = [h for h in history_or_course if h.get("term_id") == latest_term] or history_or_course
    else:
        target_items = []

    for item in target_items:
        sec = f".{item.get('section')}" if item.get("section") else ""
        title = item.get("title") or course_code
        instructor = item.get("instructor") or "N/A"
        slots = item.get("slots", [])

        for idx, s in enumerate(slots):
            day_code = s.get("day") or s.get("day_code")
            slot_hour = s.get("hour") or s.get("slot_hour")
            if not day_code or not slot_hour:
                continue

            by_day = DAY_ICAL_MAP.get(day_code)
            day_offset = DAY_OFFSET_MAP.get(day_code, 0)
            if not by_day:
                continue

            event_day = base_monday + day_offset
            start_hour = 8 + int(slot_hour)
            end_hour = 9 + int(slot_hour)

            dt_start = f"{base_year}{base_month:02d}{event_day:02d}T{start_hour:02d}0000"
            dt_end = f"{base_year}{base_month:02d}{event_day:02d}T{end_hour:02d}0000"
            uid = f"{course_code}{sec}-{day_code}-{slot_hour}-{idx}@archive.bogazici.app"
            location = s.get("room") or s.get("room_name") or "TBA"

            description = f"Course: {course_code}{sec}\\nTitle: {title}\\nInstructor: {instructor}\\nRoom: {location}"

            event_lines = [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now_str}",
                f"DTSTART;TZID=Europe/Istanbul:{dt_start}",
                f"DTEND;TZID=Europe/Istanbul:{dt_end}",
                f"RRULE:FREQ=WEEKLY;BYDAY={by_day};UNTIL=20270125T235959Z",
                f"SUMMARY:{course_code}{sec} - {title}",
                f"LOCATION:{location}",
                f"DESCRIPTION:{description}",
                "STATUS:CONFIRMED",
                "END:VEVENT"
            ]
            events.append("\r\n".join(event_lines))

    return "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//BOUN Archive//Course Catalog 1.0//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{cal_title}",
        "X-WR-TIMEZONE:Europe/Istanbul",
        *events,
        "END:VCALENDAR"
    ]) + "\r\n"
