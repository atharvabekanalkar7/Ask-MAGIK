"""
Automated tests for expanded Backend Endpoints
Ask MAGIK - Enterprise API Suite
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_overview_metrics_endpoint(client):
    """Verifies /api/overview/metrics provides the pilot KPIs."""
    res = client.get("/api/overview/metrics")
    assert res.status_code == 200
    data = res.json()
    assert data["subscribers_display"] == "9.1M"
    assert data["prepaid_pct"] == "74%"
    assert data["postpaid_pct"] == "26%"
    assert data["regions_count"] == 5
    assert data["central_analysts"] == 6
    assert len(data["governed_analytical_path"]) == 6


def test_rag_context_preflight_endpoint(client):
    """Verifies /api/rag/context returns structured context & trace."""
    res = client.post(
        "/api/rag/context",
        json={"question": "Which prepaid plans had highest customer loss in the western region last month?"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "retrieved_context" in data
    assert "analysis_trace" in data
    assert len(data["retrieved_context"]["business_glossary"]) > 0
    assert len(data["analysis_trace"]) >= 3


def test_datasources_endpoint(client):
    """Verifies /api/datasources returns all 5 DataMart tables."""
    res = client.get("/api/datasources")
    assert res.status_code == 200
    data = res.json()
    assert data["tables_count"] == 5
    table_names = [t["name"] for t in data["tables"]]
    assert "subscriber_profile" in table_names
    assert "usage_daily" in table_names
    assert "campaign_response" in table_names
    assert "revenue_monthly" in table_names
    assert "churn_events" in table_names


def test_datasource_preview_endpoint(client):
    """Verifies /api/datasources/subscriber_profile/preview returns rows."""
    res = client.get("/api/datasources/subscriber_profile/preview?limit=5")
    assert res.status_code == 200
    data = res.json()
    assert len(data["rows"]) == 5
    assert "customer_id" in data["columns"]


def test_history_and_saved_insights_lifecycle(client):
    """Verifies history query and insight bookmarking."""
    # Check history
    h_res = client.get("/api/history")
    assert h_res.status_code == 200

    # Bookmark new insight
    save_res = client.post(
        "/api/history/save",
        json={
            "question": "Test Question",
            "key_insight": "Test Key Insight",
            "supporting_figures": ["Fig 1"],
            "sql": "SELECT 1;",
            "confidence": "HIGH"
        }
    )
    assert save_res.status_code == 200
    saved_id = save_res.json()["insight"]["id"]

    # Retrieve saved insights
    get_res = client.get("/api/insights/saved")
    assert get_res.status_code == 200
    ids = [i["id"] for i in get_res.json()]
    assert saved_id in ids

    # Delete saved insight
    del_res = client.delete(f"/api/insights/saved/{saved_id}")
    assert del_res.status_code == 200


def test_security_policies_and_validation_sandbox(client):
    """Verifies /api/security/policies and /api/security/validate."""
    res = client.get("/api/security/policies")
    assert res.status_code == 200
    assert res.json()["firewall_status"] == "ACTIVE"

    # Valid SELECT
    v_res = client.post("/api/security/validate", json={"sql": "SELECT * FROM subscriber_profile LIMIT 10;"})
    assert v_res.status_code == 200
    assert v_res.json()["is_valid"] is True

    # Blocked DROP
    bad_res = client.post("/api/security/validate", json={"sql": "DROP TABLE subscriber_profile;"})
    assert bad_res.status_code == 200
    assert bad_res.json()["is_valid"] is False


def test_audit_logs_endpoint(client):
    """Verifies /api/audit/logs."""
    res = client.get("/api/audit/logs")
    assert res.status_code == 200
    logs = res.json()
    assert len(logs) > 0


def test_chat_endpoint_resilience(client):
    """Verifies /api/chat completes with structured answer and evidence."""
    res = client.post(
        "/api/chat",
        json={"question": "Which prepaid plans had the highest customer loss in the western region last month?"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "key_insight" in data
    assert "sql" in data
    assert "chart" in data
    assert "retrieved_context" in data
    assert "analysis_trace" in data
