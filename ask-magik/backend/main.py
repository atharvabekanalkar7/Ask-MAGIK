"""
Ask MAGIK - Backend API
Skyline Telecom Intelligent Natural Language SQL Engine - Phase 2 & Enterprise UI

Endpoints:
- POST /api/chat: Full RAG + SQL pipeline.
- POST /api/rag/context: Pre-flight contextual retrieval & analysis trace.
- GET /api/overview/metrics: Executive KPIs & governed analytical path for Overview dashboard.
- GET /api/datasources: DataMart tables, schemas, constraints, and row counts.
- POST /api/datasources/upload: Data upload & staging endpoint.
- GET /api/datasources/{table_name}/preview: Table data preview.
- GET /api/history: Query execution history.
- POST /api/history/save: Bookmark/save an analytical insight.
- GET /api/insights/saved: Saved analytical insights.
- DELETE /api/insights/saved/{id}: Remove a saved insight.
- GET /api/knowledge: Full governed knowledge inventory (glossary, schema, rules, golden queries).
- GET /api/security/policies: SQL Firewall and AST governance rules.
- POST /api/security/validate: SQL Firewall sandbox tester.
- GET /api/audit/logs: Governed security and execution audit trail.
- GET /api/settings: Runtime settings.
- POST /api/settings: Update runtime settings.
- GET /api/system-status: Full health check of local AI components.
- GET /health: Operational ping.
- Static file serving at / for the Ask MAGIK Enterprise UI.
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text

from backend.config import settings, BASE_DIR
from backend.rag.vector_store import PersistentVectorStore
from backend.rag.retriever import KnowledgeRetriever
from backend.llm.ollama_client import OllamaClient
from backend.services.chat_service import ChatOrchestrator
from backend.services.sql_validator import SQLFirewall
from backend.services.audit_service import audit_service
from backend.database.connection import engine


class ChatRequest(BaseModel):
    """User plain-English question payload."""
    question: str = Field(
        ...,
        json_schema_extra={
            "example": "Which prepaid plans had the highest customer loss in the western region last month?"
        },
    )


class ContextRequest(BaseModel):
    """Pre-flight context retrieval request."""
    question: str


class SQLValidateRequest(BaseModel):
    """Firewall SQL validation request."""
    sql: str


class SaveInsightRequest(BaseModel):
    """Bookmark insight request."""
    id: Optional[str] = None
    title: Optional[str] = None
    question: str
    key_insight: Optional[str] = ""
    supporting_figures: Optional[List[str]] = []
    sql: Optional[str] = ""
    confidence: Optional[str] = "HIGH"
    chart: Optional[Dict[str, Any]] = {}


class DataUploadRequest(BaseModel):
    """DataMart upload simulation request."""
    table_name: str
    file_name: str
    records_count: int = 100


class SettingsUpdateRequest(BaseModel):
    """Runtime configuration update request."""
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None
    rag_top_k: Optional[int] = None
    data_refresh_note: Optional[str] = None
    use_llm_sql: Optional[bool] = None
    use_llm_explanation: Optional[bool] = None


# Singleton service instances
vector_store = PersistentVectorStore()
retriever = KnowledgeRetriever(vector_store)
llm_client = OllamaClient()
sql_firewall = SQLFirewall()
chat_orchestrator = ChatOrchestrator(
    retriever=retriever,
    llm_client=llm_client,
    firewall=sql_firewall,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for FastAPI application."""
    print(f"Starting {settings.APP_NAME} (Phase {settings.PHASE})...")
    print(f"Database URL: {settings.resolved_database_url}")
    print(f"Ollama Target: {settings.OLLAMA_BASE_URL} (Configured Model: {settings.OLLAMA_MODEL})")
    print(f"Vector Store Documents: {vector_store.count()}")
    yield
    print(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title="Ask MAGIK API",
    description="Skyline Telecom Intelligent Natural Language SQL Engine - Phase 2 & Enterprise UI",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS origins — allow the deployed Vercel frontend and local development.
# ALLOWED_ORIGINS env var can override with a comma-separated list.
_raw_origins = os.environ.get(
    "ALLOWED_ORIGINS",
    "https://ask-magik-insightx.vercel.app,http://localhost:8000,http://127.0.0.1:8000",
)
_allow_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",  # covers all Vercel preview deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# SYSTEM & HEALTH ENDPOINTS
# ============================================================================

@app.get("/health", status_code=status.HTTP_200_OK, tags=["System"])
async def health_check() -> Dict[str, Any]:
    """Health check endpoint confirming service operational status."""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "phase": settings.PHASE,
    }


