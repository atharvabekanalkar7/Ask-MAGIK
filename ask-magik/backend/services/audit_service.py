"""
Query Audit & History Service
Ask MAGIK - Enterprise Governance Layer

Tracks:
1. Query History: User questions, generated SQL, execution metrics, and results.
2. Governed Audit Trail: Security checks, firewall approvals/rejections, timestamps, and confidence.
3. Saved Insights: Bookmarked findings with executive summaries and chart payloads.
"""

import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime


class AuditService:
    """Manages in-memory and persistent query history, audit trails, and bookmarks."""

    def __init__(self):
        self._history: List[Dict[str, Any]] = []
        self._audit_logs: List[Dict[str, Any]] = []
        self._saved_insights: List[Dict[str, Any]] = []

        # Seed initial saved insights for Skyline Telecom pilot presentation
        self._seed_initial_data()

    def _seed_initial_data(self):
        """Pre-populates demonstration insights and audit entries."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self._saved_insights.append({
            "id": "insight-001",
            "title": "Western Prepaid Churn Concentration",
            "question": "Which prepaid plans had the highest customer loss in the western region last month?",
            "key_insight": "FlexMax 199 accounts for the highest customer loss (58 churned subscribers) in the Western region.",
            "supporting_figures": [
                "FlexMax 199: 58 customer loss",
                "FlexMax 299: 46 customer loss",
                "DataPlus 249: 39 customer loss",
                "SmartTalk 199: 35 customer loss"
            ],
            "sql": "SELECT s.plan, COUNT(DISTINCT c.customer_id) AS customer_loss\nFROM churn_events c\nJOIN subscriber_profile s ON c.customer_id = s.customer_id\nWHERE s.region = 'West'\n  AND s.plan IN ('FlexMax 199', 'FlexMax 299', 'DataPlus 249', 'SmartTalk 199')\n  AND c.churn_date >= '2026-08-01' AND c.churn_date <= '2026-08-31'\nGROUP BY s.plan\nORDER BY customer_loss DESC;",
            "confidence": "HIGH",
            "saved_at": now,
        })

        self._saved_insights.append({
            "id": "insight-002",
            "title": "Ramadan Campaign YoY Regional Surge",
            "question": "How did the Ramadan campaign perform year-over-year by region?",
            "key_insight": "Ramadan Data Bundle response surged 18.4% YoY across all 5 regions, with North region leading in absolute responses.",
            "supporting_figures": [
                "Total Exposures 2026: 24,800",
                "Total Responses 2026: 3,120",
                "Response Rate: ~12.6% (vs 10.6% in 2025)",
                "North Region Responses: 820"
            ],
            "sql": "SELECT s.region, SUBSTR(c.campaign_date, 1, 4) AS campaign_year,\n       COUNT(*) AS total_exposures,\n       COUNT(CASE WHEN c.response = 'Responded' THEN 1 END) AS responses\nFROM campaign_response c\nJOIN subscriber_profile s ON c.customer_id = s.customer_id\nWHERE c.campaign_name = 'Ramadan Data Bundle'\nGROUP BY s.region, campaign_year\nORDER BY s.region, campaign_year;",
            "confidence": "HIGH",
            "saved_at": now,
        })

        # Seed recent audit events
        self._audit_logs.append({
            "audit_id": "aud-001",
            "timestamp": now,
            "user": "analyst.central@skyline.telecom",
            "client_ip": "127.0.0.1",
            "action": "QUERY_EXECUTION",
            "firewall_decision": "ALLOWED",
            "read_only_verified": True,
            "tables_accessed": ["subscriber_profile", "churn_events"],
            "execution_ms": 28.4,
            "row_count": 4,
            "confidence": "HIGH"
        })
        self._audit_logs.append({
            "audit_id": "aud-002",
            "timestamp": now,
            "user": "analyst.commercial@skyline.telecom",
            "client_ip": "127.0.0.1",
            "action": "QUERY_EXECUTION",
            "firewall_decision": "ALLOWED",
            "read_only_verified": True,
            "tables_accessed": ["subscriber_profile", "campaign_response"],
            "execution_ms": 42.1,
            "row_count": 10,
            "confidence": "HIGH"
        })

    def record_query(
        self,
        question: str,
        sql: str,
        confidence: str,
        execution_time_ms: float,
        row_count: int,
        tables_used: List[str],
        firewall_passed: bool,
        client_ip: str = "127.0.0.1",
        key_insight: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Records an executed query in history and audit trail."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query_id = f"qry-{uuid.uuid4().hex[:8]}"
        audit_id = f"aud-{uuid.uuid4().hex[:8]}"

        history_entry = {
            "id": query_id,
            "timestamp": timestamp,
            "question": question,
            "sql": sql,
            "confidence": confidence,
            "execution_time_ms": execution_time_ms,
            "row_count": row_count,
            "tables_used": tables_used,
            "firewall_passed": firewall_passed,
            "key_insight": key_insight,
        }
        self._history.insert(0, history_entry)

        audit_entry = {
            "audit_id": audit_id,
            "timestamp": timestamp,
            "user": "central_analyst@skyline.telecom",
            "client_ip": client_ip,
            "action": "QUERY_EXECUTION",
            "firewall_decision": "ALLOWED" if firewall_passed else "REJECTED",
            "read_only_verified": firewall_passed,
            "tables_accessed": tables_used,
            "execution_ms": execution_time_ms,
            "row_count": row_count,
            "confidence": confidence,
        }
        self._audit_logs.insert(0, audit_entry)

        # Cap memory buffer
        if len(self._history) > 200:
            self._history.pop()
        if len(self._audit_logs) > 300:
            self._audit_logs.pop()

        return history_entry

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns query history."""
        return self._history[:limit]

    def get_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns governed audit trail."""
        return self._audit_logs[:limit]

    def save_insight(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Saves or bookmarks an analytical insight."""
        insight_id = payload.get("id") or f"insight-{uuid.uuid4().hex[:6]}"
        entry = {
            "id": insight_id,
            "title": payload.get("title") or payload.get("question", "Saved Insight")[:60],
            "question": payload.get("question", ""),
            "key_insight": payload.get("key_insight", ""),
            "supporting_figures": payload.get("supporting_figures", []),
            "sql": payload.get("sql", ""),
            "confidence": payload.get("confidence", "HIGH"),
            "chart": payload.get("chart", {}),
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._saved_insights.insert(0, entry)
        return entry

    def get_saved_insights(self) -> List[Dict[str, Any]]:
        """Returns all bookmarked insights."""
        return self._saved_insights

    def delete_saved_insight(self, insight_id: str) -> bool:
        """Deletes a saved insight by ID."""
        initial_len = len(self._saved_insights)
        self._saved_insights = [i for i in self._saved_insights if i["id"] != insight_id]
        return len(self._saved_insights) < initial_len


# Global singleton instance
audit_service = AuditService()
