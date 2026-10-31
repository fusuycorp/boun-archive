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

VTIMEZONE_ISTANBUL = "\r\n".join([
    "BEGIN:VTIMEZONE",
    "TZID:Europe/Istanbul",
    "BEGIN:STANDARD",
    "TZOFFSETFROM:+0300",
    "TZOFFSETTO:+0300",
    "TZNAME:+03",
    "DTSTART:19700101T000000",
    "END:STANDARD",
    "END:VTIMEZONE"
])

def _escape_ical_text(text: Any) -> str:
    if text is None:
        return ""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )

# Exact official semester start ("Classes begin") and end ("Classes end" / "Last day of classes")
# sourced from https://academiccalendar.bogazici.edu.tr (akademiktakvim.bogazici.edu.tr)
OFFICIAL_TERM_BOUNDS: Dict[str, tuple[tuple[int, int, int], str]] = {
    "2014-2015-1": ((2014, 9, 22), "20141224T235959Z"),
    "2014-2015-2": ((2015, 2, 9), "20150513T235959Z"),
    "2014-2015-3": ((2015, 6, 18), "20150805T235959Z"),
    "2015-2016-1": ((2015, 9, 28), "20151225T235959Z"),
    "2015-2016-2": ((2016, 2, 8), "20160513T235959Z"),
    "2015-2016-3": ((2016, 6, 16), "20160805T235959Z"),
    "2016-2017-1": ((2016, 9, 19), "20161216T235959Z"),
    "2016-2017-2": ((2017, 2, 6), "20170515T235959Z"),
    "2016-2017-3": ((2017, 6, 15), "20170801T235959Z"),
    "2017-2018-1": ((2017, 9, 18), "20171215T235959Z"),
    "2017-2018-2": ((2018, 2, 5), "20180511T235959Z"),
    "2017-2018-3": ((2018, 6, 25), "20180807T235959Z"),
    "2018-2019-1": ((2018, 9, 20), "20181219T235959Z"),
    "2018-2019-2": ((2019, 2, 7), "20190515T235959Z"),
    "2018-2019-3": ((2019, 6, 24), "20190806T235959Z"),
    "2019-2020-1": ((2019, 9, 19), "20191218T235959Z"),
    "2019-2020-2": ((2020, 2, 6), "20200612T235959Z"),
    "2019-2020-3": ((2020, 8, 4), "20200914T235959Z"),
    "2020-2021-1": ((2020, 10, 22), "20210120T235959Z"),
    "2020-2021-2": ((2021, 3, 18), "20210616T235959Z"),
    "2020-2021-3": ((2021, 7, 16), "20210903T235959Z"),
    "2021-2022-1": ((2021, 10, 6), "20220104T235959Z"),
    "2021-2022-2": ((2022, 2, 23), "20220524T235959Z"),
    "2021-2022-3": ((2022, 6, 24), "20220816T235959Z"),
    "2022-2023-1": ((2022, 9, 28), "20221227T235959Z"),
    "2022-2023-2": ((2023, 2, 20), "20230518T235959Z"),
    "2022-2023-3": ((2023, 6, 20), "20230811T235959Z"),
    "2023-2024-1": ((2023, 9, 27), "20231226T235959Z"),
    "2023-2024-2": ((2024, 2, 12), "20240517T235959Z"),
    "2023-2024-3": ((2024, 6, 25), "20240812T235959Z"),
    "2024-2025-1": ((2024, 9, 23), "20241220T235959Z"),
    "2024-2025-2": ((2025, 2, 10), "20250516T235959Z"),
    "2024-2025-3": ((2025, 6, 24), "20250811T235959Z"),
    "2025-2026-1": ((2025, 9, 22), "20251219T235959Z"),
    "2025-2026-2": ((2026, 2, 9), "20260515T235959Z"),
    "2025-2026-3": ((2026, 6, 24), "20260812T235959Z"),
    "2026-2027-1": ((2026, 9, 21), "20261211T235959Z"),
    "2026-2027-2": ((2027, 1, 18), "20270422T235959Z"),
    "2026-2027-3": ((2027, 6, 30), "20270810T235959Z"),
}

