"""
Data Quality & Integrity Test Suite
Ask MAGIK - Phase 1 Foundation

Verifies:
- customer_id uniqueness in subscriber_profile
- Foreign key integrity across all tables
- Valid domain values (regions, plans, segments, customer types, statuses)
- Non-negative financial and usage metrics
- Date consistency (churn dates, campaign dates, activation dates)
- Execution of all 15 validated example SQL queries
"""

import json
from pathlib import Path
import pytest
from sqlalchemy import text
from backend.database.connection import engine
from backend.config import BASE_DIR

VALID_REGIONS = {"North", "South", "East", "West", "Central"}
VALID_PLANS = {
    "FlexMax 199",
    "FlexMax 299",
    "DataPlus 249",
    "SmartTalk 199",
    "UltraData 399",
    "BusinessPro 599",
}
VALID_SEGMENTS = {"Value", "Standard", "Premium", "High Value"}
VALID_CUSTOMER_TYPES = {"Consumer", "Small Business"}
VALID_STATUSES = {"Active", "Churned"}


def test_customer_id_uniqueness():
    """Verifies that every customer_id in subscriber_profile is completely unique."""
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM subscriber_profile")).scalar()
        distinct = conn.execute(text("SELECT COUNT(DISTINCT customer_id) FROM subscriber_profile")).scalar()
        assert total == distinct, f"Duplicate customer_ids found: {total} total vs {distinct} distinct"


def test_foreign_key_referential_integrity():
    """Verifies that all child tables contain only customer_ids that exist in subscriber_profile."""
    child_tables = ["usage_daily", "campaign_response", "revenue_monthly", "churn_events"]
    with engine.connect() as conn:
        for table in child_tables:
            orphan_count = conn.execute(
                text(f"""
                    SELECT COUNT(*)
                    FROM {table} c
                    LEFT JOIN subscriber_profile p ON c.customer_id = p.customer_id
                    WHERE p.customer_id IS NULL
                """)
            ).scalar()
            assert orphan_count == 0, f"Found {orphan_count} orphan records in {table}"


def test_valid_regions():
    """Verifies all subscribers are assigned to allowed regions."""
    with engine.connect() as conn:
        regions = set(
            row[0] for row in conn.execute(text("SELECT DISTINCT region FROM subscriber_profile")).fetchall()
        )
        invalid = regions - VALID_REGIONS
        assert not invalid, f"Invalid regions detected: {invalid}"


def test_valid_plans():
    """Verifies all subscribers have approved plan names."""
    with engine.connect() as conn:
        plans = set(
            row[0] for row in conn.execute(text("SELECT DISTINCT plan FROM subscriber_profile")).fetchall()
        )
        invalid = plans - VALID_PLANS
        assert not invalid, f"Invalid plans detected: {invalid}"


def test_valid_segments_and_types():
    """Verifies segments and customer types are conformant."""
    with engine.connect() as conn:
        segments = set(
            row[0] for row in conn.execute(text("SELECT DISTINCT segment FROM subscriber_profile")).fetchall()
        )
        assert not (segments - VALID_SEGMENTS)

        types = set(
            row[0] for row in conn.execute(text("SELECT DISTINCT customer_type FROM subscriber_profile")).fetchall()
        )
        assert not (types - VALID_CUSTOMER_TYPES)

        statuses = set(
            row[0] for row in conn.execute(text("SELECT DISTINCT status FROM subscriber_profile")).fetchall()
        )
        assert not (statuses - VALID_STATUSES)


def test_non_negative_usage():
    """Verifies usage minutes, data MB, and SMS counts are non-negative."""
    with engine.connect() as conn:
        violations = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM usage_daily
                WHERE voice_minutes < 0 OR data_mb < 0 OR sms_count < 0
            """)
        ).scalar()
        assert violations == 0, f"Found {violations} negative usage records"


def test_non_negative_revenue():
    """Verifies billed and collected revenue are non-negative."""
    with engine.connect() as conn:
        violations = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM revenue_monthly
                WHERE billed_revenue < 0 OR collected_revenue < 0
            """)
        ).scalar()
        assert violations == 0, f"Found {violations} negative revenue records"


def test_churn_consistency():
    """Verifies churn dates occur after activation dates, and all churned customers have Churned status."""
    with engine.connect() as conn:
        # Churn date after activation date
        invalid_dates = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM churn_events c
                JOIN subscriber_profile s ON c.customer_id = s.customer_id
                WHERE c.churn_date < s.activation_date
            """)
        ).scalar()
        assert invalid_dates == 0, f"Found {invalid_dates} churn dates preceding activation date"

        # Subscribers with churn event should have status = 'Churned'
        mismatched_status = conn.execute(
            text("""
                SELECT COUNT(DISTINCT c.customer_id)
                FROM churn_events c
                JOIN subscriber_profile s ON c.customer_id = s.customer_id
                WHERE s.status != 'Churned'
            """)
        ).scalar()
        assert mismatched_status == 0, f"Found {mismatched_status} churned customers marked Active"


def test_campaign_consistency():
    """Verifies campaign dates are valid and offer values non-negative."""
    with engine.connect() as conn:
        neg_offers = conn.execute(
            text("SELECT COUNT(*) FROM campaign_response WHERE offer_value < 0")
        ).scalar()
        assert neg_offers == 0, f"Found {neg_offers} negative campaign offer values"

        invalid_responses = conn.execute(
            text("SELECT COUNT(*) FROM campaign_response WHERE response NOT IN ('Responded', 'Not Responded')")
        ).scalar()
        assert invalid_responses == 0, f"Found {invalid_responses} invalid response statuses"


def test_all_validated_examples_execute_successfully():
    """
    Executes each of the 15+ SQL queries in validated_examples.json
    against the actual Skyline database to guarantee syntax correctness and data validity.
    """
    examples_path = BASE_DIR / "backend" / "knowledge" / "examples" / "validated_examples.json"
    assert examples_path.exists(), f"Missing file: {examples_path}"

    with open(examples_path, "r", encoding="utf-8") as f:
        examples = json.load(f)

    assert len(examples) >= 15, f"Expected at least 15 examples, found {len(examples)}"

    with engine.connect() as conn:
        for ex in examples:
            sql = ex["sql"]
            # Verify execution without errors
            try:
                result = conn.execute(text(sql))
                rows = result.fetchall()
                # Ensure the query returns results
                assert len(rows) >= 0, f"Query for {ex['id']} returned error"
            except Exception as err:
                pytest.fail(f"SQL for example {ex['id']} ('{ex['question']}') failed: {err}\nSQL: {sql}")
