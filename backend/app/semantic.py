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

TURTLE_PREFIXES = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <https://schema.org/> .
@prefix aiiso: <http://purl.org/vocab/aiiso/schema#> .
@prefix void: <http://rdfs.org/ns/void#> .
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix boun: <https://archive.bogazici.app/id/> .
@prefix wd: <https://www.wikidata.org/wiki/> .
"""

DAY_TURTLE_MAP = {
    "M": "schema:Monday",
    "T": "schema:Tuesday",
    "W": "schema:Wednesday",
    "Th": "schema:Thursday",
    "F": "schema:Friday",
    "St": "schema:Saturday",
    "Su": "schema:Sunday",
}

def escape_turtle(val: Any) -> str:
    if val is None:
        return ""
    s = str(val)
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")

def course_history_to_turtle(
    course_code: str,
    history: List[Dict[str, Any]],
    base_url: str = "https://archive.bogazici.app"
) -> str:
    latest = history[0] if history else {}
    title = latest.get("title") or course_code
    dept_code = course_code.split()[0] if " " in course_code else ""
    credits = latest.get("credits")
    ects = latest.get("ects")
    
    clean_code = course_code.replace(" ", "")
    lines = [TURTLE_PREFIXES]
    
    lines.append(
        'boun:university a schema:CollegeOrUniversity, aiiso:Institution ;\n'
        '    schema:name "Boğaziçi University" ;\n'
        '    schema:alternateName "Bogazici Universitesi" ;\n'
        '    schema:url <https://bogazici.edu.tr> ;\n'
        '    schema:sameAs wd:Q853512 .\n'
    )
    
    course_props = [
        'a schema:Course',
        f'schema:courseCode "{escape_turtle(course_code)}"',
        f'schema:name "{escape_turtle(title)}"',
        'schema:provider boun:university'
    ]
    if credits is not None:
        course_props.append(f'schema:numberOfCredits {credits}')
    if ects is not None:
        course_props.append(f'schema:educationalCredentialAwarded "ECTS {ects}"')
    if dept_code:
        course_props.append(f'schema:department boun:department/{escape_turtle(dept_code)}')
        
    for item in history:
        t_id = item.get("term_id", "").replace("/", "-")
        sec = item.get("section") or "01"
        inst_uri = f'boun:course/{clean_code}/{t_id}/{sec}'
        course_props.append(f'schema:hasCourseInstance <{inst_uri}>')

    lines.append(f'boun:course/{clean_code} ' + ' ;\n    '.join(course_props) + ' .\n')

    for item in history:
        t_id = item.get("term_id", "").replace("/", "-")
        sec = item.get("section") or "01"
        inst_name = item.get("instructor")
        inst_props = [
            'a schema:CourseInstance',
            f'schema:name "{escape_turtle(course_code)}.{sec} - {escape_turtle(item.get("title") or title)}"',
            f'schema:courseMode "{"online" if "online" in str(item.get("delivery_method", "")).lower() else "onsite"}"'
        ]
        if inst_name and inst_name != "TBA":
            inst_props.append(f'schema:instructor [ a schema:Person ; schema:name "{escape_turtle(inst_name)}" ]')

        for s in item.get("slots", []):
            d_code = s.get("day") or s.get("day_code")
            h = s.get("hour") or s.get("slot_hour")
            r = s.get("room") or s.get("room_name")
            sched_props = ['a schema:Schedule']
            if d_code and d_code in DAY_TURTLE_MAP:
                sched_props.append(f'schema:byDay {DAY_TURTLE_MAP[d_code]}')
            if h:
                sched_props.append(f'schema:startTime "{(8 + int(h)):02d}:00"')
                sched_props.append(f'schema:endTime "{(9 + int(h)):02d}:00"')
            if r and r != "N/A":
                sched_props.append(f'schema:location [ a schema:Room ; schema:name "{escape_turtle(r)}" ]')
            inst_props.append('schema:courseSchedule [ ' + ' ; '.join(sched_props) + ' ]')

        lines.append(f'boun:course/{clean_code}/{t_id}/{sec} ' + ' ;\n    '.join(inst_props) + ' .\n')

    return '\n'.join(lines)

def instructor_to_turtle(
    instructor_id: int,
    full_name: str,
    base_url: str = "https://archive.bogazici.app"
) -> str:
    lines = [
        TURTLE_PREFIXES,
        'boun:university a schema:CollegeOrUniversity, aiiso:Institution ;\n'
        '    schema:name "Boğaziçi University" ;\n'
        '    schema:url <https://bogazici.edu.tr> ;\n'
        '    schema:sameAs wd:Q853512 .\n',
        f'boun:instructor/{instructor_id} a schema:Person ;\n'
        f'    schema:name "{escape_turtle(full_name)}" ;\n'
        f'    schema:jobTitle "Faculty Instructor" ;\n'
        f'    schema:worksFor boun:university .\n'
    ]
    return '\n'.join(lines)

def departments_to_turtle(
    departments: List[Dict[str, Any]],
    base_url: str = "https://archive.bogazici.app"
) -> str:
    lines = [
        TURTLE_PREFIXES,
        'boun:university a schema:CollegeOrUniversity, aiiso:Institution ;\n'
        '    schema:name "Boğaziçi University" ;\n'
        '    schema:url <https://bogazici.edu.tr> ;\n'
        '    schema:sameAs wd:Q853512 .\n'
    ]
    for d in departments:
        code = d.get("kisaadi", "").strip().upper()
        name = d.get("bolum", "").strip()
        if not code:
            continue
        lines.append(
            f'boun:department/{escape_turtle(code)} a aiiso:Department, schema:EducationalOrganization ;\n'
            f'    schema:alternateName "{escape_turtle(code)}" ;\n'
            f'    schema:name "{escape_turtle(name)}" ;\n'
            f'    schema:parentOrganization boun:university .\n'
        )
    return '\n'.join(lines)

def generate_void_description(base_url: str = "https://archive.bogazici.app") -> str:
    return (
        f"{TURTLE_PREFIXES}\n"
        f"boun:university a schema:CollegeOrUniversity, aiiso:Institution ;\n"
        f'    schema:name "Boğaziçi University" ;\n'
        f"    schema:url <https://bogazici.edu.tr> ;\n"
        f"    schema:sameAs wd:Q853512 .\n\n"
        f"<{base_url}/#dataset> a void:Dataset, dcat:Dataset ;\n"
        f'    dcterms:title "BOUN Archive Academic Knowledge Graph" ;\n'
        f'    dcterms:description "50+ years of historical course schedules, faculties, rooms, and academic offerings at Boğaziçi University." ;\n'
        f"    dcterms:publisher boun:university ;\n"
        f'    dcterms:license <https://creativecommons.org/publicdomain/zero/1.0/> ;\n'
        f"    void:vocabulary <https://schema.org/>, <http://purl.org/vocab/aiiso/schema#> ;\n"
        f"    dcat:distribution [\n"
        f"        a dcat:Distribution ;\n"
        f'        dcat:mediaType "text/turtle" ;\n'
        f"        dcat:accessURL <{base_url}/v1/departments>\n"
        f"    ] .\n"
    )

def generate_dcat_catalog_jsonld(base_url: str = "https://archive.bogazici.app") -> Dict[str, Any]:
    return {
        "@context": {
            "dcat": "http://www.w3.org/ns/dcat#",
            "dcterms": "http://purl.org/dc/terms/",
            "schema": "https://schema.org/",
            "void": "http://rdfs.org/ns/void#"
        },
        "@id": f"{base_url}/#catalog",
        "@type": "dcat:Catalog",
        "dcterms:title": "BOUN Archive Open Data Catalog",
        "dcterms:description": "Open Academic Course Timetables and Historical Registrar Catalog for Boğaziçi University",
        "dcterms:publisher": {
            "@type": "schema:CollegeOrUniversity",
            "schema:name": "Boğaziçi University",
            "schema:url": "https://bogazici.edu.tr"
        },
        "dcat:dataset": [
            {
                "@id": f"{base_url}/#dataset",
                "@type": "dcat:Dataset",
                "dcterms:title": "BOUN Archive Course Schedules & Analytics",
                "dcterms:description": "Comprehensive historical dataset of course offerings, time slots, instructors, and quota history.",
                "dcat:distribution": [
                    {
                        "@type": "dcat:Distribution",
                        "dcat:mediaType": "application/ld+json",
                        "dcat:accessURL": f"{base_url}/v1/departments"
                    },
                    {
                        "@type": "dcat:Distribution",
                        "dcat:mediaType": "text/turtle",
                        "dcat:accessURL": f"{base_url}/v1/departments"
                    }
                ]
            }
        ]
    }