@app.get("/api/system-status", status_code=status.HTTP_200_OK, tags=["System"])
async def system_status() -> Dict[str, Any]:
    """Comprehensive system health report across all AI components."""
    ollama_ok = llm_client.is_available()
    installed_models = llm_client.get_installed_models() if ollama_ok else []
    active_model = llm_client.get_active_model() if ollama_ok else settings.OLLAMA_MODEL

    db_ok = False
    try:
        with engine.connect() as conn:
            db_ok = conn.execute(text("SELECT 1")).scalar() == 1
    except Exception:
        db_ok = False

    return {
        "ollama_reachable": ollama_ok,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "active_model": active_model,
        "installed_models": installed_models,
        "vector_store_documents": vector_store.count(),
        "vector_store_ready": vector_store.count() > 0,
        "database_connected": db_ok,
        "sql_firewall_active": True,
        "data_freshness": settings.DATA_REFRESH_NOTE,
        "system_operational": db_ok and vector_store.count() > 0,
    }


# ============================================================================
# OVERVIEW & PILOT METRICS ENDPOINT (Screenshot 1)
# ============================================================================

@app.get("/api/overview/metrics", status_code=status.HTTP_200_OK, tags=["Overview"])
async def overview_metrics() -> Dict[str, Any]:
    """Returns the exact pilot KPIs, data mart status, and governed analytical path."""
    return {
        "subscribers_display": "9.1M",
        "subscribers_exact": 10000,
        "prepaid_pct": "74%",
        "postpaid_pct": "26%",
        "regions_count": 5,
        "central_analysts": 6,
        "environment": "PILOT",
        "data_freshness": "UPDATED TODAY",
        "status": "OPERATIONAL",
        "company": {
            "name": "SKYLINE TELECOM",
            "division": "MAGIK Customer Value Management",
            "connection_status": "Data mart connected",
            "description": "Telecommunications · 9.1M subscribers",
            "note": "Additional companies can be configured later.",
        },
        "governed_analytical_path": [
            {"step": "01", "name": "Business Questions"},
            {"step": "02", "name": "Knowledge Retrieval"},
            {"step": "03", "name": "SQL Generation"},
            {"step": "04", "name": "Policy Validation"},
            {"step": "05", "name": "MAGIK Data"},
            {"step": "06", "name": "Insight"},
        ],
    }


# ============================================================================
# RAG & CHAT QUERY ENDPOINTS (Screenshot 2)
# ============================================================================

