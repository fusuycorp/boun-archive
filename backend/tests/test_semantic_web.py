import pytest
from fastapi.testclient import TestClient

def test_instructor_json_ld_content_negotiation(client: TestClient):
    """GET /v1/instructors/1 with Accept: application/ld+json returns Schema.org Person"""
    response = client.get("/v1/instructors/1", headers={"Accept": "application/ld+json"})
    assert response.status_code == 200
    assert "application/ld+json" in response.headers.get("content-type", "")
    
    data = response.json()
    assert data["@context"] == "https://schema.org"
    assert "@graph" in data
    person = next(item for item in data["@graph"] if item["@type"] == "Person")
    assert "Albert Long" in person["name"] or len(person["name"]) > 0
    assert person["jobTitle"] == "Faculty Instructor"

def test_departments_json_ld_content_negotiation(client: TestClient):
    """GET /v1/departments with Accept: application/ld+json returns Schema.org ItemList"""
    response = client.get("/v1/departments", headers={"Accept": "application/ld+json"})
    assert response.status_code == 200
    assert "application/ld+json" in response.headers.get("content-type", "")
    
    data = response.json()
    assert data["@context"] == "https://schema.org"
    item_list = next(item for item in data["@graph"] if item["@type"] == "ItemList")
    assert len(item_list["itemListElement"]) >= 1
    assert any(
        el["item"]["alternateName"] == "CMPE" or "Computer" in str(el["item"]["name"]) or "BIO" in str(el["item"]["name"])
        for el in item_list["itemListElement"]
    )

def test_course_history_json_ld_content_negotiation(client: TestClient):
    """GET /v1/courses/history/CMPE%20150 with Accept: application/ld+json returns Schema.org Course & CourseInstance"""
    response = client.get("/v1/courses/history/CMPE%20150", headers={"Accept": "application/ld+json"})
    assert response.status_code == 200
    assert "application/ld+json" in response.headers.get("content-type", "")
    
    data = response.json()
    assert data["@context"] == "https://schema.org"
    course = next(item for item in data["@graph"] if item["@type"] == "Course")
    assert course["courseCode"] == "CMPE 150"
    assert len(course["name"]) > 0
    assert len(course["hasCourseInstance"]) >= 1
    
    instance = course["hasCourseInstance"][0]
    assert "name" in instance["instructor"]
    assert len(instance["courseSchedule"]) >= 1
    assert instance["courseSchedule"][0]["startTime"] == "09:00"

def test_course_schedule_ics_feed(client: TestClient):
    """GET /v1/courses/CMPE%20150/schedule.ics returns valid RFC 5545 iCalendar stream"""
    response = client.get("/v1/courses/CMPE%20150/schedule.ics")
    assert response.status_code == 200
    assert "text/calendar" in response.headers.get("content-type", "")
    assert "attachment; filename=" in response.headers.get("content-disposition", "")
    
    body = response.text
    assert body.startswith("BEGIN:VCALENDAR\r\n")
    assert "VERSION:2.0\r\n" in body
    assert "BEGIN:VEVENT\r\n" in body
    assert "SUMMARY:CMPE 150.01 -" in body
    assert "LOCATION:NH101" in body
    assert "RRULE:FREQ=WEEKLY;BYDAY=MO" in body
    assert body.endswith("END:VCALENDAR\r\n")

def test_openapi_semantic_metadata(client: TestClient):
    """GET /openapi.json contains descriptive OpenAPI 3.1 title and descriptions"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "BOUN Archive API"
    assert "Open Data & Semantic Linked Data" in data["info"]["description"]
    assert "/v1/courses/{course_code}/schedule.ics" in data["paths"]