def _resolve_semester_bounds(term_id: Optional[str]) -> tuple[tuple[int, int, int], str]:
    # Returns ((start_year, start_month, start_day), until_utc)
    if term_id:
        clean = term_id.strip().replace("/", "-")
        if clean in OFFICIAL_TERM_BOUNDS:
            return OFFICIAL_TERM_BOUNDS[clean]
        parts = clean.split("-")
        try:
            start_yr = int(parts[0])
            sem = int(parts[-1]) if len(parts) >= 2 else 1
            from datetime import date
            if sem == 2:
                d = date(start_yr + 1 if len(parts) > 2 else start_yr, 2, 9)
                monday = 9 + ((0 - d.weekday()) % 7)
                yr = d.year
                return ((yr, 2, monday), f"{yr}0515T235959Z")
            elif sem == 3:
                d = date(start_yr + 1 if len(parts) > 2 else start_yr, 6, 22)
                monday = 22 + ((0 - d.weekday()) % 7)
                yr = d.year
                return ((yr, 6, monday), f"{yr}0812T235959Z")
            else:
                d = date(start_yr, 9, 18)
                monday = 18 + ((0 - d.weekday()) % 7)
                return ((start_yr, 9, monday), f"{start_yr}1220T235959Z")
        except Exception:
            pass
    return OFFICIAL_TERM_BOUNDS["2026-2027-1"]

def generate_course_schedule_ics(
    course_code: str,
    history_or_course: List[Dict[str, Any]],
    calendar_title: Optional[str] = None
) -> str:
    from datetime import date, timedelta
    cal_title = _escape_ical_text(calendar_title or f"BOUN {course_code} Schedule")
    now_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    events = []
    # Filter to most recent term if history list provided
    latest_term = None
    if history_or_course:
        latest_term = history_or_course[0].get("term_id") or history_or_course[0].get("term")
        target_items = [h for h in history_or_course if (h.get("term_id") or h.get("term")) == latest_term] or history_or_course
    else:
        target_items = []

    (start_yr, start_mo, start_day), until_utc = _resolve_semester_bounds(latest_term)
    sem_start_date = date(start_yr, start_mo, start_day)

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

            days_ahead = (day_offset - sem_start_date.weekday()) % 7
            first_occurrence = sem_start_date + timedelta(days=days_ahead)
            start_hour = 8 + int(slot_hour)
            end_hour = 9 + int(slot_hour)

            dt_start = f"{first_occurrence.strftime('%Y%m%d')}T{start_hour:02d}0000"
            dt_end = f"{first_occurrence.strftime('%Y%m%d')}T{end_hour:02d}0000"
            uid = f"{course_code}{sec}-{day_code}-{slot_hour}-{idx}@archive.bogazici.app"
            location = s.get("room") or s.get("room_name") or "TBA"

            summary_escaped = _escape_ical_text(f"{course_code}{sec} - {title}")
            location_escaped = _escape_ical_text(location)
            desc_escaped = (
                f"Course: {_escape_ical_text(course_code + sec)}\\n"
                f"Title: {_escape_ical_text(title)}\\n"
                f"Instructor: {_escape_ical_text(instructor)}\\n"
                f"Room: {location_escaped}"
            )

            event_lines = [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now_str}",
                f"DTSTART;TZID=Europe/Istanbul:{dt_start}",
                f"DTEND;TZID=Europe/Istanbul:{dt_end}",
                f"RRULE:FREQ=WEEKLY;BYDAY={by_day};UNTIL={until_utc}",
                f"SUMMARY:{summary_escaped}",
                f"LOCATION:{location_escaped}",
                f"DESCRIPTION:{desc_escaped}",
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
        VTIMEZONE_ISTANBUL,
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
        inst_uri = f'{base_url}/id/course/{clean_code}/{t_id}/{sec}'
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

