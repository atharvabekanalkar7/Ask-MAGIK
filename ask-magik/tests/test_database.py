"""
Database & API Infrastructure Tests
Ask MAGIK - Phase 1 Foundation
"""

import pytest
from sqlalchemy import inspect, text
from fastapi.testclient import TestClient
from backend.database.connection import engine, SessionLocal
from backend.main import app


@pytest.fixture(scope="module")
def db_session():
    """Provides a database session for test execution."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def api_client():
    """Provides a TestClient for FastAPI endpoints."""
    with TestClient(app) as client:
        yield client


def test_database_connection():
    """Verifies that the SQLAlchemy engine connects and executes basic SQL."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1


def test_all_five_tables_exist():
    """Verifies all five required tables are present in the database."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    expected_tables = {
        "subscriber_profile",
        "usage_daily",
        "campaign_response",
        "revenue_monthly",
        "churn_events",
    }
    assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"


def test_table_row_counts_exist(db_session):
    """Verifies that all tables contain populated data from the seed script."""
    expected_counts = {
        "subscriber_profile": 10000,
        "usage_daily": 800000,        # ~900k-1M
        "campaign_response": 50000,    # ~100k
        "revenue_monthly": 50000,      # ~78k
        "churn_events": 500,           # ~1.2k
    }

    with engine.connect() as conn:
        for table, min_count in expected_counts.items():
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            assert count >= min_count, f"Table {table} has {count} rows, expected at least {min_count}"


def test_fastapi_health_endpoint(api_client):
    """Verifies GET /health returns expected response body and 200 OK."""
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "Ask MAGIK"
    assert data["phase"] in (1, 2)