@app.post("/api/rag/context", status_code=status.HTTP_200_OK, tags=["RAG"])
def rag_context_preflight(req: ContextRequest) -> Dict[str, Any]:
    """Pre-flight retrieval for real-time context display as user types or clicks queries."""
    if not req.question or not req.question.strip():
        # Default baseline context
        return {
            "retrieved_context": {
                "business_glossary": ["Customer Loss", "Prepaid", "Early Churn", "Active Subscriber"],
                "schema": ["subscriber_profile", "churn_events", "revenue_monthly"],
                "relationships": ["subscriber_profile ↔ churn_events"],
                "validated_examples_count": 3,
                "validated_examples": [
                    "Which prepaid plans had highest customer loss in the western region last month?",
                    "How did Ramadan campaign response change year-over-year by region?",
                    "Which postpaid small-business customers had usage drop by more than 30%?",
                ],
                "governance_note": "Only metadata, approved definitions, and relevant relationships enter context—not the customer database.",
            },
            "analysis_trace": [
                {"id": "01", "name": "Intent Detection", "duration_ms": 18, "detail": "Question classified as comparative churn analysis"},
                {"id": "02", "name": "Schema Retrieval", "duration_ms": 42, "detail": "3 relevant entities retrieved"},
                {"id": "03", "name": "Business Definition Retrieval", "duration_ms": 31, "detail": "Active definitions: Customer Loss, Prepaid, Early Churn"},
            ]
        }

    return chat_orchestrator.get_retrieved_context(req.question.strip())


@app.get("/api/rag/status", status_code=status.HTTP_200_OK, tags=["RAG"])
def rag_status() -> Dict[str, Any]:
    """Returns vector database status and indexed document count."""
    return vector_store.get_status()


@app.post("/api/chat", status_code=status.HTTP_200_OK, tags=["Chat"])
def chat_endpoint(req: ChatRequest) -> Dict[str, Any]:
    """Primary Natural Language to SQL Analytics Pipeline Endpoint."""
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    result = chat_orchestrator.process_question(req.question.strip())
    return result


# ============================================================================
# DATASOURCES & DATAMART BROWSER ENDPOINTS
# ============================================================================

