# Ask MAGIK (Phase 1: Foundation & Synthetic DataMart)

> **Telecom DataMart & AI Grounding Foundation for Skyline Telecom**  
> *Built for Industry Case Competition Prototype*

---

## 1. What is Ask MAGIK?

**Ask MAGIK** is an AI-driven natural language analytics platform designed for **Skyline Telecom**, enabling business stakeholders, executives, and commercial analysts to ask plain-English questions about subscriber churn, network usage trends, regional campaign efficacy, and revenue performance—getting validated SQL queries and evidence-grounded insights in seconds.

### Target End-State Architecture (Phase 2):
```
User plain-English question
           ↓
          RAG (Glossary + Schema + Business Rules + Examples)
           ↓
         Llama (Code generation model)
           ↓
    SQL Generation
           ↓
    SQL Validation (AST & Read-only enforcement)
           ↓
Synthetic Skyline DataMart (SQLite / PostgreSQL)
           ↓
  Answer + Analytical Evidence
```

> **IMPORTANT SCOPE NOTICE**:  
> In accordance with Phase 1 requirements, **LLM/RAG chatbot components (Llama, Ollama, Chroma, LangChain, embeddings) are NOT included in this release**. Phase 1 establishes the clean, production-grade foundation on which Phase 2 AI layers will seamlessly build.

---

## 2. What Phase 1 Delivers

Phase 1 provides a fully operational, test-verified foundation:
1. **Dialect-Agnostic Database Layer**: SQLAlchemy 2.0 ORM models and connection abstraction (readily switchable from SQLite to PostgreSQL via `.env`).
2. **Synthetic Skyline DataMart**: 5 core tables with ~10,000 subscribers, ~1,000,000 daily usage records, ~100,000 campaign contacts, ~80,000 monthly revenue records, and ~1,200 churn events.
3. **Realistic Probabilistic Behaviors**: Natural data variation calibrated to reflect realistic telecom dynamics (e.g. Small Business usage multiples, high-value data consumption, Q3 early tenure attrition in digital channels, West prepaid churn spikes).
4. **Comprehensive Business Glossary**: 17 formal telecom definitions detailing business meaning, data lineage, key fields, and calculation rules.
5. **Business & Analytical Rules**: Standardized formulas, counting semantics (`COUNT(DISTINCT customer_id)`), period comparability, and privacy guarantees (zero PII).
6. **Schema Documentation**: Granular per-table specifications and relational join guidelines (`relationships.md`).
7. **Validated Question & SQL Examples**: 15 complete, tested SQL templates serving as few-shot training/grounding for future RAG retrieval.
8. **Automated Data Quality & System Tests**: 14 automated tests verifying referential integrity, constraints, non-negativity, and SQL query execution.
9. **Minimal FastAPI Backend**: Asynchronous web service with `GET /health` operational endpoint.

---

## 3. Database Architecture

The Skyline DataMart follows a Star-Snowflake dimensional structure centered on `subscriber_profile`:

```
                 +----------------------+
                 |  subscriber_profile  |  (10,000 rows)
                 |  PK: customer_id     |
                 +----------+-----------+
                            |
       +--------------------+--------------------+--------------------+
       |                    |                    |                    |
       v                    v                    v                    v
+--------------+   +-------------------+   +-----------------+   +--------------+
| usage_daily  |   | campaign_response |   | revenue_monthly |   | churn_events |
| ~1,000,000   |   | ~100,000 rows     |   | ~80,000 rows    |   | ~1,200 rows  |
| rows         |   | FK: customer_id   |   | FK: customer_id |   | FK: cust_id  |
+--------------+   +-------------------+   +-----------------+   +--------------+
```

### Table Summary:
- **`subscriber_profile`**: Customer demographics, plan type (`FlexMax 199`, `UltraData 399`, etc.), region (`North`, `South`, `East`, `West`, `Central`), tenure, customer segment, customer type (`Consumer`, `Small Business`), and status (`Active`, `Churned`).
- **`usage_daily`**: Daily consumption metrics (`voice_minutes`, `data_mb`, `sms_count`) across a 100-day historical window.
- **`campaign_response`**: Marketing campaigns (`Ramadan Data Bundle`, `Summer Saver`, etc.), exposure date, campaign type, offer value, and customer response (`Responded`, `Not Responded`).
- **`revenue_monthly`**: Monthly financial breakdown (`billed_revenue`, `collected_revenue`) over 8 billing cycles.
- **`churn_events`**: Disconnection events capturing `churn_date`, `churn_reason` (`Price`, `Poor Service`, etc.), and `churn_channel` (`Retail`, `Digital`, etc.).

---

## 4. Setup & Installation

### Prerequisites
- Python 3.11+
- Virtual environment or conda environment

### 1. Clone or Open Project
```powershell
cd ask-magik
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Configure Environment
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Default SQLite database path:
```ini
DATABASE_URL=sqlite:///./data/skyline.db
ENVIRONMENT=development
APP_NAME=Ask MAGIK
PHASE=1
```

---

## 5. Initializing the Database

To generate all synthetic data and populate the database, run:

```powershell
python -m backend.data.seed_database
```

### Expected Output:
```
============================================================
Skyline Telecom DataMart Initialization (Ask MAGIK Phase 1)
============================================================
Target Database URL: sqlite:///.../data/skyline.db

