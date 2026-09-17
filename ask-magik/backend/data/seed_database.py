"""
Database Initialization & Seeding Script
Ask MAGIK - Phase 1 Foundation

Usage:
    python -m backend.data.seed_database

Performs:
1. SQLite/Postgres database initialization.
2. Schema & table creation (via SQLAlchemy models).
3. Realistic synthetic data generation (10k subscribers, ~1M usage rows, campaigns, revenue, churn).
4. High-performance batch insertion.
5. Verification of row counts.
6. Execution of sanity-check queries.
"""

import sys
import time
from pathlib import Path
from datetime import date
from sqlalchemy import text
from backend.config import settings, BASE_DIR
from backend.database.connection import engine, Base, SessionLocal
from backend.database.models import (
    SubscriberProfile,
    UsageDaily,
    CampaignResponse,
    RevenueMonthly,
    ChurnEvent,
)
from backend.data.generate_data import (
    generate_subscribers,
    generate_churn_events,
    generate_usage_daily,
    generate_campaign_responses,
    generate_revenue_monthly,
)


def seed_database() -> None:
    """Initializes schema and seeds synthetic DataMart data."""
    start_time = time.time()
    print("=" * 60)
    print("Skyline Telecom DataMart Initialization (Ask MAGIK Phase 1)")
    print("=" * 60)
    print(f"Target Database URL: {settings.resolved_database_url}")

    # Ensure target directory exists for SQLite
    if settings.is_sqlite:
        db_path = Path(settings.resolved_database_url.replace("sqlite:///", ""))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # If database file already exists, recreate it cleanly
        if db_path.exists():
            print(f"Recreating existing database at: {db_path}")

    # Optimize SQLite for fast bulk ingestion
    with engine.connect() as conn:
        if settings.is_sqlite:
            conn.execute(text("PRAGMA synchronous = OFF;"))
            conn.execute(text("PRAGMA journal_mode = MEMORY;"))
            conn.execute(text("PRAGMA cache_size = 100000;"))
            conn.commit()

    # Drop and create tables
    print("\nCreating database schema and tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

    # 1. Generate Data
    print("\nGenerating synthetic datasets...")
    t0 = time.time()
    subscribers, sub_lookup = generate_subscribers(num_customers=10000)
    print(f"Generated {len(subscribers):,} subscriber profiles in {time.time() - t0:.2f}s")

    t0 = time.time()
    churn_events, churned_cust_ids = generate_churn_events(subscribers, target_churn_count=1200)
    churn_lookup = {e["customer_id"]: e["churn_date"] for e in churn_events}
    print(f"Generated {len(churn_events):,} churn events in {time.time() - t0:.2f}s")

    t0 = time.time()
    usage_daily = generate_usage_daily(subscribers, churn_lookup)
    print(f"Generated {len(usage_daily):,} daily usage records in {time.time() - t0:.2f}s")

    t0 = time.time()
    campaign_responses = generate_campaign_responses(subscribers, target_count=100000)
    print(f"Generated {len(campaign_responses):,} campaign response records in {time.time() - t0:.2f}s")

    t0 = time.time()
    revenue_monthly = generate_revenue_monthly(subscribers, churn_lookup)
    print(f"Generated {len(revenue_monthly):,} monthly revenue records in {time.time() - t0:.2f}s")

    # 2. Bulk Insert Data
    print("\nInserting data into Skyline DataMart...")
    session = SessionLocal()
    try:
        # Insert subscribers
        t0 = time.time()
        session.bulk_insert_mappings(SubscriberProfile, subscribers)
        session.commit()
        print(f"-> Inserted subscriber_profile ({len(subscribers):,} rows) in {time.time() - t0:.2f}s")

        # Insert churn events
        t0 = time.time()
        session.bulk_insert_mappings(ChurnEvent, churn_events)
        session.commit()
        print(f"-> Inserted churn_events ({len(churn_events):,} rows) in {time.time() - t0:.2f}s")

        # Insert campaign responses in batches
        t0 = time.time()
        BATCH_SIZE = 25000
        for i in range(0, len(campaign_responses), BATCH_SIZE):
            chunk = campaign_responses[i : i + BATCH_SIZE]
            session.bulk_insert_mappings(CampaignResponse, chunk)
            session.commit()
        print(f"-> Inserted campaign_response ({len(campaign_responses):,} rows) in {time.time() - t0:.2f}s")

        # Insert monthly revenues in batches
        t0 = time.time()
        for i in range(0, len(revenue_monthly), BATCH_SIZE):
            chunk = revenue_monthly[i : i + BATCH_SIZE]
            session.bulk_insert_mappings(RevenueMonthly, chunk)
            session.commit()
        print(f"-> Inserted revenue_monthly ({len(revenue_monthly):,} rows) in {time.time() - t0:.2f}s")

        # Insert daily usage in batches (1,000,000 rows)
        t0 = time.time()
        USAGE_BATCH_SIZE = 50000
        total_usage = len(usage_daily)
        for i in range(0, total_usage, USAGE_BATCH_SIZE):
            chunk = usage_daily[i : i + USAGE_BATCH_SIZE]
            session.bulk_insert_mappings(UsageDaily, chunk)
            session.commit()
            print(f"   Usage insertion progress: {min(i + USAGE_BATCH_SIZE, total_usage):,} / {total_usage:,} rows...", end="\r")
        print(f"\n-> Inserted usage_daily ({total_usage:,} rows) in {time.time() - t0:.2f}s")

    except Exception as e:
        session.rollback()
        print(f"\nERROR during insertion: {e}")
        raise e
    finally:
        session.close()

    # Reset SQLite PRAGMAs back to safe defaults
    with engine.connect() as conn:
        if settings.is_sqlite:
            conn.execute(text("PRAGMA synchronous = NORMAL;"))
            conn.execute(text("PRAGMA journal_mode = WAL;"))
            conn.commit()

    # 3. Print Row Counts
    print("\n" + "=" * 60)
    print("Skyline DataMart initialized.")
    print("=" * 60)
    with engine.connect() as conn:
        for table_name in [
            "subscriber_profile",
            "usage_daily",
            "campaign_response",
            "revenue_monthly",
            "churn_events",
        ]:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            print(f"{table_name}: {count:,} rows")
    print("Database ready.\n")

    # 4. Run Sanity-Check Queries
    print("-" * 60)
    print("Running Sanity-Check Queries:")
    print("-" * 60)
    with engine.connect() as conn:
        # Check 1: Active vs Churned
        res = conn.execute(
            text("SELECT status, COUNT(*) FROM subscriber_profile GROUP BY status")
        ).fetchall()
        print(f"1. Subscriber status breakdown: {dict(res)}")

        # Check 2: Average Data MB by Segment
        res = conn.execute(
            text("""
                SELECT s.segment, ROUND(AVG(u.data_mb), 2) as avg_data_mb
                FROM subscriber_profile s
                JOIN usage_daily u ON s.customer_id = u.customer_id
                GROUP BY s.segment
                ORDER BY avg_data_mb DESC
            """)
        ).fetchall()
        print(f"2. Avg Daily Data MB by Segment: {res}")

        # Check 3: Top Churn Reasons
        res = conn.execute(
            text("""
                SELECT churn_reason, COUNT(*) as count
                FROM churn_events
                GROUP BY churn_reason
                ORDER BY count DESC
                LIMIT 3
            """)
        ).fetchall()
        print(f"3. Top 3 Churn Reasons: {res}")

        # Check 4: Ramadan Campaign Responses by Year
        res = conn.execute(
            text("""
                SELECT SUBSTR(campaign_date, 1, 4) as year, response, COUNT(*) as count
                FROM campaign_response
                WHERE campaign_name = 'Ramadan Data Bundle'
                GROUP BY year, response
                ORDER BY year, response
            """)
        ).fetchall()
        print(f"4. Ramadan Campaign Breakdown by Year: {res}")

    total_elapsed = time.time() - start_time
    print("-" * 60)
    print(f"Initialization complete in {total_elapsed:.2f} seconds.")
    print("=" * 60)


if __name__ == "__main__":
    seed_database()