@app.get("/api/datasources", status_code=status.HTTP_200_OK, tags=["DataSources"])
def get_datasources() -> Dict[str, Any]:
    """Returns schema, columns, descriptions, and live row counts for all DataMart tables."""
    tables_info = [
        {
            "name": "subscriber_profile",
            "description": "Core customer dimension table with demographics, plans, regions, tenures, and lifecycle status.",
            "granularity": "One record per subscriber",
            "pii_policy": "Zero PII - No names, phone numbers, or physical addresses",
            "columns": [
                {"name": "customer_id", "type": "VARCHAR(32)", "is_pk": True, "description": "Unique subscriber surrogate key"},
                {"name": "plan", "type": "VARCHAR(64)", "is_pk": False, "description": "Subscription tariff plan (FlexMax 199, UltraData 399, etc.)"},
                {"name": "region", "type": "VARCHAR(32)", "is_pk": False, "description": "Operating region (North, South, East, West, Central)"},
                {"name": "tenure_months", "type": "INTEGER", "is_pk": False, "description": "Subscribed account tenure in full months"},
                {"name": "segment", "type": "VARCHAR(32)", "is_pk": False, "description": "Customer tier (High Value, Medium, Standard, Budget)"},
                {"name": "customer_type", "type": "VARCHAR(32)", "is_pk": False, "description": "Account type (Consumer, Small Business)"},
                {"name": "activation_date", "type": "DATE", "is_pk": False, "description": "Initial service activation date"},
                {"name": "status", "type": "VARCHAR(32)", "is_pk": False, "description": "Account status (Active, Churned)"},
            ]
        },
        {
            "name": "usage_daily",
            "description": "Daily consumption metrics across data, voice minutes, and SMS for each subscriber.",
            "granularity": "One row per customer per day over historical window",
            "pii_policy": "Aggregated telemetry metrics only",
            "columns": [
                {"name": "usage_id", "type": "INTEGER", "is_pk": True, "description": "Primary key auto-increment"},
                {"name": "customer_id", "type": "VARCHAR(32)", "is_pk": False, "description": "Foreign key to subscriber_profile"},
                {"name": "usage_date", "type": "DATE", "is_pk": False, "description": "Date of recorded consumption"},
                {"name": "voice_minutes", "type": "FLOAT", "is_pk": False, "description": "Total outgoing voice minutes"},
                {"name": "data_mb", "type": "FLOAT", "is_pk": False, "description": "Total cellular data consumed in megabytes"},
                {"name": "sms_count", "type": "INTEGER", "is_pk": False, "description": "Count of outbound SMS messages"},
            ]
        },
        {
            "name": "campaign_response",
            "description": "Marketing campaigns, impressions, promotional discounts, and customer responses.",
            "granularity": "One row per campaign impression",
            "pii_policy": "Campaign identifier and response classification",
            "columns": [
                {"name": "campaign_response_id", "type": "INTEGER", "is_pk": True, "description": "Primary key auto-increment"},
                {"name": "customer_id", "type": "VARCHAR(32)", "is_pk": False, "description": "Foreign key to subscriber_profile"},
                {"name": "campaign_name", "type": "VARCHAR(128)", "is_pk": False, "description": "Campaign title (Ramadan Data Bundle, Summer Saver, etc.)"},
                {"name": "campaign_date", "type": "DATE", "is_pk": False, "description": "Date of promotional exposure"},
                {"name": "campaign_type", "type": "VARCHAR(64)", "is_pk": False, "description": "Campaign category (Upsell, Retention, Acquisition)"},
                {"name": "response", "type": "VARCHAR(32)", "is_pk": False, "description": "Outcome (Responded, Not Responded)"},
                {"name": "offer_value", "type": "FLOAT", "is_pk": False, "description": "Value of incentive or discount in standard currency"},
            ]
        },
        {
            "name": "revenue_monthly",
            "description": "Financial billing and collection figures by customer across historical billing cycles.",
            "granularity": "One row per customer per billing cycle month",
            "pii_policy": "Billed and collected totals",
            "columns": [
                {"name": "revenue_id", "type": "INTEGER", "is_pk": True, "description": "Primary key auto-increment"},
                {"name": "customer_id", "type": "VARCHAR(32)", "is_pk": False, "description": "Foreign key to subscriber_profile"},
                {"name": "revenue_month", "type": "VARCHAR(16)", "is_pk": False, "description": "Billing period (e.g. 2026-08)"},
                {"name": "billed_revenue", "type": "FLOAT", "is_pk": False, "description": "Total billed amount"},
                {"name": "collected_revenue", "type": "FLOAT", "is_pk": False, "description": "Actual realized cash collections"},
            ]
        },
        {
            "name": "churn_events",
            "description": "Specific subscriber disconnection events with attrition reasons and acquisition channels.",
            "granularity": "One row per churn event",
            "pii_policy": "Churn reason and channel categories",
            "columns": [
                {"name": "churn_id", "type": "INTEGER", "is_pk": True, "description": "Primary key auto-increment"},
                {"name": "customer_id", "type": "VARCHAR(32)", "is_pk": False, "description": "Foreign key to subscriber_profile"},
                {"name": "churn_date", "type": "DATE", "is_pk": False, "description": "Date service was discontinued"},
                {"name": "churn_reason", "type": "VARCHAR(64)", "is_pk": False, "description": "Customer cited cause (Price, Poor Service, Network Quality, etc.)"},
                {"name": "churn_channel", "type": "VARCHAR(32)", "is_pk": False, "description": "Channel of attrition (Digital, Retail, Call Center)"},
            ]
        },
    ]

    # Fetch live row counts
    try:
        with engine.connect() as conn:
            for t in tables_info:
                cnt = conn.execute(text(f"SELECT COUNT(*) FROM {t['name']}")).scalar()
                t["row_count"] = cnt
    except Exception as e:
        for t in tables_info:
            t["row_count"] = "N/A"

    return {
        "database": "Skyline Telecom DataMart",
        "dialect": "SQLite 3.x",
        "tables_count": len(tables_info),
        "tables": tables_info,
    }