Creating database schema and tables...
Tables created successfully.

Generating synthetic datasets...
Generated 10,000 subscriber profiles
Generated 1,200 churn events
Generated ~950,000 daily usage records
Generated 100,000 campaign response records
Generated ~78,000 monthly revenue records

Inserting data into Skyline DataMart...
-> Inserted subscriber_profile (10,000 rows)
-> Inserted churn_events (1,200 rows)
-> Inserted campaign_response (100,000 rows)
-> Inserted revenue_monthly (78,789 rows)
-> Inserted usage_daily (945,278 rows)

============================================================
Skyline DataMart initialized.
============================================================
subscriber_profile: 10,000 rows
usage_daily: 945,278 rows
campaign_response: 100,000 rows
revenue_monthly: 78,789 rows
churn_events: 1,200 rows
Database ready.
```

---

## 6. Running the FastAPI Application

Start the FastAPI application with Uvicorn:

```powershell
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Check the Health Endpoint:
Open your browser or run curl:
```powershell
curl http://127.0.0.1:8000/health
```

**Response:**
```json
{
  "status": "ok",
  "service": "Ask MAGIK",
  "phase": 1
}
```

Interactive OpenAPI docs: `http://127.0.0.1:8000/docs`.

---

## 7. Running the Test Suite

Execute pytest across the database and data quality test suites:

```powershell
pytest -v tests/
```

### Test Coverage:
- `test_database.py`: Verifies engine connectivity, schema table existence, populated row counts, and FastAPI `/health` endpoint response.
- `test_data_quality.py`: Verifies `customer_id` uniqueness, foreign key referential integrity, domain constraints (regions, plans, segments), non-negativity of revenue and usage, chronological consistency of churn events, and executes **all 15 validated example SQL queries** against the live SQLite DataMart.

---

## 8. Five Core Analytical Demo Questions & Queries

The DataMart is calibrated so the following 5 analytical queries return actionable, realistic results:

### Query 1: Western Region Prepaid Customer Loss Last Month
```sql
SELECT 
    s.plan, 
    COUNT(DISTINCT c.customer_id) AS customer_loss
FROM churn_events c
JOIN subscriber_profile s ON c.customer_id = s.customer_id
WHERE s.region = 'West'
  AND s.plan IN ('FlexMax 199', 'FlexMax 299', 'DataPlus 249', 'SmartTalk 199')
  AND c.churn_date >= '2026-08-01' AND c.churn_date <= '2026-08-31'
GROUP BY s.plan
ORDER BY customer_loss DESC;
```

### Query 2: Churned Customers by Region
```sql
SELECT 
    s.region, 
    COUNT(DISTINCT c.customer_id) AS churned_customers
FROM churn_events c
JOIN subscriber_profile s ON c.customer_id = s.customer_id
GROUP BY s.region
ORDER BY churned_customers DESC;
```

### Query 3: Campaign with Highest Response Rate
```sql
SELECT 
    campaign_name, 
    campaign_type,
    COUNT(*) AS total_exposures,
    COUNT(CASE WHEN response = 'Responded' THEN 1 END) AS responses,
    ROUND(COUNT(CASE WHEN response = 'Responded' THEN 1 END) * 100.0 / COUNT(*), 2) AS response_rate_pct
FROM campaign_response
GROUP BY campaign_name, campaign_type
ORDER BY response_rate_pct DESC;
```

### Query 4: Customer Segment with Highest Average Data Usage
```sql
SELECT 
    s.segment, 
    ROUND(AVG(u.data_mb), 2) AS avg_daily_data_mb,
    ROUND(AVG(u.voice_minutes), 2) AS avg_daily_voice_minutes
FROM subscriber_profile s
JOIN usage_daily u ON s.customer_id = u.customer_id
GROUP BY s.segment
ORDER BY avg_daily_data_mb DESC;
```

### Query 5: Monthly Trend in Collected Revenue
```sql
SELECT 
    revenue_month, 
    ROUND(SUM(billed_revenue), 2) AS total_billed, 
    ROUND(SUM(collected_revenue), 2) AS total_collected,
    ROUND(SUM(collected_revenue) * 100.0 / SUM(billed_revenue), 2) AS collection_efficiency_pct
FROM revenue_monthly
GROUP BY revenue_month
ORDER BY revenue_month ASC;
```

---

## 9. Phase 2 Roadmap

The Ask MAGIK Phase 2 expansion will introduce:
1. **RAG Knowledge Ingestion**: Vector embedding of the Business Glossary, Schema Docs, Business Rules, and Validated Examples into ChromaDB using sentence-transformers.
2. **LLM Integration**: Local/self-hosted Llama-3 (via Ollama) or remote inference.
3. **Few-Shot SQL Generator**: RAG-augmented prompt orchestrator assembling schema snippets and golden question-SQL pairs.
4. **SQL Safety Validator**: Abstract Syntax Tree (AST) parser preventing write mutations, verifying table/column permissions, and asserting join safety.
5. **Interactive UI**: Web interface showing plain-English questions, generated SQL, visual data charts, and business reasoning evidence.
