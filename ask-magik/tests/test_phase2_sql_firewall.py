"""
Phase 2 Tests: SQL Firewall & Execution Security
"""

import pytest
from backend.services.sql_validator import SQLFirewall
from backend.services.query_executor import SafeQueryExecutor


@pytest.fixture(scope="module")
def firewall():
    return SQLFirewall()


@pytest.fixture(scope="module")
def executor():
    return SafeQueryExecutor()


def test_select_query_accepted(firewall):
    """Verifies valid SELECT queries pass the firewall."""
    sql = "SELECT customer_id, plan, region FROM subscriber_profile WHERE region = 'West';"
    res = firewall.validate_and_sanitize(sql)
    assert res.is_valid is True
    assert "subscriber_profile" in res.tables_used
    assert len(res.errors) == 0


def test_delete_rejected(firewall):
    """Verifies DELETE statements are rejected."""
    sql = "DELETE FROM subscriber_profile WHERE customer_id = 'CUST-00001';"
    res = firewall.validate_and_sanitize(sql)
    assert res.is_valid is False
    assert any("DELETE" in err for err in res.errors)


def test_update_rejected(firewall):
    """Verifies UPDATE statements are rejected."""
    sql = "UPDATE subscriber_profile SET status = 'Active' WHERE customer_id = 'CUST-00001';"
    res = firewall.validate_and_sanitize(sql)
    assert res.is_valid is False
    assert any("UPDATE" in err for err in res.errors)


def test_drop_rejected(firewall):
    """Verifies DROP TABLE statements are rejected."""
    sql = "DROP TABLE churn_events;"
    res = firewall.validate_and_sanitize(sql)
    assert res.is_valid is False
    assert any("DROP" in err for err in res.errors)


def test_multiple_statements_rejected(firewall):
    """Verifies multi-statement injection is blocked."""
    sql = "SELECT * FROM subscriber_profile; DROP TABLE subscriber_profile;"
    res = firewall.validate_and_sanitize(sql)
    assert res.is_valid is False
    assert any("Multiple SQL statements" in err for err in res.errors)


def test_invalid_table_rejected(firewall):
    """Verifies queries targeting unapproved tables are rejected."""
    sql = "SELECT * FROM secret_passwords WHERE id = 1;"
    res = firewall.validate_and_sanitize(sql)
    assert res.is_valid is False
    assert any("Disallowed or unknown tables" in err for err in res.errors)


def test_safe_limit_applied(firewall):
    """Verifies unbounded raw SELECT queries get a safe LIMIT injected."""
    sql = "SELECT customer_id FROM subscriber_profile;"
    res = firewall.validate_and_sanitize(sql)
    assert res.is_valid is True
    assert "LIMIT" in res.sanitized_sql


def test_executor_blocks_mutation(executor):
    """Verifies query executor refuses to run mutating queries."""
    res = executor.execute("DELETE FROM churn_events WHERE churn_event_id = 1;")
    assert res.success is False
    assert "rejected by SQL Firewall" in res.error_message
