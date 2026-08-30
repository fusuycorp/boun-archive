from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    """GET /health -> 200 {'status': 'healthy'}"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_terms_contract(client: TestClient):
    """GET /v1/terms -> 200 list of terms"""
    response = client.get("/v1/terms")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    term = data[0]
    assert "id" in term
    assert "academic_year" in term
    assert "semester_num" in term
    assert term["id"] == "2024-2025-1"


def test_departments_contract(client: TestClient):
    """GET /v1/departments -> 200 list of departments"""
    response = client.get("/v1/departments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    dept = data[0]
    assert "kisaadi" in dept
    assert "bolum" in dept
    assert dept["kisaadi"] == "CMPE"


def test_system_status_contract(client: TestClient):
    """GET /v1/system/status -> 200 schema"""
    response = client.get("/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "status" in data
    assert "last_scraped_at" in data
    assert "last_sync_at" in data
    assert "latest_scrape_time" in data
    assert "is_stale" in data
    assert "feeds" in data
    assert isinstance(data["feeds"], dict)


def test_facets_contract(client: TestClient):
    """GET /v1/facets -> 200 facets dictionary"""
    response = client.get("/v1/facets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "term" in data
    assert "dept_code" in data
    assert isinstance(data["term"], dict)
    assert isinstance(data["dept_code"], dict)


def test_search_contract(client: TestClient):
    """GET /v1/search?limit=5 -> 200 hits dictionary"""
    response = client.get("/v1/search?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "hits" in data
    assert isinstance(data["hits"], list)
    assert len(data["hits"]) >= 1
    assert "limit" in data
    assert data["limit"] == 5
    assert "offset" in data
    assert ("estimatedTotalHits" in data) or ("totalHits" in data)
    
    first_hit = data["hits"][0]
    assert "slots" in first_hit
    assert isinstance(first_hit["slots"], list)
    assert len(first_hit["slots"]) >= 1
    assert first_hit["slots"][0]["day_code"] == "M"
    assert first_hit["slots"][0]["room_name"] == "NH101"

    # Test search query with spaces
    res_space = client.get("/v1/search?q=CMPE%20150")
    assert res_space.status_code == 200
    assert len(res_space.json()["hits"]) >= 1

    # Test search query without spaces
    res_nospace = client.get("/v1/search?q=CMPE150")
    assert res_nospace.status_code == 200
    assert len(res_nospace.json()["hits"]) >= 1


def test_course_detail_contract(client: TestClient):
    """GET /v1/courses/{course_id} -> 200 course object"""
    response = client.get("/v1/courses/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["course_code"] == "CMPE 150"
    assert data["term_id"] == "2024-2025-1"


def test_course_history_contract(client: TestClient):
    """GET /v1/courses/history/{course_code} -> 200 history array"""
    response = client.get("/v1/courses/history/CMPE%20150")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["term_id"] == "2024-2025-1"
    assert data[0]["title"] == "Introduction to Computing"


def test_course_quota_contract(client: TestClient):
    """GET /v1/courses/{course_code}/quota -> 200 quota array"""
    response = client.get("/v1/courses/CMPE%20150/quota")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["course_code"] == "CMPE 150"


def test_course_changes_contract(client: TestClient):
    """GET /v1/courses/{course_code}/changes -> 200 changes array"""
    response = client.get("/v1/courses/CMPE%20150/changes")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["course_code"] == "CMPE 150"


def test_instructors_contract(client: TestClient):
    """GET /v1/instructors -> 200 list of instructors"""
    response = client.get("/v1/instructors")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["full_name"] == "Albert Long"
