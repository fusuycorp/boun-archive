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
    assert "/.well-known/void" in data["paths"]
    assert "/v1/catalog.jsonld" in data["paths"]
    assert "/v1/optimizer/schedule" in data["paths"]

def test_instructor_turtle_content_negotiation(client: TestClient):
    """GET /v1/instructors/1 with Accept: text/turtle returns valid Turtle RDF"""
    response = client.get("/v1/instructors/1", headers={"Accept": "text/turtle"})
    assert response.status_code == 200
    assert "text/turtle" in response.headers.get("content-type", "")
    assert "@prefix schema:" in response.text
    assert "boun:instructor/1 a schema:Person" in response.text
    assert 'schema:name "Albert Long"' in response.text

def test_departments_turtle_content_negotiation(client: TestClient):
    """GET /v1/departments with Accept: text/turtle returns valid Turtle RDF"""
    response = client.get("/v1/departments", headers={"Accept": "text/turtle"})
    assert response.status_code == 200
    assert "text/turtle" in response.headers.get("content-type", "")
    assert "@prefix aiiso:" in response.text
    assert "boun:department/CMPE a aiiso:Department" in response.text
    assert 'schema:alternateName "CMPE"' in response.text

def test_course_history_turtle_content_negotiation(client: TestClient):
    """GET /v1/courses/history/CMPE 150 with Accept: text/turtle returns valid Turtle RDF"""
    response = client.get("/v1/courses/history/CMPE%20150", headers={"Accept": "text/turtle"})
    assert response.status_code == 200
    assert "text/turtle" in response.headers.get("content-type", "")
    assert "@prefix schema:" in response.text
    assert "boun:course/CMPE150 a schema:Course" in response.text
    assert 'schema:courseCode "CMPE 150"' in response.text

def test_void_dataset_description_endpoint(client: TestClient):
    """GET /.well-known/void returns W3C VoID dataset description in Turtle"""
    response = client.get("/.well-known/void")
    assert response.status_code == 200
    assert "text/turtle" in response.headers.get("content-type", "")
    assert "a void:Dataset, dcat:Dataset" in response.text
    assert "BOUN Archive Academic Knowledge Graph" in response.text

def test_dcat_catalog_endpoint(client: TestClient):
    """GET /v1/catalog.jsonld returns DCAT 2 catalog in JSON-LD"""
    response = client.get("/v1/catalog.jsonld")
    assert response.status_code == 200
    assert "application/ld+json" in response.headers.get("content-type", "")
    data = response.json()
    assert data["@type"] == "dcat:Catalog"
    assert "BOUN Archive Open Data Catalog" in data["dcterms:title"]

def test_schedule_optimizer_csp_endpoint(client: TestClient):
    """POST /v1/optimizer/schedule returns valid conflict-free combinations"""
    payload = {
        "term_id": "2024-2025-1",
        "target_courses": ["CMPE 150"],
        "min_hour": 1,
        "max_hour": 14,
        "avoid_days": []
    }
    response = client.post("/v1/optimizer/schedule", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["total_combinations_found"] >= 1
    assert len(data["combinations"]) >= 1
    comb = data["combinations"][0]
    assert comb["total_credits"] >= 3
    assert comb["sections"][0]["course_code"] == "CMPE 150"

def test_mcp_server_tools_execution(client: TestClient):
    """Verify MCP tools list and execution directly"""
    from app.mcp_server import TOOLS_DEFINITIONS, execute_tool
    from tests.conftest import TestingSessionLocal
    
    assert len(TOOLS_DEFINITIONS) >= 4
    tool_names = [t["name"] for t in TOOLS_DEFINITIONS]
    assert "boun_search_courses" in tool_names
    assert "boun_optimize_schedule" in tool_names
    
    # Test tool execution against SQLite test DB
    with TestingSessionLocal() as db:
        res = execute_tool("boun_get_course_history", {"course_code": "CMPE 150"}, db)
        assert res["course_code"] == "CMPE 150"
        assert "history" in res


