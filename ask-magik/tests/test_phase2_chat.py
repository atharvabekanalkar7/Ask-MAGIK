"""
Phase 2 Tests: Chat Orchestration, Endpoints & Question Execution
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.query_executor import SafeQueryExecutor
from backend.services.result_validator import ResultValidator
from backend.services.confidence import ConfidenceScorer
from backend.services.sql_validator import SQLValidationResult
from backend.rag.retriever import GroundedContextPackage
from backend.llm.ollama_client import OllamaClient


@pytest.fixture(scope="module")
def api_client():
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="module")
def executor():
    return SafeQueryExecutor()


def test_q1_sql_execution(executor):
    """Verifies Q1 SQL execution on West prepaid churn."""
    sql = """
    SELECT s.plan, COUNT(DISTINCT c.customer_id) AS customer_loss
    FROM churn_events c
    JOIN subscriber_profile s ON c.customer_id = s.customer_id
    WHERE s.region = 'West'
      AND s.plan IN ('FlexMax 199', 'FlexMax 299', 'DataPlus 249', 'SmartTalk 199')
      AND c.churn_date >= '2026-08-01' AND c.churn_date <= '2026-08-31'
    GROUP BY s.plan
    ORDER BY customer_loss DESC;
    """
    res = executor.execute(sql)
    assert res.success is True
    assert res.row_count > 0
    assert "FlexMax 199" in str(res.rows)


def test_q2_sql_execution(executor):
    """Verifies Q2 SQL execution on Ramadan campaign YoY."""
    sql = """
    SELECT s.region, SUBSTR(c.campaign_date, 1, 4) AS campaign_year,
           COUNT(*) AS total_exposures,
           COUNT(CASE WHEN c.response = 'Responded' THEN 1 END) AS responses
    FROM campaign_response c
    JOIN subscriber_profile s ON c.customer_id = s.customer_id
    WHERE c.campaign_name = 'Ramadan Data Bundle'
    GROUP BY s.region, campaign_year
    ORDER BY s.region, campaign_year;
    """
    res = executor.execute(sql)
    assert res.success is True
    assert res.row_count == 10  # 5 regions * 2 years


def test_q3_sql_execution(executor):
    """Verifies Q3 SQL execution on Small Business postpaid >30% usage drop."""
    sql = """
    WITH period_usage AS (
        SELECT u.customer_id,
               AVG(CASE WHEN u.usage_date >= '2026-08-02' AND u.usage_date <= '2026-08-31' THEN u.data_mb END) AS recent_avg_data,
               AVG(CASE WHEN u.usage_date >= '2026-07-03' AND u.usage_date <= '2026-08-01' THEN u.data_mb END) AS prior_avg_data
        FROM usage_daily u
        WHERE u.usage_date >= '2026-07-03' AND u.usage_date <= '2026-08-31'
        GROUP BY u.customer_id
    )
    SELECT s.customer_id, s.plan, s.region,
           ROUND(p.prior_avg_data, 2) AS prior_30d_avg_mb,
           ROUND(p.recent_avg_data, 2) AS recent_30d_avg_mb,
           ROUND((p.prior_avg_data - p.recent_avg_data) * 100.0 / p.prior_avg_data, 2) AS usage_drop_pct
    FROM period_usage p
    JOIN subscriber_profile s ON p.customer_id = s.customer_id
    WHERE s.customer_type = 'Small Business'
      AND s.plan IN ('UltraData 399', 'BusinessPro 599')
      AND p.prior_avg_data > 0
      AND ((p.prior_avg_data - p.recent_avg_data) * 100.0 / p.prior_avg_data) > 30.0
    ORDER BY usage_drop_pct DESC;
    """
    res = executor.execute(sql)
    assert res.success is True
    assert res.row_count >= 100, f"Expected >= 100 declining customers, got {res.row_count}"


def test_q4_sql_execution(executor):
    """Verifies Q4 SQL execution on Q3 early customer loss by channel."""
    sql = """
    SELECT c.churn_channel, COUNT(DISTINCT c.customer_id) AS early_churn_count
    FROM churn_events c
    JOIN subscriber_profile s ON c.customer_id = s.customer_id
    WHERE s.tenure_months <= 6 AND c.churn_date >= '2026-06-01'
    GROUP BY c.churn_channel
    ORDER BY early_churn_count DESC;
    """
    res = executor.execute(sql)
    assert res.success is True
    assert res.row_count > 0
    assert res.rows[0][0] == "Digital"


def test_empty_result_audit():
    """Verifies result validator flags empty results properly."""
    validator = ResultValidator()
    audit = validator.validate(columns=["plan", "loss"], rows=[])
    assert audit.stats["empty_result"] is True
    assert len(audit.warnings) > 0


def test_confidence_scorer_classification():
    """Verifies confidence scorer assigns HIGH when all criteria met."""
    scorer = ConfidenceScorer()
    dummy_pkg = GroundedContextPackage("test", [{"source_type": "example"}], "", "", "", "", ["subscriber_profile"])
    dummy_val = SQLValidationResult(True, "SELECT 1;", ["subscriber_profile"], [], [])
    dummy_audit = ResultValidator().validate(["plan"], [["FlexMax 199"]])

    assessment = scorer.evaluate(
        context_package=dummy_pkg,
        sql_validation=dummy_val,
        result_audit=dummy_audit,
        ambiguity_detected=False,
        clarification_needed=False,
        assumptions=[],
    )
    assert assessment.level == "HIGH"
    assert assessment.score >= 0.80


def test_fastapi_system_and_rag_status_endpoints(api_client):
    """Verifies GET /api/system-status and GET /api/rag/status endpoints."""
    res_sys = api_client.get("/api/system-status")
    assert res_sys.status_code == 200
    data_sys = res_sys.json()
    assert "database_connected" in data_sys
    assert data_sys["database_connected"] is True
    assert "vector_store_ready" in data_sys
    assert data_sys["vector_store_ready"] is True

    res_rag = api_client.get("/api/rag/status")
    assert res_rag.status_code == 200
    data_rag = res_rag.json()
    assert data_rag["status"] == "ready"
    assert data_rag["document_count"] >= 45