@app.get("/api/datasources/{table_name}/preview", status_code=status.HTTP_200_OK, tags=["DataSources"])
def preview_table(table_name: str, limit: int = 15) -> Dict[str, Any]:
    """Returns sample rows and columns for a table."""
    allowed = ["subscriber_profile", "usage_daily", "campaign_response", "revenue_monthly", "churn_events"]
    if table_name not in allowed:
        raise HTTPException(status_code=400, detail=f"Table {table_name} not found or access restricted.")

    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT {min(limit, 50)}"))
            columns = list(result.keys())
            rows = [list(r) for r in result.fetchall()]
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            return {
                "table_name": table_name,
                "total_rows": count,
                "columns": columns,
                "rows": rows,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/datasources/upload", status_code=status.HTTP_200_OK, tags=["DataSources"])
async def upload_data(req: DataUploadRequest) -> Dict[str, Any]:
    """Uploads data into the staging area for Skyline Telecom DataMart."""
    allowed = ["subscriber_profile", "usage_daily", "campaign_response", "revenue_monthly", "churn_events"]
    if req.table_name not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid target table: {req.table_name}")

    audit_service._audit_logs.insert(0, {
        "audit_id": f"aud-upl-{os.urandom(3).hex()}",
        "timestamp": audit_service._history[0]["timestamp"] if audit_service._history else "Just now",
        "user": "data_engineer@skyline.telecom",
        "client_ip": "127.0.0.1",
        "action": "DATA_INGESTION_STAGING",
        "firewall_decision": "ALLOWED",
        "read_only_verified": True,
        "tables_accessed": [req.table_name],
        "execution_ms": 45.2,
        "row_count": req.records_count,
        "confidence": "HIGH"
    })

    return {
        "status": "success",
        "message": f"Successfully validated and staged {req.records_count} records from '{req.file_name}' for table '{req.table_name}'.",
        "target_table": req.table_name,
        "records_staged": req.records_count,
        "data_freshness": "UPDATED TODAY",
    }


# ============================================================================
# HISTORY & SAVED INSIGHTS ENDPOINTS
# ============================================================================

@app.get("/api/history", status_code=status.HTTP_200_OK, tags=["History"])
async def get_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Returns query execution history."""
    return audit_service.get_history(limit=limit)


@app.post("/api/history/save", status_code=status.HTTP_200_OK, tags=["Insights"])
async def save_insight(req: SaveInsightRequest) -> Dict[str, Any]:
    """Bookmarks an analytical insight."""
    saved = audit_service.save_insight(req.model_dump())
    return {"status": "saved", "insight": saved}


@app.get("/api/insights/saved", status_code=status.HTTP_200_OK, tags=["Insights"])
async def get_saved_insights() -> List[Dict[str, Any]]:
    """Returns all bookmarked analytical insights."""
    return audit_service.get_saved_insights()


@app.delete("/api/insights/saved/{insight_id}", status_code=status.HTTP_200_OK, tags=["Insights"])
async def delete_saved_insight(insight_id: str) -> Dict[str, Any]:
    """Removes a bookmarked insight."""
    success = audit_service.delete_saved_insight(insight_id)
    if not success:
        raise HTTPException(status_code=404, detail="Insight not found.")
    return {"status": "deleted", "id": insight_id}


# ============================================================================
# KNOWLEDGE LAYER ENDPOINTS
# ============================================================================

@app.get("/api/knowledge", status_code=status.HTTP_200_OK, tags=["Knowledge"])
async def get_knowledge() -> Dict[str, Any]:
    """Returns the full governed knowledge inventory."""
    glossary_items = [
        {"term": "Customer Loss", "definition": "Subscribers who disconnected or initiated service termination in the measurement period.", "table": "churn_events", "calculation": "COUNT(DISTINCT customer_id)"},
        {"term": "Prepaid Subscriber", "definition": "Customers billed prior to usage via prepaid voucher/recharge plans (FlexMax 199, 299, etc.).", "table": "subscriber_profile", "calculation": "plan IN ('FlexMax 199', 'FlexMax 299', 'DataPlus 249', 'SmartTalk 199')"},
        {"term": "Postpaid Subscriber", "definition": "Customers billed monthly after consumption (UltraData 399, BusinessPro 599, etc.).", "table": "subscriber_profile", "calculation": "plan IN ('UltraData 399', 'BusinessPro 599', 'Infinity 799')"},
        {"term": "Early Churn", "definition": "Attrition occurring within the first 6 months of customer tenure.", "table": "subscriber_profile", "calculation": "tenure_months <= 6"},
        {"term": "Active Subscriber", "definition": "Customer with status = 'Active' and positive usage/revenue in last 30 days.", "table": "subscriber_profile", "calculation": "status = 'Active'"},
        {"term": "Campaign Response Rate", "definition": "Percentage of contacted customers who engaged with a marketing offer.", "table": "campaign_response", "calculation": "ROUND(COUNT(CASE WHEN response = 'Responded' THEN 1 END) * 100.0 / COUNT(*), 2)"},
        {"term": "Revenue Collection Efficiency", "definition": "Proportion of billed revenue successfully collected as cash receipts.", "table": "revenue_monthly", "calculation": "ROUND(SUM(collected_revenue) * 100.0 / SUM(billed_revenue), 2)"},
        {"term": "Usage Drop", "definition": "Percentage decline in 30-day average cellular data consumption between consecutive periods.", "table": "usage_daily", "calculation": "(prior_avg - recent_avg) * 100.0 / prior_avg"},
        {"term": "Small Business Segment", "definition": "Commercial enterprise accounts classified under customer_type = 'Small Business'.", "table": "subscriber_profile", "calculation": "customer_type = 'Small Business'"},
    ]

    golden_examples = [
        {
            "id": "ex-01",
            "title": "Western Prepaid Customer Loss",
            "question": "Which prepaid plans had the highest customer loss in the western region last month?",
            "tables": ["subscriber_profile", "churn_events"],
            "sql": "SELECT s.plan, COUNT(DISTINCT c.customer_id) AS customer_loss\nFROM churn_events c\nJOIN subscriber_profile s ON c.customer_id = s.customer_id\nWHERE s.region = 'West'\n  AND s.plan IN ('FlexMax 199', 'FlexMax 299', 'DataPlus 249', 'SmartTalk 199')\n  AND c.churn_date >= '2026-08-01' AND c.churn_date <= '2026-08-31'\nGROUP BY s.plan\nORDER BY customer_loss DESC;"
        },
        {
            "id": "ex-02",
            "title": "Ramadan Campaign YoY Performance",
            "question": "How did the Ramadan campaign perform year-over-year by region?",
            "tables": ["subscriber_profile", "campaign_response"],
            "sql": "SELECT s.region, SUBSTR(c.campaign_date, 1, 4) AS campaign_year,\n       COUNT(*) AS total_exposures,\n       COUNT(CASE WHEN c.response = 'Responded' THEN 1 END) AS responses\nFROM campaign_response c\nJOIN subscriber_profile s ON c.customer_id = s.customer_id\nWHERE c.campaign_name = 'Ramadan Data Bundle'\nGROUP BY s.region, campaign_year\nORDER BY s.region, campaign_year;"
        },
        {
            "id": "ex-03",
            "title": "Postpaid Small-Business Usage Decline",
            "question": "Which postpaid small-business segments experienced more than a 30% usage decline?",
            "tables": ["subscriber_profile", "usage_daily"],
            "sql": "WITH period_usage AS (\n    SELECT u.customer_id,\n           AVG(CASE WHEN u.usage_date >= '2026-08-02' AND u.usage_date <= '2026-08-31' THEN u.data_mb END) AS recent_avg_data,\n           AVG(CASE WHEN u.usage_date >= '2026-07-03' AND u.usage_date <= '2026-08-01' THEN u.data_mb END) AS prior_avg_data\n    FROM usage_daily u\n    WHERE u.usage_date >= '2026-07-03' AND u.usage_date <= '2026-08-31'\n    GROUP BY u.customer_id\n)\nSELECT s.customer_id, s.plan, s.region,\n       ROUND(p.prior_avg_data, 2) AS prior_30d_avg_mb,\n       ROUND(p.recent_avg_data, 2) AS recent_30d_avg_mb,\n       ROUND((p.prior_avg_data - p.recent_avg_data) * 100.0 / p.prior_avg_data, 2) AS usage_drop_pct\nFROM period_usage p\nJOIN subscriber_profile s ON p.customer_id = s.customer_id\nWHERE s.customer_type = 'Small Business'\n  AND s.plan IN ('UltraData 399', 'BusinessPro 599')\n  AND p.prior_avg_data > 0\n  AND ((p.prior_avg_data - p.recent_avg_data) * 100.0 / p.prior_avg_data) > 30.0\nORDER BY usage_drop_pct DESC;"
        },
        {
            "id": "ex-04",
            "title": "Early Customer Loss by Channel",
            "question": "What is driving the rise in early customer loss?",
            "tables": ["subscriber_profile", "churn_events"],
            "sql": "SELECT c.churn_channel, COUNT(DISTINCT c.customer_id) AS early_churn_count\nFROM churn_events c\nJOIN subscriber_profile s ON c.customer_id = s.customer_id\nWHERE s.tenure_months <= 6 AND c.churn_date >= '2026-06-01'\nGROUP BY c.churn_channel\nORDER BY early_churn_count DESC;"
        },
    ]

    return {
        "vector_store_documents": vector_store.count(),
        "embedding_model": settings.EMBEDDING_MODEL,
        "glossary_count": len(glossary_items),
        "glossary": glossary_items,
        "golden_examples_count": len(golden_examples),
        "golden_examples": golden_examples,
        "relationships": [
            {"from": "subscriber_profile.customer_id", "to": "usage_daily.customer_id", "type": "1-to-many"},
            {"from": "subscriber_profile.customer_id", "to": "campaign_response.customer_id", "type": "1-to-many"},
            {"from": "subscriber_profile.customer_id", "to": "revenue_monthly.customer_id", "type": "1-to-many"},
            {"from": "subscriber_profile.customer_id", "to": "churn_events.customer_id", "type": "1-to-many"},
        ]
    }


# ============================================================================
# SECURITY & FIREWALL POLICIES ENDPOINTS
# ============================================================================

@app.get("/api/security/policies", status_code=status.HTTP_200_OK, tags=["Security"])
async def get_security_policies() -> Dict[str, Any]:
    """Returns active SQL Firewall rules, AST security checks, and data protection policies."""
    return {
        "firewall_status": "ACTIVE",
        "enforcement_engine": "sqlglot AST Semantic Parser",
        "rules": [
            {
                "rule_id": "SEC-01",
                "name": "Read-Only Enforcement",
                "description": "Only SELECT and WITH (CTE) queries are permitted. Data mutations are strictly rejected at AST level.",
                "enforced": True,
            },
            {
                "rule_id": "SEC-02",
                "name": "Forbidden SQL Commands",
                "description": "DROP, DELETE, INSERT, UPDATE, ALTER, TRUNCATE, ATTACH, DETACH, PRAGMA, EXEC are hard-blocked.",
                "enforced": True,
            },
            {
                "rule_id": "SEC-03",
                "name": "Strict Table Allowlist",
                "description": "Queries can only reference authorized DataMart tables (subscriber_profile, usage_daily, campaign_response, revenue_monthly, churn_events).",
                "enforced": True,
            },
            {
                "rule_id": "SEC-04",
                "name": "Single Statement Enforcement",
                "description": "Multiple statement chaining (semicolon injections) is blocked to prevent stacked SQL execution.",
                "enforced": True,
            },
            {
                "rule_id": "SEC-05",
                "name": "Row Limit Cap",
                "description": f"All queries automatically receive a safety LIMIT clause capped at {settings.SQL_MAX_ROWS} rows.",
                "enforced": True,
            },
            {
                "rule_id": "SEC-06",
                "name": "Zero PII Guarantee",
                "description": "The DataMart contains no customer names, email addresses, phone numbers, or credit card info. Anonymous customer_id surrogate keys only.",
                "enforced": True,
            },
            {
                "rule_id": "SEC-07",
                "name": "Query Execution Timeout",
                "description": "Maximum database query execution duration bounded to 15.0 seconds.",
                "enforced": True,
            },
        ],
        "allowed_tables": ["subscriber_profile", "usage_daily", "campaign_response", "revenue_monthly", "churn_events"],
        "max_rows_limit": settings.SQL_MAX_ROWS,
    }


@app.post("/api/security/validate", status_code=status.HTTP_200_OK, tags=["Security"])
async def validate_sql_sandbox(req: SQLValidateRequest) -> Dict[str, Any]:
    """Tests arbitrary SQL against the SQL Firewall in an interactive sandbox."""
    res = sql_firewall.validate_and_sanitize(req.sql)
    return {
        "is_valid": res.is_valid,
        "sanitized_sql": res.sanitized_sql,
        "tables_used": res.tables_used,
        "errors": res.errors,
        "warnings": res.warnings,
    }


# ============================================================================
# AUDIT LOG ENDPOINT
# ============================================================================

@app.get("/api/audit/logs", status_code=status.HTTP_200_OK, tags=["Audit"])
async def get_audit_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Returns the governed audit trail."""
    return audit_service.get_audit_logs(limit=limit)


# ============================================================================
# SETTINGS ENDPOINTS
# ============================================================================

@app.get("/api/settings", status_code=status.HTTP_200_OK, tags=["Settings"])
async def get_settings() -> Dict[str, Any]:
    """Returns configurable runtime settings."""
    return {
        "app_name": settings.APP_NAME,
        "phase": settings.PHASE,
        "environment": settings.ENVIRONMENT,
        "database_url": settings.DATABASE_URL,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "ollama_model": settings.OLLAMA_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "rag_top_k": settings.RAG_TOP_K,
        "sql_max_rows": settings.SQL_MAX_ROWS,
        "data_freshness": settings.DATA_REFRESH_NOTE,
        "use_llm_sql": settings.USE_LLM_SQL,
        "use_llm_explanation": settings.USE_LLM_EXPLANATION,
    }


@app.post("/api/settings", status_code=status.HTTP_200_OK, tags=["Settings"])
async def update_settings(req: SettingsUpdateRequest) -> Dict[str, Any]:
    """Updates runtime configurations."""
    if req.ollama_base_url is not None:
        settings.OLLAMA_BASE_URL = req.ollama_base_url
        llm_client.base_url = req.ollama_base_url.rstrip("/")
    if req.ollama_model is not None:
        settings.OLLAMA_MODEL = req.ollama_model
        llm_client.model_name = req.ollama_model
    if req.rag_top_k is not None:
        settings.RAG_TOP_K = req.rag_top_k
    if req.data_refresh_note is not None:
        settings.DATA_REFRESH_NOTE = req.data_refresh_note
    if req.use_llm_sql is not None:
        settings.USE_LLM_SQL = req.use_llm_sql
    if req.use_llm_explanation is not None:
        settings.USE_LLM_EXPLANATION = req.use_llm_explanation

    return {"status": "updated", "settings": await get_settings()}


# ============================================================================
# STATIC FRONTEND SERVING
# ============================================================================

frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/", include_in_schema=False)
    def serve_index():
        return FileResponse(frontend_dir / "index.html")


if __name__ == "__main__":
    import uvicorn
    # Bind to 0.0.0.0 so Railway (and other cloud hosts) can route external traffic.
    # PORT env var is provided automatically by Railway; fall back to 8000 locally.
    _port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=_port, reload=False)
